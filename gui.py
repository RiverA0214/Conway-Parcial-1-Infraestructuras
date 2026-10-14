"""Interfaz gráfica: Juego de la Vida con un motor secuencial y uno paralelo lado a lado."""

import customtkinter as ctk

from life.core import empty_grid, random_grid
from life.engines import make_engine, runtime_info
from life.patterns import PATTERNS, place
from gui_tablero import Tablero

TAMANOS = ["100", "500", "1000"]
MODOS = {"Hilos": "threads", "Procesos": "processes"}
WORKERS = ["1", "2", "4", "8", "12"]


def ms(ns):
    return f"{ns / 1e6:.2f}"


def razon(a, b):
    return f"{a / b:.2f}x" if b else "-"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Juego de la Vida: secuencial vs paralelo")
        self.corriendo = False
        self.pendiente = None
        self.seq = None
        self.par = None
        self.n = 0
        self.tablero = Tablero(self, self.alternar)
        self.tablero.pack(side="left", padx=8, pady=8)
        self.construir_panel()
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.recrear()

    def construir_panel(self):
        panel = ctk.CTkFrame(self)
        panel.pack(side="right", fill="y", padx=8, pady=8)

        info = runtime_info()
        gil = "activo" if info["gil_enabled"] else "desactivado"
        texto = f"Python {info['python_version']} | GIL {gil} | {info['cpu_count']} CPUs"
        ctk.CTkLabel(panel, text=texto).pack(pady=(8, 4))

        self.tamano = self.opcion(panel, "Tamaño", TAMANOS, "100")
        self.modo = self.opcion(panel, "Modo paralelo", list(MODOS), "Hilos")
        self.workers = self.opcion(panel, "Workers", WORKERS, "4")
        self.patron = self.opcion(panel, "Patrón", list(PATTERNS), "glider", recrear=False)
        self.boton(panel, "Colocar", self.colocar)

        fila = ctk.CTkFrame(panel, fg_color="transparent")
        fila.pack(pady=4)
        self.boton(fila, "Aleatorio", self.aleatorio, lado="left")
        self.boton(fila, "Limpiar", self.limpiar, lado="left")
        fila = ctk.CTkFrame(panel, fg_color="transparent")
        fila.pack(pady=4)
        self.boton(fila, "Paso", self.un_paso, lado="left")
        self.boton_iniciar = self.boton(fila, "Iniciar", self.alternar_corriendo, lado="left")

        ctk.CTkLabel(panel, text="Retardo (ms)").pack()
        self.retardo = ctk.CTkSlider(panel, from_=0, to=500, number_of_steps=50)
        self.retardo.set(50)
        self.retardo.pack(padx=10, pady=(0, 8))

        self.metricas = ctk.CTkLabel(panel, justify="left", font=ctk.CTkFont(family="monospace"))
        self.metricas.pack(padx=10, pady=8)
        self.error = ctk.CTkLabel(panel, text="", text_color="red", wraplength=240)
        self.error.pack(padx=10, pady=4)

    def opcion(self, panel, titulo, valores, inicial, recrear=True):
        ctk.CTkLabel(panel, text=titulo).pack()
        comando = (lambda _: self.recrear()) if recrear else None
        menu = ctk.CTkOptionMenu(panel, values=valores, command=comando)
        menu.set(inicial)
        menu.pack(pady=(0, 6))
        return menu

    def boton(self, padre, texto, comando, lado=None):
        b = ctk.CTkButton(padre, text=texto, command=comando, width=100)
        if lado:
            b.pack(side=lado, padx=3)
        else:
            b.pack(pady=4)
        return b

    def cerrar_motores(self):
        for motor in (self.seq, self.par):
            if motor:
                motor.close()
        self.seq = self.par = None

    def recrear(self):
        self.pausar()
        self.cerrar_motores()
        self.n = int(self.tamano.get())
        workers = int(self.workers.get())
        self.seq = make_engine("sequential", self.n, self.n)
        self.par = make_engine(MODOS[self.modo.get()], self.n, self.n, workers)
        self.tablero.configurar(self.n)
        self.cargar(random_grid(self.n, self.n))

    def cargar(self, grid):
        self.seq.load(grid)
        self.par.load(grid)
        self.generacion = 0
        self.pasos = 0
        self.t_seq = self.t_par = 0
        self.acum_seq = self.acum_par = 0
        self.vivas = sum(map(sum, grid))
        self.error.configure(text="")
        self.refrescar()

    def refrescar(self):
        self.tablero.dibujar(self.seq.board)
        t = self.t_seq, self.t_par
        self.metricas.configure(text=(
            f"Generación: {self.generacion}\n"
            f"Células vivas: {self.vivas}\n\n"
            f"Último paso\n"
            f"  Secuencial: {ms(t[0])} ms\n"
            f"  Paralelo:   {ms(t[1])} ms\n"
            f"  Speedup:    {razon(*t)}\n\n"
            f"Acumulado\n"
            f"  Secuencial: {ms(self.acum_seq)} ms\n"
            f"  Paralelo:   {ms(self.acum_par)} ms\n"
            f"  Speedup:    {razon(self.acum_seq, self.acum_par)}"))

    def aleatorio(self):
        self.pausar()
        self.cargar(random_grid(self.n, self.n, seed=None))

    def limpiar(self):
        self.pausar()
        self.cargar(empty_grid(self.n, self.n))

    def colocar(self):
        patron = PATTERNS[self.patron.get()]
        alto, ancho = len(patron), max(map(len, patron))
        buf = bytearray(self.seq.grid())
        place(buf, self.n, self.n, patron, (self.n - alto) // 2, (self.n - ancho) // 2)
        self.cargar([list(buf[i * self.n:(i + 1) * self.n]) for i in range(self.n)])

    def alternar(self, i, j):
        if self.corriendo:
            return
        grid = [list(fila) for fila in self.seq.board]
        grid[i][j] = 1 - grid[i][j]
        generacion = self.generacion
        self.cargar(grid)
        self.generacion = generacion
        self.refrescar()

    def un_paso(self):
        if self.corriendo:
            return
        self.paso()

    def paso(self):
        try:
            r_seq = self.seq.step()
            r_par = self.par.step()
        except Exception as e:
            self.pausar()
            self.error.configure(text=f"ERROR: {e}. Cambia tamaño/modo/workers para recrear los motores.")
            return
        if self.seq.board != self.par.board:
            self.pausar()
            self.error.configure(text="ERROR: los tableros secuencial y paralelo difieren")
            return
        self.generacion += 1
        self.pasos += 1
        self.vivas = r_seq.alive
        self.t_seq, self.t_par = r_seq.compute_ns, r_par.compute_ns
        if self.pasos > 1:
            self.acum_seq += self.t_seq
            self.acum_par += self.t_par
        self.refrescar()

    def alternar_corriendo(self):
        if self.corriendo:
            self.pausar()
        else:
            self.corriendo = True
            self.boton_iniciar.configure(text="Pausar")
            self.bucle()

    def pausar(self):
        self.corriendo = False
        if self.pendiente:
            self.after_cancel(self.pendiente)
            self.pendiente = None
        self.boton_iniciar.configure(text="Iniciar")

    def bucle(self):
        if not self.corriendo:
            return
        self.paso()
        if self.corriendo:
            self.pendiente = self.after(int(self.retardo.get()), self.bucle)

    def cerrar(self):
        self.pausar()
        self.cerrar_motores()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
