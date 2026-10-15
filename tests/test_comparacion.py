import unittest

from life.comparacion import comparar
from life.engines import make_engine
from life.grid import random_grid


class CompararMotores(unittest.TestCase):
    def test_mide_los_ciclos_pedidos_y_deja_los_dos_motores_iguales(self):
        g = random_grid(40, 40, 0.3, seed=9)
        with make_engine("sequential", 40, 40) as seq, make_engine("threads", 40, 40, 3) as par:
            seq.load(g)
            r = comparar(seq, par, 10)
            self.assertIsNone(r.error)
            self.assertEqual(r.ciclos, 10)
            self.assertEqual(seq.grid(), par.grid())
            self.assertGreater(r.total_seq, 0)
            self.assertGreater(r.speedup_ciclo, 0)
            self.assertGreater(r.ultimo_seq, 0)

    def test_avanza_los_ciclos_medidos_mas_uno_de_calentamiento(self):
        g = random_grid(30, 30, 0.3, seed=9)
        with make_engine("sequential", 30, 30) as seq, make_engine("threads", 30, 30, 2) as par, \
                make_engine("sequential", 30, 30) as ref:
            seq.load(g); ref.load(g)
            comparar(seq, par, 7)
            ref.run(8)
            self.assertEqual(seq.grid(), ref.grid())

    def test_con_un_solo_ciclo_la_desviacion_es_cero(self):
        with make_engine("sequential", 20, 20) as seq, make_engine("threads", 20, 20, 2) as par:
            seq.load(random_grid(20, 20))
            self.assertEqual(comparar(seq, par, 1).ciclo_seq[1], 0.0)

    def test_detecta_motores_que_difieren(self):
        class Roto(make_engine("sequential", 5, 5).__class__):
            def advance(self):
                super().advance()
                self.board[0][0] ^= 1                    # un motor que se equivoca
                return 0, 0
        with make_engine("sequential", 20, 20) as seq, Roto(20, 20) as par:
            seq.load(random_grid(20, 20))
            self.assertIn("difieren", comparar(seq, par, 3).error)


if __name__ == "__main__":
    unittest.main()
