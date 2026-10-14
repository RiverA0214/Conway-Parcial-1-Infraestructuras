"""Genera las gráficas del informe a partir del JSON de bench.py.

Uso: uv run --no-project --with matplotlib python scripts/graficas.py results/bench-XXXX.json
Los PNG quedan en results/graficas/ (o en --out).
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR = {"sequential": "#a78bfa", "threads": "#fbbf24", "threads_ft": "#34d399", "processes": "#38bdf8"}
ESTILO = {"3.14 (GIL)": "-", "3.14t (free-threaded)": "--", "3.14t (GIL=1)": ":"}
MARCA = {"3.14 (GIL)": "o", "3.14t (free-threaded)": "s", "3.14t (GIL=1)": "^"}
MODO = {"sequential": "Secuencial", "threads": "Hilos", "processes": "Procesos"}
FT = "3.14t (free-threaded)"


def color(modo, interp):
    if modo == "threads" and interp == FT:
        return COLOR["threads_ft"]
    return COLOR[modo]


def etiqueta(modo, interp):
    return f"{MODO[modo]} - {interp}"


def cargar(ruta):
    filas = json.loads(Path(ruta).read_text())["rows"]
    return {(f["label"], f["mode"], f["rows"], f["workers"]): f for f in filas}


def serie(datos, interp, modo, n, campo):
    ws = sorted({k[3] for k in datos if k[:3] == (interp, modo, n)})
    return ws, [datos[(interp, modo, n, w)][campo] for w in ws]


def estilo_base(ax, titulo, xlabel, ylabel):
    ax.set_title(titulo, fontsize=13)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def guardar(fig, out, nombre):
    fig.tight_layout()
    fig.savefig(out / nombre, dpi=140)
    plt.close(fig)
    print("escrito", out / nombre)


def lineas(datos, interps, modos, n, campo):
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for modo in modos:
        for it in interps:
            ws, ys = serie(datos, it, modo, n, campo)
            ax.plot(ws, ys, ESTILO[it], marker=MARCA[it], color=color(modo, it),
                    linewidth=2, markersize=6, label=etiqueta(modo, it))
    return fig, ax


def g_speedup(datos, interps, n, out, nombre):
    fig, ax = lineas(datos, interps, ["threads", "processes"], n, "speedup")
    ws = sorted({k[3] for k in datos})
    ax.plot(ws, ws, color="#6b7280", linewidth=1.2, linestyle="-.", label="Ideal (lineal)")
    ax.set_xticks(ws)
    estilo_base(ax, f"Speedup vs. workers, tablero {n}x{n}", "Workers", "Speedup (T secuencial / T)")
    ax.legend(fontsize=8, loc="upper left")
    guardar(fig, out, nombre)


def g_eficiencia(datos, interps, n, out):
    fig, ax = lineas(datos, interps, ["threads", "processes"], n, "efficiency")
    ws = sorted({k[3] for k in datos})
    ax.axhline(1, color="#6b7280", linewidth=1.2, linestyle="-.", label="Ideal (1.0)")
    ax.set_xticks(ws)
    estilo_base(ax, f"Eficiencia vs. workers, tablero {n}x{n}", "Workers", "Eficiencia (speedup / workers)")
    ax.legend(fontsize=8, loc="upper right")
    guardar(fig, out, f"03_eficiencia_{n}.png")


def g_tamano(datos, interps, tamanos, out):
    fig, ax = plt.subplots(figsize=(8, 5.2))
    for modo in ["sequential", "threads", "processes"]:
        for it in interps:
            ys = []
            for n in tamanos:
                ws, ms = serie(datos, it, modo, n, "step_ms")
                ys.append(min(ms))
            ax.plot(tamanos, ys, ESTILO[it], marker=MARCA[it], color=color(modo, it),
                    linewidth=2, markersize=6, label=etiqueta(modo, it))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(tamanos)
    ax.set_xticklabels([f"{n}x{n}" for n in tamanos])
    ax.minorticks_off()
    estilo_base(ax, "Tiempo por generación vs. tamaño (mejor nº de workers)", "Tamaño del tablero",
                "ms por generación (escala log)")
    ax.legend(fontsize=8, loc="upper left")
    guardar(fig, out, "04_ms_vs_tamano.png")


def g_barras(datos, interps, n, w, out):
    fig, ax = plt.subplots(figsize=(9, 5.4))
    items = [("sequential", it, 1) for it in interps]
    items += [(m, it, w) for m in ("threads", "processes") for it in interps]
    for i, (modo, it, ww) in enumerate(items):
        v = datos[(it, modo, n, ww)]["step_ms"]
        ax.bar(i, v, color=color(modo, it), edgecolor="#374151",
               hatch={"3.14 (GIL)": "", FT: "//", "3.14t (GIL=1)": ".."}[it])
        ax.text(i, v + 1.5, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(range(len(items)))
    ax.set_xticklabels([f"{MODO[m]}\n{it.replace(' (', chr(10) + '(')}" for m, it, _ in items], fontsize=7.5)
    estilo_base(ax, f"ms por generación, {n}x{n}, {w} workers (secuencial: 1)", "", "ms por generación")
    guardar(fig, out, f"05_barras_{n}_{w}w.png")


def g_gil(datos, interps, n, out):
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ws = sorted({k[3] for k in datos})
    for it in interps:
        _, ys = serie(datos, it, "threads", n, "speedup")
        ax.plot(ws, ys, ESTILO[it], marker=MARCA[it], color=color("threads", it), linewidth=2.2,
                markersize=7, label=f"Hilos - {it}")
    ax.plot(ws, ws, color="#6b7280", linewidth=1.2, linestyle="-.", label="Ideal (lineal)")
    ax.axhline(1, color="#9ca3af", linewidth=0.8)
    ax.set_xticks(ws)
    estilo_base(ax, f"Efecto del GIL: speedup de hilos, tablero {n}x{n}", "Hilos", "Speedup (T secuencial / T)")
    ax.legend(fontsize=9, loc="upper left")
    guardar(fig, out, f"06_gil_hilos_{n}.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(a.json).parent / "graficas"
    out.mkdir(parents=True, exist_ok=True)
    datos = cargar(a.json)
    interps = [i for i in ESTILO if any(k[0] == i for k in datos)]
    tamanos = sorted({k[2] for k in datos})
    n1 = tamanos[-1]
    n2 = tamanos[-2] if len(tamanos) > 1 else n1
    workers = sorted({k[3] for k in datos})
    w = 8 if 8 in workers else workers[-1]
    g_speedup(datos, interps, n1, out, f"01_speedup_{n1}.png")
    g_speedup(datos, interps, n2, out, f"02_speedup_{n2}.png")
    g_eficiencia(datos, interps, n1, out)
    g_tamano(datos, interps, tamanos, out)
    g_barras(datos, interps, n1, w, out)
    g_gil(datos, interps, n1, out)


if __name__ == "__main__":
    main()
