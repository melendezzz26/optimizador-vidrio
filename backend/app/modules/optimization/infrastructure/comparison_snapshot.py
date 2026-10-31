"""Snapshots multimétodo y DTO JSON desconectado para procesos spawn.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
El codec FF histórico permanece intacto. No ejecutar optimizadores al decodificar.
"""
from collections.abc import Mapping
from dataclasses import fields
import hashlib
import json

from ..domain.best_fit import BestFitResult
from ..domain.worst_fit import WorstFitResult
from ..domain.problem import OptimizationProblem, OptimizationResult
from .run_snapshot import decode as decode_legacy, json_value

METHODS = ("FF", "BF", "WF")
RESULT_TYPES = {"FF": OptimizationResult, "BF": BestFitResult, "WF": WorstFitResult}
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_RESULT_BYTES = 8 * 1024 * 1024


class ComparisonSnapshotError(ValueError):
    """Snapshot incompatible, incoherente o demasiado grande; sin detalles internos."""


def canonical_json(value, *, maximum_bytes=MAX_RESULT_BYTES):
    try:
        text = json.dumps(json_value(value), sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ComparisonSnapshotError("El snapshot no contiene JSON canónico válido.") from error
    if len(text.encode("utf-8")) > maximum_bytes:
        raise ComparisonSnapshotError("El snapshot excede el tamaño permitido.")
    return text


def _detached(value, maximum_bytes):
    return json.loads(canonical_json(value, maximum_bytes=maximum_bytes))


def _read_result(data):
    try:
        return decode_legacy({"snapshot_version": 1, "result": data})
    except (KeyError, TypeError, ValueError, ArithmeticError, OverflowError) as error:
        raise ComparisonSnapshotError("El resultado persistido no es válido.") from error


def encode_result(result: OptimizationResult) -> dict:
    if not isinstance(result, OptimizationResult) or result.method not in METHODS:
        raise ComparisonSnapshotError("Método de resultado no soportado.")
    return _detached({"snapshot_version": 2, "method": result.method,
                      "result": json_value(result)}, MAX_RESULT_BYTES)


def decode_result(snapshot: Mapping, *, expected_method: str | None = None) -> OptimizationResult:
    """Conservar el método del sobre; contrastarlo con la fila dueña si se indica.

    V1 solo puede representar FF. Nunca reinterpretarlo como BF/WF por petición
    del llamador ni intentar inferir un algoritmo a partir de sus colocaciones.
    """
    if expected_method is not None and expected_method not in METHODS:
        raise ComparisonSnapshotError("Método esperado no soportado.")
    value = _detached(snapshot, MAX_RESULT_BYTES)
    if not isinstance(value, dict) or type(value.get("snapshot_version")) is not int:
        raise ComparisonSnapshotError("Versión de snapshot inválida.")
    version = value["snapshot_version"]
    if version == 1:
        method = "FF"
        if "method" in value and value["method"] != method:
            raise ComparisonSnapshotError("El formato histórico solo representa First Fit.")
    elif version == 2 and set(value) == {"snapshot_version", "method", "result"}:
        method = value["method"]
    else:
        raise ComparisonSnapshotError("Versión de snapshot no soportada.")
    if not isinstance(method, str) or method not in METHODS or expected_method not in (None, method):
        raise ComparisonSnapshotError("El método del resultado no corresponde a su ejecución.")
    base = _read_result(value.get("result"))
    return RESULT_TYPES[method](**{field.name: getattr(base, field.name)
                                  for field in fields(OptimizationResult)})


def encode_problem(problem: OptimizationProblem) -> dict:
    if not isinstance(problem, OptimizationProblem):
        raise ComparisonSnapshotError("Se requiere una entrada de optimización válida.")
    return _detached({"input_version": 1, "problem": json_value(problem)}, MAX_INPUT_BYTES)


def decode_problem(payload: Mapping) -> OptimizationProblem:
    value = _detached(payload, MAX_INPUT_BYTES)
    if (not isinstance(value, dict) or set(value) != {"input_version", "problem"}
            or type(value["input_version"]) is not int or value["input_version"] != 1):
        raise ComparisonSnapshotError("Versión de entrada no soportada.")
    return _read_result({"problem": value["problem"], "placements": [], "metrics": None,
                         "computation_time_ms": None}).problem


def problem_fingerprint(problem: OptimizationProblem) -> str:
    """Incluye configuración, cantidades expandidas, geometrías y ranking de stock."""
    text = canonical_json(encode_problem(problem), maximum_bytes=MAX_INPUT_BYTES)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
