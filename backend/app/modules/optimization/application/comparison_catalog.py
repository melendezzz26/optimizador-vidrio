"""TA-043/B01: opt-in method identities; does not register an HTTP runner."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from ..domain.first_fit import FirstFitOptimizer
from ..domain.best_fit import BestFitOptimizer, BestFitResult
from ..domain.worst_fit import WorstFitOptimizer, WorstFitResult
from ..domain.hole_filling import HoleFillingOptimizer, HoleFillingResult
from ..domain.best_residual_fit import BestResidualFitOptimizer, BestResidualFitResult
from ..domain.beam_search import BeamSearchOptimizer, BeamSearchResult
from ..domain.problem import OptimizationResult

MethodV2 = Literal["FF", "BF", "WF", "HF", "M5", "M6-BS"]
PROFILE_V2 = "comparison-v2"
HTTP_SCHEMA_V2 = 2
COMPARISON_SNAPSHOT_V2 = 2
RESULT_SNAPSHOT_V3 = 3


@dataclass(frozen=True)
class MethodDefinition:
    code: str
    label: str
    name: str
    optimizer_type: type
    result_type: type
    observation: str = "PLACEMENT_FACTS"
    native_visual: bool = True
    checkpoint: bool = True
    beam_width: int | None = None

    def public(self):
        return dict(code=self.code, label=self.label, name=self.name,
                    observation=self.observation, native_visual=self.native_visual,
                    checkpoint=self.checkpoint, beam_width=self.beam_width)


CATALOG_V2 = (
    MethodDefinition("FF", "FF", "First Fit", FirstFitOptimizer, OptimizationResult),
    MethodDefinition("BF", "BF", "Best Fit", BestFitOptimizer, BestFitResult),
    MethodDefinition("WF", "WF", "Worst Fit", WorstFitOptimizer, WorstFitResult),
    MethodDefinition("HF", "HF", "Hole Filling", HoleFillingOptimizer, HoleFillingResult,
                     observation="CHOSEN_SOLUTION_REPLAY"),
    MethodDefinition("M5", "BRF", "Best Residual Fit", BestResidualFitOptimizer, BestResidualFitResult),
    MethodDefinition("M6-BS", "BS-2", "Beam Search acotada", BeamSearchOptimizer, BeamSearchResult,
                     observation="SEARCH_PROGRESS", native_visual=False, beam_width=2),
)
CATALOG_V1 = CATALOG_V2[:3]
METHODS_V2 = tuple(entry.code for entry in CATALOG_V2)
METHODS_V1 = tuple(entry.code for entry in CATALOG_V1)
BY_METHOD = MappingProxyType({entry.code: entry for entry in CATALOG_V2})


def validate_methods(methods, *, profile=PROFILE_V2, require_all=False):
    """Validate explicit identities, preserving supplied order, never inferring by index."""
    profiles = {"comparison-v1": METHODS_V1, PROFILE_V2: METHODS_V2}
    if profile not in profiles or not isinstance(methods, (list, tuple)) or not methods:
        raise ValueError("Unknown comparison profile or empty method collection")
    allowed = profiles[profile]
    if any(type(method) is not str or method not in allowed for method in methods):
        raise ValueError("Unknown method for comparison profile")
    if len(set(methods)) != len(methods):
        raise ValueError("Duplicate method identity")
    if require_all and set(methods) != set(allowed):
        raise ValueError("Comparison requires the complete profile catalog")
    return tuple(methods)
