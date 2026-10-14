import time
import random
import threading
import tkinter as tk
from tkinter import ttk

from juego_vida import work_section, split_rows, make_padded


COLOR_VIVA = "#2b2b2b"
COLOR_MUERTA = "#ffffff"
COLOR_LINEA = "#dddddd"


def par_step(read: list[list[int]], write: list[list[int]], num_threads: int) -> bool:
    # Una sola generación en paralelo: cada hilo lee la matriz completa
    # y escribe solo en su bloque de filas de `write`; al terminar (join)
    # `write` ya contiene la nueva generación completa.
    n = len(read) - 2
    num_threads = max(1, min(num_threads, n))
    ranges = split_rows(n, num_threads)
    changed = [False] * num_threads

    def worker(t: int):
        start, end = ranges[t]
        changed[t] = work_section(read, write, start, end)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
    for th in threads: th.start()
    for th in threads: th.join()

    return any(changed)


class GameOfLifeApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Juego de la Vida")

        self.n = 30
        self.new_boards()
        self.running = False
        self.after_id = None
        self.generation = 1
        self.total_time = 0.0
        self.count = 0
        self.paint_state = 1

        # --- controles ---
        controls = ttk.Frame(root, padding=8)
        controls.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(controls, text="Tamaño:").pack(side=tk.LEFT)
        self.size_var = tk.IntVar(value=self.n)
        tk.Spinbox(controls, from_=5, to=150, width=4, textvariable=self.size_var).pack(side=tk.LEFT)
        ttk.Button(controls, text="Aplicar", command=self.resize).pack(side=tk.LEFT, padx=(2, 12))

        ttk.Label(controls, text="Modo:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="Secuencial")
        mode = ttk.Combobox(controls, textvariable=self.mode_var, values=["Secuencial", "Paralelo"],
                            state="readonly", width=11)
        mode.pack(side=tk.LEFT)
        mode.bind("<<ComboboxSelected>>", lambda e: self.reset_stats())

        ttk.Label(controls, text="Hilos:").pack(side=tk.LEFT, padx=(12, 0))
        self.threads_var = tk.IntVar(value=4)
        tk.Spinbox(controls, from_=1, to=32, width=3, textvariable=self.threads_var,
                   command=self.reset_stats).pack(side=tk.LEFT)

        ttk.Label(controls, text="Espera (ms):").pack(side=tk.LEFT, padx=(12, 0))
        self.delay_var = tk.IntVar(value=200)
        ttk.Scale(controls, from_=0, to=1000, variable=self.delay_var, length=120,
                  command=lambda v: self.delay_label.config(text=f"{int(float(v))}")).pack(side=tk.LEFT)
        self.delay_label = ttk.Label(controls, text="200", width=4)
        self.delay_label.pack(side=tk.LEFT)

        buttons = ttk.Frame(root, padding=(8, 0, 8, 8))
        buttons.pack(side=tk.TOP, fill=tk.X)
        self.start_btn = ttk.Button(buttons, text="Iniciar", command=self.toggle)
        self.start_btn.pack(side=tk.LEFT)
        ttk.Button(buttons, text="Paso", command=self.single_step).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Aleatorio", command=self.randomize).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Glider", command=self.glider).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Limpiar", command=self.clear).pack(side=tk.LEFT, padx=4)

        # --- tablero ---
        self.canvas = tk.Canvas(root, bg=COLOR_MUERTA, highlightthickness=0)
        self.canvas.pack(side=tk.TOP, padx=8)
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)

        # --- estadísticas ---
        self.stats = ttk.Label(root, padding=8, font=("Consolas", 10))
        self.stats.pack(side=tk.TOP, fill=tk.X)

        self.build_grid()
        self.update_stats()

    # ---------- tablero ----------

    def new_boards(self):
        # matriz actual y buffer de escritura (ping-pong), ambas con padding
        self.mat = make_padded(self.n)
        self.buf = make_padded(self.n)

    def build_grid(self):
        self.canvas.delete("all")
        self.cell = max(4, min(20, 640 // self.n))
        size = self.n * self.cell
        self.canvas.config(width=size, height=size)
        self.rects = []
        for i in range(self.n):
            row = []
            for j in range(self.n):
                x, y = j * self.cell, i * self.cell
                color = COLOR_VIVA if self.mat[i + 1][j + 1] else COLOR_MUERTA
                row.append(self.canvas.create_rectangle(x, y, x + self.cell, y + self.cell,
                                                        fill=color, outline=COLOR_LINEA))
            self.rects.append(row)

    def draw_cell(self, i: int, j: int):
        color = COLOR_VIVA if self.mat[i + 1][j + 1] else COLOR_MUERTA
        self.canvas.itemconfig(self.rects[i][j], fill=color)

    def redraw(self, old: list[list[str]]):
        # solo se repintan las celdas que cambiaron
        for i in range(self.n):
            for j in range(self.n):
                if old[i + 1][j + 1] != self.mat[i + 1][j + 1]:
                    self.draw_cell(i, j)

    def cell_at(self, event):
        i, j = event.y // self.cell, event.x // self.cell
        if 0 <= i < self.n and 0 <= j < self.n:
            return i, j
        return None

    def on_press(self, event):
        if self.running: return
        pos = self.cell_at(event)
        if pos is None: return
        i, j = pos
        # si haces clic en una viva, arrastrar borra; si es muerta, arrastrar pinta
        self.paint_state = 0 if self.mat[i + 1][j + 1] else 1
        self.mat[i + 1][j + 1] = self.paint_state
        self.draw_cell(i, j)

    def on_drag(self, event):
        if self.running: return
        pos = self.cell_at(event)
        if pos is None: return
        i, j = pos
        if self.mat[i + 1][j + 1] != self.paint_state:
            self.mat[i + 1][j + 1] = self.paint_state
            self.draw_cell(i, j)

    # ---------- botones ----------

    def resize(self):
        self.stop()
        try:
            n = int(self.size_var.get())
        except (tk.TclError, ValueError):
            return
        self.n = max(5, min(150, n))
        self.new_boards()
        self.generation = 1
        self.reset_stats()
        self.build_grid()

    def randomize(self):
        self.stop()
        self.new_boards()
        for i in range(1, self.n + 1):
            for j in range(1, self.n + 1):
                if random.random() < 0.3:
                    self.mat[i][j] = 1
        self.generation = 1
        self.reset_stats()
        self.build_grid()

    def glider(self):
        self.clear()
        for i, j in [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]:
            if i < self.n and j < self.n:
                self.mat[i + 1][j + 1] = 1
                self.draw_cell(i, j)

    def clear(self):
        self.stop()
        self.new_boards()
        self.generation = 1
        self.reset_stats()
        self.build_grid()

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.running = True
            self.start_btn.config(text="Pausar")
            self.tick()

    def stop(self):
        self.running = False
        self.start_btn.config(text="Iniciar")
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def single_step(self):
        if not self.running:
            self.step()

    # ---------- simulación ----------

    def step(self) -> bool:
        try:
            num_threads = int(self.threads_var.get())
        except (tk.TclError, ValueError):
            num_threads = 1

        # solo se mide el cálculo de la generación, no el dibujo ni la espera
        start = time.perf_counter()
        if self.mode_var.get() == "Secuencial":
            changed = work_section(self.mat, self.buf, 0, self.n)
        else:
            changed = par_step(self.mat, self.buf, num_threads)
        elapsed = time.perf_counter() - start

        old = self.mat
        self.mat, self.buf = self.buf, old   # ping-pong
        self.generation += 1
        self.last_time = elapsed
        self.total_time += elapsed
        self.count += 1
        self.redraw(old)
        self.update_stats("Estable (no hay cambios)" if not changed else None)
        return changed

    def tick(self):
        if not self.running: return
        changed = self.step()
        if not changed:
            self.stop()
            return
        delay = int(self.delay_var.get())
        self.after_id = self.root.after(delay, self.tick)

    def reset_stats(self):
        self.total_time = 0.0
        self.count = 0
        self.last_time = 0.0
        self.update_stats()

    def update_stats(self, extra: str | None = None):
        avg = self.total_time / self.count if self.count else 0.0
        modo = self.mode_var.get()
        if modo == "Paralelo":
            modo += f" ({self.threads_var.get()} hilos)"
        text = (f"Generación: {self.generation:<6} Modo: {modo}\n"
                f"Cálculo último frame: {getattr(self, 'last_time', 0.0) * 1000:8.3f} ms   "
                f"Promedio: {avg * 1000:8.3f} ms  ({self.count} frames)")
        if extra:
            text += f"\n{extra}"
        self.stats.config(text=text)


if __name__ == '__main__':
    root = tk.Tk()
    GameOfLifeApp(root)
    root.mainloop()
