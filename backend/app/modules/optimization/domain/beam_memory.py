"""Run-local M6 state accounting; raster-cache and worker limits stay separate.

Measure the live immutable graph by identity, including cached scores. Reserve
construction/scoring scratch BEFORE allocating a successor. The walk's identity
set is charged too; it never becomes an unbounded node cache. During search
(S2-M6) the base graph's identities are kept for one parent's expansion only,
so each child is measured once instead of re-walking the whole graph.
"""
from collections.abc import Mapping
from dataclasses import is_dataclass
from decimal import Decimal
from enum import Enum
import sys

from .preparation import bbox_dimensions
from .rotation import _fingerprint


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
    """All sources remain present; identical materials are charged once.

    S2-M6: sources with the same material raster also share ONE immutable empty
    layout (see beam_search._initial_layouts), so its usable rows and empty
    occupied/blocked tuple are charged per distinct material, not per source.
    Each source still pays for its own references and score slot.
    """
    seen = set()
    total, scratch = 16384, 0
    for stock in stocks:
        columns, rows = dimensions(stock, config)
        # Same normalized key used by RasterCache, including translated polygons.
        geometry = _fingerprint(stock.geometry)
        if geometry not in seen:
            seen.add(geometry)
            # Material raster.
            total += rows * row_bytes(columns) + 4096
            # Shared empty layout: usable rows plus the empty occupied/blocked tuple.
            total += rows * (row_bytes(columns) + 8) + 4096
        # Per-source layout/score references, rank entry and source bookkeeping.
        total += 4096
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


def graph_bytes(roots, checkpoint=None):
    """Owned data only: never follow classes, functions, enums or module globals."""
    seen, pending = set(), list(roots)
    total, stack_peak = 0, 0
    while pending:
        if checkpoint is not None and len(seen) % 512 == 0:
            checkpoint()
        stack_peak = max(stack_peak, sys.getsizeof(pending))
        value = pending.pop()
        identity = id(value)
        if identity in seen:
            continue
        seen.add(identity)
        # Instance dictionaries use CPython split-key tables whose reported
        # capacity shrinks as later instances are created. Charge a stable upper
        # bound instead, so diagnostics/admission do not depend on warm-up.
        size = sys.getsizeof(value)
        if isinstance(value, dict):
            size = max(size, 128 + 72 * len(value))
        elif isinstance(value, list):
            size = max(size, 128 + 16 * len(value))
        total += size
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
    # Resizing can temporarily retain old AND new set/list buffers. Identity
    # integers themselves are shared between those buffers, not copied.
    return total + 2 * sys.getsizeof(seen) + len(seen) * 32 + 2 * stack_peak + 4096


# --- S2-M6: incremental accounting, an upper bound of graph_bytes -------------
#
# graph_bytes(roots) = (sum of owned sizes of the distinct objects)
#                      + 2 * size(seen set) + 32 * len(seen) + 2 * stack peak + 4096.
# During one parent's expansion only the ``children`` list changes, so the rest
# of the graph (the "base") is walked once per parent and each child once, for
# the objects the base does not already own. Every term is then the same or larger:
#   * owned sizes: exact per object; an object shared by two children (never
#     by base and child) may be charged twice;
#   * seen set: the exact CPython size of a set grown one add at a time, for a
#     count that can only be larger than the true number of distinct objects;
#   * stack peak: graph_bytes' depth-first stack never holds more than
#     (number of roots) + the largest sum of out-degrees along one path.

_LEAVES = frozenset((int, bool, float, complex, str, bytes, type(None), Decimal))


def _owned_size(value):
    # Identical to graph_bytes' per-object charge.
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size = max(size, 128 + 72 * len(value))
    elif isinstance(value, list):
        size = max(size, 128 + 16 * len(value))
    if not isinstance(value, Enum) and isinstance(value, Mapping) and not isinstance(value, dict):
        size += 128 + 72 * len(value)
    return size


def _edges(value):
    # Exactly what graph_bytes pushes for this value.
    if isinstance(value, Enum):
        return ()
    if isinstance(value, Mapping):
        return [item for pair in value.items() for item in pair]
    if isinstance(value, (tuple, list, set, frozenset)):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return (vars(value),)
    return ()


