# *QSign*

>[!NOTE]
> Scroll past the theoretical description of the protocol to receive instructions on how to run the code!
##
### A business idea from **Kyproula Mitsidi & Konstantinos Pourgourides**
### Part of the course CS4090 Quantum Communication & Cryptography @ TU Delft
##
### What is the problem we aim to solve?

Imagine a scenario where we have 3 high-ranking executives in a company (CEO, CFO, CLO), and they all have to sign a particular document to approve a decision within the company. In some instances, a subset of the executives might want to pass a decision for their own personal benefit, ignoring the disagreement of the others. In a classical world, the corrupted executives can take a look at who did not sign the document, commit signature forgery and make it appear such that all executives signed the document.

We aim to create a service-type solution to other companies so that we can securely ensure whether everyone has truthfully signed the document or not, while also providing decision privacy and security against forgery among the executives, based on some concepts from quantum information.

##

# The protocol
##

QSign begins by choosing a polynomial of n-1 degree, where n is the number of executives participating, in this case 3.

$$ f(x) = s + \alpha x + \beta x^2 \mod p$$

where $p$ is a prime number, and the intercept of the polynomial $s=f(0)$ is referred to as the "secret". We proceed by randomly choosing a random phase 

$$ \phi \in \bf{\Phi} = \{0, \frac{\pi}{2},\pi,\frac{3\pi}{2}\} $$

Then, we apply a gate with this randomly chosen phase as well as an additional phase based on the polynomial secret on a qubit which is initially in the $\ket{+}$ state

$$\ket{\psi} =R_z\left(\phi - \frac{2\pi s}{p} \right)\ket{+} = \frac{\ket{0} + e^{i(\phi - \frac{2\pi s}{p})}\ket{1}}{\sqrt{2}} $$

We proceed by publicly announcing the prime number $p$, as well as 3 interpolation points $\{x_1,x_2,x_3\} = \{1,2,3\}$, each one belonging to an executive. Then, we privately communicate to the executives an evalutation of the polynomial at their corresponding interpolation point (for example, executive $i$ receives f($x_i$) ).

##

At this point, we teleport $\ket{\psi}$ to the executive with the first interpolation point $x_1$ by making an EPR pair with them and sending them the corrections over a classical channel. The executive randomly picks a phase $\phi_1 \in \mathbf{\Phi}$, and computes the Lagrange coefficient $c_1$. The calculation of this coefficient will become apparent later in the protocol

$$c_1 = \left[f(x_1)\prod_{i>0, i\neq 1}^{3}\frac{x_i}{x_i-x_1}\right]\mod p $$

Continuing, the executive applies the rotation below

