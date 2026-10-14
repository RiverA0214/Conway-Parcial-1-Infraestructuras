"""Zoom y desplazamiento del tablero. Lógica pura, sin Tk.

Una sola Vista la comparten los dos tableros, así que siempre muestran la misma zona.

Escala = píxeles por célula (una fracción). Hay dos formas de mostrar el tablero:
  - recortada: la escala es un entero (x1, x2, x4...) y el tablero no cabe en el panel;
    se ve un recorte de `panel // zoom` células por lado y se puede desplazar.
  - completa: el tablero entero cabe en el panel (nivel "ajustado" o tableros chicos);
    si la escala es menor que 1 se omiten células (subsample).
"""

from fractions import Fraction

ZOOMS = (1, 2, 4, 8, 16)


def limitar(x, minimo, maximo):
    return max(minimo, min(maximo, x))


class Vista:
    def __init__(self, panel: int):
        self.panel = panel               # lado del panel en píxeles
        self.n = 0
        self.niveles = [Fraction(1)]     # escalas disponibles, de menor a mayor
        self.nivel = 0
        self.ox = self.oy = 0.0          # esquina superior izquierda del recorte, en células

    def configurar(self, n: int):
        self.n = n
        ajustado = Fraction(self.panel, n)                     # escala a la que cabe completo
        self.niveles = sorted({ajustado, *map(Fraction, ZOOMS)})
        # se arranca en la mayor escala <= max(1, ajustado): x1 si no cabe, o llenando el panel si sobra espacio
        inicial = max(e for e in self.niveles if e <= max(1, ajustado))
        self.nivel = self.niveles.index(inicial)
        self.ox = self.oy = 0.0

    # ---------- geometría ----------

    @property
    def escala(self) -> Fraction:
        return self.niveles[self.nivel]

    @property
    def zoom(self) -> int:               # factor de ampliación (numerador)
        return self.escala.numerator

    @property
    def sub(self) -> int:                # factor de reducción (denominador)
        return self.escala.denominator

    @property
    def recorta(self) -> bool:
        return self.sub == 1 and self.n * self.zoom > self.panel

    @property
    def visibles(self) -> int:
        """Células por lado que se ven (todas, si el tablero cabe completo)."""
        return self.panel // self.zoom if self.recorta else self.n

    @property
    def lado(self) -> int:
        """Píxeles por lado que ocupa el tablero cuando se muestra completo."""
        return -(-self.n // self.sub) * self.zoom

    def region(self) -> tuple[int, int, int]:
        """(fila, columna, células por lado) de la esquina del recorte."""
        v = self.visibles
        maximo = self.n - v
        return int(round(limitar(self.oy, 0, maximo))), int(round(limitar(self.ox, 0, maximo))), v

    def origen_imagen(self) -> tuple[int, int]:
        """Dónde se pone la imagen en el panel: pegada arriba a la izquierda, o centrada si cabe completa."""
        if self.recorta:
            return 0, 0
        m = (self.panel - self.lado) // 2
        return m, m

    def celda(self, x: int, y: int) -> tuple[int, int]:
        """Célula (fila, columna) bajo el píxel (x, y) del panel."""
        if self.recorta:
            i0, j0, v = self.region()
            return (i0 + limitar(y // self.zoom, 0, v - 1),
                    j0 + limitar(x // self.zoom, 0, v - 1))
        m, _ = self.origen_imagen()
        return (limitar((y - m) * self.n // self.lado, 0, self.n - 1),
                limitar((x - m) * self.n // self.lado, 0, self.n - 1))

    # ---------- acciones ----------

    def cambiar_zoom(self, pasos: int, x: int, y: int) -> bool:
        """Sube (+) o baja (-) de nivel manteniendo la célula bajo (x, y) en su sitio. True si cambió."""
        nuevo = limitar(self.nivel + pasos, 0, len(self.niveles) - 1)
        if nuevo == self.nivel:
            return False
        i, j = self.celda(x, y)
        self.nivel = nuevo
        if self.recorta:
            self.oy = limitar(i - y / self.zoom, 0, self.n - self.visibles)
            self.ox = limitar(j - x / self.zoom, 0, self.n - self.visibles)
        return True

    def mover(self, dx: float, dy: float):
        """Desplaza el recorte dx, dy píxeles."""
        if self.recorta:
            maximo = self.n - self.visibles
            self.ox = limitar(self.ox + dx / self.zoom, 0, maximo)
            self.oy = limitar(self.oy + dy / self.zoom, 0, maximo)

    def barra(self, eje: str, *args):
        """Atiende el comando de una scrollbar de Tk: ('moveto', f) o ('scroll', n, 'units'|'pages')."""
        if not self.recorta:
            return
        v = self.visibles
        actual = self.ox if eje == "x" else self.oy
        if args[0] == "moveto":
            nuevo = float(args[1]) * self.n
        else:
            nuevo = actual + int(args[1]) * (v if args[2] == "pages" else max(1, v // 10))
        nuevo = limitar(nuevo, 0, self.n - v)
        if eje == "x":
            self.ox = nuevo
        else:
            self.oy = nuevo

    def rango_barras(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Posición de las scrollbars: ((x0, x1), (y0, y1)) como fracciones del tablero."""
        if not self.recorta:
            return (0.0, 1.0), (0.0, 1.0)
        i0, j0, v = self.region()
        return (j0 / self.n, (j0 + v) / self.n), (i0 / self.n, (i0 + v) / self.n)

    def texto(self) -> str:
        if self.recorta:
            i0, j0, v = self.region()
            return f"x{self.zoom} · filas {i0 + 1}–{i0 + v} · columnas {j0 + 1}–{j0 + v} de {self.n}"
        if self.sub > 1 and self.zoom == 1:
            return f"ajustado · 1 de cada {self.sub} celdas"
        return f"ajustado · x{float(self.escala):g}" if self.escala != 1 else "x1 · tablero completo"
