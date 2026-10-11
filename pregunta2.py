from qiskit import QuantumCircuit

from deutsch_jozsa import is_constant

N = 7


def _oraculo_f1() -> QuantumCircuit:
    n, r = N, 3
    a1, a2, a3 = n, n + 1, n + 2   # auxiliares (acarreos)
    y = n + r                      # qubit de salida

    # V: tres sumadores completos (sum en el último qubit de entrada, carry en aux)
    v = QuantumCircuit(n + r + 1, name="V")

    def sumador(a: int, b: int, c: int, carry: int) -> None:
        v.rccx(a, b, carry)  # carry ^= a b
        v.cx(a, b)           # b = a ^ b
        v.rccx(b, c, carry)  # carry ^= (a ^ b) c   -> carry = MAJ(a, b, c)
        v.cx(b, c)           # c = a ^ b ^ c

    sumador(0, 1, 2, a1)     # q2 = x0^x1^x2, a1 = c1
    sumador(3, 4, 5, a2)     # q5 = x3^x4^x5, a2 = c2
    sumador(2, 5, 6, a3)     # q6 = paridad total, a3 = c3

    qc = QuantumCircuit(n + r + 1, name="Of1")
    qc.compose(v, inplace=True)

    # y ^= 1 xor MAJ3(a1, a2, a3), usando MAJ(a,b,c) = a ^ ((a^b)(a^c))
    qc.x(y)
    qc.cx(a1, a2)
    qc.cx(a1, a3)
    qc.ccx(a2, a3, y)
    qc.cx(a1, y)
    qc.cx(a1, a3)
    qc.cx(a1, a2)

    qc.compose(v.inverse(), inplace=True)
    return qc


def _oraculo_f2() -> QuantumCircuit:
    return QuantumCircuit(N + 1, name="Of2")


oraculo_f1 = _oraculo_f1()
oraculo_f2 = _oraculo_f2()


if __name__ == "__main__":
    for nombre, oraculo in (("f1", oraculo_f1), ("f2", oraculo_f2)):
        tipo = "constante" if is_constant(oraculo, N, num_iter=1000) else "balanceada"
        print(f"{nombre} es {tipo}")