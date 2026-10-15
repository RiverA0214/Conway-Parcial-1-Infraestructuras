import unittest

from life.engines import SequentialEngine, ThreadEngine, make_engine, split_rows
from life.grid import empty_grid, random_grid, to_bytes

from .ayudas import avanzar


class ParticionDeFilas(unittest.TestCase):
    def test_cubre_todas_las_filas_sin_huecos_ni_solapes(self):
        for filas in (1, 7, 100, 1000):
            for hilos in (1, 2, 3, 8, 12):
                with self.subTest(filas=filas, hilos=hilos):
                    bloques = split_rows(filas, hilos)
                    self.assertEqual(bloques[0][0], 0)
                    self.assertEqual(bloques[-1][1], filas)
                    for (_, fin), (inicio, _) in zip(bloques, bloques[1:]):
                        self.assertEqual(fin, inicio)

    def test_bloques_parejos(self):
        tamanos = [fin - inicio for inicio, fin in split_rows(1000, 12)]
        self.assertLessEqual(max(tamanos) - min(tamanos), 1)


class MotoresContraElKernel(unittest.TestCase):
    def test_secuencial_coincide_con_el_kernel(self):
        g = random_grid(60, 90, 0.3, seed=123)
        with make_engine("sequential", 60, 90) as e:
            e.load(g)
            e.run(15)
            self.assertEqual(e.grid(), to_bytes(avanzar(g, 15)))

    def test_hilos_coincide_con_el_secuencial(self):
        for filas, columnas in ((60, 90), (13, 5), (31, 31)):
            g = random_grid(filas, columnas, 0.3, seed=filas)
            with make_engine("sequential", filas, columnas) as e:
                e.load(g)
                e.run(15)
                esperado = e.grid()
            for hilos in (1, 2, 3, 4, 7, 12):
                with self.subTest(tablero=f"{filas}x{columnas}", hilos=hilos):
                    with make_engine("threads", filas, columnas, hilos) as e:
                        e.load(to_bytes(g))
                        e.run(15)
                        self.assertEqual(e.grid(), esperado)

    def test_mas_hilos_que_filas(self):
        g = random_grid(5, 8, 0.4, seed=1)
        with make_engine("sequential", 5, 8) as a, make_engine("threads", 5, 8, 12) as b:
            a.load(g); b.load(g)
            a.run(6); b.run(6)
            self.assertEqual(a.grid(), b.grid())


class InterfazDelMotor(unittest.TestCase):
    def setUp(self):
        self.motores = [SequentialEngine(20, 20), ThreadEngine(20, 20, 3)]

    def tearDown(self):
        for e in self.motores:
            e.close()

    def test_load_no_modifica_ni_comparte_filas_con_la_entrada(self):
        g = random_grid(20, 20, 0.4, seed=4)
        copia = [fila[:] for fila in g]
        for e in self.motores:
            e.load(g)
            e.run(5)                                  # con ping-pong se reescriben los dos tableros del motor
            self.assertEqual(g, copia)

    def test_load_acepta_bytes_y_filas_y_valida_el_tamano(self):
        g = random_grid(20, 20, 0.4, seed=4)
        for e in self.motores:
            e.load(to_bytes(g)); a = e.grid()
            e.load(g); self.assertEqual(e.grid(), a)
            with self.assertRaises(ValueError):
                e.load(bytes(399))

    def test_advance_devuelve_cambiadas_y_vivas(self):
        for e in self.motores:
            e.load(empty_grid(20, 20))
            e.set_cells([(5, 4), (5, 5), (5, 6)], 1)  # un blinker
            self.assertEqual(e.advance(), (4, 3))
            self.assertEqual(e.advance(), (4, 3))
            e.set_cells([(5, 5)], 0)
            self.assertEqual(e.grid().count(1), 2)

    def test_tablero_estable_devuelve_cero_cambios(self):
        for e in self.motores:
            e.load(empty_grid(20, 20))
            e.set_cells([(2, 2), (2, 3), (3, 2), (3, 3)], 1)   # bloque
            self.assertEqual(e.advance(), (0, 4))

    def test_set_cells_se_mantiene_entre_ciclos(self):
        for e in self.motores:
            e.load(empty_grid(20, 20))
            e.advance(); e.advance()                  # los dos tableros ya se alternaron
            e.set_cells([(1, 1), (1, 2), (1, 3)], 1)
            self.assertEqual(e.grid().count(1), 3)

    def test_set_cells_pone_exactamente_las_celdas_pedidas(self):
        celdas = [(0, 0), (3, 7), (19, 19), (10, 2)]
        for e in self.motores:
            e.load(empty_grid(20, 20))
            e.set_cells(celdas, 1)
            vivas = {i for i, c in enumerate(e.grid()) if c}
            self.assertEqual(vivas, {i * 20 + j for i, j in celdas})
            e.set_cells(celdas[:2], 0)
            self.assertEqual({i for i, c in enumerate(e.grid()) if c}, {19 * 20 + 19, 10 * 20 + 2})

    def test_un_motor_cerrado_no_avanza(self):
        e = ThreadEngine(10, 10, 2)
        e.close()
        e.close()                                      # cerrar dos veces no falla
        with self.assertRaises(RuntimeError):
            e.advance()

    def test_modos_invalidos(self):
        with self.assertRaises(ValueError):
            make_engine("procesos", 10, 10, 2)
        with self.assertRaises(ValueError):
            make_engine("threads", 10, 10, 0)


if __name__ == "__main__":
    unittest.main()
