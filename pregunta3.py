import argparse
import json
import warnings
from datetime import datetime, timezone

from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

from deutsch_jozsa import circuito_deutsch_jozsa
from pregunta2 import oraculo_f1, oraculo_f2

# SamplerV2 sigue funcionando en qiskit-ibm-runtime 0.50, pero emite un aviso de deprecación
warnings.filterwarnings("ignore", category=DeprecationWarning, module="qiskit_ibm_runtime|__main__")

N = 7
SHOTS = 1000
UMBRAL = 0.5


def es_constante_con_ruido(counts: dict, shots: int) -> bool:
    """f es constante si la fracción de resultados 0^n es al menos UMBRAL."""
    return counts.get("0" * N, 0) / shots >= UMBRAL


def elegir_backend(args):
    if args.simulador:
        from qiskit_ibm_runtime.fake_provider import FakeTorino
        return FakeTorino()  # simulación local con el modelo de ruido de ibm_torino
    service = QiskitRuntimeService()
    if args.backend:
        return service.backend(args.backend)
    return service.least_busy(operational=True, simulator=False, min_num_qubits=N + 4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", help="nombre del computador (ej. ibm_torino)")
    parser.add_argument("--simulador", action="store_true", help="probar localmente con FakeTorino")
    args = parser.parse_args()

    backend = elegir_backend(args)
    print(f"Computador: {backend.name}")

    pm = generate_preset_pass_manager(optimization_level=3, backend=backend, seed_transpiler=0)
    sampler = Sampler(mode=backend)

    registro = {"backend": backend.name, "fecha": datetime.now(timezone.utc).isoformat(), "resultados": {}}

    # 1) Transpilar y enviar ambos trabajos (así esperan en la cola al mismo tiempo)
    trabajos = {}
    for nombre, oraculo in (("f1", oraculo_f1), ("f2", oraculo_f2)):
        circuito = pm.run(circuito_deutsch_jozsa(oraculo, N))
        dos_qubits = circuito.num_nonlocal_gates()
        print(f"{nombre}: circuito transpilado con {dos_qubits} compuertas de dos qubits, "
              f"profundidad {circuito.depth()}")
        job = sampler.run([circuito], shots=SHOTS)
        print(f"{nombre}: job ID = {job.job_id()}")
        trabajos[nombre] = (job, circuito, dos_qubits)

    # 2) Esperar resultados y aplicar el criterio
    for nombre, (job, circuito, dos_qubits) in trabajos.items():
        resultado = job.result()[0]
        counts = resultado.data[circuito.cregs[0].name].get_counts()
        ceros = counts.get("0" * N, 0)
        constante = es_constante_con_ruido(counts, SHOTS)
        registro["resultados"][nombre] = {
            "job_id": job.job_id(),
            "compuertas_dos_qubits": dos_qubits,
            "profundidad": circuito.depth(),
            "veces_0000000": ceros,
            "counts": counts,
        }
        print(f"{nombre}: 0000000 obtenido {ceros}/{SHOTS} veces ({ceros / SHOTS:.1%})")
        graficar(nombre, counts, ceros, backend.name)
        registro["resultados"][nombre]["tipo"] = "constante" if constante else "balanceada"

    with open("resultados_pregunta3.json", "w") as fh:
        json.dump(registro, fh, indent=2)

    print()
    for nombre in ("f1", "f2"):
        print(f"{nombre} es {registro['resultados'][nombre]['tipo']}")


def graficar(nombre, counts, ceros, backend_name, top=20):
    """Guarda histograma_<nombre>.png con los `top` resultados más frecuentes (0^7 destacado)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    orden = sorted(counts.items(), key=lambda kv: -kv[1])
    claves = [k for k, _ in orden[:top]]
    if "0" * N not in claves:
        claves = ["0" * N] + claves[: top - 1]
    valores = [counts.get(k, 0) for k in claves]
    colores = ["#d62728" if k == "0" * N else "#1f77b4" for k in claves]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(claves, valores, color=colores)
    ax.set_xticks(range(len(claves)))
    ax.set_xticklabels(claves, rotation=70, fontfamily="monospace", fontsize=8)
    ax.set_ylabel("Número de mediciones")
    ax.set_title(f"Deutsch-Jozsa para {nombre} en {backend_name} "
                 f"({SHOTS} shots) — 0000000: {ceros} veces")
    otros = SHOTS - sum(valores)
    if otros > 0:
        ax.text(0.99, 0.95, f"otros {len(counts) - len(claves)} strings: {otros} mediciones",
                transform=ax.transAxes, ha="right", va="top", fontsize=9)
    fig.tight_layout()
    fig.savefig(f"histograma_{nombre}.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()

