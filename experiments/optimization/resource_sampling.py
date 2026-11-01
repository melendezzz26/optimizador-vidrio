"""Muestreo Linux del supervisor y sus tres workers para la sonda T00.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
RSS suma páginas compartidas varias veces; no equivale a memoria física única.
El máximo muestreado no asegura capturar picos entre dos lecturas.
"""
import os
from pathlib import Path
import threading
import time


def resident_bytes(pid):
    try:
        pages = int(Path(f"/proc/{pid}/statm").read_text().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE")
    except (FileNotFoundError, ProcessLookupError):
        return 0


class ResourceSampler:
    def __init__(self, processes, interval_seconds=0.01):
        self.processes = processes
        self.interval_seconds = interval_seconds
        self.samples = 0
        self.maximum_rss_sum = 0
        self.maximum_processes = 0
        self.maximum_gap_ms = 0
        self._last = None
        self._stop = threading.Event()
        self._failure = None
        self._lock = threading.Lock()

    def _sample(self):
        now = time.monotonic()
        if self._last is not None:
            self.maximum_gap_ms = max(self.maximum_gap_ms, (now - self._last) * 1000)
        self._last = now
        pids = {os.getpid(), *(p.pid for p in self.processes if p.pid is not None)}
        readings = [resident_bytes(pid) for pid in pids]
        self.maximum_rss_sum = max(self.maximum_rss_sum, sum(readings))
        self.maximum_processes = max(self.maximum_processes, sum(value > 0 for value in readings))
        self.samples += 1

    def capture(self):
        with self._lock:
            self._sample()

    def _run(self):
        try:
            while not self._stop.wait(self.interval_seconds):
                self.capture()
        except Exception as error:
            self._failure = error

    def __enter__(self):
        if not Path("/proc/self/statm").is_file():
            raise RuntimeError("La medición agregada necesita procfs de Linux.")
        self.capture()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args):
        self._stop.set()
        self._thread.join(timeout=5)
        self.capture()
        if self._failure is not None:
            raise RuntimeError("Falló el muestreo de recursos.") from self._failure

    def report(self):
        return {"metric": "sampled_supervisor_and_three_workers_rss_sum",
                "sample_interval_ms": self.interval_seconds * 1000,
                "samples": self.samples, "maximum_gap_ms": self.maximum_gap_ms,
                "maximum_processes": self.maximum_processes,
                "maximum_rss_sum_bytes": self.maximum_rss_sum}
