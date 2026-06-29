"""
QSign Server for a multi-party quantum signature protocol using SimulaQron.

This module coordinates the three executives (CEO, CFO, CLO), prepares
and distributes quantum states, performs teleportation-based exchange,
collects phase information, and determines whether a contract is signed.
"""

import asyncio
from asyncio import StreamReader, StreamWriter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import sys
import numpy as np
from netqasm.runtime.settings import set_simulator
set_simulator("simulaqron")
from netqasm.sdk.external import NetQASMConnection 
from netqasm.sdk import EPRSocket, Qubit                 
from simulaqron.general.host_config import SocketsConfig
from simulaqron.sdk.protocol import SimulaQronClassicalServer
from simulaqron.settings import network_config, simulaqron_settings
from simulaqron.settings.network_config import NodeConfigType
from helper_theoretical_prob import  possibilities

participants = ["CEO", "CFO", "CLO"]
global A, B, C, P, NUM_QUBITS
A = 6
B = 1
C = 1 
P = 5  # Parameters defining polynomial

@dataclass
class QSignContext:
    writers: dict[str, StreamWriter] = field(default_factory=dict)
    readers: dict[str, StreamReader] = field(default_factory=dict)
    all_connected: asyncio.Event = field(default_factory=asyncio.Event)
    protocol_task: Optional[asyncio.Task] = None
    vault: dict = field(default_factory=dict)
    all_phases: dict = field(default_factory=dict)


def get_point(x):
    """
    Evaluate the secret-sharing polynomial at a given point.

    Args:
        x : int 
        Point at which to evaluate the polynomial.

    Returns:
        y: int
        Polynomial value at x.
    """
    y = A + B*x + C*x**2
    return y


def gen_random_phase():
    """
    Generate a random phase from the allowed set.

    Returns:
        phi: float
        Random phase in multiples of π.
    """
    phi = np.random.choice([0, 0.5, 1, 1.5])
    return phi


async def handle_state_preparation(conn, ctx, num_request):
    """
    Prepare the initial quantum states with the secret and random phase.

    Args:
        conn : NetQASMConnection
            Quantum connection used to create qubits.
        ctx : QSignContext
            QSign context storing protocol data.
        num_request : int
            Identifier for the current signing request.

    Returns:
        None.
    """
    s = get_point(0)
    secret = -2*np.pi*s / P
    phi = gen_random_phase()
    ctx.all_phases['QSign'] = phi
    
    print(f'QSign: Using polynomial f(x) = {A} + {B}x + {C}x^2 mod {P}')
    print(f'QSign: Secret = {s}')
    print(f'QSign: Chose random phase φ = {phi}π')
    
    q_list = []
    for i in range(NUM_QUBITS):
        # Preparing qubit
        q = Qubit(conn)
        q.H()

        # Adding phases
        q.rot_Z(angle=secret)
        q.rot_Z(angle=phi*np.pi)
        conn.flush()
        q_list.append(q)
    
    ctx.vault[num_request] = q_list
    print(f"QSign: {NUM_QUBITS} States prepared for teleportation")
    

