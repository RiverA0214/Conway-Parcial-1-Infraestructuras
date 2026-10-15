"""Funciones de apoyo para las pruebas: una implementación de referencia, independiente del kernel."""

from life.core import step_rows
from life.grid import empty_grid, from_bytes
from life.patterns import place


def referencia(mat):
    """Una generación con la versión original: dx/dy y chequeo de bordes por vecino (matriz de '*' y '.')."""
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
    """El kernel solo, sin motores, con dos tableros. Trabaja sobre una copia: no modifica `grid`."""
    rows, cols = len(grid), len(grid[0])
    leer, escribir = [fila[:] for fila in grid], empty_grid(rows, cols)
    for _ in range(gens):
        step_rows(leer, escribir, 0, rows)
        leer, escribir = escribir, leer
    return leer


def con_patron(nombre, i, j, rows=12, cols=15):
    buf = bytearray(rows * cols)
    place(buf, rows, cols, nombre, i, j)
    return from_bytes(buf, rows, cols)
