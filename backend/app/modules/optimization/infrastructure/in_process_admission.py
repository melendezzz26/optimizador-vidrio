"""TA-037 T03: admisión en memoria del proceso web (SPEC-TA-037 §5.1, GAP-03).

Válida mientras haya un solo proceso uvicorn (Procfile). Con varios dynos o
workers se necesita una admisión compartida, y esa decisión requiere un ADR.
"""
import threading
import time

from ..application.admission import OptimizerBusy
from ..application.load_budget import DEFAULT_RUN_LOAD_BUDGET

# Respaldo ante una plaza que nunca se liberó: L-12 (120 s) + un tramo entre hitos
# (~31 s, L-07) + guardado. Ninguna ejecución sana dura tanto.
LEASE_TIMEOUT_SECONDS = 300


class _Lease:
    def __init__(self, admission, token):
        self._admission, self._token = admission, token

    def release(self):
        self._admission._release(self._token)


class InProcessRunAdmission:
    def __init__(self, max_active=DEFAULT_RUN_LOAD_BUDGET.max_active_runs,
                 max_per_user=DEFAULT_RUN_LOAD_BUDGET.max_active_runs_per_user,
                 lease_timeout=LEASE_TIMEOUT_SECONDS, clock=time.monotonic):
        self.max_active, self.max_per_user = max_active, max_per_user
        self.lease_timeout, self.clock = lease_timeout, clock
        self._lock = threading.Lock()
        self._leases = {}  # token -> (user_id, acquired_at)

    def _expire(self):
        limit = self.clock() - self.lease_timeout
        for token in [t for t, (_, acquired) in self._leases.items() if acquired <= limit]:
            del self._leases[token]

    def acquire(self, user_id):
        with self._lock:
            self._expire()
            mine = sum(1 for owner, _ in self._leases.values() if owner == user_id)
            if mine >= self.max_per_user:                                   # L-11
                raise OptimizerBusy("active_runs_per_user", self.max_per_user, mine)
            if len(self._leases) >= self.max_active:                        # L-10
                raise OptimizerBusy("active_runs", self.max_active, len(self._leases))
            token = object()
            self._leases[token] = (user_id, self.clock())
            return _Lease(self, token)

    def _release(self, token):
        with self._lock:
            self._leases.pop(token, None)

    def active(self):
        with self._lock:
            self._expire()
            return len(self._leases)