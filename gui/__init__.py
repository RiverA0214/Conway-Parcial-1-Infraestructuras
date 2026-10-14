"""Interfaz gráfica: el mismo tablero corre en un motor secuencial y en uno paralelo, lado a lado.

    python -m gui

Módulos (cada uno depende solo de los de arriba):
    render     matriz de 0/1 (bytes) -> imagen PPM. Función pura.
    simulador  hilo que calcula las generaciones y publica el último frame. No toca Tk.
    tablero    un tablero: imagen, pintado con el mouse y sus métricas.
    app        ventana: controles y resumen; conecta el simulador con los tableros.
"""
