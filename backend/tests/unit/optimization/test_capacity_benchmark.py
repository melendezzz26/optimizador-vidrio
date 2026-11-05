"""Classification contract for TA-044 benchmark outcomes."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.optimization.benchmark_capacity import classify_status, run_single_benchmark


@pytest.mark.parametrize("placed,total,reason,expected", [
    (10, 10, None, "COMPLETE"),
    (5, 10, None, "PARTIAL"),
    (5, 10, "TIME_LIMIT", "TIMEOUT"),
    (10, 10, "TIME_LIMIT", "TIMEOUT"),
    (5, 10, "NODE_LIMIT", "PARTIAL"),
])
def test_classify_status(placed, total, reason, expected):
    assert classify_status(placed, total, reason) == expected


def test_optimizer_exception_is_error():
    class Broken:
        def optimize(self, problem):
            raise ValueError("synthetic")

    result = run_single_benchmark(10, "broken", Broken)
    assert result.status == "ERROR"
    assert result.error_message == "ValueError: synthetic"
