"""Juego de la Vida: tablero como lista de listas con 0/1, bordes muertos, regla B3/S23.

El kernel lee una generación y escribe la siguiente en otro tablero (doble buffer): nunca se
actualiza el tablero que se está leyendo, porque cada célula debe ver la generación anterior
completa, no los valores que otras ya cambiaron.
"""

import hashlib
import random


def step_rows(read, write, r0, r1):
    """Calcula las filas [r0, r1) de la siguiente generación.

    Lee de `read` (el tablero completo, solo lectura) y escribe en las mismas filas de
    `write`, sin tocar las demás: así varios hilos pueden llamarla a la vez, cada uno con
    su bloque. Escribe todas las celdas de sus filas, así que `write` puede traer datos viejos.
    Devuelve (celdas_que_cambiaron, celdas_vivas) de ese bloque.
    """
    rows, cols = len(read), len(read[0])
    cero = [0] * (cols + 2)
    changed = 0
    alive = 0
    for i in range(r0, r1):
        up = [0] + read[i - 1] + [0] if i > 0 else cero
        mid = [0] + read[i] + [0]
        down = [0] + read[i + 1] + [0] if i < rows - 1 else cero
        new = write[i]
        for j in range(cols):
            vecinos = (up[j] + up[j + 1] + up[j + 2]
                       + mid[j] + mid[j + 2]
                       + down[j] + down[j + 1] + down[j + 2])
            vive = 1 if (vecinos == 3 or (vecinos == 2 and mid[j + 1])) else 0
            new[j] = vive
            alive += vive
            if vive != mid[j + 1]:
                changed += 1
    return changed, alive


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
