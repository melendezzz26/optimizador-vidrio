"""Deployment memory metadata and explicit, bounded comparison overrides.

No optimization semantics change here. Missing overrides preserve the audited
defaults; a larger dyno alone never silently increases algorithm/process limits.
"""
from dataclasses import replace
import os
from pathlib import Path

from ..application.comparison_limits import ComparisonBudget, MIB
from ..application.errors import RunError
from ..application.sequential_policy import SequentialPolicy


def cgroup_memory(root=Path('/sys/fs/cgroup'), membership=Path('/proc/self/cgroup')):
    """Return the tightest (limit, usage) of accessible cgroup v1/v2 ancestors."""
    candidates = [(root, 'memory.max', 'memory.current'),
                  (root/'memory', 'memory.limit_in_bytes', 'memory.usage_in_bytes'),
                  (root, 'memory.limit_in_bytes', 'memory.usage_in_bytes')]
    try:
        for entry in membership.read_text().splitlines():
            _, controllers, relative = entry.split(':', 2)
            if '..' in Path(relative).parts:
                continue
            if not controllers:
                candidates.append((root/relative.lstrip('/'), 'memory.max', 'memory.current'))
            elif 'memory' in controllers.split(','):
                candidates.append((root/'memory'/relative.lstrip('/'), 'memory.limit_in_bytes', 'memory.usage_in_bytes'))
    except (OSError, ValueError):
        pass
    readings = []
    seen = set()
    for directory, limit_name, usage_name in candidates:
        # Walk to the mount root as well: parent limits also constrain nested groups.
        while directory.is_relative_to(root):
            key = directory/limit_name
            if key not in seen:
                seen.add(key)
                try:
                    value = key.read_text().strip()
                    if value != 'max':
                        limit, usage = int(value), int((directory/usage_name).read_text())
                        if 0 < limit < 1 << 60 and usage >= 0:
                            readings.append((limit, usage))
                except (OSError, ValueError):
                    pass
            if directory == root: break
            directory = directory.parent
    return readings


def configured_policy(environment=None):
    values = os.environ if environment is None else environment
    names = dict(supervisor_rss_bytes='NEWGLASS_COMPARISON_SUPERVISOR_MIB',
        worker_address_bytes='NEWGLASS_COMPARISON_WORKER_MIB',
        aggregate_rss_bytes='NEWGLASS_COMPARISON_AGGREGATE_MIB')
    supplied = [name for name in names.values() if name in values]
    try:
        large_seconds = values.get('NEWGLASS_COMPARISON_LARGE_SECONDS')
        if large_seconds is not None:
            if not isinstance(large_seconds, str) or not large_seconds.isascii() or not large_seconds.isdigit():
                raise ValueError('Large-order deadline must be integer seconds')
            large_seconds = int(large_seconds)
        if not supplied:
            return SequentialPolicy(large_calculation_seconds=large_seconds)
        if len(supplied) != len(names):
            raise ValueError('Provide all three memory limits together')
        updates = {}
        for field, name in names.items():
            raw = values[name]
            if not isinstance(raw, str) or not raw.isascii() or not raw.isdigit() or not 64 <= int(raw) <= 4096:
                raise ValueError('Memory limits must be integer MiB between 64 and 4096')
            updates[field] = int(raw)*MIB
        budget = replace(ComparisonBudget(), **updates)
        if budget.supervisor_rss_bytes + budget.worker_address_bytes + budget.helper_reserve_bytes > budget.aggregate_rss_bytes:
            raise ValueError('The aggregate must cover both processes and helper reserve')
        capacities = [limit for limit, _ in cgroup_memory()]
        if 'NEWGLASS_DYNO_MEMORY_MIB' in values:
            raw = values['NEWGLASS_DYNO_MEMORY_MIB']
            if not raw.isascii() or not raw.isdigit() or not 128 <= int(raw) <= 65536:
                raise ValueError('Invalid explicit dyno capacity')
            capacities.append(int(raw)*MIB)
        if not capacities:
            raise ValueError('Cannot validate overrides without a detected or explicit container capacity')
        # Capacity reserve is independent from the helper processes already counted by the watchdog.
        capacity = min(capacities)
        if budget.aggregate_rss_bytes + max(64*MIB, capacity//10) > capacity:
            raise ValueError('Comparison budget leaves insufficient container headroom')
        return SequentialPolicy(budget=budget, memory_ceiling=budget, large_calculation_seconds=large_seconds)
    except (TypeError, ValueError) as error:
        raise RunError('RESOURCE_UNAVAILABLE', 'Los presupuestos de optimización configurados no son válidos para este servidor.') from error
