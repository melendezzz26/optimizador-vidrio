"""Run-local M6 state accounting; raster-cache and worker limits stay separate.

Measure the live immutable graph by identity, including cached scores. Reserve
construction/scoring scratch BEFORE allocating a successor. The walk's identity
set is temporary and charged too; it never becomes an unbounded node cache.
"""
from collections.abc import Mapping
from dataclasses import is_dataclass
from enum import Enum
import sys

from .preparation import bbox_dimensions


class StateMemoryLimit(RuntimeError):
    def __init__(self):
        super().__init__("STATE_MEMORY_LIMIT")


def row_bytes(columns):
    # CPython integer digits plus an eight-byte tuple/list reference, rounded up.
    return 40 + 4 * ((columns + 29) // 30)


def dimensions(stock, config):
    return tuple(int((v / config.resolution_mm).to_integral_value(
        rounding="ROUND_CEILING")) for v in bbox_dimensions(stock.geometry))


def initial_bound(stocks, config):
    """All sources remain present; identical material masks are charged once."""
    seen = set()
    total, scratch = 16384, 0
    for stock in stocks:
        columns, rows = dimensions(stock, config)
        geometry = tuple(sorted(stock.geometry.items()))
        if geometry not in seen:
            seen.add(geometry)
            total += rows * row_bytes(columns) + 4096
        # Usable rows and the shared empty occupied/blocked tuple per source.
        total += rows * (row_bytes(columns) + 8) + 4096
        scratch = max(scratch, 3 * rows * row_bytes(columns) + 65536)
    return total + scratch


def successor_reserve(material, units):
    """Upper bound, independent of how sparse the next placement happens to be.

    Covers an outstanding yielded layout plus the next layout, place/check
    lists, dilation intermediates, free rows, score histograms/stacks/cells,
    placement/trace tuples, and sort/list copies. Unchanged graph objects are
    measured separately, once. No reservation relies on future pruning.
    """
    rows, columns = material.row_count, material.columns
    return (6 * rows * row_bytes(columns) + rows * 192 + columns * 256
            + units * 2048 + 65536)


def graph_bytes(roots):
    """Owned data only: never follow classes, functions, enums or module globals."""
    seen, pending = set(), list(roots)
    total, stack_peak = 0, 0
    while pending:
        stack_peak = max(stack_peak, sys.getsizeof(pending))
        value = pending.pop()
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        total += sys.getsizeof(value)
        if isinstance(value, Enum):
            continue
        if isinstance(value, Mapping):
            if not isinstance(value, dict):
                # MappingProxyType does not report its backing dictionary.
                total += 128 + 72 * len(value)
            for key, item in value.items():
                pending.extend((key, item))
        elif isinstance(value, (tuple, list, set, frozenset)):
            pending.extend(value)
        elif is_dataclass(value) and not isinstance(value, type):
            pending.append(vars(value))
    # Identity integers, set storage and traversal stack coexist with the graph.
    return total + sys.getsizeof(seen) + len(seen) * 32 + stack_peak + 4096


class BeamStateMemory:
    def __init__(self, maximum):
        self.maximum = maximum
        self.peak = self.required = 0

    def reserve(self, amount):
        self.required = max(self.required, amount)
        if amount > self.maximum:
            raise StateMemoryLimit()
        self.peak = max(self.peak, amount)

    def check(self, roots, scratch=0):
        self.reserve(graph_bytes(roots) + scratch)

    def statistics(self):
        return dict(state_bytes_bound=self.required, state_bytes_peak=self.peak)
