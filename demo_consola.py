"""Demo por consola: corre la simulación secuencial y la de hilos sobre un tablero pequeño e imprime el resultado.

    python demo_consola.py
"""

import time

from life.core import from_matrix, to_matrix
from life.engines import make_engine

# . muerta
# * viva


def print_matrix(mat):
    for row in mat:
        print("".join(row))


def simular(mode, mat, workers, max_steps, show):
    """Avanza hasta que nada cambie o se llegue a max_steps.
    Devuelve (matriz final, segundos de cálculo)."""
    rows, cols = len(mat), len(mat[0])
    total_s = 0.0
    with make_engine(mode, rows, cols, workers) as engine:
        engine.load(from_matrix(mat))
        steps = 1
        if show:
            print(f"{steps = }")
            print_matrix(mat)
        while steps < max_steps:
            steps += 1
            inicio = time.perf_counter()
            changed, _ = engine.advance()
            total_s += time.perf_counter() - inicio      # solo el cálculo, sin imprimir
            if show:
                print(f"{steps = }")
                print_matrix(to_matrix(engine.board))
                time.sleep(0.5)
            if changed == 0:
                break
        return to_matrix(engine.board), total_s


def sec(mat, max_steps=1000, show=True):
    return simular("sequential", mat, 1, max_steps, show)


def par(mat, num_threads=4, max_steps=1000, show=True):
    return simular("threads", mat, num_threads, max_steps, show)


def main(start_mat):
    result, t_sec = sec(start_mat, 50, False)
    print(f"secuencial: {t_sec: .6f}s")
    print_matrix(result)

    result_par, t_par = par(start_mat, 4, 50, False)
    print(f"paralelo: {t_par: .6f}s")
    print_matrix(result_par)
    print(f"mismo resultado: {result == result_par}")


tablero_test = [
    ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '*', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '*', '.', '.', '.', '.', '.'],
    ['.', '.', '*', '*', '*', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.', '.', '.']
]
tablero_pequeno = [
    ['.', '.', '.', '.', '.'],
    ['.', '.', '*', '.', '.'],
    ['.', '.', '*', '.', '.'],
    ['.', '.', '*', '.', '.'],
    ['.', '.', '.', '.', '.']
]

if __name__ == '__main__':
    main(tablero_test)
    main(tablero_pequeno)
