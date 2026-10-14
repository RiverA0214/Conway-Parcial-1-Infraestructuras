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
        self.construir_controles()
        self.construir_tableros()
        self.construir_resumen()
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.recrear()
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")

    def construir_controles(self):
        barra = ctk.CTkFrame(self)
        barra.pack(fill="x", padx=8, pady=(8, 0))
        self.tamano = self.opcion(barra, "Tamaño", TAMANOS, "100", 80)
        self.modo = self.opcion(barra, "Modo", list(MODOS), "Hilos", 100)
        self.workers = self.opcion(barra, "Workers", WORKERS, "4", 70)
        self.patron = self.opcion(barra, "Patrón", list(PATTERNS), "glider", 110, recrear=False)
        self.boton(self.campo(barra, " "), "Colocar", self.colocar)
        barra = ctk.CTkFrame(self)
        barra.pack(fill="x", padx=8, pady=(4, 0))
        self.boton(self.campo(barra, " "), "Aleatorio", self.aleatorio)
        self.boton(self.campo(barra, " "), "Limpiar", self.limpiar)
        self.boton(self.campo(barra, " "), "Paso", self.un_paso)
        self.boton_iniciar = self.boton(self.campo(barra, " "), "Iniciar", self.alternar_corriendo)
        campo = self.campo(barra, "Retardo (ms)")
        self.retardo = ctk.CTkSlider(campo, from_=0, to=500, number_of_steps=50, width=110)
        self.retardo.set(50)
        self.retardo.pack(pady=6)

    def construir_tableros(self):
        zona = ctk.CTkFrame(self, fg_color="transparent")
        zona.pack(padx=8, pady=4)
        self.tab_seq = Tablero(zona, self.empezar_pintar, self.pintar, self.terminar_pintar)
        self.tab_seq.pack(side="left", padx=4)
        self.tab_par = Tablero(zona, self.empezar_pintar, self.pintar, self.terminar_pintar)
        self.tab_par.pack(side="left", padx=4)
        self.tab_seq.titulo.configure(text="Secuencial")

    def construir_resumen(self):
        franja = ctk.CTkFrame(self)
        franja.pack(fill="x", padx=8, pady=(0, 4))
        self.generacion_txt = self.dato(franja, "Generación")
        self.vivas_txt = self.dato(franja, "Células vivas")
        self.speedup_ultimo = self.dato(franja, "Speedup último paso")
        self.speedup_acum = self.dato(franja, "Speedup acumulado", grande=True)

        info = runtime_info()
        gil = "activo" if info["gil_enabled"] else "desactivado"
        texto = f"Python {info['python_version']} | GIL {gil} | {info['cpu_count']} CPUs"
        ctk.CTkLabel(self, text=texto).pack()
        self.error = ctk.CTkLabel(self, text="", text_color="red")
        self.error.pack()
        ctk.CTkLabel(self, text="Clic izquierdo: pintar · Clic derecho: borrar",
                     text_color="gray").pack(pady=(0, 6))

    def dato(self, padre, titulo, grande=False):
        caja = ctk.CTkFrame(padre, fg_color="transparent")
        caja.pack(side="left", expand=True, padx=10, pady=4)
        ctk.CTkLabel(caja, text=titulo).pack()
        tam = 28 if grande else 16
        valor = ctk.CTkLabel(caja, text="-", font=ctk.CTkFont(size=tam, weight="bold"))
        valor.pack()
        return valor

    def campo(self, barra, titulo):
        caja = ctk.CTkFrame(barra, fg_color="transparent")
        caja.pack(side="left", padx=4, pady=4)
        ctk.CTkLabel(caja, text=titulo, font=ctk.CTkFont(size=11)).pack()
        return caja

    def opcion(self, barra, titulo, valores, inicial, ancho, recrear=True):
        comando = (lambda _: self.recrear()) if recrear else None
        menu = ctk.CTkOptionMenu(self.campo(barra, titulo), values=valores, command=comando, width=ancho)
        menu.set(inicial)
        menu.pack()
        return menu

    def boton(self, padre, texto, comando):
        b = ctk.CTkButton(padre, text=texto, command=comando, width=80)
        b.pack()
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
        self.tab_par.titulo.configure(text=f"Paralelo: {self.modo.get()} x{workers}")
        self.tab_seq.configurar(self.n)
        self.tab_par.configurar(self.n)
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
        self.tab_seq.dibujar(self.seq.board)
        self.tab_par.dibujar(self.par.board)
        self.tab_seq.metricas.configure(text=f"Último: {ms(self.t_seq)} ms | Acum: {ms(self.acum_seq)} ms")
        self.tab_par.metricas.configure(text=f"Último: {ms(self.t_par)} ms | Acum: {ms(self.acum_par)} ms")
        self.generacion_txt.configure(text=str(self.generacion))
        self.vivas_txt.configure(text=str(self.vivas))
        self.speedup_ultimo.configure(text=razon(self.t_seq, self.t_par))
        self.speedup_acum.configure(text=razon(self.acum_seq, self.acum_par))

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

    def empezar_pintar(self):
        self.pausar()

    def pintar(self, celdas, valor):
        for i, j in celdas:
            self.seq.board[i][j] = valor
            self.par.board[i][j] = valor
        self.tab_seq.dibujar(self.seq.board)
        self.tab_par.dibujar(self.par.board)

    def terminar_pintar(self):
        self.vivas = sum(map(sum, self.seq.board))
        self.vivas_txt.configure(text=str(self.vivas))

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
