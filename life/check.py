"""Verificación: python -m life.check (sale con código 1 si algo falla)."""

import sys

from .core import from_bytes, from_matrix, random_grid, step_rows, to_bytes, to_matrix
from .engines import make_engine
from .patterns import place

fallos = 0


def reporte(nombre, ok):
    global fallos
    fallos += not ok
    print(f"[{'OK' if ok else 'FAIL'}] {nombre}")


def referencia(mat):
    # versión original: dx/dy y chequeo de bordes por vecino
    dx = [1, -1, 0, 0, 1, -1, 1, -1]
    dy = [0, 0, -1, 1, -1, -1, 1, 1]
    n, m = len(mat), len(mat[0])
    nueva = [['.'] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            v = 0
            for k in range(8):
                a, b = i + dx[k], j + dy[k]
                if 0 <= a < n and 0 <= b < m and mat[a][b] == '*':
                    v += 1
            if (mat[i][j] == '*' and v in (2, 3)) or (mat[i][j] == '.' and v == 3):
                nueva[i][j] = '*'
    return nueva


def avanzar(grid, gens):
    rows, cols = len(grid), len(grid[0])
    for _ in range(gens):
        grid = step_rows(grid, rows, cols, 0, rows)[0]
    return grid


def con_patron(nombre, i, j, rows=12, cols=15):
    buf = bytearray(rows * cols)
    place(buf, rows, cols, nombre, i, j)
    return from_bytes(buf, rows, cols)


def patrones():
    g = con_patron("blinker", 5, 5)
    reporte("blinker: periodo 2", avanzar(g, 1) != g and avanzar(g, 2) == g)
    g = con_patron("glider", 1, 1)
    esperado = con_patron("glider", 2, 2)
    reporte("glider: 4 generaciones lo mueven (+1,+1)", avanzar(g, 4) == esperado)


def contra_referencia():
    g = random_grid(17, 23, 0.35, seed=7)
    mat = to_matrix(g)
    ok = True
    for _ in range(15):
        g = avanzar(g, 1)
        mat = referencia(mat)
        ok = ok and to_matrix(g) == mat
    reporte("kernel == versión original (17x23, 15 gens)", ok and from_matrix(mat) == g)


def comparar_motores():
    rows, cols, gens = 60, 90, 15
    g = random_grid(rows, cols, 0.3, seed=123)
    with make_engine("sequential", rows, cols) as e:
        e.load(g)
        e.run(gens)
        esperado = e.grid()
    reporte("secuencial == kernel", esperado == to_bytes(avanzar(g, gens)))
    for w in (1, 2, 3, 4, 7):
        with make_engine("threads", rows, cols, w) as e:
            e.load(to_bytes(g))
            e.run(gens)
            reporte(f"threads workers={w} == secuencial", e.grid() == esperado)


def main():
    patrones()
    contra_referencia()
    comparar_motores()
    print("TODO OK" if fallos == 0 else f"FALLARON {fallos}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
