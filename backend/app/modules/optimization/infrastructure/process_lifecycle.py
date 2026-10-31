"""Identidad Linux por PID/inicio y terminación de hijos al perder supervisor.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
import ctypes
import os
from pathlib import Path
import signal


def process_identity(pid):
    try:
        # comm puede contener espacios/paréntesis; starttime es el campo 22.
        values = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {"pid": pid, "start_ticks": values[19]}
    except (FileNotFoundError, ProcessLookupError):
        return None


def protect_against_parent_exit(expected):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
        raise OSError(ctypes.get_errno(), "Unable to protect worker lifetime")
    # Cierra la carrera en la que el padre murió antes de instalar prctl.
    if expected is not None and process_identity(os.getppid()) != expected:
        os._exit(0)
