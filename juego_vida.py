import time
import json
import random
import threading



# . empty
# * cell

# right, left, up, down
# upper right, upper left
# lower right, lower left
dx = [1,-1,0,0,1,-1,1,-1]
dy = [0,0,-1,1,-1,-1,1,1]

def is_valid(mat: list[list[str]],i: int, j: int) -> int:
    n: int = len(mat)
    if i >= 0 and i < n and j  >= 0 and j < n and mat[i][j] == '*':
        return 1
    return 0

def count_neighboors(mat: list[list[str]], i: int, j: int) -> int:
    count = 0
    for k in range(8):
        count += is_valid(mat,i + dx[k], j + dy[k])
    return count

def print_matrix(mat: list[list[str]]):

    for row in mat:
        for c in row:
            print(c,end="")
        print()

def timeit(fn, *args):
    start = time.perf_counter()
    result  = fn(*args)
    end = time.perf_counter()
    return (result, end - start)


# ------------------------------------------------------------------
# Versión secuencial
# ------------------------------------------------------------------

def work_sec(mat: list[list[str]]):
    n: int = len(mat)
    new_mat: list[list[str]] = [['.'] * n for _ in range(n)]

    lives: bool = False   # True si alguna celda cambió en esta generación

    for i in range(n):
        for j in range(n):
            neighboors = count_neighboors(mat,i,j)
            if mat[i][j] == '.' and neighboors == 3:
                lives = True
                new_mat[i][j] = '*'
                continue
            if mat[i][j] == '.': continue

            if neighboors < 2 or neighboors > 3:
                lives = True
                new_mat[i][j] = '.'
            else:
                new_mat[i][j] = mat[i][j]

    return new_mat, lives

def sec(mat: list[list[str]], max_steps: int = 1000, show: bool = True):

    new_mat: list[list[str]] = mat
    steps = 1
    if show:
        print(f"{steps = }")
        print_matrix(new_mat)
    while True:
        steps += 1
        new_mat, lives = work_sec(new_mat)
        if show:
            print(f"{steps = }")
            print_matrix(new_mat)
            time.sleep(0.5)
        # max_steps evita un ciclo infinito con patrones que oscilan (ej. blinker)
        if not lives or steps >= max_steps: break
    return new_mat


# ------------------------------------------------------------------
# Versión paralela (hilos)
#
# - Todos los hilos comparten la matriz de SOLO LECTURA de la generación actual.
# - Cada hilo tiene su propia matriz de ESCRITURA con un bloque de filas
#   [start, end); solo escribe ahí, así que no hay condiciones de carrera.
# - Una barrera espera a que todos terminen su bloque. Cuando llega el último,
#   la acción de la barrera junta todos los bloques en una matriz grande nueva,
#   que pasa a ser la matriz de solo lectura del siguiente ciclo.
# ------------------------------------------------------------------

def work_section(read_mat: list[list[str]], write_mat: list[list[str]], start: int, end: int) -> bool:
    n: int = len(read_mat)
    lives: bool = False

    for i in range(start, end):
        row = write_mat[i - start]   # fila local dentro del bloque del hilo
        for j in range(n):
            neighboors = count_neighboors(read_mat, i, j)
            cell = read_mat[i][j]
            if cell == '.' and neighboors == 3:
                lives = True
                row[j] = '*'
            elif cell == '*' and (neighboors < 2 or neighboors > 3):
                lives = True
                row[j] = '.'
            else:
                row[j] = cell

    return lives

def split_rows(n: int, num_threads: int) -> list[tuple[int, int]]:
    # reparte n filas en bloques lo más parejos posible
    base, extra = divmod(n, num_threads)
    ranges = []
    start = 0
    for t in range(num_threads):
        end = start + base + (1 if t < extra else 0)
        ranges.append((start, end))
        start = end
    return ranges

