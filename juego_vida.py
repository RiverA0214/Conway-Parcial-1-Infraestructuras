import time
import json
import random
import threading



# Representación: matriz con padding de (n+2) x (n+2) enteros 0/1.
#   0 = celda muerta, 1 = celda viva
# El tablero real ocupa las posiciones 1..n; el borde (fila/columna 0 y n+1)
# siempre vale 0 y nunca se escribe, así que los 8 vecinos se suman sin
# comprobar límites.

def make_padded(n: int) -> list[list[int]]:
    return [[0] * (n + 2) for _ in range(n + 2)]

def pad(rows: list[list[int]]) -> list[list[int]]:
    # agrega el borde muerto a un tablero de n x n
    zeros = [0] * (len(rows) + 2)
    return [zeros[:]] + [[0, *row, 0] for row in rows] + [zeros[:]]

def unpad(mat: list[list[int]]) -> list[list[int]]:
    return [row[1:-1] for row in mat[1:-1]]

def print_matrix(mat: list[list[int]]):
    for row in unpad(mat):
        print("".join(map(str, row)))

def timeit(fn, *args):
    start = time.perf_counter()
    result  = fn(*args)
    end = time.perf_counter()
    return (result, end - start)


# ------------------------------------------------------------------
# Kernel: calcula la siguiente generación de un bloque de filas
#
# Lee de `read` (todo el tablero) y escribe en `write` SOLO las filas
# [start, end) del tablero real (índices sin padding). Devuelve True si
# alguna celda de su bloque cambió.
# ------------------------------------------------------------------

def work_section(read: list[list[int]], write: list[list[int]], start: int, end: int) -> bool:
    n: int = len(read) - 2
    changed: bool = False

    for i in range(start + 1, end + 1):   # +1 por el padding
        up, cur, down, out = read[i - 1], read[i], read[i + 1], write[i]
        for j in range(1, n + 1):
            s = (up[j - 1] + up[j] + up[j + 1] +
                 cur[j - 1]        + cur[j + 1] +
                 down[j - 1] + down[j] + down[j + 1])
            c = cur[j]
            new = 1 if (s == 3 or (c and s == 2)) else 0
            out[j] = new
            if new != c:
                changed = True

    return changed


# ------------------------------------------------------------------
# Versión secuencial
# ------------------------------------------------------------------

def sec(mat: list[list[int]], max_steps: int = 1000, show: bool = True):
    n: int = len(mat) - 2
    # dos matrices que se alternan (ping-pong); no se modifica la de entrada
    read = [row[:] for row in mat]
    write = make_padded(n)

    steps = 1
    if show:
        print(f"{steps = }")
        print_matrix(read)
    while True:
        steps += 1
        changed = work_section(read, write, 0, n)
        read, write = write, read
        if show:
            print(f"{steps = }")
            print_matrix(read)
            time.sleep(0.5)
        # max_steps evita un ciclo infinito con patrones que oscilan (ej. blinker)
        if not changed or steps >= max_steps: break
    return read


# ------------------------------------------------------------------
# Versión paralela (hilos)
#
# - Hay dos matrices completas que se alternan (ping-pong): en cada
#   generación todos los hilos LEEN de una (solo lectura) y ESCRIBEN en la
#   otra, cada uno únicamente en su bloque de filas [start, end); como los
#   bloques son disjuntos no hay condiciones de carrera.
# - Una barrera espera a que todos terminen. Cuando llega el último, la
#   acción de la barrera solo intercambia las dos referencias (O(1)): la
#   matriz recién escrita pasa a ser la de lectura del siguiente ciclo.
#   No se copia nada.
# ------------------------------------------------------------------

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

def par(mat: list[list[int]], num_threads: int = 4, max_steps: int = 1000, show: bool = True):
    n: int = len(mat) - 2
    num_threads = max(1, min(num_threads, n))
    ranges = split_rows(n, num_threads)

    # cada hilo escribe únicamente en su posición -> sin carreras
    changed: list[bool] = [False] * num_threads

    # no se modifica la matriz de entrada
    state = {'read': [row[:] for row in mat], 'write': make_padded(n), 'steps': 1, 'stop': False}

    if show:
        print(f"steps = {state['steps']}")
        print_matrix(state['read'])

    def merge():
        # La ejecuta UN solo hilo, cuando todos llegaron a la barrera
        # y antes de liberarlos.
        state['read'], state['write'] = state['write'], state['read']
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
            changed[t] = work_section(state['read'], state['write'], start, end)
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

def random_matrix(n: int, density: float = 0.3, seed: int = 42) -> list[list[int]]:
    rng = random.Random(seed)
    mat = make_padded(n)
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if rng.random() < density:
                mat[i][j] = 1
    return mat

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


def main(start_mat: list[list[int]]):

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
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
]
tablero_pequeno = [
    [0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0]
]

# matrix10x10
if __name__ == '__main__':
    # with open('matrix.json', 'r') as file:
    #     data = json.load(file)
    #     main(pad(data))
    main(pad(tablero_test))

    # Para el análisis de rendimiento (tarda varios minutos con 1000x1000):
    results = benchmark()
    plot_speedup(results)
