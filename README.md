# Juego de la Vida de Conway: secuencial vs hilos

Parcial 1 de Infraestructuras Paralelas y Distribuidas. Una versión secuencial y una paralela con hilos (`threading`) del juego de Conway, con interfaz gráfica que muestra las dos a la vez y un benchmark que compara los tiempos con y sin GIL.

## Requisitos

- **Python 3.14 free-threaded (`python3.14t`)** para ver el paralelismo real: sin GIL los hilos escalan; con el Python normal (GIL) el paralelo no acelera, y eso es parte del análisis. En Arch: paquete AUR `python314-freethreaded`; en general: `uv python install 3.14t`.
- **customtkinter** para la GUI. Las pruebas y el benchmark no necesitan nada externo.
- `matplotlib` solo para generar las gráficas (`scripts/graficas.py`).

```
python3.14t -m venv .venv
.venv/bin/pip install customtkinter
```

## Cómo se usa

| Qué | Comando |
|---|---|
| Interfaz gráfica | `.venv/bin/python -m gui` |
| Pruebas (54, tardan ~1 s) | `python -m unittest` |
| Benchmark rápido | `python -m benchmark --quick` |
| Benchmark completo | `python -m benchmark --out results/bench-parcial.json` |
| Gráficas | `python3 scripts/graficas.py results/bench-parcial.json` (necesita matplotlib) |
| Demo por consola | `python demo_consola.py` |

El benchmark busca `python3` (con GIL) y `python3.14t` en el `PATH`, y mide cada caso dentro de su intérprete. Opciones: `--sizes`, `--workers`, `--ciclos`, `--reps`, `--modes`, `--with-gil1` (agrega 3.14t con el GIL forzado, la comparación más limpia del efecto del GIL). Cada caso se valida comparando el hash del tablero final con el del secuencial.

En la GUI: clic izquierdo pinta y derecho borra; la rueda del mouse hace zoom (el nivel más bajo es "ajustado", el tablero completo en el panel); el desplazamiento es con las barras o arrastrando con el botón central, y los dos tableros se mueven juntos.

## Cómo está hecho

**Paralelización (hilos).** Descomposición de dominio por filas: `split_rows` reparte el tablero en bloques contiguos, uno por hilo.

**Sincronización.** Doble buffer (ping-pong): hay dos tableros completos. En cada ciclo todos los hilos *leen* de uno (solo lectura) y cada uno *escribe* su bloque de filas en el otro; los bloques no se solapan, así que no hacen falta locks. Una `Barrier` espera a que todos terminen y entonces solo se intercambian las dos referencias. El doble buffer no es una optimización: la regla exige que cada célula vea la generación *anterior* completa, y actualizar sobre el mismo tablero da un resultado distinto incluso con un solo hilo (`tests/test_semantica.py`).

**Hilos persistentes.** Se crean una vez y esperan en la barrera entre ciclos, en vez de crearse en cada generación.

## Estructura

```
life/            núcleo, sin dependencias del resto
  core.py          kernel: una generación de un bloque de filas
  grid.py          crear, serializar y convertir tableros
  engines.py       Engine, SequentialEngine, ThreadEngine, split_rows, make_engine
  runtime.py       versión de Python, GIL, CPUs
  cronometro.py    medir ciclos de un motor
  comparacion.py   comparar secuencial y paralelo en X ciclos
  patterns.py      glider, pulsar, cañón de Gosper...
benchmark/       python -m benchmark: config, medicion (dentro de cada intérprete), ejecucion, salida
gui/             python -m gui
  simulador.py     hilo que calcula y publica el último frame (no usa Tk)
  vista.py         zoom y desplazamiento (lógica pura, sin Tk)
  render.py        matriz -> imagen PPM
  tablero.py, app.py   la interfaz
tests/           pruebas con unittest
scripts/         gráficas a partir de los resultados del benchmark
results/         resultados, gráficas e informe
```

Las dependencias van en una sola dirección: `gui` y `benchmark` usan `life`; `life` no conoce a nadie. La GUI nunca espera al cálculo: el `Simulador` corre en su propio hilo y la ventana dibuja, ~30 veces por segundo, el último frame disponible.

## Convención de nombres

Los identificadores de `life/` y de los datos del benchmark (claves de los JSON y CSV) están en inglés; `gui/`, `tests/`, `cronometro.py`, `comparacion.py`, los comentarios y los textos de la interfaz, en español. Es una mezcla que viene de cómo creció el proyecto; los dos módulos en español dentro de `life/` son la excepción conocida.
