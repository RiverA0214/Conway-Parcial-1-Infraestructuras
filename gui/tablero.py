"""Un tablero: título, panel con zoom y desplazamiento, pintado con el mouse y métricas propias.

Qué parte se ve y a qué escala lo decide la Vista, que comparten los dos tableros.
Rueda del mouse: zoom (más allá de x1 se muestra el tablero completo, omitiendo células).
Scrollbars o arrastre con el botón central: desplazamiento. Clic izquierdo pinta, derecho borra.
"""

import tkinter as tk

import customtkinter as ctk

from .render import to_ppm
from .vista import Vista

LADO = 500          # píxeles por lado del panel; con 500 los tamaños 100, 500 y 1000 dan escalas exactas


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
    def __init__(self, master, vista: Vista, al_pintar, al_cambiar_vista):
        super().__init__(master)
        self.vista = vista
        self.al_pintar = al_pintar                  # (celdas, valor)
        self.al_cambiar_vista = al_cambiar_vista    # hay que redibujar los dos tableros
        self.n = 0
        self.raw = None                             # último frame: n*n bytes con 0/1
        self.imagen = tk.PhotoImage()               # recorte (o tablero completo) a 1 píxel por célula
        self.imagen_vista = None                    # lo que se ve: la imagen ya ampliada o reducida
        self.valor = 1
        self.anterior = None
        self.arrastre = None

        self.titulo = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=15, weight="bold"))
        self.titulo.pack(pady=(6, 0))

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(padx=6, pady=6)
        self.canvas = tk.Canvas(cuerpo, width=LADO, height=LADO, bg="#111827",
                                highlightthickness=0, cursor="crosshair")
        self.canvas.grid(row=0, column=0)
        self.barra_y = ctk.CTkScrollbar(cuerpo, orientation="vertical", command=lambda *a: self.barra("y", *a))
        self.barra_y.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.barra_x = ctk.CTkScrollbar(cuerpo, orientation="horizontal", command=lambda *a: self.barra("x", *a))
        self.barra_x.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        self.item = self.canvas.create_image(0, 0, anchor="nw")

        self.vista_txt = ctk.CTkLabel(self, text="", text_color="gray")
        self.vista_txt.pack()
        self.metricas = ctk.CTkLabel(self, text="", font=ctk.CTkFont(family="monospace"))
        self.metricas.pack(pady=(0, 6))

        self.canvas.bind("<Button-1>", lambda e: self.empezar(e, 1))
        self.canvas.bind("<B1-Motion>", self.mover)
        self.canvas.bind("<ButtonRelease-1>", self.terminar)
        self.canvas.bind("<Button-3>", lambda e: self.empezar(e, 0))
        self.canvas.bind("<B3-Motion>", self.mover)
        self.canvas.bind("<ButtonRelease-3>", self.terminar)
        self.canvas.bind("<MouseWheel>", lambda e: self.rueda(1 if e.delta > 0 else -1, e))   # Windows y macOS
        self.canvas.bind("<Button-4>", lambda e: self.rueda(1, e))                           # Linux
        self.canvas.bind("<Button-5>", lambda e: self.rueda(-1, e))
        self.canvas.bind("<ButtonPress-2>", self.empezar_arrastre)
        self.canvas.bind("<B2-Motion>", self.arrastrar)

    def configurar(self, n):
        self.n = n
        self.raw = None
        self.canvas.itemconfig(self.item, image="")

    # ---------- dibujo ----------

    def dibujar(self, raw):
        self.raw = raw
        self.redibujar()

    def redibujar(self):
        if self.raw is None:
            return
        v, n = self.vista, self.n
        if v.recorta:
            # solo se codifica la parte visible: n*n bytes -> un recorte de v x v células
            i0, j0, lado = v.region()
            pedazo = b"".join(self.raw[(i0 + r) * n + j0:(i0 + r) * n + j0 + lado] for r in range(lado))
            self.imagen.configure(data=to_ppm(pedazo, lado, lado), format="PPM")
            copia = ("-zoom", v.zoom, v.zoom)
        else:
            self.imagen.configure(data=to_ppm(self.raw, n, n), format="PPM")
            copia = ("-zoom", v.zoom, v.zoom, "-subsample", v.sub, v.sub)
        # una imagen nueva cada vez: copy no encoge una imagen que ya tiene tamaño
        self.imagen_vista = tk.PhotoImage()
        self.imagen_vista.tk.call(self.imagen_vista, "copy", self.imagen, *copia)
        self.canvas.itemconfig(self.item, image=self.imagen_vista)
        self.canvas.coords(self.item, *v.origen_imagen())
        (x0, x1), (y0, y1) = v.rango_barras()
        self.barra_x.set(x0, x1)
        self.barra_y.set(y0, y1)
        self.vista_txt.configure(text=v.texto())

    # ---------- zoom y desplazamiento ----------

    def rueda(self, pasos, evento):
        if self.vista.cambiar_zoom(pasos, evento.x, evento.y):
            self.al_cambiar_vista()

    def barra(self, eje, *args):
        self.vista.barra(eje, *args)
        self.al_cambiar_vista()

    def empezar_arrastre(self, evento):
        self.arrastre = (evento.x, evento.y)

    def arrastrar(self, evento):
        if self.arrastre:
            x, y = self.arrastre
            self.vista.mover(x - evento.x, y - evento.y)    # la imagen sigue al mouse
            self.arrastre = (evento.x, evento.y)
            self.al_cambiar_vista()

    # ---------- pintar ----------

    def empezar(self, evento, valor):
        self.valor = valor
        self.anterior = None
        self.mover(evento)

    def mover(self, evento):
        actual = self.vista.celda(evento.x, evento.y)
        celdas = linea(*self.anterior, *actual) if self.anterior else [actual]
        self.anterior = actual
        self.al_pintar(celdas, self.valor)

    def terminar(self, evento):
        self.anterior = None