async def handle_teleportation(conn, epr_socket, ctx, node_name, num_request):
    """
    Teleport the quantum state to a participant and receive the signed state back.

    Args:
        conn : NetQASMConnection
            Quantum connection used for teleportation operations.
        epr_socket : EPRSocket
            EPR socket shared with the participant.
        ctx : QSignContext
            QSign context storing protocol data.
        node_name : str
            Name of the participant involved in the teleportation.
        num_request : int
            Identifier of the current signing request.

    Returns:
        None.
    """
    print(f'--------------------{node_name}--------------------')
    # Stream selection
    writer = ctx.writers[node_name]
    reader =  ctx.readers[node_name]

    # Calculate point
    x_client = participants.index(node_name) + 1
    y_client = get_point(x_client)
    writer.write(f'{x_client}:{y_client}:{P}:{NUM_QUBITS}\n'.encode())
    #------------------------------------------------------------------
    epr_list = []
    m1_list = []
    m2_list = []

    states = ctx.vault[num_request]

    for i in range(NUM_QUBITS):
        # Create EPR pairs
        epr = epr_socket.create_keep()[0]  #Share EPR pairs with the Client
        conn.flush()
        epr_list.append(epr)

        # Bell measurement
        states[i].cnot(epr_list[i])
        states[i].H()
        m1 = states[i].measure()
        m2 = epr_list[i].measure()
        conn.flush()

        # Save measurements
        m1, m2 = int(m1), int(m2)
        m1_list.append(m1)
        m2_list.append(m2)
        
    msg1 = "".join(map(str, m1_list))
    msg2 = "".join(map(str, m2_list))
    writer.write(f"{msg1}:{msg2}\n".encode())  #Send corrections
    await writer.drain()
    print(f"QSign: Sent corrections to {node_name}")
    #------------------------------------------------------------------
    # Receive EPR pairs
    q_list = []
    for i in range(NUM_QUBITS):
        q = epr_socket.recv_keep()[0]   
        conn.flush()
        q_list.append(q)

   # Receive corrections
    data = await reader.readline()
    msg = data.decode().strip()
    m1, m2 = msg.split(":", 1)
    m1 = [int(i) for i in m1]
    m2 = [int(i) for i in m2]

    # Apply corrections
    for i in range(NUM_QUBITS):
        if m2[i] == 1:  # Apply corrections
            q_list[i].X()

        if m1[i] == 1:
            q_list[i].Z()
    conn.flush()

    ctx.vault[num_request] = q_list
    print(f"QSign: Received corrections from {node_name}")
    print(f"QSign: {node_name} signature procedure done")
    

async def handle_outcome(conn, ctx, num_request):
    """
    Collect participants' phases, measure the final state, and determine the signing outcome.

    Args:
        conn : NetQASMConnection
            Quantum connection used to perform the final measurements.
        ctx : QSignContext
            QSign context storing protocol data.
        num_request : int
            Identifier of the current signing request.

    Returns:
        None.
    """
    print(f'-----------------MEASURING-----------------')
    # Requesting phase
    for node in participants:
        writer = ctx.writers[node]
        writer.write(b"PHASE?\n")
        await writer.drain()

    # Receiving phase
    print('QSign: Receiving phase from participants...')
    for node in participants:
        reader = ctx.readers[node]
        phase = float((await reader.readline()).decode().strip())
        ctx.all_phases[node] = phase

    # Calculating total phase
    phi_sum = ctx.all_phases['QSign']
    for node_name in participants:
        phi_sum += ctx.all_phases[node_name]
    state_phase = (phi_sum*np.pi) % (2*np.pi)

    states = ctx.vault[num_request] 

    if state_phase == 0 or state_phase == np.pi:
            print(f'QSign: Expected phase sum (mod 2π) = {state_phase/np.pi}π -> measuring in X basis')
            if state_phase == 0:
                expectation = 0
                print('QSign: Contract signed if all measurements = 0 (Projection on |+> state)')
            else:
                expectation = 1
                print('QSign: Contract signed if all measurements = 1 (Projection on |-> state)')
    if state_phase == np.pi/2 or state_phase == 3*np.pi/2:
            print(f'QSign: Expected phase sum (mod 2π) = {state_phase/np.pi}π -> measuring in Y basis')
            if state_phase == np.pi/2:
                expectation = 0
                print('QSign: Contract signed if all measurements = 0 (Projection on |+i> state)')
            else:
                expectation = 1
                print('QSign: Contract signed if all measurements = 1 (Projection on |-i> state)')

    # Perform measurements    
    measurements = []
    for state in states:
        if state_phase == 0 or state_phase == np.pi:
            state.H()
            m = state.measure()
            conn.flush()
            m = int(m)
        if state_phase == np.pi/2 or state_phase == 3*np.pi/2:
            state.K()
            m = state.measure()
            conn.flush()
            m = int(m)
        measurements.append(m)
    
    print(f"QSign: Measured 0: {measurements.count(0)} times")
    print(f"QSign: Measured 1: {measurements.count(1)} times") 
    print(f"Probability of correct projection: {(measurements.count(expectation)*100/NUM_QUBITS):.1f}%")

    # Final verdict
    if sum(measurements)/NUM_QUBITS == expectation:
        print('QSign: All parties agree -> Contract signed')
        verdict = "SIGN"
    else:
        print('QSign: At least one member disagrees -> Contract not signed')
        verdict = "NO_SIGN"
        possibilities(state_phase, A, B, C, P)

    for node in participants:
        writer = ctx.writers[node]
        writer.write(f"{verdict}\n".encode())
        await writer.drain()
        
    conn.close()


