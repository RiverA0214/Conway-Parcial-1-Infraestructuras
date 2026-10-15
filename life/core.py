"""Juego de la Vida: tablero como lista de listas con 0/1, bordes muertos, regla B3/S23.

El kernel lee una generación y escribe la siguiente en otro tablero (doble buffer): nunca se
actualiza el tablero que se está leyendo, porque cada célula debe ver la generación anterior
completa, no los valores que otras ya cambiaron.
"""


def step_rows(read, write, r0, r1):
    """Calcula las filas [r0, r1) de la siguiente generación.

    Lee de `read` (el tablero completo, solo lectura) y escribe en las mismas filas de
    `write`, sin tocar las demás: así varios hilos pueden llamarla a la vez, cada uno con
    su bloque. Escribe todas las celdas de sus filas, así que `write` puede traer datos viejos.
    Devuelve (celdas_que_cambiaron, celdas_vivas) de ese bloque.
    """
    rows, cols = len(read), len(read[0])
    cero = [0] * (cols + 2)
    changed = 0
    alive = 0
    for i in range(r0, r1):
        up = [0] + read[i - 1] + [0] if i > 0 else cero
        mid = [0] + read[i] + [0]
        down = [0] + read[i + 1] + [0] if i < rows - 1 else cero
        new = write[i]
        for j in range(cols):
            vecinos = (up[j] + up[j + 1] + up[j + 2]
                       + mid[j] + mid[j + 2]
                       + down[j] + down[j + 1] + down[j + 2])
            vive = 1 if (vecinos == 3 or (vecinos == 2 and mid[j + 1])) else 0
            new[j] = vive
            alive += vive
            if vive != mid[j + 1]:
                changed += 1
    return changed, alive
