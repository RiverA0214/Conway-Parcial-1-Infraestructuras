"""El hilo de simulación, sin Tk: se espera (con tiempo límite) a que publique lo que se le pidió."""

import time
import unittest

from gui.simulador import Simulador
from life.grid import empty_grid, random_grid


def esperar(condicion, limite=10.0):
    fin = time.time() + limite
    while time.time() < fin:
        if condicion():
            return True
        time.sleep(0.005)
    return False


class SimuladorSinInterfaz(unittest.TestCase):
    def setUp(self):
        self.sim = Simulador(20, 3)
        self.addCleanup(self.sim.cerrar)

    def test_un_paso_avanza_una_generacion_y_los_tableros_coinciden(self):
        self.sim.cargar(random_grid(20, 20, 0.3, seed=1))
        self.sim.un_paso()
        self.assertTrue(esperar(lambda: self.sim.ultimo.generacion == 1))
        f = self.sim.ultimo
        self.assertEqual(f.seq, f.par)
        self.assertIsNone(f.error)

    def test_pintar_cambia_las_celdas_y_pausa(self):
        self.sim.cargar(empty_grid(20, 20))
        self.sim.pintar([(1, 1), (1, 2), (1, 3)], 1)
        self.assertEqual(self.sim.ultimo.vivas, 3)
        self.assertFalse(self.sim.corriendo)
        self.sim.un_paso()
        self.assertTrue(esperar(lambda: self.sim.ultimo.generacion == 1))     # el blinker sigue vivo tras pintar
        self.assertEqual(self.sim.ultimo.vivas, 3)

    def test_iniciar_y_pausar(self):
        self.sim.retardo = 0
        self.sim.cargar(random_grid(20, 20, 0.3, seed=2))
        self.sim.iniciar()
        self.assertTrue(esperar(lambda: self.sim.ultimo.generacion >= 5))
        self.sim.pausar()
        time.sleep(0.2)
        g = self.sim.ultimo.generacion
        time.sleep(0.2)
        self.assertEqual(self.sim.ultimo.generacion, g)

    def test_correr_ciclos_publica_el_resultado(self):
        self.sim.cargar(random_grid(20, 20, 0.3, seed=3))
        self.sim.correr_ciclos(10)
        self.assertTrue(esperar(lambda: self.sim.resultado is not None and not self.sim.ocupado))
        r = self.sim.resultado
        self.assertIsNone(r.error)
        self.assertEqual(r.ciclos, 10)
        self.assertEqual(self.sim.ultimo.generacion, 11)       # 10 medidos + 1 de calentamiento
        self.assertEqual(self.sim.ultimo.seq, self.sim.ultimo.par)

    def test_los_ids_de_frame_crecen(self):
        self.sim.cargar(empty_grid(20, 20))
        a = self.sim.ultimo.id
        self.sim.cargar(empty_grid(20, 20))
        self.assertGreater(self.sim.ultimo.id, a)


if __name__ == "__main__":
    unittest.main()
