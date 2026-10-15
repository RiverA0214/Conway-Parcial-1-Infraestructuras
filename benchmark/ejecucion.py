"""Orquestación: un subproceso por intérprete, eventos de progreso, speedups y eficiencia."""

import json
import os
import subprocess
import threading
import time

from .config import LABEL_GIL, ROOT, count_cases


def resolve_cmd(cmd: list[str]):
    return cmd if os.path.isabs(cmd[0]) and os.access(cmd[0], os.X_OK) else None


def run_interpreter(label, cmd, config, on_event, cancel):
    worker_cfg = {**config, "label": label}
    del worker_cfg["interpreters"]
    proc = subprocess.Popen(
        [*cmd, "-m", "benchmark.medicion", "--json-config", json.dumps(worker_cfg)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT)
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
    # speedup = T_seq / T_par (mismo intérprete), por ciclo y en el total de X ciclos;
    # global = total del secuencial del intérprete base / total
    seq = {(r["label"], r["rows"], r["cols"]): r for r in rows if r["mode"] == "sequential"}
    for r in rows:
        s = seq.get((r["label"], r["rows"], r["cols"]))
        g = seq.get((baseline_label, r["rows"], r["cols"]))
        r["speedup_ciclo"] = s["ciclo_ms_prom"] / r["ciclo_ms_prom"] if s else None
        r["speedup_total"] = s["total_s_prom"] / r["total_s_prom"] if s else None
        r["efficiency"] = r["speedup_total"] / r["workers"] if s else None
        r["speedup_global"] = g["total_s_prom"] / r["total_s_prom"] if g else None


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
