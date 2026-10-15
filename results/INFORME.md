# Informe: Juego de la Vida en paralelo (hilos con y sin GIL)

## 1. Objetivo

Implementar el Juego de la Vida de Conway en una versión secuencial (referencia) y en versión paralela con hilos, y medir cuánto se gana al paralelizar para tableros de 100x100, 500x500 y 1000x1000 con 1, 2, 4, 8 y 12 hilos. Como en Python la ganancia de los hilos depende del GIL, la comparación central es hilos con GIL contra hilos sin GIL, y todo se midió en tres configuraciones del intérprete: CPython 3.14 normal (con GIL), 3.14t free-threaded sin GIL y el mismo 3.14t con el GIL forzado.

## 2. Implementación

### 2.1 Reglas y kernel común

Las dos versiones usan el mismo kernel (`life/core.py`, función `step_rows`): tablero como lista de listas de 0/1, bordes muertos y la regla B3/S23 del enunciado (una célula viva sobrevive con 2 o 3 vecinos y muere con menos de 2 o más de 3; una muerta nace con exactamente 3). `step_rows(grid, rows, cols, r0, r1)` calcula solo las filas `[r0, r1)` de la siguiente generación leyendo el tablero actual, y devuelve las filas nuevas, cuántas células cambiaron y cuántas quedaron vivas. Lo único que cambia entre versiones es cómo se reparten las filas.

- **Secuencial** (`Engine`): una sola llamada a `step_rows` sobre todas las filas.
- **Hilos** (`ThreadEngine`): hilos persistentes sincronizados con `threading.Barrier`. Todos leen el mismo tablero (memoria compartida, solo lectura) y cada uno calcula su bloque de filas. Al final de la generación el hilo principal concatena los bloques.

### 2.2 Estrategia de paralelización

**División del trabajo: por bloques de filas contiguas.** `split_rows(rows, n)` reparte las filas en `n` bloques lo más parejos posible (si no se dividen exacto, los primeros bloques llevan una fila de más). Se eligieron filas y no columnas o bloques 2D porque el tablero es una lista de filas: cada worker recorre filas completas de memoria contigua, la unión final es una simple concatenación y cada bloque solo tiene dos fronteras (arriba y abajo).

```
Tablero de 1000 filas, 4 workers (split_rows)

  fila 0    +-----------------------+
            | bloque 0 (0..249)     |  <- worker 0
  fila 250  +-----------------------+
            | bloque 1 (250..499)   |  <- worker 1
  fila 500  +-----------------------+
            | bloque 2 (500..749)   |  <- worker 2
  fila 750  +-----------------------+
            | bloque 3 (750..999)   |  <- worker 3
            +-----------------------+

Hilos:    los 4 leen el mismo tablero (memoria compartida).
```

**Sincronización: doble buffer y barrera.** Una generación se calcula siempre a partir de la anterior completa, así que nadie escribe sobre el tablero que se está leyendo: cada worker produce filas nuevas en su propia lista y el tablero viejo solo se reemplaza cuando todos terminaron. En hilos se usa una `Barrier(workers + 1)` (los workers más el hilo principal) que se cruza dos veces por generación: la primera da la orden de empezar y la segunda garantiza que todos terminaron antes de unir los bloques.

### 2.3 Interfaz gráfica

El paquete `gui/` (customtkinter) simula el juego con dos motores sobre el mismo tablero: uno secuencial y uno paralelo, con el número de workers (hilos) que se elija. Los tamaños disponibles son los del enunciado: 100x100, 500x500 y 1000x1000 (los tableros se ven a escala real: la rueda del mouse hace zoom hasta x16; el nivel más bajo es "ajustado" (el tablero completo en el panel, omitiendo células si no cabe a x1) y nunca se muestra más chico que el panel; se recorre con scrollbars o arrastrando con el botón central, y los dos tableros siempre muestran la misma zona), y los workers 1, 2, 4, 8 y 12, los mismos del benchmark. En cada generación se ejecuta primero el secuencial y después el paralelo, y se comparan los tableros resultantes; si difieren, la simulación se detiene y muestra un error. La ventana muestra el tablero, el número de generación y de células vivas, el tiempo de cálculo del último paso de cada motor con su speedup, y el acumulado de toda la corrida (sin contar el primer paso, que incluye calentamiento). También se puede pintar con clic, colocar patrones clásicos (glider, pulsar, cañón de Gosper…), generar tableros aleatorios y cambiar el retardo.

