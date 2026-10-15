"""Salida del benchmark: archivos JSON/CSV, tabla por consola y mensajes de progreso."""

import csv
import json
import sys
import time
from pathlib import Path

from .config import RESULTS_DIR


CSV_COLS = ["label", "rows", "cols", "mode", "workers", "ciclos", "reps", "ciclo_ms_prom", "ciclo_ms_std",
            "total_s_prom", "total_s_std", "speedup_ciclo", "speedup_total", "efficiency",
            "speedup_global", "setup_s", "valid", "hash"]


def save_results(result: dict, out: str | None = None) -> tuple[Path, Path]:
    if out:
        json_path = Path(out)
    else:
        json_path = RESULTS_DIR / f"bench-{time.strftime('%Y%m%d-%H%M%S')}.json"
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
        print(f"\n=== {r}x{c} ({filas[0]['ciclos']} ciclos, {filas[0]['reps']} reps) ===")
        print(f"{'intérprete':<24}{'modo':<11}{'w':>3}{'ms/ciclo':>17}{'total s':>17}"
              f"{'sp.ciclo':>9}{'sp.total':>9}{'efic.':>7}{'global':>8}  valid")
        for x in filas:
            if (x["rows"], x["cols"]) != (r, c):
                continue
            sc = f"{x['speedup_ciclo']:.2f}" if x["speedup_ciclo"] else "-"
            st = f"{x['speedup_total']:.2f}" if x["speedup_total"] else "-"
            ef = f"{x['efficiency']:.2f}" if x["efficiency"] else "-"
            gl = f"{x['speedup_global']:.2f}" if x["speedup_global"] else "-"
            ciclo = f"{x['ciclo_ms_prom']:.2f} ± {x['ciclo_ms_std']:.2f}"
            total = f"{x['total_s_prom']:.3f} ± {x['total_s_std']:.3f}"
            print(f"{x['label']:<24}{x['mode']:<11}{x['workers']:>3}{ciclo:>17}{total:>17}"
                  f"{sc:>9}{st:>9}{ef:>7}{gl:>8}  {'ok' if x['valid'] else 'NO'}")


def print_event(ev: dict):
    t = ev["event"]
    if t == "progress":
        print(f"[{ev['label']}] {ev['done'] + 1}/{ev['total']}: {ev['rows']}x{ev['cols']} "
              f"{ev['mode']} w={ev['workers']}", flush=True)
    elif t == "skip":
        print(f"AVISO: se salta '{ev['label']}': {ev['reason']}", file=sys.stderr)
    elif t in ("error", "log"):
        print(f"[{ev.get('label', '?')}] {ev.get('message') or ev.get('text')}", file=sys.stderr)