$$\ket{\psi'} = R_z\left(\phi_1 + \frac{2\pi c_1}{p}\right)\ket{\psi} $$

The second phase containing $c_1$ is essentially the **signature** of the executive. The executive then teleports this state back to QSign, and this sequence is repeated for the rest of the executives, building on the same state. After everybody has cast their votes, the privately communicate with QSign to give their randomly chosen phase $\phi_i$. At the end, QSign holds this state

$$     \ket{\psi}_{\text{final}} = \frac{\ket{0} + 
    e^{i\left[\phi + \sum_i\phi_i + \frac{2\pi}{p}(\sum_ic_i - s) \right]}
    \ket{1}}{\sqrt{2}} $$

The Lagrange coefficient contributions from all the executives cancel out with the secret of the polynomial 

$$f(0) = s = \sum_j \left[f(x_j)\prod_{i>0, i\neq j}^{3}\frac{x_i}{x_i-x_j}\right]\mod p = \sum_j c_j $$

and we are left with

$$  \ket{\psi}_{\text{final}} = \frac{\ket{0} + 
    e^{i\left[\phi + \sum_i\phi_i \right]}
    \ket{1}}{\sqrt{2}} $$

We recognize that $\left(\phi + \sum_i \phi_i\right)\mod 2\pi \in \mathbf{\Phi}$, and thus we have 4 distinct possibilities for the final state (remember, QSign knows the value of all randomly chosen phases of the executives). Depending on the final state, QSign measures it in the appropriate basis, expecting a projection on the corresponding eigenbasis **if everyone signed the document**.

$$ \phi + \sum_i\phi_i = 0 \rightarrow \ket{\psi}_{\text{final}} = \frac{\ket{0}+\ket{1}}{\sqrt{2}} \rightarrow \text{Measure in X basis, will project on }\ket{+}\\ $$

$$ \phi + \sum_i\phi_i = \frac{\pi}{2} \rightarrow \ket{\psi}_{\text{final}} = \frac{\ket{0}+i\ket{1}}{\sqrt{2}} \rightarrow \text{Measure in Y basis, will project on }\ket{i}\\ $$

$$ \phi + \sum_i\phi_i = \pi \rightarrow \ket{\psi}_{\text{final}} = \frac{\ket{0}-\ket{1}}{\sqrt{2}} \rightarrow \text{Measure in X basis, will project on }\ket{-}\\ $$

$$ \phi + \sum_i\phi_i = \frac{3\pi}{2} \rightarrow \ket{\psi}_{\text{final}} = \frac{\ket{0}-i\ket{1}}{\sqrt{2}} \rightarrow \text{Measure in Y basis, will project on }\ket{-i}\\ $$

By inspecting the final result, we can know whether everyone has truthfully signed the document or not.

## What if someone doesn't sign?

If executive $i$ doesn't sign the document, they essentially don't apply the rotation $R_z\left(\frac{2\pi c_i}{p} \right)$, which results in the non-cancellation of the polynomial secret and the Lagrange coefficient contributions in $\ket{\psi}_{\text{final}}$. Instead, QSign ends up with a final state of this form

$$ \ket{\psi}_{\text{final}} = \frac{\ket{0}+e^{i\chi}\ket{1}}{\sqrt{2}}$$

Where $\chi$ depends on $\left(\phi + \sum_i \phi_i\right)$, the structure of the polynomial as well as the combination of executives who did not sign the document (e.g.: only CEO, CFO + CLO, etc.). The interesting thing is that this state still has a non-zero probability of being projected onto the state we would expect in the case everyone signed, fooling us into thinking that this happened. For example, for the 4 different cases for $\left(\phi + \sum_i \phi_i\right)$, we measure in the appropriate basis and expect that we will project the state to corresponding eigenstate. The probability of this happening for the different cases is

$$
P\left(\ket{\psi}_{\text{final}} \to \ket{+}\right) = \cos^2\left(\frac{\chi}{2}\right) \quad \left(\phi + \sum_i \phi_i = 0\right) $$

$$ P\left(\ket{\psi}_{\text{final}} \to \ket{i}\right) = \frac{1}{2}(1-\sin(\chi)) \quad \left(\phi + \sum_i \phi_i = \frac{\pi}{2} \right) $$

$$ P\left(\ket{\psi}_{\text{final}} \to \ket{-}\right) = \sin^2\left(\frac{\chi}{2}\right) \quad \left(\phi + \sum_i \phi_i = \pi\right) $$

$$ P\left(\ket{\psi}_{\text{final}} \to \ket{-i}\right) = \frac{1}{2}(1+\sin(\chi)) \quad \left(\phi + \sum_i \phi_i = \frac{3\pi}{2}\right) $$

The realization of the protocol using only 1 qubit could lead to the wrong result probasbilistically. For example, if $P\left(\ket{\psi}_{\text{final}} \to \ket{\text{expected eigenbasis}} \right) \approx 0.5$, we have a 50-50 chances of believing that everybody signed the document when this did not happen in reality if we run the protocol with just 1 qubit. Thus, we need to realize the protocol using multiple qubits and measurements, and let the statistics speak.

## Concrete Example

Let's show a concrete example to exhibit how the protocol works in practice. We consider the following polynomial

$$ f(x) = 6 + x + x^2 \mod 5$$

We are also in the case where $\phi + \sum_i\phi_i = 0$ for simplicity. If everyone has voted, $\ket{\psi}_{\text{final}} = \ket{+}$, and we expect to project the final state on $\ket{+}$ with probability 1. Let's examine how this probability changes when different combinations of executives did not sign

- Everyone signed

$$ P\left(\ket{\psi}_{\text{final}} \to \ket{+}\right) = 1$$

- CEO, CFO did not sign, or nobody signed

$$ P\left(\ket{\psi}_{\text{final}} \to \ket{+}\right) \approx 0.65$$

- CLO, CEO+CFO, CEO+CLO, CFO+CLO did not sign

$$ P\left(\ket{\psi}_{\text{final}} \to \ket{+}\right) \approx 0.10$$

Clearly, by performing the protocol with multiple states and measurements, we can statistically uncover what went on during the signing procedure, as a single measurement could probabilistically lead to deceiving results. Additionally, the fact that the probabilities of different combinations coincide (for some selected choices of polynomial), preserves the privacy of the executives after the final result has been announced by QSign.

## Quantum Advantage

Our approach offers the following advantages based on quantum mechanics:

- Privacy with respect to each executive's decision, no one can uncover this information during or after the protocol

- Prevention of state copying and manipulation

- Destruction of sensitive information if an executive tries to measure the state

- Inaccessibility of the company to sensitive information due to the randomly chosen phases of the participants on the quantum state during the protocol

##
# How to run the code

In order to run the code, you will need to open **5 different terminals**. In the first, run the following command:

```
simulaqron start --nodes=QSign,CEO,CFO,CLO \
  --network-config-file simulaqron_network.json \
  --simulaqron-config-file simulaqron_settings.json
```

The other four terminals correspond to QSign (our company), and the 3 executives (CEO, CFO & CLO). 

In the second terminal, run 

```
python3 QSign.py <NUM_QUBITS>
```

where ```NUM_QUBITS``` is an integer number in the range [2,100] you have to give as an input. It corresponds to the number of states used in the protocol.
> Higher values of ```NUM_QUBITS``` will result in better statistics in the end, but will need higher runtime. For example, for ```NUM_QUBITS=100``` the procedure needs ~ 3 minutes to run, while for ```NUM_QUBITS=10``` it needs ~ 30 seconds to run.

In the third, fourth and fifth terminal, run these respectively

```
python3 CEO.py <DECISION> / python3 CFO.py <DECISION> / python3 CLO.py <DECISION>
```

Where ```DECISION``` can either be ```SIGN``` or ```NO_SIGN``` depending on if you want the corresponding executive to sign the document or not.

## Expected outputs

### QSign

For QSign, which acts as the server, you will see that the three executives have connected. Following, the details of the protocol will be printed, such as: 
- the polynomial
- the secret of the polynomial
- The randomly chosen phase (should be in $\{0, \frac{\pi}{2}, \pi, \frac{3\pi}{2}\}$)
- The number of states (qubits) used for the protocol (should be same as ```NUM_QUBITS```)

Following, for each executive (in the order CEO $\to$ CFO $\to$ CLO) QSign will print the following:

- it has sent the teleportation corrections 
- it received the corrections after the executive has signed
- the signature procedure is done

QSign will then print the following to wrap up the protocol: 

- the expected (in case where everyone signed) sum of phases, based on the inputs of the executives, as well as the corresponding measurement basis

- the state in which they expect to project the final state according to the expected sum of phases

- the statistics of their measurements (how many times they projected on the expected state or not)

- the final verdict based on the statistics (contract signed by everyone or not). In the case of no sign, you will also see a table with different possible scenarios as to who hasn't signed the contract accompanied by the probability of correct projection. As you will see, many of those probabilities align, covering the identity of the person(s) who did not sign

### Executives

For all the executives, you should see the following:

- a message that they have successfully connected to QSign (server) 

- their interpolation point $x_i$ and their private evaluation of the polynomial $f(x_i)$

- that QSign has teleported the states to them (received corrections)

- their calculation of the Lagrange coefficient $c_i$

- their decision on whether to sign the contract or not

- that they teleported the states back to the company (sent corrections)

- the reception of the final verdict from the company on whether the contract has been signed by everyone or not.
