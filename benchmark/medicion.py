"""Medición de los casos. Corre DENTRO del intérprete que se está evaluando.

La lanza ejecucion.py como `python -m benchmark.medicion --json-config ...` y le
devuelve los resultados por stdout, una línea JSON por evento.
"""

import argparse
import json
import signal
import sys
import time

from life.cronometro import medir_ciclos, resumen
from life.core import grid_hash, random_grid
from life.engines import make_engine
from life.runtime import runtime_info

from .config import LABEL_FT, LABEL_FT_GIL1, LABEL_GIL, count_cases


def emit(obj: dict):
    print(json.dumps(obj), flush=True)


def measure_case(config, rows, cols, mode, workers, initial, expected_hash):
    ciclos, reps = config["ciclos"], config["reps"]
    t0 = time.perf_counter()
    engine = make_engine(mode, rows, cols, workers)
    setup_s = time.perf_counter() - t0
    por_ciclo, totales, hashes = [], [], []
    try:
        engine.load(initial)
        engine.run(config["warmup"])              # calentamiento
        for _ in range(reps):
            engine.load(initial)
            tiempos, total = medir_ciclos(engine, ciclos)
            por_ciclo.extend(tiempos)
            totales.append(total)
            hashes.append(grid_hash(engine.grid()))
    finally:
        engine.close()
    h = hashes[-1]
    ciclo_prom, ciclo_std = resumen(por_ciclo)
    total_prom, total_std = resumen(totales)
    return {
        "rows": rows, "cols": cols, "mode": mode, "workers": workers,
        "ciclos": ciclos, "reps": reps,
        "ciclo_ms_prom": ciclo_prom * 1000, "ciclo_ms_std": ciclo_std * 1000,
        "total_s_prom": total_prom, "total_s_std": total_std, "totales_s": totales,
        "setup_s": setup_s, "hash": h,
        "valid": all(x == expected_hash for x in hashes),
    }


def reference_hash(initial, rows, cols, ciclos):
    with make_engine("sequential", rows, cols, 1) as e:
        e.load(initial)
        e.run(ciclos)
        return grid_hash(e.grid())


def runtime_error(label, info):
    # None si el intérprete es el que dice la etiqueta
    gil, ft = info["gil_enabled"], info["free_threaded_build"]
    if label == LABEL_GIL and not gil:
        return "el GIL está desactivado"
    if label in (LABEL_FT, LABEL_FT_GIL1) and not ft:
        return "no es un build free-threaded"
    if label == LABEL_FT and gil:
        return "el GIL está activo (se esperaba gil=0)"
    if label == LABEL_FT_GIL1 and not gil:
        return "el GIL está desactivado (se esperaba gil=1)"


def worker_main(config: dict):
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))      # para que los motores cierren sus hilos
    info = runtime_info()
    emit({"event": "runtime", "info": info})
    error = runtime_error(config["label"], info)
    if error:
        emit({"event": "skip", "reason": f"{info['executable']} no coincide con '{config['label']}': {error}"})
        return
    total = count_cases(config)
    done = 0
    for rows, cols in config["sizes"]:
        initial = random_grid(rows, cols, config["density"], config["seed"])
        expected = reference_hash(initial, rows, cols, config["ciclos"])
        for mode in config["modes"]:
            for w in ([1] if mode == "sequential" else config["workers"]):
                emit({"event": "progress", "done": done, "total": total,
                      "rows": rows, "cols": cols, "mode": mode, "workers": w})
                try:
                    fila = measure_case(config, rows, cols, mode, w, initial, expected)
                except Exception as e:
                    emit({"event": "error", "message": f"{rows}x{cols} {mode} w={w}: {e!r}"})
                    done += 1
                    continue
                done += 1
                emit({"event": "result", **fila})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-config", required=True)
    worker_main(json.loads(ap.parse_args().json_config))