Los tiempos de la interfaz sirven para ver el efecto en vivo, pero la medición de referencia es el paquete `benchmark` (sección 4): la interfaz calcula en un hilo aparte pero comparte la CPU con el dibujo y con el hilo de Tk.

## 3. Desafíos de la implementación paralela

- **Condiciones de carrera al actualizar el tablero.** Si cada hilo actualizara las células en el mismo tablero que los demás están leyendo, un hilo podría ver vecinos ya actualizados a la generación siguiente y el resultado dependería del orden de ejecución. Se resolvió con doble buffer: el tablero actual es de solo lectura durante la generación y cada worker escribe en sus propias filas nuevas. Por eso no hace falta ningún lock sobre las células.
- **Resultados parciales sin locks.** Cada hilo guarda su resultado en `self.parts[t]`, una posición distinta de una lista preasignada; ningún par de hilos escribe en la misma posición y el hilo principal solo lee `parts` después de la segunda barrera, así que tampoco hace falta un mutex.
- **Sincronización entre generaciones.** El hilo principal no puede unir los bloques ni empezar la generación siguiente hasta que todos terminen. Con `join` habría que crear hilos nuevos en cada generación; con la barrera los hilos son persistentes y solo esperan. El costo es que la barrera obliga a esperar al hilo más lento en cada generación.
- **Errores y bloqueos.** Si un hilo falla, los demás quedarían esperando en la barrera para siempre. El hilo que falla guarda la excepción y llama a `barrier.abort()`, lo que despierta a todos con `BrokenBarrierError`; el hilo principal relanza el error original.
- **El GIL.** En CPython normal el código es correcto con hilos pero no se acelera, porque solo un hilo ejecuta bytecode a la vez (sección 5.1). Para medir paralelismo real con hilos hizo falta el build free-threaded 3.14t.
- **Validación.** Para asegurar que el paralelismo no cambia el resultado, `python -m life.check` compara los motores con una implementación de referencia, y el benchmark compara el hash blake2b del tablero final de cada caso con el del secuencial. Los 54 casos medidos (secuencial e hilos) dieron `valid = true`.

## 4. Entorno y metodología

**Hardware.** Intel Core i5-12450H (12th Gen), 12 CPU lógicas, 15 GiB de RAM. Son 8 núcleos físicos con arquitectura híbrida: 4 núcleos de rendimiento (P) con SMT, que dan las CPU 0 a 7 y llegan a 4.4 GHz, y 4 núcleos de eficiencia (E), CPU 8 a 11, sin SMT y con máximo de 3.3 GHz (según `lscpu -e`). Por eso las 12 CPU lógicas no equivalen a 12 núcleos: dos hilos en el mismo núcleo P con SMT se reparten sus unidades de ejecución, y los núcleos E son más lentos. El máximo teórico de speedup con 12 workers está bastante por debajo de 12.

**Intérpretes.**

| Etiqueta | Versión | GIL |
|---|---|---|
| 3.14 (GIL) | 3.14.8, build normal | activo |
| 3.14t (free-threaded) | 3.14.7, build free-threaded, `-X gil=0` | desactivado |
| 3.14t (GIL=1) | 3.14.7, mismo binario, `-X gil=1` | activo |

Los dos binarios son builds distintos: `/usr/bin/python3` es el 3.14.8 de Arch y `python3.14t` es el 3.14.7 de python-build-standalone, instalado con uv. Por eso la comparación limpia del GIL es gil=0 contra gil=1 del mismo binario (3.14t).

