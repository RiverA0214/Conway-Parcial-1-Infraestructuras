"""Benchmark: secuencial vs hilos, con y sin GIL de Python.

    python -m benchmark              # completo (estimado: 15-20 min con ambos intérpretes)
    python -m benchmark --quick      # prueba rápida (unos segundos)
    python -m benchmark --with-gil1  # añade python3.14t con -X gil=1

Módulos:
    config     qué se mide: tamaños, modos, workers, intérpretes
    medicion   se ejecuta DENTRO de cada intérprete y mide los casos
    ejecucion  lanza un subproceso por intérprete, junta resultados y calcula speedups
    salida     guarda JSON/CSV e imprime tablas y avisos
"""
