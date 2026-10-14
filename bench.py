"""Benchmark del Juego de la Vida: secuencial vs hilos vs procesos, en varios intérpretes.

    python bench.py              # completo (estimado: 4-6 min con ambos intérpretes)
    python bench.py --quick      # prueba rápida (unos segundos)
    python bench.py --with-gil1  # añade python3.14t con -X gil=1

Para cada intérprete lanza `bench.py --worker` y lee líneas JSON de su stdout.
Uso desde otro módulo: run_benchmark(config, on_event=None, cancel=None) -> dict.
Eventos: start, skip, runtime, progress, result, log, error, done.
Cada fila: label, rows, cols, mode, workers, gens, reps, setup_s, times_s, median_s,
min_s, max_s, step_ms, hash, valid (más speedup, efficiency, speedup_global al final).
"""

import argparse
import csv
import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from life.core import grid_hash, random_grid  # noqa: E402
from life.engines import make_engine, runtime_info  # noqa: E402

MODES = ("sequential", "threads", "processes")
LABEL_GIL = "3.14 (GIL)"
LABEL_FT = "3.14t (free-threaded)"
LABEL_FT_GIL1 = "3.14t (GIL=1)"


def parse_sizes(texto: str) -> list[list[int]]:
    sizes = []
    for s in texto.split(","):
        s = s.strip().lower()
        if "x" in s:
            r, c = s.split("x")
            sizes.append([int(r), int(c)])
        elif s:
            sizes.append([int(s), int(s)])
    return sizes


def parse_ints(texto: str) -> list[int]:
    return [int(x) for x in texto.split(",") if x.strip()]


def find_python(name: str) -> str:
    # ruta absoluta de un python del sistema, sin pasar por el venv donde corre este script
    path = os.environ.get("PATH", "").split(os.pathsep)
    if sys.prefix != sys.base_prefix:
        path = [d for d in path if d != os.path.join(sys.prefix, "bin")]
    exe = shutil.which(name, path=os.pathsep.join(path))
    return os.path.realpath(exe) if exe else name      # sin ruta absoluta: resolve_cmd lo descarta


def default_interpreters(with_gil1: bool = False) -> list[dict]:
    gil = "/usr/bin/python3" if os.access("/usr/bin/python3", os.X_OK) else find_python("python3")
    ft = find_python("python3.14t")
    interp = [{"label": LABEL_GIL, "cmd": [gil]},
              {"label": LABEL_FT, "cmd": [ft, "-X", "gil=0"]}]
    if with_gil1:
        interp.append({"label": LABEL_FT_GIL1, "cmd": [ft, "-X", "gil=1"]})
    return interp


def default_config() -> dict:
    return {
        "sizes": [[100, 100], [200, 200], [400, 400], [800, 800]],
        "modes": list(MODES),
        "workers": [1, 2, 4, 8, 12],
        "gens": 10,
        "reps": 3,
        "warmup": 2,
        "density": 0.3,
        "seed": 42,
        "interpreters": default_interpreters(),
    }


def count_cases(config: dict) -> int:
    n = 0
    for _ in config["sizes"]:
        for mode in config["modes"]:
            n += 1 if mode == "sequential" else len(config["workers"])
    return n


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
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))      # para que los motores cierren sus hilos/procesos
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


def resolve_cmd(cmd: list[str]):
    return cmd if os.path.isabs(cmd[0]) and os.access(cmd[0], os.X_OK) else None