**Qué se mide.** Solo el cálculo de las generaciones (`run(10)` sobre el motor ya creado). No entra I/O, dibujo ni la construcción del motor; el tiempo de setup (crear los hilos) se guarda aparte en el JSON. Para cada caso: 2 generaciones de calentamiento, luego 3 repeticiones de 10 generaciones y se toma la mediana. El tablero es aleatorio con semilla 42 y densidad 0.3. Tamaños 100x100, 500x500 y 1000x1000; workers 1, 2, 4, 8 y 12.

**Definiciones.** El speedup se calcula contra el secuencial del mismo intérprete (`T_seq / T`) y la eficiencia es `speedup / workers`.

**Ruido.** La CPU es híbrida y no se fijó la afinidad: el sistema operativo decide si un worker cae en un núcleo P o E. Entre las 3 repeticiones de un mismo caso, la mediana de la razón máximo/mínimo es 1.06x (6 %), con un peor caso de 1.55x (100x100, hilos con 3.14t GIL=1, 12 workers). Entre corridas completas la variación es mayor: en una corrida previa idéntica los hilos free-threaded en 1000x1000 con 12 workers dieron 4.67x, contra 3.77x en la que se reporta aquí. Diferencias de 10-20 % no deben tomarse como significativas.

## 5. Resultados

Datos completos: `results/bench-parcial.csv` (el `.json` de esa corrida quedó truncado; el CSV está completo). Las filas de procesos que traen esos archivos de una versión anterior del proyecto se descartan y no se usan en este informe.

### 5.1 Tablero 1000x1000

| Modo | Intérprete | Workers | ms/gen | Speedup | Eficiencia |
|---|---|---:|---:|---:|---:|
| Secuencial | 3.14 (GIL) | 1 | 165.8 | 1.00 | 1.00 |
| Secuencial | 3.14t (free-threaded) | 1 | 147.1 | 1.00 | 1.00 |
| Secuencial | 3.14t (GIL=1) | 1 | 146.2 | 1.00 | 1.00 |
| Hilos | 3.14 (GIL) | 1 | 178.1 | 0.93 | 0.93 |
| Hilos | 3.14 (GIL) | 2 | 165.6 | 1.00 | 0.50 |
| Hilos | 3.14 (GIL) | 4 | 169.4 | 0.98 | 0.24 |
| Hilos | 3.14 (GIL) | 8 | 175.3 | 0.95 | 0.12 |
| Hilos | 3.14 (GIL) | 12 | 180.2 | 0.92 | 0.08 |
| Hilos | 3.14t (free-threaded) | 1 | 148.1 | 0.99 | 0.99 |
| Hilos | 3.14t (free-threaded) | 2 | 86.0 | 1.71 | 0.85 |
| Hilos | 3.14t (free-threaded) | 4 | 56.3 | 2.61 | 0.65 |
| Hilos | 3.14t (free-threaded) | 8 | 38.8 | 3.79 | 0.47 |
| Hilos | 3.14t (free-threaded) | 12 | 39.0 | 3.77 | 0.31 |
| Hilos | 3.14t (GIL=1) | 1 | 149.6 | 0.98 | 0.98 |
| Hilos | 3.14t (GIL=1) | 2 | 141.5 | 1.03 | 0.52 |
| Hilos | 3.14t (GIL=1) | 4 | 144.9 | 1.01 | 0.25 |
| Hilos | 3.14t (GIL=1) | 8 | 150.8 | 0.97 | 0.12 |
| Hilos | 3.14t (GIL=1) | 12 | 150.7 | 0.97 | 0.08 |

![](graficas/01_speedup_1000.png)

![](graficas/03_eficiencia_1000.png)

![](graficas/05_barras_1000_8w.png)

### 5.2 Tablero 500x500

