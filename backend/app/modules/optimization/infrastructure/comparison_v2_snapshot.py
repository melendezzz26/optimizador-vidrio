"""B01 pure JSON codecs. V1 codecs/UoW remain unmodified; no DB writes here."""
from collections.abc import Mapping
from dataclasses import fields
from decimal import Decimal

from ..application.comparison_catalog import BY_METHOD, RESULT_SNAPSHOT_V3, validate_methods
from ..application.comparison_v2_contracts import ComparisonInputV2, ExecutionDiagnostic, ExecutionPayloadV2
from ..domain.problem import OptimizationResult
from .comparison_snapshot import (ComparisonSnapshotError, canonical_json,
    decode_result as decode_historical, encode_problem, decode_problem, problem_fingerprint)
from .run_snapshot import json_value, decode as decode_geometry
import json


def encode_result_v3(payload: ExecutionPayloadV2):
    if not isinstance(payload, ExecutionPayloadV2) or payload.diagnostic is None:
        raise ComparisonSnapshotError("V3 requires explicit execution diagnostics")
    return json.loads(canonical_json(dict(snapshot_version=RESULT_SNAPSHOT_V3,
        profile="comparison-v2", method=payload.method, result=json_value(payload.result),
        diagnostic=payload.diagnostic.public())))


def decode_result_v3(snapshot: Mapping, *, expected_method=None):
    try:
        value = json.loads(canonical_json(snapshot))
        if (not isinstance(value, dict) or set(value) != {
            "snapshot_version", "profile", "method", "result", "diagnostic"
        } or type(value["snapshot_version"]) is not int or value["snapshot_version"] != 3
                or value["profile"] != "comparison-v2"):
            raise ValueError("Invalid V3 result envelope")
        method = value["method"]
        validate_methods((method,))
        if expected_method is not None:
            validate_methods((expected_method,))
            if method != expected_method:
                raise ValueError("Snapshot belongs to another method")
        diagnostic = ExecutionDiagnostic(**value["diagnostic"])
        result = None
        if value["result"] is not None:
            base = decode_geometry({"snapshot_version": 1, "result": value["result"]})
            result = BY_METHOD[method].result_type(**{
                field.name: getattr(base, field.name) for field in fields(OptimizationResult)})
        return ExecutionPayloadV2(method=method, result=result, diagnostic=diagnostic)
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError) as error:
        raise ComparisonSnapshotError("Snapshot comparison-v2 inválido o incoherente") from error


def decode_compatible_result(snapshot: Mapping, *, expected_method=None):
    """Dispatch by stored version. Never synthesize historical diagnostics/methods."""
    if isinstance(snapshot, Mapping) and type(snapshot.get("snapshot_version")) is int:
        if snapshot["snapshot_version"] == 3:
            return decode_result_v3(snapshot, expected_method=expected_method)
        if snapshot["snapshot_version"] in (1, 2):
            result = decode_historical(snapshot, expected_method=expected_method)
            return ExecutionPayloadV2(method=result.method, result=result, diagnostic=None)
    raise ComparisonSnapshotError("Versión de snapshot no soportada")


def encode_comparison_input_v2(value: ComparisonInputV2):
    if not isinstance(value, ComparisonInputV2):
        raise ComparisonSnapshotError("Se requiere entrada congelada comparison-v2")
    return json.loads(canonical_json(dict(comparison_snapshot_version=2, profile="comparison-v2",
        methods=value.methods, input=encode_problem(value.problem), input_sha256=problem_fingerprint(value.problem),
        configuration_id=value.configuration_id, configuration_version=value.configuration_version,
        requested_pieces=value.requested_pieces, minimum_width_mm=value.minimum_width_mm,
        minimum_height_mm=value.minimum_height_mm, engine_parameters={"M6-BS": {"width": 2}})))


def decode_comparison_input_v2(snapshot: Mapping):
    """B01 input envelope only; mutable runtime/DB metadata belongs to B02/B05."""
    try:
        value = json.loads(canonical_json(snapshot))
        if not isinstance(value, dict) or set(value) != {
            "comparison_snapshot_version", "profile", "methods", "input", "input_sha256",
            "configuration_id", "configuration_version", "requested_pieces", "minimum_width_mm",
            "minimum_height_mm", "engine_parameters"
        } or type(value["comparison_snapshot_version"]) is not int or value["comparison_snapshot_version"] != 2:
            raise ValueError("Invalid comparison input envelope")
        problem = decode_problem(value["input"])
        parameters = value["engine_parameters"]
        if (value["profile"] != "comparison-v2" or value["input_sha256"] != problem_fingerprint(problem)
                or parameters != {"M6-BS": {"width": 2}}
                or type(parameters["M6-BS"]["width"]) is not int):
            raise ValueError("Input fingerprint/profile/BS-2 variant mismatch")
        if any(type(value[name]) is not str for name in ("minimum_width_mm", "minimum_height_mm")):
            raise ValueError("Persisted residual thresholds require decimal strings")
        return ComparisonInputV2(problem=problem, methods=tuple(value["methods"]),
            configuration_id=value["configuration_id"], configuration_version=value["configuration_version"],
            requested_pieces=value["requested_pieces"], minimum_width_mm=Decimal(value["minimum_width_mm"]),
            minimum_height_mm=Decimal(value["minimum_height_mm"]))
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError) as error:
        raise ComparisonSnapshotError("Entrada comparison-v2 inválida o incoherente") from error
