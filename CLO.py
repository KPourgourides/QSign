"""
CLO Client for a multi-party quantum signature protocol using SimulaQron.

This module connects the CLO executive to the QSign server, 
receives quantum states via EPR-based teleportation, applies 
corrections, adds a participant-specific phase, and returns 
the processed quantum state back to the server to determine 
whether the contract is signed.
"""

from asyncio import StreamReader, StreamWriter
from pathlib import Path
import numpy as np
import sys
from netqasm.runtime.settings import set_simulator
set_simulator("simulaqron")
from netqasm.sdk.external import NetQASMConnection  
from netqasm.sdk import Qubit, EPRSocket            
from simulaqron.general.host_config import SocketsConfig
from simulaqron.settings import network_config, simulaqron_settings
from simulaqron.settings.network_config import NodeConfigType
from simulaqron.sdk.protocol import SimulaQronClassicalClient


global SIGN, NUM_QUBITS


async def run_client(reader: StreamReader, writer: StreamWriter) -> None:
    """
    Establishes a NetQASM connection to the QSign server and delegates
    execution to the signature request protocol.

    Args:
        reader : StreamReader
            Async stream reader for incoming messages.
        writer : StreamWriter
            Async stream writer for outgoing messages.

    Returns:
        None
    """
    print(f"CLO: Connection succesful", flush=True)

    epr_socket = EPRSocket("QSign")
    conn = NetQASMConnection("CLO", epr_sockets=[epr_socket], max_qubits=1000)
    await run_signature_request(reader, writer, conn, epr_socket)


async def run_signature_request(reader: StreamReader, writer: StreamWriter,
                   conn: NetQASMConnection, epr_socket: EPRSocket) -> None:
    """
    Receive the quantum state from QSign and teleport the signed state back.

    Args:
        reader : StreamReader
            Async stream reader for incoming messages from QSign.
        writer : StreamWriter
            Async stream writer for sending messages to QSign.
        conn : NetQASMConnection
            Active NetQASM quantum connection
        epr_socket : EPRSocket
            Socket used to create and receive EPR pairs with QSign.

    Returns:
        None
    """
    writer.write(b"CLO:SIGN\n")  # Signature request

    # Receive point
    point_p = await reader.readline() 
    x, y, p, NUM_QUBITS = point_p.decode().strip().split(':', 3)
    x, y, p, NUM_QUBITS = int(x), int(y), int(p), int(NUM_QUBITS)
    print(f"CLO: Received point x={x}, f(x)={y} from QSign")

    # Receive EPR pairs 
    qlist = []
    for i in range(NUM_QUBITS):
        q = epr_socket.recv_keep()[0] 
        conn.flush()
        qlist.append(q)
    
    # Receive corrections
    data = await reader.readline()
    msg = data.decode().strip()
    m1, m2 = msg.split(":", 1)
    m1 = [int(i) for i in m1]
    m2 = [int(i) for i in m2]

    # Apply corrections
    for i in range(NUM_QUBITS):
        if m2[i] == 1: 
            qlist[i].X()

        if m1[i] == 1:
            qlist[i].Z()
        conn.flush()
    
    print(f"CLO: Received corrections from QSign")
    #----------------------------------------------
    # Adding secret and random phases
    c = (y*(2/(2-x))*((1)/(1-x))) % p
    print(f'CLO: Calculated c={c}')
    phase_secret = 2*np.pi*c/p
    phase_random = np.random.choice([0, 0.5, 1, 1.5])
    if SIGN:
        print("CLO: Signing the contract...")
    else:
        print("CLO: Decided not to sign")

    for i in range(NUM_QUBITS):
        if SIGN:
            qlist[i].rot_Z(angle=phase_secret) # Applies secret phase if client wants to sign
        qlist[i].rot_Z(angle=phase_random*np.pi)
            
    #----------------------------------------------
    epr_list = []
    m1_list = []
    m2_list = []

    for i in range(NUM_QUBITS):
        epr = epr_socket.create_keep()[0]  # Share EPR pairs with QSign
        conn.flush()
        epr_list.append(epr)

        # Bell measurement
        qlist[i].cnot(epr_list[i])
        qlist[i].H()
        m1 = qlist[i].measure()
        m2 = epr_list[i].measure()
        conn.flush()

        # Save measurements
        m1, m2 = int(m1), int(m2)
        m1_list.append(m1)
        m2_list.append(m2)
        
    msg1 = "".join(map(str, m1_list))
    msg2 = "".join(map(str, m2_list))

    writer.write(f"{msg1}:{msg2}\n".encode()) # Send corrections
    await writer.drain()
    print(f"CLO: Sent corrections to QSign")

    # Phase request from QSign
    request = (await reader.readline()).decode().strip()
    if request == "PHASE?":
        writer.write(f"{phase_random}\n".encode())
        await writer.drain()
    print(f"CLO: Sent chosen phase φ={phase_random}π to QSign")

    # Receive final verdict
    verdict = (await reader.readline()).decode().strip()
    if verdict.startswith("NO"):
        print('CLO: Received final decision -> Contract not signed!')
    else:
        print('CLO: Received final decision -> Contract signed!')
    conn.close()
    
def _parse_argv(argv: list[str]):
    """
    Parses command-line arguments to determine CLO signing decision.

    Args:
        argv : list[str]
            Command-line argument list.

    Returns:
        SIGN : bool
            True if the CLO chooses to sign the contract, False otherwise.
    """
    if len(argv) != 2:
        print("Usage: python3 CLO.py SIGN or NO_SIGN")
        sys.exit(1)

    msg = argv[1]
    if msg=='SIGN':
        return True
    
    elif msg=='NO_SIGN':
        return False
    else:
        print("Arguments could not be correctly parsed." \
        "Usage: python3 CLO.py SIGN or NO_SIGN")
        sys.exit(1)

if __name__ == "__main__":
    SIGN = _parse_argv(sys.argv)
    _here = Path(__file__).parent
    simulaqron_settings.read_from_file(_here / "simulaqron_settings.json")
    network_config.read_from_file(_here / "simulaqron_network.json")
    sockets_config = SocketsConfig(network_config, "default", NodeConfigType.APP)

    client = SimulaQronClassicalClient(sockets_config)
    print(f"CLO: Connecting to QSign...", flush=True)
    client.run_client("QSign", run_client)
