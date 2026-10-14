"""Juego de la Vida: tablero como lista de listas con 0/1, bordes muertos, regla B3/S23."""

import hashlib
import random


def step_rows(grid, rows, cols, r0, r1):
    """Calcula las filas [r0, r1) de la siguiente generación.
    Devuelve (filas_nuevas, celdas_que_cambiaron, celdas_vivas)."""
    cero = [0] * (cols + 2)
    new_rows = []
    changed = 0
    alive = 0
    for i in range(r0, r1):
        up = [0] + grid[i - 1] + [0] if i > 0 else cero
        mid = [0] + grid[i] + [0]
        down = [0] + grid[i + 1] + [0] if i < rows - 1 else cero
        new = [0] * cols
        for j in range(cols):
            vecinos = (up[j] + up[j + 1] + up[j + 2]
                       + mid[j] + mid[j + 2]
                       + down[j] + down[j + 1] + down[j + 2])
            if vecinos == 3 or (vecinos == 2 and mid[j + 1]):
                new[j] = 1
                alive += 1
            if new[j] != mid[j + 1]:
                changed += 1
        new_rows.append(new)
    return new_rows, changed, alive


def empty_grid(rows, cols):
    return [[0] * cols for _ in range(rows)]


def random_grid(rows, cols, density=0.3, seed=42):
    rng = random.Random(seed)
    return [[1 if rng.random() < density else 0 for _ in range(cols)] for _ in range(rows)]


def to_bytes(grid):
    return b"".join(bytes(fila) for fila in grid)


def from_bytes(buf, rows, cols):
    return [list(buf[i * cols:(i + 1) * cols]) for i in range(rows)]


def grid_hash(grid):
    return hashlib.blake2b(to_bytes(grid), digest_size=16).hexdigest()


def from_matrix(mat):
    """Matriz de '*'/'.' -> tablero de 0/1."""
    return [[1 if c == '*' else 0 for c in fila] for fila in mat]


def to_matrix(grid):
    return [['*' if c else '.' for c in fila] for fila in grid]


def split_rows(rows, n):
    """Reparte las filas en n bloques [inicio, fin) lo más parejos posible."""
    base, extra = divmod(rows, n)
    ranges = []
    start = 0
    for t in range(n):
        end = start + base + (1 if t < extra else 0)
        ranges.append((start, end))
        start = end
    return ranges