def run_interpreter(label, cmd, config, on_event, cancel):
    worker_cfg = {**config, "label": label}
    del worker_cfg["interpreters"]
    proc = subprocess.Popen(
        [*cmd, str(HERE / "bench.py"), "--worker", "--json-config", json.dumps(worker_cfg)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=HERE)
    info, filas = None, []

    def vigilar():      # cancelar mata al worker de inmediato, sin esperar a su próxima línea
        while proc.poll() is None:
            if cancel.wait(0.1):
                proc.terminate()
                return

    if cancel is not None:
        threading.Thread(target=vigilar, daemon=True).start()
    try:
        for linea in proc.stdout:
            linea = linea.rstrip("\n")
            try:
                ev = json.loads(linea)
                if not isinstance(ev, dict) or "event" not in ev:
                    raise ValueError
            except ValueError:
                on_event({"event": "log", "label": label, "text": linea})
                continue
            ev["label"] = label
            if ev["event"] == "runtime":
                info = ev["info"]
            elif ev["event"] == "skip":
                info = None             # no corrió: no cuenta como intérprete usado
            elif ev["event"] == "result":
                filas.append({k: v for k, v in ev.items() if k != "event"})
            on_event(ev)
    finally:
        proc.stdout.close()
        try:
            code = proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            code = proc.wait()
    if code not in (0, None) and not (cancel is not None and cancel.is_set()):
        on_event({"event": "error", "label": label, "message": f"el worker terminó con código {code}"})
    return info, filas


def add_speedups(rows: list[dict], baseline_label: str | None):
    # speedup = T_seq / T (mismo intérprete); global = T_seq del intérprete base / T
    seq = {(r["label"], r["rows"], r["cols"]): r["median_s"] for r in rows if r["mode"] == "sequential"}
    for r in rows:
        t_seq = seq.get((r["label"], r["rows"], r["cols"]))
        t_glob = seq.get((baseline_label, r["rows"], r["cols"]))
        r["speedup"] = t_seq / r["median_s"] if t_seq else None
        r["efficiency"] = r["speedup"] / r["workers"] if r["speedup"] else None
        r["speedup_global"] = t_glob / r["median_s"] if t_glob else None


def hardware_info() -> dict:
    modelo = "desconocido"
    try:
        with open("/proc/cpuinfo") as f:
            for linea in f:
                if linea.startswith("model name"):
                    modelo = linea.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    return {"cpu_model": modelo, "cores": os.cpu_count()}


def run_benchmark(config: dict, on_event=None, cancel: threading.Event | None = None) -> dict:
    on_event = on_event or (lambda ev: None)
    runtime, filas, usados = {}, [], []
    plan = []
    for it in config["interpreters"]:
        cmd = resolve_cmd(it["cmd"])
        if cmd is None:
            on_event({"event": "skip", "label": it["label"], "reason": f"no se encontró {it['cmd'][0]}"})
        else:
            plan.append((it["label"], cmd))
            usados.append(it["label"])
    on_event({"event": "start", "interpreters": usados, "total": count_cases(config) * len(plan)})
    for label, cmd in plan:
        if cancel is not None and cancel.is_set():
            break
        info, f = run_interpreter(label, cmd, config, on_event, cancel)
        if info:
            runtime[label] = info
        filas.extend(f)
    baseline = LABEL_GIL if LABEL_GIL in runtime else next(iter(runtime), None)
    add_speedups(filas, baseline)
    on_event({"event": "done", "total_rows": len(filas)})
    meta = {"fecha": time.strftime("%Y-%m-%d %H:%M:%S"), "hardware": hardware_info(),
            "config": config, "baseline": baseline}
    return {"meta": meta, "runtime": runtime, "rows": filas}


CSV_COLS = ["label", "rows", "cols", "mode", "workers", "gens", "reps", "setup_s", "median_s",
            "min_s", "max_s", "step_ms", "speedup", "efficiency", "speedup_global", "valid", "hash"]


def save_results(result: dict, out: str | None = None) -> tuple[Path, Path]:
    if out:
        json_path = Path(out)
    else:
        json_path = HERE / "results" / f"bench-{time.strftime('%Y%m%d-%H%M%S')}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2))
    csv_path = json_path.with_suffix(".csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(result["rows"])
    return json_path, csv_path


def print_table(result: dict):
    filas = result["rows"]
    if not filas:
        print("sin resultados")
        return
    print(f"\nCPU: {result['meta']['hardware']['cpu_model']} ({result['meta']['hardware']['cores']} cores)")
    for (r, c) in dict.fromkeys((x["rows"], x["cols"]) for x in filas):
        print(f"\n=== {r}x{c} ({filas[0]['gens']} generaciones) ===")
        print(f"{'intérprete':<24}{'modo':<11}{'w':>3}{'mediana s':>11}{'ms/gen':>9}"
              f"{'speedup':>9}{'efic.':>7}{'global':>8}{'setup s':>9}  valid")
        for x in filas:
            if (x["rows"], x["cols"]) != (r, c):
                continue
            sp = f"{x['speedup']:.2f}" if x["speedup"] else "-"
            ef = f"{x['efficiency']:.2f}" if x["efficiency"] else "-"
            gl = f"{x['speedup_global']:.2f}" if x["speedup_global"] else "-"
            print(f"{x['label']:<24}{x['mode']:<11}{x['workers']:>3}{x['median_s']:>11.4f}"
                  f"{x['step_ms']:>9.2f}{sp:>9}{ef:>7}{gl:>8}{x['setup_s']:>9.3f}  "
                  f"{'ok' if x['valid'] else 'NO'}")


def print_event(ev: dict):
    t = ev["event"]
    if t == "progress":
        print(f"[{ev['label']}] {ev['done'] + 1}/{ev['total']}: {ev['rows']}x{ev['cols']} "
              f"{ev['mode']} w={ev['workers']}", flush=True)
    elif t == "skip":
        print(f"AVISO: se salta '{ev['label']}': {ev['reason']}", file=sys.stderr)
    elif t in ("error", "log"):
        print(f"[{ev.get('label', '?')}] {ev.get('message') or ev.get('text')}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Benchmark del Juego de la Vida")
    ap.add_argument("--worker", action="store_true", help="(interno) modo worker")
    ap.add_argument("--json-config", help="(interno) configuración JSON para el worker")
    ap.add_argument("--quick", action="store_true", help="prueba rápida")
    ap.add_argument("--with-gil1", action="store_true", help="añade python3.14t con -X gil=1")
    ap.add_argument("--sizes", help="ej. 100,200,200x300")
    ap.add_argument("--workers", help="ej. 1,2,4,8,12")
    ap.add_argument("--modes", help="ej. sequential,threads,processes")
    ap.add_argument("--gens", type=int)
    ap.add_argument("--reps", type=int)
    ap.add_argument("--out", help="ruta del JSON (el CSV usa el mismo nombre)")
    args = ap.parse_args()

    if args.worker:
        worker_main(json.loads(args.json_config))
        return

    cfg = default_config()
    if args.quick:
        cfg.update(sizes=parse_sizes("40,80"), gens=3, reps=1, workers=[1, 2, 4])
    if args.sizes:
        cfg["sizes"] = parse_sizes(args.sizes)
    if args.workers:
        cfg["workers"] = parse_ints(args.workers)
    if args.modes:
        cfg["modes"] = [m.strip() for m in args.modes.split(",")]
        malos = [m for m in cfg["modes"] if m not in MODES]
        if malos:
            ap.error(f"modos inválidos: {malos}")
    if args.gens:
        cfg["gens"] = args.gens
    if args.reps:
        cfg["reps"] = args.reps
    cfg["interpreters"] = default_interpreters(args.with_gil1)

    result = run_benchmark(cfg, print_event)
    json_path, csv_path = save_results(result, args.out)
    print_table(result)
    malos = [r for r in result["rows"] if not r["valid"]]
    print(f"\nResultados: {json_path}\n            {csv_path}")
    if malos:
        print(f"ATENCIÓN: {len(malos)} casos con resultado inválido", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
