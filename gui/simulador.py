"""Simulación en segundo plano: un hilo calcula las generaciones y publica el último frame.

La interfaz nunca espera al cálculo: lee `ultimo` cuando le conviene y se salta los
frames que no alcanzó a dibujar. Este módulo no usa Tk.

Quién toca los motores: el hilo de simulación (al avanzar) y la interfaz (al pintar o
cargar), siempre con `self.lock`, así que nunca lo hacen a la vez.
"""

import threading
from dataclasses import dataclass

from life.comparacion import Resultado, comparar
from life.cronometro import medir_ciclos
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
        self.resultado: Resultado | None = None   # última corrida de X ciclos
        self.ocupado = False                      # corriendo X ciclos: ignora el resto de órdenes

        self.lock = threading.Lock()     # protege los motores
        self.cv = threading.Condition()  # despierta al hilo (iniciar, paso, cerrar)
        self.pasos_pedidos = 0
        self.ciclos_pedidos = 0
        self.salir = False
        self.generacion = self.pasos = self.acum_seq = self.acum_par = 0
        self.t_seq = self.t_par = 0
        self.id = 0

        self.hilo = threading.Thread(target=self.bucle, daemon=True)
        self.hilo.start()

    # ---------- órdenes desde la interfaz ----------

    def iniciar(self):
        with self.cv:
            if self.ocupado:
                return
            self.corriendo = True
            self.pasos_pedidos = 0
            self.cv.notify()

    def pausar(self):
        with self.cv:
            self.corriendo = False

    def un_paso(self):
        with self.cv:
            if not self.corriendo and not self.ocupado:
                self.pasos_pedidos += 1
                self.cv.notify()

    def correr_ciclos(self, x: int):
        """Pausa y mide x ciclos en cada motor, desde el tablero actual. Se ejecuta en el hilo de simulación."""
        with self.cv:
            if self.ocupado or x < 1:
                return
            self.corriendo = False
            self.ocupado = True
            self.pasos_pedidos = 0
            self.ciclos_pedidos = x
            self.cv.notify()

    def cargar(self, grid):
        """Reemplaza el tablero (lista de filas o n*n bytes) en los dos motores y reinicia las métricas."""
        if self.ocupado:
            return
        self.pausar()
        with self.lock:
            self.seq.load(grid)
            self.par.load(grid)
            self.generacion = self.pasos = self.acum_seq = self.acum_par = 0
            self.t_seq = self.t_par = 0
            self.publicar()

    def pintar(self, celdas, valor: int):
        if self.ocupado:
            return
        self.pausar()
        with self.lock:
            self.seq.set_cells(celdas, valor)
            self.par.set_cells(celdas, valor)
            self.publicar()

    def tablero(self) -> bytes:
        with self.lock:
            return self.seq.grid()

    def cerrar(self):
        with self.cv:
            self.salir = True
            self.corriendo = False
            self.cv.notify()
        self.hilo.join(5)                # si está midiendo, el hilo cierra los motores al terminar

    # ---------- hilo de simulación ----------

    def bucle(self):
        try:
            self.repetir()
        finally:
            self.seq.close()
            self.par.close()

    def repetir(self):
        while True:
            with self.cv:
                while not (self.salir or self.corriendo or self.pasos_pedidos or self.ciclos_pedidos):
                    self.cv.wait()
                if self.salir:
                    return
                x, self.ciclos_pedidos = self.ciclos_pedidos, 0
            if x:
                try:
                    with self.lock:
                        self.medir(x)
                finally:
                    self.ocupado = False
                continue
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
            t_seq = medir_ciclos(self.seq, 1)[1]
            t_par = medir_ciclos(self.par, 1)[1]
            raw_seq, raw_par = self.seq.grid(), self.par.grid()
        except Exception as e:
            self.corriendo = False
            self.publicar(f"ERROR: {e}. Cambia tamaño/workers para recrear los motores.")
            return
        self.generacion += 1
        self.pasos += 1
        self.t_seq, self.t_par = int(t_seq * 1e9), int(t_par * 1e9)
        if self.pasos > 1:
            self.acum_seq += self.t_seq
            self.acum_par += self.t_par
        if raw_seq != raw_par:
            self.corriendo = False
            self.publicar("ERROR: los tableros secuencial y paralelo difieren", raw_seq, raw_par)
            return
        self.publicar(None, raw_seq, raw_par)

    def medir(self, x):
        # se llama con self.lock tomado; los dos motores parten del mismo tablero
        try:
            self.resultado = comparar(self.seq, self.par, x)
        except Exception as e:
            error = f"ERROR: {e}. Cambia tamaño/workers para recrear los motores."
            self.resultado = Resultado(x, 0, 0, (0, 0), (0, 0), 0, 0, error)
            self.publicar(error)
            return
        r = self.resultado
        self.generacion += x + 1             # los x ciclos medidos más el de calentamiento
        self.t_seq, self.t_par = int(r.ultimo_seq * 1e9), int(r.ultimo_par * 1e9)
        self.publicar(r.error)

    def publicar(self, error=None, raw_seq=None, raw_par=None):
        # se llama con self.lock tomado
        raw_seq = raw_seq if raw_seq is not None else self.seq.grid()
        raw_par = raw_par if raw_par is not None else self.par.grid()
        self.id += 1
        self.ultimo = Frame(self.id, self.generacion, raw_seq.count(1), self.t_seq, self.t_par,
                            self.acum_seq, self.acum_par, raw_seq, raw_par, error)
