from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler


def circuito_deutsch_jozsa(oraculo: QuantumCircuit, n: int) -> QuantumCircuit:
    total = oraculo.num_qubits
    if n < 1 or n + 1 > total:
        raise ValueError("n debe cumplir 1 <= n <= num_qubits - 1")

    y = total - 1  # qubit n + r
    qc = QuantumCircuit(total, n)

    # Estado inicial |0 0^r 0^n> -> preparar y en |->, x en superposición uniforme
    qc.x(y)
    qc.h(y)
    qc.h(range(n))
    qc.barrier()

    # Oráculo (phase kickback: |x>|-> -> (-1)^f(x) |x>|->)
    qc.compose(oraculo, qubits=range(total), inplace=True)
    qc.barrier()

    # Hadamard sobre x y medición del qubit i en el bit clásico i
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def is_constant(oraculo: QuantumCircuit, n: int, num_iter: int = 1000) -> bool:
    qc = circuito_deutsch_jozsa(oraculo, n)
    sampler = StatevectorSampler()
    resultado = sampler.run([qc], shots=num_iter).result()[0]
    counts = resultado.data[qc.cregs[0].name].get_counts()
    return counts.get("0" * n, 0) == num_iter