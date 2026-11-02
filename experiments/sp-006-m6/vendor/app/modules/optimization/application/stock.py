"""Run-local stock snapshots, deliberately not a process-wide inventory cache."""
from dataclasses import replace

from .ports import CompatibleStockProvider


class CompatibleStockCache:
    def __init__(self, provider: CompatibleStockProvider):
        self.provider = provider
        self._groups = {}

    def list_compatible(self, group_key):
        if group_key not in self._groups:
            candidates = tuple(self.provider.list_compatible(group_key))
            if any(c.material_key != group_key for c in candidates):
                raise ValueError("Stock provider returned an incompatible candidate.")
            self._groups[group_key] = candidates
        return self._groups[group_key]


def with_compatible_stock(problem, provider: CompatibleStockProvider):
    cache = CompatibleStockCache(provider)
    return replace(problem, groups=tuple(
        replace(group, stock_candidates=cache.list_compatible(group.key)) for group in problem.groups
    ))
