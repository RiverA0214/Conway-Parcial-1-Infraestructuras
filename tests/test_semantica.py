"""Por qué hace falta el doble buffer: la regla pide que cada célula vea la generación ANTERIOR completa."""

import unittest

from life.core import step_rows
from life.grid import random_grid

from .ayudas import avanzar


def avanzar_en_el_mismo_tablero(grid, gens):
    """Lo que NO hay que hacer: leer y escribir sobre el mismo tablero, célula tras célula."""
    rows = len(grid)
    g = [fila[:] for fila in grid]
    for _ in range(gens):
        for i in range(rows):
            step_rows(g, g, i, i + 1)          # lee la fila i+1 y vecinas ya actualizadas
    return g


class ActualizarSobreElMismoTablero(unittest.TestCase):
    def test_da_un_resultado_distinto_al_correcto_incluso_con_un_solo_hilo(self):
        g = random_grid(40, 40, 0.3, seed=7)
        self.assertNotEqual(avanzar_en_el_mismo_tablero(g, 10), avanzar(g, 10))

    def test_con_un_solo_ciclo_ya_se_nota(self):
        g = random_grid(40, 40, 0.3, seed=7)
        self.assertNotEqual(avanzar_en_el_mismo_tablero(g, 1), avanzar(g, 1))


if __name__ == "__main__":
    unittest.main()
