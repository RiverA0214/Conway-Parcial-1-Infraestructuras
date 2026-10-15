"""Comparación secuencial contra paralelo: mide X ciclos en cada motor desde el mismo tablero."""

from dataclasses import dataclass

from .cronometro import medir_ciclos, resumen


@dataclass
class Resultado:
    ciclos: int
    total_seq: float           # s del bucle completo
    total_par: float
    ciclo_seq: tuple           # (promedio, desviación) en ms por ciclo
    ciclo_par: tuple
    speedup_ciclo: float
    speedup_total: float
    error: str | None = None
    ultimo_seq: float = 0.0    # s del último ciclo medido
    ultimo_par: float = 0.0


def comparar(seq, par, ciclos) -> Resultado:
    """Carga en `par` el tablero de `seq`, hace un ciclo de calentamiento y mide `ciclos` ciclos en cada motor.

    Los dos motores quedan avanzados `ciclos + 1` generaciones. Si sus tableros finales
    no coinciden, el resultado trae un mensaje de error.
    """
    par.load(seq.grid())
    medir_ciclos(seq, 1)                     # calentamiento, como el benchmark
    medir_ciclos(par, 1)
    tiempos_seq, total_seq = medir_ciclos(seq, ciclos)
    tiempos_par, total_par = medir_ciclos(par, ciclos)
    ciclo_seq, ciclo_par = resumen(tiempos_seq), resumen(tiempos_par)
    error = None if seq.grid() == par.grid() else "ERROR: los tableros secuencial y paralelo difieren"
    return Resultado(
        ciclos, total_seq, total_par,
        (ciclo_seq[0] * 1000, ciclo_seq[1] * 1000), (ciclo_par[0] * 1000, ciclo_par[1] * 1000),
        ciclo_seq[0] / ciclo_par[0], total_seq / total_par, error,
        tiempos_seq[-1], tiempos_par[-1])
