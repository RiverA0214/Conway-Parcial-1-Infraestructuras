import unittest

from life.grid import empty_grid, from_bytes, from_matrix, grid_hash, random_grid, to_bytes, to_matrix


class Conversiones(unittest.TestCase):
    def test_bytes_ida_y_vuelta(self):
        g = random_grid(7, 11, 0.4, seed=5)
        self.assertEqual(from_bytes(to_bytes(g), 7, 11), g)
        self.assertEqual(len(to_bytes(g)), 7 * 11)

    def test_caracteres_ida_y_vuelta(self):
        g = random_grid(6, 4, 0.5, seed=5)
        self.assertEqual(from_matrix(to_matrix(g)), g)
        self.assertTrue(set(c for fila in to_matrix(g) for c in fila) <= {"*", "."})


class Creacion(unittest.TestCase):
    def test_tablero_vacio(self):
        self.assertEqual(empty_grid(3, 2), [[0, 0], [0, 0], [0, 0]])

    def test_aleatorio_es_reproducible_con_la_misma_semilla(self):
        self.assertEqual(random_grid(20, 20, seed=1), random_grid(20, 20, seed=1))
        self.assertNotEqual(random_grid(20, 20, seed=1), random_grid(20, 20, seed=2))

    def test_filas_independientes(self):
        g = empty_grid(3, 3)
        g[0][0] = 1
        self.assertEqual(g[1][0], 0)

    def test_hash_distingue_tableros(self):
        g = random_grid(10, 10)
        h = grid_hash(g)
        g[0][0] ^= 1
        self.assertNotEqual(grid_hash(g), h)


if __name__ == "__main__":
    unittest.main()
