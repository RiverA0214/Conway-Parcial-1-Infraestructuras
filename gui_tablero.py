"""Dibujo del tablero: una PhotoImage de n x n píxeles ampliada con zoom."""

import tkinter as tk

import customtkinter as ctk

LADO = 600
VIVA = "#34d399"
MUERTA = "#111827"


class Tablero(ctk.CTkFrame):
    def __init__(self, master, al_clic):
        super().__init__(master)
        self.n = 0
        self.zoom = 1
        self.al_clic = al_clic
        self.canvas = tk.Canvas(self, width=LADO, height=LADO, bg=MUERTA, highlightthickness=0)
        self.canvas.pack(padx=6, pady=6)
        self.canvas.bind("<Button-1>", self.clic)
        self.imagen = None
        self.imagen_zoom = None

    def configurar(self, n):
        self.n = n
        self.zoom = max(LADO // n, 1)
        self.imagen = tk.PhotoImage(width=n, height=n)
        self.imagen_zoom = self.imagen.zoom(self.zoom)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.imagen_zoom, anchor="nw")

    def dibujar(self, board):
        filas = ["{" + " ".join(VIVA if c else MUERTA for c in fila) + "}" for fila in board]
        self.imagen.put(" ".join(filas), to=(0, 0))
        self.imagen_zoom.tk.call(self.imagen_zoom, "copy", self.imagen, "-zoom", self.zoom)

    def clic(self, evento):
        i, j = evento.y // self.zoom, evento.x // self.zoom
        if 0 <= i < self.n and 0 <= j < self.n:
            self.al_clic(i, j)
