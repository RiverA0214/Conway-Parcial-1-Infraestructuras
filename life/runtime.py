"""Información del intérprete en el que corre el programa (versión, GIL, CPUs)."""

import os
import sys
import sysconfig


def runtime_info():
    gil = getattr(sys, "_is_gil_enabled", None)
    return {
        "python_version": sys.version.split()[0],
        "implementation": sys.implementation.name,
        "gil_enabled": gil() if gil else True,
        "free_threaded_build": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
        "cpu_count": os.cpu_count(),
        "executable": sys.executable,
    }