async def run_protocol(ctx: QSignContext) -> None:
    """
    Execute the complete QSign signing protocol.

    Args:
        ctx : QSignContext
            QSign context storing protocol data.

    Returns:
        None.
    """
    await ctx.all_connected.wait()
    print("QSign: CEO, CFO and CLO connected", flush=True)

    ceo_socket = EPRSocket("CEO")
    cfo_socket = EPRSocket("CFO")
    clo_socket = EPRSocket("CLO")
    epr_sockets = [ceo_socket, cfo_socket, clo_socket]
    conn = NetQASMConnection("QSign", epr_sockets=epr_sockets, max_qubits=1000)

    num_request = np.random.randint(1,1000)  # Assigning a number to this request

    await handle_state_preparation(conn, ctx, num_request)
    await handle_teleportation(conn, epr_sockets[0], ctx, "CEO", num_request)
    await handle_teleportation(conn, epr_sockets[1], ctx, "CFO", num_request)
    await handle_teleportation(conn, epr_sockets[2], ctx, "CLO", num_request)
    await handle_outcome(conn, ctx, num_request)
    

async def handle_client(ctx, reader, writer):
    """
    Register a participant and start the signing protocol once all participants are connected.

    Args:
        ctx : QSignContext
            QSign context storing protocol data.
        reader : StreamReader
            Stream used to receive messages from the participant.
        writer : StreamWriter
            Stream used to send messages to the participant.

    Returns:
        None.
    """
    data = await reader.read(255)
    if not data:
        return

    msg = data.decode().strip()
    if msg.endswith(":SIGN"):
        party = msg.split(":", maxsplit=1)[0]

        ctx.writers[party] = writer
        ctx.readers[party] = reader

        if set(ctx.writers) == {"CEO", "CFO", "CLO"}:
            ctx.all_connected.set()

            if ctx.protocol_task is None:
                ctx.protocol_task = asyncio.create_task(run_protocol(ctx))
    return

async def run_QSign(reader: StreamReader, writer: StreamWriter) -> None:
    """
    Entry point for the QSign server client handler.

    Args:
        reader : StreamReader
            Stream used to receive incoming client messages.
        writer : StreamWriter
            Stream used to send outgoing messages to the client.

    Returns:
        None.
    """
    await handle_client(run_QSign.ctx, reader, writer)


def _parse_argv(argv: list[str]):
    """
    Parse and validate command-line argument for number of qubits.

    Args:
        argv : list[str]
            Command-line argument list (sys.argv-style input).

    Returns:
        int: Number of qubits if valid (2 <= value <=100).

    Raises:
        ValueError: If argument format is incorrect.
        SystemExit: If argument is missing or out of valid range.
    """
    if len(argv) != 2:
        print("Usage: python3 QSign.py <int:NUM_QUBITS>")
        sys.exit(1)
    try:
        argv = int(argv[1])
    except:
        raise ValueError("Usage: python3 QSign.py <int:NUM_QUBITS>")
    
    if argv <= 100 and argv > 1:
        return int(argv)
    else:
        print("Pick a number in range [2, 100] " \
        "Usage: python3 QSign.py <int:NUM_QUBITS>")
        sys.exit(1)


if __name__ == "__main__":
    NUM_QUBITS = _parse_argv(sys.argv)

    _here = Path(__file__).parent
    simulaqron_settings.read_from_file(_here / "simulaqron_settings.json")
    network_config.read_from_file(_here / "simulaqron_network.json")

    run_QSign.ctx = QSignContext()

    sockets_config = SocketsConfig(network_config, "default", NodeConfigType.APP)
    server = SimulaQronClassicalServer(sockets_config, "QSign")
    server.register_client_handler(run_QSign)
    print("QSign: starting server...", flush=True)
    server.start_serving()
