"""Dibujo del tablero: una imagen de n x n píxeles ampliada o reducida para ocupar LADO píxeles."""

import tkinter as tk

import customtkinter as ctk

LADO = 500
VIVA = bytes([52, 211, 153])
MUERTA = bytes([17, 24, 39])


class Tablero(ctk.CTkFrame):
    def __init__(self, master, al_clic):
        super().__init__(master)
        self.n = 0
        self.al_clic = al_clic
        self.canvas = tk.Canvas(self, width=LADO, height=LADO, bg="#111827", highlightthickness=0)
        self.canvas.pack(padx=6, pady=6)
        self.canvas.bind("<Button-1>", self.clic)
        self.imagen = None
        self.imagen_vista = None

    def configurar(self, n):
        # 100 -> se amplía x5, 500 -> tal cual, 1000 -> se reduce a la mitad
        self.n = n
        self.imagen = tk.PhotoImage(width=n, height=n)
        if n <= LADO:
            self.escala = ("-zoom", LADO // n)
        else:
            self.escala = ("-subsample", -(-n // LADO))
        self.imagen_vista = tk.PhotoImage()
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.imagen_vista, anchor="nw")

    def dibujar(self, board):
        # imagen PPM: cabecera + 3 bytes de color por célula, mucho más rápido que put() por píxel
        pixeles = b"".join(VIVA if c else MUERTA for fila in board for c in fila)
        self.imagen.configure(data=b"P6 %d %d 255\n" % (self.n, self.n) + pixeles, format="PPM")
        self.imagen_vista.blank()
        self.imagen_vista.tk.call(self.imagen_vista, "copy", self.imagen, *self.escala)

    def clic(self, evento):
        i, j = evento.y * self.n // LADO, evento.x * self.n // LADO
        if 0 <= i < self.n and 0 <= j < self.n:
            self.al_clic(i, j)
