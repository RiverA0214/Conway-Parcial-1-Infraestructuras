import unittest

from life.core import step_rows
from life.grid import empty_grid, from_matrix, random_grid, to_matrix

from .ayudas import avanzar, con_patron, referencia


class PatronesClasicos(unittest.TestCase):
    def test_blinker_tiene_periodo_2(self):
        g = con_patron("blinker", 5, 5)
        self.assertNotEqual(avanzar(g, 1), g)
        self.assertEqual(avanzar(g, 2), g)

    def test_bloque_es_estable(self):
        g = con_patron("block", 4, 4)
        self.assertEqual(avanzar(g, 5), g)

    def test_glider_se_mueve_una_celda_en_diagonal_cada_4_generaciones(self):
        self.assertEqual(avanzar(con_patron("glider", 1, 1), 4), con_patron("glider", 2, 2))


class ContraLaVersionOriginal(unittest.TestCase):
    def test_coincide_generacion_por_generacion(self):
        for filas, columnas in ((17, 23), (1, 9), (9, 1), (2, 2)):
            with self.subTest(tablero=f"{filas}x{columnas}"):
                g = random_grid(filas, columnas, 0.35, seed=7)
                mat = to_matrix(g)
                for _ in range(15):
                    g = avanzar(g, 1)
                    mat = referencia(mat)
                    self.assertEqual(to_matrix(g), mat)
                self.assertEqual(from_matrix(mat), g)


class Contrato(unittest.TestCase):
    def test_solo_escribe_las_filas_de_su_bloque(self):
        leer = random_grid(10, 10, 0.5, seed=1)
        escribir = [[7] * 10 for _ in range(10)]          # marca para ver qué filas se tocaron
        step_rows(leer, escribir, 3, 6)
        for i in range(10):
            tocada = escribir[i] != [7] * 10
            self.assertEqual(tocada, 3 <= i < 6, f"fila {i}")

    def test_no_modifica_el_tablero_que_lee(self):
        leer = random_grid(12, 12, 0.4, seed=2)
        copia = [fila[:] for fila in leer]
        step_rows(leer, empty_grid(12, 12), 0, 12)
        self.assertEqual(leer, copia)

    def test_sobrescribe_todas_las_celdas_aunque_el_destino_traiga_datos_viejos(self):
        leer = random_grid(12, 12, 0.4, seed=3)
        limpio, sucio = empty_grid(12, 12), [[1] * 12 for _ in range(12)]
        step_rows(leer, limpio, 0, 12)
        step_rows(leer, sucio, 0, 12)
        self.assertEqual(limpio, sucio)

    def test_cuenta_celdas_cambiadas_y_vivas(self):
        leer = con_patron("blinker", 5, 5)                # 3 vivas; en un ciclo mueren 2 y nacen 2
        cambiadas, vivas = step_rows(leer, empty_grid(12, 15), 0, 12)
        self.assertEqual((cambiadas, vivas), (4, 3))

    def test_un_tablero_estable_no_cambia(self):
        cambiadas, vivas = step_rows(con_patron("block", 4, 4), empty_grid(12, 15), 0, 12)
        self.assertEqual((cambiadas, vivas), (0, 4))


if __name__ == "__main__":
    unittest.main()
