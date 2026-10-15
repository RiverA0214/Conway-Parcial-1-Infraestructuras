"""Medición de los casos. Corre DENTRO del intérprete que se está evaluando.

La lanza ejecucion.py como `python -m benchmark.medicion --json-config ...` y le
devuelve los resultados por stdout, una línea JSON por evento.
"""

import argparse
import json
import signal
import statistics
import sys
import time

from life.core import grid_hash, random_grid
from life.engines import make_engine, runtime_info

from .config import LABEL_FT, LABEL_FT_GIL1, LABEL_GIL, count_cases


def emit(obj: dict):
    print(json.dumps(obj), flush=True)


def measure_case(config, rows, cols, mode, workers, initial, expected_hash):
    gens, reps = config["gens"], config["reps"]
    t0 = time.perf_counter()
    engine = make_engine(mode, rows, cols, workers)
    setup_s = time.perf_counter() - t0
    times, hashes = [], []
    try:
        engine.load(initial)
        engine.run(config["warmup"])              # calentamiento
        for _ in range(reps):
            engine.load(initial)
            t = time.perf_counter()
            engine.run(gens)
            times.append(time.perf_counter() - t)
            hashes.append(grid_hash(engine.grid()))
    finally:
        engine.close()
    h = hashes[-1]
    med = statistics.median(times)
    return {
        "rows": rows, "cols": cols, "mode": mode, "workers": workers,
        "gens": gens, "reps": reps, "setup_s": setup_s, "times_s": times,
        "median_s": med, "min_s": min(times), "max_s": max(times),
        "step_ms": med / gens * 1000, "hash": h,
        "valid": all(x == expected_hash for x in hashes),
    }


def reference_hash(initial, rows, cols, gens):
    with make_engine("sequential", rows, cols, 1) as e:
        e.load(initial)
        e.run(gens)
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
        expected = reference_hash(initial, rows, cols, config["gens"])
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
