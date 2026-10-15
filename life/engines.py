"""Motores: secuencial e hilos (Barrier). Los dos usan step_rows."""

import os
import sys
import sysconfig
import threading
import time
from dataclasses import dataclass

from .core import empty_grid, from_bytes, split_rows, step_rows, to_bytes


@dataclass
class StepResult:
    changed: int
    alive: int
    compute_ns: int


class Engine:
    def __init__(self, rows, cols, workers=1):
        self.rows, self.cols, self.workers = rows, cols, workers
        self.board = empty_grid(rows, cols)

    def load(self, buf):
        if isinstance(buf, (bytes, bytearray)):
            if len(buf) != self.rows * self.cols:
                raise ValueError("tamaño de tablero incorrecto")
            self.board = from_bytes(buf, self.rows, self.cols)
        else:
            self.board = [list(fila) for fila in buf]

    def grid(self):
        return to_bytes(self.board)

    def step(self):
        t0 = time.perf_counter_ns()
        changed, alive = self.advance()
        return StepResult(changed, alive, time.perf_counter_ns() - t0)

    def run(self, gens):
        for _ in range(gens):
            self.advance()

    def advance(self):
        # calcula la siguiente generación; deja el resultado en self.board
        new_rows, changed, alive = step_rows(self.board, self.rows, self.cols, 0, self.rows)
        self.board = new_rows
        return changed, alive

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class ThreadEngine(Engine):
    # Hilos persistentes. Todos leen self.board (solo lectura) y cada uno calcula su
    # bloque de filas. Barrier de workers + 1: el hilo que llama a step() también espera.
    def __init__(self, rows, cols, workers):
        super().__init__(rows, cols, workers)
        self.ranges = split_rows(rows, workers)
        self.parts = [None] * workers      # cada hilo escribe solo su posición
        self.barrier = threading.Barrier(workers + 1)
        self.stop = False
        self.error = None
        self.closed = False
        self.threads = [threading.Thread(target=self.worker, args=(t,), daemon=True)
                        for t in range(workers)]
        for th in self.threads:
            th.start()

    def worker(self, t):
        r0, r1 = self.ranges[t]
        try:
            while True:
                self.barrier.wait()        # espera la orden de empezar la generación
                if self.stop:
                    return
                self.parts[t] = step_rows(self.board, self.rows, self.cols, r0, r1)
                self.barrier.wait()        # espera a que todos terminen su bloque
        except threading.BrokenBarrierError:
            pass
        except BaseException as e:
            self.error = e
            self.barrier.abort()           # que nadie se quede colgado

    def advance(self):
        if self.closed:
            raise RuntimeError("el motor está cerrado")
        try:
            self.barrier.wait()
            self.barrier.wait()
        except threading.BrokenBarrierError:
            error = self.error
            self.close()
            raise error or RuntimeError("falló la barrera") from None
        self.board = [fila for part in self.parts for fila in part[0]]
        return sum(p[1] for p in self.parts), sum(p[2] for p in self.parts)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.stop = True
        try:
            self.barrier.wait(5)           # despierta a los hilos para que salgan
        except threading.BrokenBarrierError:
            pass
        self.barrier.abort()
        for th in self.threads:
            th.join(5)


def make_engine(mode, rows, cols, workers=1):
    if mode == "sequential":
        return Engine(rows, cols, 1)
    if workers < 1:
        raise ValueError("workers debe ser >= 1")
    if mode == "threads":
        return ThreadEngine(rows, cols, workers)
    raise ValueError(f"modo desconocido: {mode!r}")


def runtime_info():
    gil = getattr(sys, "_is_gil_enabled", None)
    return {
        "python_version": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "gil_enabled": gil() if gil else True,
        "free_threaded_build": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "cpu_count": os.cpu_count(),
        "executable": sys.executable,
    }
