"""Cronómetro: mide los ciclos de un motor sin que el motor sepa que lo miden."""

import statistics
import time


def medir_ciclos(engine, ciclos):
    """Avanza `ciclos` generaciones. Devuelve (segundos de cada ciclo, segundos del bucle completo)."""
    tiempos = []
    inicio = time.perf_counter()
    for _ in range(ciclos):
        t = time.perf_counter()
        engine.advance()
        tiempos.append(time.perf_counter() - t)
    return tiempos, time.perf_counter() - inicio


def resumen(muestras):
    """Devuelve (promedio, desviación estándar); la desviación es 0 con una sola muestra."""
    desviacion = statistics.stdev(muestras) if len(muestras) > 1 else 0.0
    return statistics.mean(muestras), desviacion