| Modo | Intérprete | Workers | ms/gen | Speedup | Eficiencia |
|---|---|---:|---:|---:|---:|
| Secuencial | 3.14 (GIL) | 1 | 37.1 | 1.00 | 1.00 |
| Secuencial | 3.14t (free-threaded) | 1 | 35.1 | 1.00 | 1.00 |
| Secuencial | 3.14t (GIL=1) | 1 | 36.0 | 1.00 | 1.00 |
| Hilos | 3.14 (GIL) | 2 | 37.5 | 0.99 | 0.49 |
| Hilos | 3.14 (GIL) | 4 | 40.2 | 0.92 | 0.23 |
| Hilos | 3.14 (GIL) | 8 | 43.4 | 0.86 | 0.11 |
| Hilos | 3.14 (GIL) | 12 | 46.1 | 0.81 | 0.07 |
| Hilos | 3.14t (free-threaded) | 2 | 20.5 | 1.71 | 0.86 |
| Hilos | 3.14t (free-threaded) | 4 | 13.0 | 2.71 | 0.68 |
| Hilos | 3.14t (free-threaded) | 8 | 9.6 | 3.67 | 0.46 |
| Hilos | 3.14t (free-threaded) | 12 | 8.8 | 3.97 | 0.33 |
| Hilos | 3.14t (GIL=1) | 2 | 35.4 | 1.02 | 0.51 |
| Hilos | 3.14t (GIL=1) | 4 | 36.1 | 1.00 | 0.25 |
| Hilos | 3.14t (GIL=1) | 8 | 38.6 | 0.93 | 0.12 |
| Hilos | 3.14t (GIL=1) | 12 | 41.5 | 0.87 | 0.07 |

(Los casos de 1 worker están en el CSV; se comportan igual que en 1000x1000.)

![](graficas/02_speedup_500.png)

### 5.3 Tablero 100x100

Se resume cada configuración con su mejor número de workers.

| Intérprete | Secuencial (ms/gen) | Hilos, mejor caso (workers) |
|---|---:|---|
| 3.14 (GIL) | 1.22 | 1.39 ms, 0.88x (1) |
| 3.14t (free-threaded) | 1.41 | 0.42 ms, 3.39x (8) |
| 3.14t (GIL=1) | 1.28 | 1.60 ms, 0.80x (1) |

### 5.4 Tiempo contra tamaño

![](graficas/04_ms_vs_tamano.png)

El tiempo secuencial crece con el número de células, como se espera: de 1.2 ms (10 000 células) a unos 36 ms (250 000) y 147-166 ms (1 000 000), es decir aproximadamente lineal en `filas x columnas`.

## 6. Análisis

### 6.1 El GIL

Con el GIL activo, agregar hilos no ayuda y en la mayoría de los casos empeora. En 1000x1000 los hilos de 3.14 se quedan entre 0.92x y 1.00x para cualquier número de hilos; en 500x500 bajan de 0.99x con 2 hilos a 0.81x con 12, y en 100x100 llegan a 0.50x con 8.

El mismo binario 3.14t con `-X gil=1` se comporta igual (0.97x a 1.03x en 1000x1000, 0.28x con 12 hilos en 100x100). Es la comparación más limpia del experimento, porque lo único que cambia respecto a la corrida free-threaded es el GIL. Con el GIL solo un hilo ejecuta bytecode a la vez, así que el cálculo no avanza más rápido y encima se paga el cambio de hilo y la espera en la barrera en cada generación; por eso el empeoramiento crece con el número de hilos y es mayor en tableros pequeños, donde cada generación hace poco trabajo entre sincronizaciones.

![](graficas/06_gil_hilos_1000.png)

### 6.2 Free-threading: los hilos sí escalan

Con `-X gil=0` los mismos hilos, sin tocar el código, bajan de 147.1 a 38.8 ms/gen en 1000x1000 con 8 workers: 3.79x. Con 2 y 4 hilos el speedup es 1.71x y 2.61x (eficiencias de 0.85 y 0.65). En 500x500 se llega a 3.97x con 12 hilos y en 100x100 a 3.39x con 8.

La curva se satura alrededor de 8 workers: en 1000x1000, 12 hilos dan lo mismo que 8 (3.77x contra 3.79x), y en 100x100 con 12 hilos el tiempo empeora (2.33x) porque cada hilo recibe apenas 8 filas y la barrera pesa más que el cálculo. La saturación coincide con el hardware (sección 6.4): pasados 4 workers se empiezan a ocupar hilos SMT y núcleos E.

### 6.3 Tamaño del problema

