"""Tableros: crearlos, convertirlos a bytes (GUI, hash) y a caracteres (demo, pruebas).

Un tablero es una lista de filas, cada fila una lista de 0 (muerta) y 1 (viva).
"""

import hashlib
import random


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
