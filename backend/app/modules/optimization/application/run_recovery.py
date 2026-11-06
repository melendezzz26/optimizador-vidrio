"""Explicit FF reconciliation after an operationally verified service stop."""
from .errors import RunError


class RecoverStoppedRun:
    def __init__(self, unit_of_work):
        self.unit_of_work = unit_of_work

    def execute(self, optimization_id, *, service_stopped=False):
        if not service_stopped:
            raise RunError("RECOVERY_BLOCKED", "Verifica la parada del servicio antes de reconciliar la corrida.")
        with self.unit_of_work() as tx:
            return tx.runs.recover_stopped(optimization_id)