En 100x100 una generación secuencial cuesta 1.2 a 1.4 ms y la sincronización por generación (la barrera) es del mismo orden. Solo los hilos free-threaded ganan claramente (3.39x con 8). Desde 500x500 el paralelismo compensa con hilos free-threaded desde 2 workers, y el speedup de 500x500 y 1000x1000 es muy parecido, lo que indica que a partir de ese tamaño el límite ya no es el tamaño del tablero sino el hardware y la parte serial.

### 6.4 Ley de Amdahl

Con la ley de Amdahl, `S = 1 / (s + (1 - s)/p)`, la fracción serial efectiva sale de `s = (1/S - 1/p) / (1 - 1/p)`. Este valor mezcla la parte realmente secuencial del programa con todo lo que impide escalar (SMT, núcleos E, memoria, contención), así que es una estimación "efectiva".

| Caso (1000x1000) | p | Speedup | s estimada | Speedup máximo (1/s) |
|---|---:|---:|---:|---:|
| Hilos 3.14t gil=0 | 4 | 2.61 | 0.18 | 5.6 |
| Hilos 3.14t gil=0 | 8 | 3.79 | 0.16 | 6.3 |
| Hilos 3.14t gil=0 | 12 | 3.77 | 0.20 | 5.0 |

Para los hilos free-threaded la fracción efectiva está entre 0.16 y 0.20, lo que sugiere un techo de unas 5-6x en esta máquina.

Fuentes de la parte serial, de lo medible a lo hipotético. La unión de bloques y la suma de contadores corren en el hilo principal y son proporcionales al número de filas, no de celdas, así que son pequeñas. La barrera obliga a esperar al worker más lento en cada generación, y con núcleos de velocidad distinta (4.4 GHz contra 3.3 GHz) el más lento fija el tiempo. Por último, núcleos físicos contra SMT: solo 4 núcleos son P con doble hilo y 4 son E, así que más allá de 4 workers cada worker adicional aporta menos que uno completo. Esto es coherente con que la eficiencia caiga de 0.65 con 4 hilos a 0.47 con 8, pero no separé experimentalmente cuánto de la caída es SMT y cuánto es contención de memoria, así que es una hipótesis.

## 7. Conclusiones

- **El paralelismo sí es efectivo en este juego**, porque cada célula de una generación se calcula de forma independiente a partir de la generación anterior: el problema se divide en bloques de filas sin dependencias dentro de una generación, y solo hay que sincronizar entre generaciones y compartir las filas de borde.
- **Secuencial:** suficiente para tableros de 100x100 o menores cuando no hay free-threading. A ese tamaño paralelizar con hilos con GIL no compensa.
- **Hilos con GIL (3.14 normal):** no sirven para este cálculo en Python puro. Con más de un hilo el resultado fue igual o peor que el secuencial (hasta 0.50x en 100x100 y 0.81x en 500x500).
- **Hilos en 3.14t sin GIL:** la mejor opción medida en todos los tamaños: 3.79x en 1000x1000, 3.97x en 500x500 y 3.39x en 100x100, sin serialización y sin cambiar el código. Conviene usar entre 4 y 8 workers; pasado ese punto el beneficio es nulo o negativo en esta CPU.
- **Límite práctico:** el speedup se satura alrededor de 4x por la parte serial efectiva (≈16-20 % en hilos free-threaded) y por la arquitectura híbrida de la CPU, lejos del ideal lineal de 12x.

## 8. Cómo reproducir

Verificación de correctitud de los motores:

```
.venv/bin/python -m life.check
```

Interfaz gráfica (usa el `.venv` del proyecto, CPython 3.14t free-threaded):

```
.venv/bin/python -m gui
```

Benchmark con los tres intérpretes y los tamaños de este informe; escribe JSON y CSV en `results/`:

```
python3 -m benchmark --with-gil1 --sizes 100,500,1000 --out results/bench-parcial.json
```

Gráficas (el `--no-project` evita que `uv` recree el `.venv` del proyecto):

```
uv run --no-project --with matplotlib python scripts/graficas.py results/bench-parcial.csv
```
