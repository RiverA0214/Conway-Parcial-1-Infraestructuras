import unittest
from fractions import Fraction

from gui.vista import Vista


def vista(n, panel=500):
    v = Vista(panel)
    v.configurar(n)
    return v


class EscalaInicial(unittest.TestCase):
    def test_los_tamanos_del_parcial_con_panel_de_500(self):
        self.assertEqual(vista(100).escala, 5)
        self.assertEqual(vista(500).escala, 1)
        self.assertEqual(vista(1000).escala, 1)

    def test_el_tablero_grande_se_recorta_y_el_chico_se_ve_completo(self):
        self.assertFalse(vista(100).recorta)
        self.assertFalse(vista(500).recorta)
        v = vista(1000)
        self.assertTrue(v.recorta)
        self.assertEqual(v.region(), (0, 0, 500))


class Zoom(unittest.TestCase):
    def test_el_minimo_es_ajustado_y_no_baja_mas(self):
        for n, minimo in ((100, 5), (500, 1), (1000, Fraction(1, 2))):
            with self.subTest(n=n):
                v = vista(n)
                v.cambiar_zoom(-10, 250, 250)
                self.assertEqual(v.escala, minimo)
                self.assertFalse(v.cambiar_zoom(-1, 250, 250))
                self.assertFalse(v.recorta)

    def test_ajustado_llena_el_panel(self):
        for n in (5, 100, 150, 200, 300, 500, 700, 1000, 2000):
            with self.subTest(n=n):
                v = vista(n)
                v.nivel = 0
                self.assertLessEqual(abs(v.lado - 500), v.zoom)

    def test_el_zoom_mantiene_la_celda_bajo_el_cursor(self):
        v = vista(1000)
        v.cambiar_zoom(-1, 250, 250)
        self.assertEqual(v.celda(250, 250), (500, 500))
        v.cambiar_zoom(+2, 250, 250)
        self.assertEqual(v.escala, 2)
        self.assertEqual(v.celda(250, 250), (500, 500))

    def test_niveles_fuera_de_rango_no_cambian_nada(self):
        v = vista(500)
        v.cambiar_zoom(100, 0, 0)
        self.assertEqual(v.escala, 16)
        self.assertFalse(v.cambiar_zoom(1, 0, 0))


class Desplazamiento(unittest.TestCase):
    def setUp(self):
        self.v = vista(1000)
        self.v.cambiar_zoom(-1, 0, 0)
        self.v.cambiar_zoom(+2, 250, 250)               # x2: se ven 250 celdas por lado

    def test_no_se_sale_del_tablero(self):
        self.v.mover(-10_000, -10_000)
        self.assertEqual(self.v.region(), (0, 0, 250))
        self.v.mover(10_000, 10_000)
        self.assertEqual(self.v.region(), (750, 750, 250))

    def test_scrollbar(self):
        self.v.barra("y", "moveto", "0.5")
        self.assertEqual(self.v.region()[0], 500)
        self.v.barra("x", "scroll", "-1", "pages")
        self.assertEqual(self.v.region()[1], max(0, int(round(self.v.ox))))
        self.v.barra("x", "moveto", "0")
        self.v.barra("x", "scroll", "1", "units")
        self.assertEqual(self.v.region()[1], 25)        # 250 // 10 celdas

    def test_rango_de_las_barras(self):
        self.v.barra("x", "moveto", "0.5")
        self.v.barra("y", "moveto", "0.25")
        (x0, x1), (y0, y1) = self.v.rango_barras()
        self.assertEqual((x0, x1, y0, y1), (0.5, 0.75, 0.25, 0.5))

    def test_si_el_tablero_cabe_no_hay_desplazamiento(self):
        v = vista(100)
        v.mover(500, 500)
        v.barra("x", "moveto", "0.9")
        self.assertEqual(v.rango_barras(), ((0.0, 1.0), (0.0, 1.0)))


class CeldaBajoElMouse(unittest.TestCase):
    def test_tablero_completo(self):
        v = vista(100)
        self.assertEqual(v.celda(0, 0), (0, 0))
        self.assertEqual(v.celda(499, 499), (99, 99))
        self.assertEqual(v.celda(-50, 900), (99, 0))     # fuera del panel se acota

    def test_recorte(self):
        v = vista(1000)
        v.cambiar_zoom(+2, 0, 0)                          # x4, 125 celdas por lado
        v.barra("y", "moveto", "0.5")
        v.barra("x", "moveto", "0.25")
        self.assertEqual(v.celda(0, 0), (500, 250))
        self.assertEqual(v.celda(499, 499), (500 + 124, 250 + 124))


if __name__ == "__main__":
    unittest.main()
