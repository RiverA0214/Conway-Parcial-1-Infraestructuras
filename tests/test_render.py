import unittest

from gui.render import MUERTA, VIVA, to_ppm


class ImagenPPM(unittest.TestCase):
    def test_cabecera_y_tamano(self):
        img = to_ppm(bytes([0, 1, 1, 0, 1, 0]), 3, 2)
        cabecera, _, datos = img.partition(b"\n")
        self.assertEqual(cabecera, b"P6 3 2 255")
        self.assertEqual(len(datos), 3 * 2 * 3)

    def test_colores(self):
        datos = to_ppm(bytes([0, 1]), 2, 1).partition(b"\n")[2]
        self.assertEqual(tuple(datos[:3]), MUERTA)
        self.assertEqual(tuple(datos[3:]), VIVA)

    def test_igual_que_armar_el_pixel_celda_por_celda(self):
        raw = bytes((i * 7 + i // 3) % 2 for i in range(40 * 25))
        lento = b"".join(bytes(VIVA) if c else bytes(MUERTA) for c in raw)
        self.assertEqual(to_ppm(raw, 40, 25).partition(b"\n")[2], lento)


if __name__ == "__main__":
    unittest.main()
