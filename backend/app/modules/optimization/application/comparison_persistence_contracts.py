"""B02 durable views; no calculation, supervisor or selection use cases."""
from dataclasses import dataclass
import re

from .comparison_catalog import METHODS_V2, validate_methods
from .comparison_contracts import Comparison, ComparisonExecution, immutable_json
from .comparison_v2_contracts import ExecutionDiagnostic


@dataclass(frozen=True, kw_only=True)
class VisualReferenceV2:
    comparison_id: int
    execution_id: int
    method: str
    mask_ref: str

    def __post_init__(self):
        validate_methods((self.method,))
        if any(type(v) is not int or not 0 < v <= 2147483647
               for v in (self.comparison_id, self.execution_id)):
            raise ValueError("Visual reference requires positive owner identities")
        if not isinstance(self.mask_ref, str) or re.fullmatch(r"[a-f0-9]{32}", self.mask_ref) is None:
            raise ValueError("Invalid visual reference")

    def record(self):
        return dict(profile="comparison-v2", schema_version=2, comparison_id=self.comparison_id,
                    execution_id=self.execution_id, method=self.method, mask_ref=self.mask_ref)

    @classmethod
    def from_record(cls, value):
        if (not isinstance(value, dict) or set(value) != {
            "profile", "schema_version", "comparison_id", "execution_id", "method", "mask_ref"
        } or value["profile"] != "comparison-v2" or type(value["schema_version"]) is not int
                or value["schema_version"] != 2):
            raise ValueError("Invalid durable visual reference envelope")
        return cls(**{key: value[key] for key in ("comparison_id", "execution_id", "method", "mask_ref")})


@dataclass(frozen=True, kw_only=True)
class PersistedExecutionV2(ComparisonExecution):
    dispatch_state: str
    diagnostic: ExecutionDiagnostic | None
    visual_references: tuple[VisualReferenceV2, ...] = ()

    @property
    def outcome(self):
        if self.status == "EN_EJECUCION":
            return None
        return "FAILED" if self.status == "FALLIDA" else "COMPLETE" if self.result.complete else "PARTIAL"


@dataclass(frozen=True, kw_only=True)
class PersistedComparisonV2(Comparison):
    executions: tuple[PersistedExecutionV2, ...]
    methods: tuple[str, ...] = METHODS_V2
    profile: str = "comparison-v2"
    runtime: object = None

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, "executions", tuple(self.executions))
        object.__setattr__(self, "methods", tuple(self.methods))
        object.__setattr__(self, "confirmation", immutable_json(self.confirmation))
        object.__setattr__(self, "runtime", immutable_json(self.runtime))

    @property
    def incomplete(self):
        return any(e.outcome in ("PARTIAL", "FAILED") for e in self.executions)

    @property
    def supervisor_stopped(self):
        return self.workers_stopped
