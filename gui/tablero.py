"""Un tablero: título, imagen de n x n píxeles ampliada o reducida a LADO píxeles, pintado con el mouse y métricas propias."""

import math
import tkinter as tk

import customtkinter as ctk

from .render import to_ppm

LADO = 400


def linea(i0, j0, i1, j1):
    # celdas entre dos puntos (Bresenham), incluye ambos extremos
    celdas = []
    di, dj = abs(i1 - i0), abs(j1 - j0)
    si = 1 if i0 < i1 else -1
    sj = 1 if j0 < j1 else -1
    err = dj - di
    while True:
        celdas.append((i0, j0))
        if (i0, j0) == (i1, j1):
            return celdas
        e2 = 2 * err
        if e2 > -di:
            err -= di
            j0 += sj
        if e2 < dj:
            err += dj
            i0 += si


class Tablero(ctk.CTkFrame):
    def __init__(self, master, al_pintar):
        super().__init__(master)
        self.n = 0
        self.al_pintar = al_pintar
        self.valor = 1
        self.anterior = None
        self.imagen = None
        self.imagen_vista = None

        self.titulo = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=15, weight="bold"))
        self.titulo.pack(pady=(6, 0))
        self.canvas = tk.Canvas(self, width=LADO, height=LADO, bg="#111827",
                                highlightthickness=0, cursor="crosshair")
        self.canvas.pack(padx=6, pady=6)
        self.metricas = ctk.CTkLabel(self, text="", font=ctk.CTkFont(family="monospace"))
        self.metricas.pack(pady=(0, 6))

        self.canvas.bind("<Button-1>", lambda e: self.empezar(e, 1))
        self.canvas.bind("<B1-Motion>", self.mover)
        self.canvas.bind("<ButtonRelease-1>", self.terminar)
        self.canvas.bind("<Button-3>", lambda e: self.empezar(e, 0))
        self.canvas.bind("<B3-Motion>", self.mover)
        self.canvas.bind("<ButtonRelease-3>", self.terminar)

    def configurar(self, n):
        # escala LADO/n como fracción zoom/subsample: 100 -> x4, 500 -> x4/5, 1000 -> x2/5
        self.n = n
        self.imagen = tk.PhotoImage(width=n, height=n)
        comun = math.gcd(LADO, n)
        self.escala = ("-zoom", LADO // comun, LADO // comun, "-subsample", n // comun, n // comun)
        self.imagen_vista = tk.PhotoImage()
        self.canvas.delete("all")
        self.canvas.create_image(LADO // 2, LADO // 2, image=self.imagen_vista, anchor="center")

    def dibujar(self, raw):
        # raw: n*n bytes con 0/1. La imagen tiene 1 píxel por célula y se escala al copiarla.
        self.imagen.configure(data=to_ppm(raw, self.n), format="PPM")
        self.imagen_vista.blank()
        self.imagen_vista.tk.call(self.imagen_vista, "copy", self.imagen, *self.escala)

    def celda(self, evento):
        # la imagen está centrada en el canvas
        ancho = self.imagen_vista.width()
        x = evento.x - (LADO - ancho) // 2
        y = evento.y - (LADO - ancho) // 2
        i, j = y * self.n // ancho, x * self.n // ancho
        return min(max(i, 0), self.n - 1), min(max(j, 0), self.n - 1)

    def empezar(self, evento, valor):
        self.valor = valor
        self.anterior = None
        self.mover(evento)

    def mover(self, evento):
        actual = self.celda(evento)
        celdas = linea(*self.anterior, *actual) if self.anterior else [actual]
        self.anterior = actual
        self.al_pintar(celdas, self.valor)

    def terminar(self, evento):
        self.anterior = None
