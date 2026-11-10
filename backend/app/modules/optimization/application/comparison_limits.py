"""Presupuesto inicial del runner comparativo, independiente de HTTP/ORM.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
Los máximos individuales TA-037 siguen vigentes. RSS es un umbral de aborto
muestreado; el límite duro por trabajador se aplica a espacio virtual en Linux.
"""
from dataclasses import dataclass
import math

MIB = 1024 * 1024
LARGE_COMPARISON_MIN_UNITS = 200
MAX_LARGE_CALCULATION_SECONDS = 900


@dataclass(frozen=True)
class ComparisonBudget:
    aggregate_rss_bytes: int = 1024 * MIB
    worker_address_bytes: int = 256 * MIB
    supervisor_rss_bytes: int = 240 * MIB
    helper_reserve_bytes: int = 16 * MIB
    packet_bytes: int = 12 * MIB
    visual_packet_bytes: int = 4 * MIB
    queued_packets_per_worker: int = 1
    retained_visual_bytes: int = 32 * MIB
    retained_event_bytes: int = 8 * MIB
    startup_seconds: float = 30
    calculation_seconds: float = 120
    # 6 motores × (30 s de arranque + 120 s de cálculo) = 900 s: ningún motor
    # queda sin despachar por el plazo global (revisión del profesor, 04/11/2026).
    global_seconds: float = 900

    def __post_init__(self):
        for name, value in vars(self).items():
            if name.endswith("seconds"):
                valid = type(value) in (int, float) and math.isfinite(value) and value > 0
            else:
                valid = type(value) is int and value > 0
            if not valid:
                raise ValueError(f"Invalid comparison budget: {name}")


DEFAULT_COMPARISON_BUDGET = ComparisonBudget()
