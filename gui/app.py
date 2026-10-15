"""Ventana principal: controles, dos tableros (secuencial y paralelo) y resumen de métricas.

No calcula nada: le pide al Simulador que avance y dibuja el último frame que este publicó.
"""

import customtkinter as ctk

from life.core import empty_grid, random_grid
from life.engines import runtime_info
from life.patterns import PATTERNS, place

from .simulador import Simulador
from .tablero import LADO, Tablero
from .vista import Vista

TAMANOS = {"100 × 100": 100, "500 × 500": 500, "1000 × 1000": 1000}   # filas × columnas
WORKERS = ["1", "2", "4", "8", "12"]
REFRESCO_MS = 33           # la interfaz mira si hay un frame nuevo ~30 veces por segundo


def ms(ns):
    return f"{ns / 1e6:.2f}"


def razon(a, b):
    return f"{a / b:.2f}x" if b else "-"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Juego de la Vida: secuencial vs paralelo")
        self.sim: Simulador | None = None
        self.n = 0
        self.dibujado = 0          # id del último frame dibujado
        self.vista = Vista(LADO)   # zoom y desplazamiento, compartidos por los dos tableros
        self.construir_controles()
        self.construir_tableros()
        self.construir_resumen()
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.recrear()
        self.update_idletasks()
        self.geometry(f"{self.winfo_reqwidth()}x{self.winfo_reqheight()}")
        self.after(REFRESCO_MS, self.refrescar)

    def construir_controles(self):
        barra = ctk.CTkFrame(self)
        barra.pack(fill="x", padx=8, pady=(8, 0))
        self.tamano = self.opcion(barra, "Tamaño (filas × columnas)", list(TAMANOS), "100 × 100", 120)
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
        self.retardo.configure(command=self.cambiar_retardo)
        self.retardo.pack(pady=6)

    def construir_tableros(self):
        zona = ctk.CTkFrame(self, fg_color="transparent")
        zona.pack(padx=8, pady=4)
        self.tab_seq = Tablero(zona, self.vista, self.pintar, self.redibujar)
        self.tab_seq.pack(side="left", padx=4)
        self.tab_par = Tablero(zona, self.vista, self.pintar, self.redibujar)
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

    # ---------- simulador ----------

    def recrear(self):
        # nuevo tamaño o workers: se crea otro simulador (con motores nuevos)
        if self.sim:
            self.sim.cerrar()
        self.n = TAMANOS[self.tamano.get()]
        workers = int(self.workers.get())
        self.sim = Simulador(self.n, workers)
        self.dibujado = 0          # el simulador nuevo numera sus frames desde 1
        self.cambiar_retardo(self.retardo.get())
        self.tab_par.titulo.configure(text=f"Paralelo: hilos x{workers}")
        self.vista.configurar(self.n)
        self.tab_seq.configurar(self.n)
        self.tab_par.configurar(self.n)
        self.error.configure(text="")
        self.sim.cargar(random_grid(self.n, self.n))

    def redibujar(self):
        self.tab_seq.redibujar()
        self.tab_par.redibujar()

    def cambiar_retardo(self, ms):
        if self.sim:
            self.sim.retardo = float(ms) / 1000

    def refrescar(self):
        # corre en el hilo de Tk cada REFRESCO_MS: dibuja el último frame si es nuevo
        frame = self.sim.ultimo
        if frame and frame.id != self.dibujado:
            self.dibujado = frame.id
            self.tab_seq.dibujar(frame.seq)
            self.tab_par.dibujar(frame.par)
            self.tab_seq.metricas.configure(text=f"Último: {ms(frame.t_seq)} ms | Acum: {ms(frame.acum_seq)} ms")
            self.tab_par.metricas.configure(text=f"Último: {ms(frame.t_par)} ms | Acum: {ms(frame.acum_par)} ms")
            self.generacion_txt.configure(text=str(frame.generacion))
            self.vivas_txt.configure(text=str(frame.vivas))
            self.speedup_ultimo.configure(text=razon(frame.t_seq, frame.t_par))
            self.speedup_acum.configure(text=razon(frame.acum_seq, frame.acum_par))
            self.error.configure(text=frame.error or "")
        self.boton_iniciar.configure(text="Pausar" if self.sim.corriendo else "Iniciar")
        self.after(REFRESCO_MS, self.refrescar)

    # ---------- botones ----------

    def aleatorio(self):
        self.sim.cargar(random_grid(self.n, self.n, seed=None))

    def limpiar(self):
        self.sim.cargar(empty_grid(self.n, self.n))

    def colocar(self):
        patron = PATTERNS[self.patron.get()]
        alto, ancho = len(patron), max(map(len, patron))
        self.sim.pausar()
        buf = bytearray(self.sim.tablero())
        place(buf, self.n, self.n, patron, (self.n - alto) // 2, (self.n - ancho) // 2)
        self.sim.cargar(bytes(buf))

    def un_paso(self):
        self.sim.un_paso()

    def alternar_corriendo(self):
        if self.sim.corriendo:
            self.sim.pausar()
        else:
            self.sim.iniciar()

    # ---------- pintar con el mouse ----------

    def pintar(self, celdas, valor):
        self.sim.pintar(celdas, valor)    # pausa la simulación y repinta

    def cerrar(self):
        self.sim.cerrar()
        self.destroy()
