"""Simulación en segundo plano: un hilo calcula las generaciones y publica el último frame.

La interfaz nunca espera al cálculo: lee `ultimo` cuando le conviene y se salta los
frames que no alcanzó a dibujar. Este módulo no usa Tk.

Quién toca los motores: el hilo de simulación (al avanzar) y la interfaz (al pintar o
cargar), siempre con `self.lock`, así que nunca lo hacen a la vez.
"""

import threading
from dataclasses import dataclass

from life.engines import make_engine


@dataclass
class Frame:
    id: int                    # crece con cada publicación; sirve para saber si ya se dibujó
    generacion: int
    vivas: int
    t_seq: int                 # ns de cálculo del último paso (solo el cálculo, no el dibujo)
    t_par: int
    acum_seq: int              # ns acumulados, sin contar el primer paso (calentamiento)
    acum_par: int
    seq: bytes                 # tablero secuencial, n*n bytes con 0/1
    par: bytes
    error: str | None = None


class Simulador:
    def __init__(self, n: int, workers: int):
        self.n = n
        self.seq = make_engine("sequential", n, n)
        self.par = make_engine("threads", n, n, workers)
        self.retardo = 0.05              # s entre generaciones
        self.corriendo = False
        self.ultimo: Frame | None = None

        self.lock = threading.Lock()     # protege los motores
        self.cv = threading.Condition()  # despierta al hilo (iniciar, paso, cerrar)
        self.pasos_pedidos = 0
        self.salir = False
        self.generacion = self.pasos = self.acum_seq = self.acum_par = 0
        self.t_seq = self.t_par = 0
        self.id = 0

        self.hilo = threading.Thread(target=self.bucle, daemon=True)
        self.hilo.start()

    # ---------- órdenes desde la interfaz ----------

    def iniciar(self):
        with self.cv:
            self.corriendo = True
            self.cv.notify()

    def pausar(self):
        with self.cv:
            self.corriendo = False

    def un_paso(self):
        with self.cv:
            if not self.corriendo:
                self.pasos_pedidos += 1
                self.cv.notify()

    def cargar(self, grid):
        """Reemplaza el tablero (lista de filas o n*n bytes) en los dos motores y reinicia las métricas."""
        self.pausar()
        with self.lock:
            self.seq.load(grid)
            self.par.load(grid)
            self.generacion = self.pasos = self.acum_seq = self.acum_par = 0
            self.t_seq = self.t_par = 0
            self.publicar()

    def pintar(self, celdas, valor: int):
        self.pausar()
        with self.lock:
            for i, j in celdas:
                self.seq.board[i][j] = valor
                self.par.board[i][j] = valor
            self.publicar()

    def tablero(self) -> bytes:
        with self.lock:
            return self.seq.grid()

    def cerrar(self):
        with self.cv:
            self.salir = True
            self.corriendo = False
            self.cv.notify()
        self.hilo.join()
        self.seq.close()
        self.par.close()

    # ---------- hilo de simulación ----------

    def bucle(self):
        while True:
            with self.cv:
                while not (self.salir or self.corriendo or self.pasos_pedidos):
                    self.cv.wait()
                if self.salir:
                    return
            with self.lock:
                # la interfaz pudo pausar mientras esperábamos el lock
                manual = self.pasos_pedidos > 0 and not self.corriendo
                if not (self.corriendo or manual):
                    continue
                if manual:
                    self.pasos_pedidos -= 1
                self.avanzar()
            if self.corriendo:
                with self.cv:
                    self.cv.wait(self.retardo)

    def avanzar(self):
        try:
            r_seq = self.seq.step()
            r_par = self.par.step()
            raw_seq, raw_par = self.seq.grid(), self.par.grid()
        except Exception as e:
            self.corriendo = False
            self.publicar(f"ERROR: {e}. Cambia tamaño/workers para recrear los motores.")
            return
        self.generacion += 1
        self.pasos += 1
        self.t_seq, self.t_par = r_seq.compute_ns, r_par.compute_ns
        if self.pasos > 1:
            self.acum_seq += self.t_seq
            self.acum_par += self.t_par
        if raw_seq != raw_par:
            self.corriendo = False
            self.publicar("ERROR: los tableros secuencial y paralelo difieren", raw_seq, raw_par)
            return
        self.publicar(None, raw_seq, raw_par)

    def publicar(self, error=None, raw_seq=None, raw_par=None):
        # se llama con self.lock tomado
        raw_seq = raw_seq if raw_seq is not None else self.seq.grid()
        raw_par = raw_par if raw_par is not None else self.par.grid()
        self.id += 1
        self.ultimo = Frame(self.id, self.generacion, raw_seq.count(1), self.t_seq, self.t_par,
                            self.acum_seq, self.acum_par, raw_seq, raw_par, error)
