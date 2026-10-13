"""Casos de uso de inventario independientes de HTTP y persistencia concreta."""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import fields, replace
from datetime import datetime, timezone
from decimal import Decimal

from ..domain.exceptions import (
    InventoryConflictError, InventoryNotFoundError, InventoryValidationError,
)
from ..domain.geometry import calculate_area_mm2
from ..domain.writeoff import BajaManual
from .dto import (
    BajaInventarioResult, CreatePlancha, CreateRetazo, CreateTipoVidrio, MovimientoInventarioData,
    PlanchaData, RetazoData, TipoVidrioData, UpdatePlancha, UpdateRetazo,
)
from .ports import InventoryRepository
from .catalog import validate_tipo_espesor


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise InventoryValidationError(f"{field} debe contener entre 1 y {maximum} caracteres.")
    return value.strip()


def _positive_decimal(value: object, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int)):
        raise InventoryValidationError(f"{field} debe ser Decimal o entero, no booleano.")
    number = Decimal(value)
    if not number.is_finite() or number <= 0:
        raise InventoryValidationError(f"{field} debe ser finito y mayor que cero.")
    return number


def _thickness(value: object) -> Decimal:
    return _positive_decimal(value, "espesor_mm")


def _integer(value: object, field: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InventoryValidationError(f"{field} debe ser entero y mayor o igual que {minimum}.")
    return value


def _changes(command: UpdatePlancha | UpdateRetazo) -> dict[str, object]:
    changes = {field.name: getattr(command, field.name) for field in fields(command)
               if getattr(command, field.name) is not None}
    if not changes:
        raise InventoryValidationError("La edición debe incluir al menos un campo.")
    if "estado" in changes and not isinstance(changes["estado"], bool):
        raise InventoryValidationError("estado debe ser booleano.")
    if "id_tipo_vidrio" in changes:
        changes["id_tipo_vidrio"] = _integer(changes["id_tipo_vidrio"], "id_tipo_vidrio")
    if "espesor_mm" in changes:
        changes["espesor_mm"] = _thickness(changes["espesor_mm"])
    return changes


class InventoryService:
    def __init__(self, repository: InventoryRepository, *, now: Callable[[], datetime] = _utc_now):
        self._repository = repository
        self._now = now

    def _registration_time(self) -> datetime:
        value = self._now()
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise InventoryValidationError("El reloj debe devolver una fecha con zona horaria.")
        return value.astimezone(timezone.utc)

    def create_tipo_vidrio(self, command: CreateTipoVidrio) -> TipoVidrioData:
        nombre = _text(command.nombre, "nombre", 100)
        if command.descripcion is not None and not isinstance(command.descripcion, str):
            raise InventoryValidationError("descripcion debe ser texto o None.")
        with self._repository.transaction():
            if self._repository.tipo_nombre_exists(nombre):
                raise InventoryConflictError("El nombre de tipo de vidrio ya existe.")
            return self._repository.create_tipo_vidrio(
                nombre=nombre, descripcion=command.descripcion, estado=True)

    def list_tipos_vidrio(self) -> list[TipoVidrioData]:
        with self._repository.transaction():
            return self._repository.list_tipos_vidrio()

    def create_plancha(self, command: CreatePlancha) -> PlanchaData:
        ancho = _positive_decimal(command.ancho_mm, "ancho_mm")
        alto = _positive_decimal(command.alto_mm, "alto_mm")
        espesor = _thickness(command.espesor_mm)
        cantidad = _integer(command.cantidad, "cantidad")
        tipo = _integer(command.id_tipo_vidrio, "id_tipo_vidrio")
        fecha = self._registration_time()
        with self._repository.transaction():
            validate_tipo_espesor(self._repository, tipo, espesor)
            return self._repository.create_plancha(
                ancho_mm=ancho, alto_mm=alto, espesor_mm=espesor, cantidad=cantidad,
                id_tipo_vidrio=tipo, estado=True, fecha_registro=fecha)

    def list_planchas(self) -> list[PlanchaData]:
        with self._repository.transaction():
            return self._repository.list_planchas()

    def list_plancha_movements(self, id_plancha: int) -> list[MovimientoInventarioData]:
        identifier = _integer(id_plancha, "id_plancha")
        with self._repository.read_transaction():
            movements = self._repository.list_plancha_movements(identifier)
            if movements is None:
                raise InventoryNotFoundError("Plancha inexistente.")
            return movements

    def update_plancha(self, id_plancha: int, command: UpdatePlancha) -> PlanchaData:
        identifier = _integer(id_plancha, "id_plancha")
        changes = _changes(command)
        for field in ("ancho_mm", "alto_mm"):
            if field in changes:
                changes[field] = _positive_decimal(changes[field], field)
        if "cantidad" in changes:
            changes["cantidad"] = _integer(changes["cantidad"], "cantidad", minimum=0)
        with self._repository.transaction():
            current = self._repository.lock_plancha_for_update(identifier)
            if current is None:
                raise InventoryNotFoundError("Plancha inexistente.")
            if changes.get("cantidad", current.cantidad) == 0:
                changes["estado"] = False
            if command.estado is True and not current.estado and self._repository.has_manual_writeoff_plancha(identifier):
                raise InventoryConflictError("Una plancha dada de baja no puede reactivarse.")
            tipo = changes.get("id_tipo_vidrio", current.id_tipo_vidrio)
            espesor = changes.get("espesor_mm", current.espesor_mm)
            if (tipo, espesor) != (current.id_tipo_vidrio, current.espesor_mm):
                validate_tipo_espesor(self._repository, tipo, espesor)
            return self._repository.save_plancha(replace(current, **changes))

    def create_retazo(self, command: CreateRetazo) -> RetazoData:
        codigo = _text(command.codigo, "codigo", 40)
        espesor = _thickness(command.espesor_mm)
        tipo = _integer(command.id_tipo_vidrio, "id_tipo_vidrio")
        geometria = deepcopy(command.geometria)
        area = calculate_area_mm2(geometria)
        fecha = self._registration_time()
        with self._repository.transaction():
            validate_tipo_espesor(self._repository, tipo, espesor)
            if self._repository.retazo_codigo_exists(codigo):
                raise InventoryConflictError("El código de retazo ya existe.")
            return self._repository.create_retazo(
                codigo=codigo, espesor_mm=espesor, geometria=geometria, area_mm2=area,
                id_tipo_vidrio=tipo, estado=True, fecha_registro=fecha, id_ejecucion_origen=None)

    def list_retazos(self) -> list[RetazoData]:
        with self._repository.transaction():
            return self._repository.list_retazos()

    def list_retazo_movements(self, id_retazo: int) -> list[MovimientoInventarioData]:
        identifier = _integer(id_retazo, "id_retazo")
        with self._repository.read_transaction():
            movements = self._repository.list_retazo_movements(identifier)
            if movements is None:
                raise InventoryNotFoundError("Retazo inexistente.")
            return movements

    def update_retazo(self, id_retazo: int, command: UpdateRetazo) -> RetazoData:
        identifier = _integer(id_retazo, "id_retazo")
        changes = _changes(command)
        if "codigo" in changes:
            changes["codigo"] = _text(changes["codigo"], "codigo", 40)
        if "geometria" in changes:
            changes["geometria"] = deepcopy(changes["geometria"])
            changes["area_mm2"] = calculate_area_mm2(changes["geometria"])
        with self._repository.transaction():
            current = self._repository.lock_retazo_for_update(identifier)
            if current is None:
                raise InventoryNotFoundError("Retazo inexistente.")
            if changes.get("estado") is True and self._repository.has_manual_writeoff_retazo(identifier):
                raise InventoryConflictError("Un retazo dado de baja no puede reactivarse.")
            tipo = changes.get("id_tipo_vidrio", current.id_tipo_vidrio)
            espesor = changes.get("espesor_mm", current.espesor_mm)
            if (tipo, espesor) != (current.id_tipo_vidrio, current.espesor_mm):
                validate_tipo_espesor(self._repository, tipo, espesor)
            if "codigo" in changes and self._repository.retazo_codigo_exists(changes["codigo"], exclude_id=identifier):
                raise InventoryConflictError("El código de retazo ya existe.")
            return self._repository.save_retazo(replace(current, **changes))

    def writeoff_plancha(
        self, id_plancha: int, command: BajaManual, *, id_usuario: int,
    ) -> BajaInventarioResult:
        identifier = _integer(id_plancha, "id_plancha")
        actor = _integer(id_usuario, "id_usuario")
        if not isinstance(command, BajaManual):
            raise InventoryValidationError("La solicitud de baja no es válida.")

        with self._repository.transaction():
            current = self._repository.lock_plancha_for_update(identifier)
            if current is None:
                raise InventoryNotFoundError("Plancha inexistente.")
            if not current.estado or current.cantidad <= 0:
                raise InventoryConflictError("La plancha no tiene stock disponible.")
            quantity = _integer(command.cantidad_afectada, "cantidad_afectada")
            if quantity > current.cantidad:
                raise InventoryValidationError("cantidad_afectada excede la cantidad disponible.")
            remaining = current.cantidad - quantity

            movement = self._repository.create_plancha_writeoff_movement(
                identifier,
                tipo_evento=command.tipo_evento.value,
                motivo=command.motivo,
                observacion=command.observacion,
                id_usuario=actor,
                cantidad_afectada=quantity,
            )
            updated = self._repository.save_plancha(replace(
                current, cantidad=remaining, estado=remaining > 0,
            ))
        return BajaInventarioResult(movimiento=movement, estado=updated.estado, cantidad=updated.cantidad)

    def writeoff_retazo(
        self, id_retazo: int, command: BajaManual, *, id_usuario: int,
    ) -> BajaInventarioResult:
        identifier = _integer(id_retazo, "id_retazo")
        actor = _integer(id_usuario, "id_usuario")
        if not isinstance(command, BajaManual):
            raise InventoryValidationError("La solicitud de baja no es válida.")

        if command.cantidad_afectada not in (None, 1):
            raise InventoryValidationError("La baja de retazo afecta exactamente una unidad.")

        with self._repository.transaction():
            current = self._repository.lock_retazo_for_update(identifier)
            if current is None:
                raise InventoryNotFoundError("Retazo inexistente.")
            if self._repository.has_manual_writeoff_retazo(identifier):
                raise InventoryConflictError("El retazo ya tiene una baja manual registrada.")

            movement = self._repository.create_retazo_writeoff_movement(
                identifier,
                tipo_evento=command.tipo_evento.value,
                motivo=command.motivo,
                observacion=command.observacion,
                id_usuario=actor,
            )
            self._repository.save_retazo(replace(current, estado=False))
        return BajaInventarioResult(movimiento=movement, estado=False)