def par(mat: list[list[str]], num_threads: int = 4, max_steps: int = 1000, show: bool = True):
    n: int = len(mat)
    num_threads = max(1, min(num_threads, n))
    ranges = split_rows(n, num_threads)

    # una matriz de escritura por hilo (solo sus filas)
    write_mats = [[['.'] * n for _ in range(end - start)] for start, end in ranges]
    # cada hilo escribe únicamente en su posición -> sin carreras
    changed: list[bool] = [False] * num_threads

    state = {'read': mat, 'steps': 1, 'stop': False}

    if show:
        print(f"steps = {state['steps']}")
        print_matrix(state['read'])

    def merge():
        # La ejecuta UN solo hilo, cuando todos llegaron a la barrera
        # y antes de liberarlos. Copiamos las filas porque los write_mats
        # se reutilizan en el siguiente ciclo.
        state['read'] = [row[:] for wm in write_mats for row in wm]
        state['steps'] += 1
        if show:
            print(f"steps = {state['steps']}")
            print_matrix(state['read'])
            time.sleep(0.5)
        if not any(changed) or state['steps'] >= max_steps:
            state['stop'] = True

    barrier = threading.Barrier(num_threads, action=merge)

    def worker(t: int):
        start, end = ranges[t]
        while True:
            changed[t] = work_section(state['read'], write_mats[t], start, end)
            barrier.wait()          # aquí se ejecuta merge()
            if state['stop']:
                break

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
    for th in threads: th.start()
    for th in threads: th.join()

    return state['read']


# ------------------------------------------------------------------
# Pruebas de rendimiento
# ------------------------------------------------------------------

def random_matrix(n: int, density: float = 0.3, seed: int = 42) -> list[list[str]]:
    rng = random.Random(seed)
    return [['*' if rng.random() < density else '.' for _ in range(n)] for _ in range(n)]

def benchmark(sizes=(100, 500, 1000), threads=(1, 2, 4, 8), generations: int = 10):
    results = {}   # results[n] = {'sec': t, num_threads: t, ...}
    for n in sizes:
        mat = random_matrix(n)
        sec_res, sec_time = timeit(sec, mat, generations, False)
        results[n] = {'sec': sec_time}
        print(f"\n{n}x{n} ({generations} generaciones)")
        print(f"  secuencial: {sec_time: .4f}s")
        for t in threads:
            par_res, par_time = timeit(par, mat, t, generations, False)
            assert par_res == sec_res, "la versión paralela no coincide con la secuencial"
            results[n][t] = par_time
            print(f"  {t} hilos:   {par_time: .4f}s  speedup = {sec_time / par_time: .2f}")
    return results

def plot_speedup(results, threads=(1, 2, 4, 8), filename: str = "speedup.png"):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib no está instalado (pip install matplotlib), no se genera la gráfica")
        return
    for n, times in results.items():
        plt.plot(threads, [times['sec'] / times[t] for t in threads], marker='o', label=f"{n}x{n}")
    plt.plot(threads, threads, '--', color='gray', label="ideal")
    plt.xlabel("Número de hilos")
    plt.ylabel("Speedup (T_secuencial / T_paralelo)")
    plt.title("Juego de la Vida - Speedup")
    plt.legend()
    plt.grid(True)
    plt.savefig(filename)
    print(f"gráfica guardada en {filename}")


def main(start_mat: list[list[str]]):

    result, sec_time = timeit(sec, start_mat)
    print(f"secuencial: {sec_time: .6f}s")
    print(f"result: ")
    print_matrix(result)

    result_par, par_time = timeit(par, start_mat, 4)
    print(f"paralelo: {par_time: .6f}s")
    print(f"result: ")
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

# matrix10x10
if __name__ == '__main__':
    # with open('matrix.json', 'r') as file:
    #     data = json.load(file)
    #     main(data)
    main(tablero_test)

    # Para el análisis de rendimiento (tarda varios minutos con 1000x1000):
    results = benchmark()
    plot_speedup(results)