def set_bytes(count):
    """sys.getsizeof of a CPython 3.11 set after ``count`` distinct adds (no removals).

    setobject.c grows when fill*5 >= mask*3, to the smallest power of two above
    used*4 (used*2 beyond 50000 entries); entries are 16 bytes outside the
    8-slot small table. Nondecreasing in ``count``.
    """
    slots = 8
    while True:
        trigger = -(-3 * (slots - 1) // 5)
        if trigger > count:
            break
        minimum = trigger * 2 if trigger > 50000 else trigger * 4
        slots = 8
        while slots <= minimum:
            slots <<= 1
    return sys.getsizeof(set()) + (16 * slots if slots > 8 else 0)


def list_bytes_bound(length):
    """Upper bound of sys.getsizeof of a list that never held more than ``length`` items."""
    capacity = ((length + (length >> 3) + 6) & ~3) + 4
    return sys.getsizeof([]) + 8 * capacity


class _Walk:
    """Measures the objects reachable from some values, minus those in ``known``.

    ``memo``/``known`` map id -> longest out-degree path below that object. The
    ids stay valid because every measured object is reachable from a value the
    caller keeps alive while the measurement is in use.
    """
    def __init__(self, known, checkpoint):
        self.known, self.memo, self.total = known, {}, 0
        self.checkpoint = checkpoint

    def path(self, value):
        identity, memo, known = id(value), self.memo, self.known
        found = memo.get(identity)
        if found is None and known is not None:
            found = known.get(identity)
        if found is not None:
            return found
        if self.checkpoint is not None and len(memo) % 512 == 0:
            self.checkpoint()
        self.total += _owned_size(value)
        memo[identity] = 0
        edges = _edges(value)
        deepest = 0
        for item in edges:
            if type(item) in _LEAVES:
                key = id(item)
                if key not in memo and (known is None or key not in known):
                    memo[key] = 0
                    self.total += sys.getsizeof(item)
                continue
            depth = self.path(item)
            if depth > deepest:
                deepest = depth
        memo[identity] = len(edges) + deepest
        return memo[identity]


class BeamStateMemory:
    def __init__(self, maximum, checkpoint=None):
        self.maximum = maximum
        self.checkpoint = checkpoint
        self.peak = self.required = 0
        self._base = None
        self._children = {}

    def reserve(self, amount):
        self.required = max(self.required, amount)
        if amount > self.maximum:
            raise StateMemoryLimit()
        self.peak = max(self.peak, amount)

    def check(self, roots, scratch=0):
        self.reserve(graph_bytes(roots, self.checkpoint) + scratch)

    def search_bytes(self, base, children):
        """Upper bound of graph_bytes(base + (children,)), reusing earlier walks.

        ``base`` must be the same immutable objects while only ``children``
        (one list, mutated in place) changes; any other base forces a new walk.
        """
        base = tuple(base)
        cached = self._base
        if cached is None or len(cached[0]) != len(base) or any(
                old is not new for old, new in zip(cached[0], base)):
            # Holding the previous refs until here keeps their ids unique.
            walk = _Walk(None, self.checkpoint)
            depth = max((walk.path(root) for root in base), default=0)
            self._base = cached = (base, walk.memo, walk.total, depth)
            self._children = {}
        _, known, total, depth = cached
        count = len(known)
        entries, deepest = {}, 0
        for child in children:
            entry = self._children.get(id(child))
            if entry is None or entry[0] is not child:
                walk = _Walk(known, self.checkpoint)
                entry = (child, walk.path(child), walk.total, len(walk.memo))
            entries[id(child)] = entry
            deepest = max(deepest, entry[1])
            total += entry[2]
            count += entry[3]
        self._children = entries
        # The children list itself, as one more root object.
        total += _owned_size(children)
        count += 1
        depth = max(depth, len(children) + deepest)
        pending = len(base) + 1 + depth
        return total + 2 * set_bytes(count) + 32 * count + 2 * list_bytes_bound(pending) + 4096

    def check_search(self, base, children, scratch=0):
        self.reserve(self.search_bytes(base, children) + scratch)

    def statistics(self):
        return dict(state_bytes_bound=self.required, state_bytes_peak=self.peak)
