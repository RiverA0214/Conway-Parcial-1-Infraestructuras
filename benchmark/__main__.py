"""Línea de comandos: python -m benchmark [--quick] [--sizes ...] [--workers ...]"""

import argparse
import sys

from .config import MODES, default_config, default_interpreters, parse_ints, parse_sizes
from .ejecucion import run_benchmark
from .salida import print_event, print_table, save_results


def main():
    ap = argparse.ArgumentParser(prog="python -m benchmark", description="Benchmark del Juego de la Vida")
    ap.add_argument("--quick", action="store_true", help="prueba rápida")
    ap.add_argument("--with-gil1", action="store_true", help="añade python3.14t con -X gil=1")
    ap.add_argument("--sizes", help="ej. 100,200,200x300")
    ap.add_argument("--workers", help="ej. 1,2,4,8,12")
    ap.add_argument("--modes", help="ej. sequential,threads")
    ap.add_argument("--ciclos", type=int)
    ap.add_argument("--reps", type=int)
    ap.add_argument("--out", help="ruta del JSON (el CSV usa el mismo nombre)")
    args = ap.parse_args()

    cfg = default_config()
    if args.quick:
        cfg.update(sizes=parse_sizes("40,80"), ciclos=3, reps=1, workers=[1, 2, 4])
    if args.sizes:
        cfg["sizes"] = parse_sizes(args.sizes)
    if args.workers:
        cfg["workers"] = parse_ints(args.workers)
    if args.modes:
        cfg["modes"] = [m.strip() for m in args.modes.split(",")]
        malos = [m for m in cfg["modes"] if m not in MODES]
        if malos:
            ap.error(f"modos inválidos: {malos}")
    if args.ciclos:
        cfg["ciclos"] = args.ciclos
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
