"""Configuración del benchmark: qué tamaños, modos, workers e intérpretes se miden."""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

MODES = ("sequential", "threads")
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
    return os.path.realpath(exe) if exe else name


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
        "sizes": [[100, 100], [500, 500], [1000, 1000]],
        "modes": list(MODES),
        "workers": [1, 2, 4, 8, 12],
        "ciclos": 50,
        "reps": 10,
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
