"""Adaptador SQLAlchemy del repositorio de inventario."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MovimientoInventario, Plancha, Retazo, TipoVidrio, TipoVidrioEspesor
from app.modules.inventory.application.dto import (
    MovimientoInventarioData, PlanchaData, RetazoData, TipoVidrioData,
)
from app.modules.inventory.domain.exceptions import InventoryConflictError, InventoryNotFoundError, InventoryValidationError
from app.modules.inventory.domain.writeoff import TipoEventoBajaManual

_MANUAL_WRITEOFF_EVENTS = tuple(event.value for event in TipoEventoBajaManual)

_UNIQUE_CONFLICT_CONSTRAINTS = frozenset({
    "tipos_vidrio_nombre_key",
    "retazos_codigo_key",
    "uq_movimientos_baja_manual_retazo",
})


class SqlAlchemyInventoryRepository:
    """Implementa InventoryRepository con SQLAlchemy + PostgreSQL.

    Recibe un callable que crea Session (sessionmaker o factory equivalente).
    Gestiona una única sesión activa dentro de ``transaction()``.
    """

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    # ------------------------------------------------------------------ #
    # Transacción                                                         #
    # ------------------------------------------------------------------ #

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("No active transaction — call transaction() first.")
        return self._session

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        if self._session is not None:
            raise RuntimeError("Transacción anidada no permitida: ya hay una sesión activa.")

        session: Session = self._session_factory()
        self._session = session
        try:
            yield
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            self._translate_or_raise(exc)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._session = None

    @contextmanager
    def read_transaction(self) -> Generator[None, None, None]:
        """Abre una sesión de lectura que nunca confirma cambios."""
        if self._session is not None:
            raise RuntimeError("Transacción anidada no permitida: ya hay una sesión activa.")

        session: Session = self._session_factory()
        self._session = session
        try:
            yield
        finally:
            try:
                session.rollback()
            finally:
                try:
                    session.close()
                finally:
                    self._session = None

    @staticmethod
    def _translate_or_raise(exc: IntegrityError) -> None:
        constraint = getattr(getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", None)
        if constraint in _UNIQUE_CONFLICT_CONSTRAINTS:
            raise InventoryConflictError(f"Unique constraint violation: {constraint}") from exc
        raise exc

    # ------------------------------------------------------------------ #
    # Mapeo ORM → DTO                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_tipo_vidrio(row: TipoVidrio, espesores: tuple[Decimal, ...] = ()) -> TipoVidrioData:
        return TipoVidrioData(
            id_tipo_vidrio=row.id_tipo_vidrio,
            nombre=row.nombre,
            descripcion=row.descripcion,
            estado=row.estado,
            espesores_mm=espesores,
        )

    @staticmethod
    def _to_plancha(row: Plancha) -> PlanchaData:
        return PlanchaData(
            id_plancha=row.id_plancha,
            ancho_mm=row.ancho_mm,
            alto_mm=row.alto_mm,
            espesor_mm=row.espesor_mm,
            cantidad=row.cantidad,
            estado=row.estado,
            fecha_registro=row.fecha_registro,
            id_tipo_vidrio=row.id_tipo_vidrio,
        )

    @staticmethod
    def _encode_geometria(data: object) -> object:
        if isinstance(data, dict):
            return {k: SqlAlchemyInventoryRepository._encode_geometria(v) for k, v in data.items()}
        # Pydantic's Python-mode dump preserves vertex pairs as tuples of Decimal.
        # Both containers must be traversed at the JSONB boundary (POST and PATCH).
        elif isinstance(data, (list, tuple)):
            return [SqlAlchemyInventoryRepository._encode_geometria(v) for v in data]
        elif isinstance(data, Decimal):
            if data == data.to_integral_value():
                return int(data)
            return float(data)
        return data

    @staticmethod
    def _to_retazo(row: Retazo) -> RetazoData:
        return RetazoData(
            id_retazo=row.id_retazo,
            codigo=row.codigo,
            espesor_mm=row.espesor_mm,
            geometria=deepcopy(row.geometria),
            area_mm2=row.area_mm2,
            estado=row.estado,
            fecha_registro=row.fecha_registro,
            id_tipo_vidrio=row.id_tipo_vidrio,
            id_ejecucion_origen=row.id_ejecucion_origen,
        )

    @staticmethod
    def _to_movement(row: MovimientoInventario) -> MovimientoInventarioData:
        return MovimientoInventarioData(
            id_movimiento=row.id_movimiento,
            id_plancha=row.id_plancha,
            id_retazo=row.id_retazo,
            tipo_evento=row.tipo_evento,
            motivo=row.motivo,
            observacion=row.observacion,
            id_usuario=row.id_usuario,
            fecha=row.fecha,
            id_optimizacion=row.id_optimizacion,
            cantidad_afectada=row.cantidad_afectada,
        )

    # ------------------------------------------------------------------ #
    # TipoVidrio                                                          #
    # ------------------------------------------------------------------ #

    def get_tipo_vidrio(self, id_tipo_vidrio: int) -> TipoVidrioData | None:
        session = self._require_session()
        row = session.get(TipoVidrio, id_tipo_vidrio)
        if row is None:
            return None
        return self._to_tipo_vidrio(row, self._catalog_thicknesses([id_tipo_vidrio]).get(id_tipo_vidrio, ()))

    def _catalog_thicknesses(self, identifiers: list[int]) -> dict[int, tuple[Decimal, ...]]:
        session = self._require_session()
        if not identifiers:
            return {}
        rows = session.query(TipoVidrioEspesor).filter(
            TipoVidrioEspesor.id_tipo_vidrio.in_(identifiers)
        ).order_by(TipoVidrioEspesor.espesor_mm).all()
        grouped: dict[int, list[Decimal]] = {}
        for row in rows:
            grouped.setdefault(row.id_tipo_vidrio, []).append(row.espesor_mm)
        return {identifier: tuple(values) for identifier, values in grouped.items()}

    def tipo_nombre_exists(self, nombre: str) -> bool:
        session = self._require_session()
        return session.query(
            session.query(TipoVidrio).filter(TipoVidrio.nombre == nombre).exists()
        ).scalar()

    def create_tipo_vidrio(self, *, nombre: str, descripcion: str | None,
                           estado: bool) -> TipoVidrioData:
        session = self._require_session()
        row = TipoVidrio(nombre=nombre, descripcion=descripcion, estado=estado)
        session.add(row)
        session.flush()
        return self._to_tipo_vidrio(row)

    def list_tipos_vidrio(self) -> list[TipoVidrioData]:
        session = self._require_session()
        rows = session.query(TipoVidrio).all()
        thicknesses = self._catalog_thicknesses([row.id_tipo_vidrio for row in rows])
        return [self._to_tipo_vidrio(row, thicknesses.get(row.id_tipo_vidrio, ())) for row in rows]

    # ------------------------------------------------------------------ #
    # Plancha                                                             #
    # ------------------------------------------------------------------ #

    def get_plancha(self, id_plancha: int) -> PlanchaData | None:
        session = self._require_session()
        row = session.get(Plancha, id_plancha)
        return self._to_plancha(row) if row is not None else None

    def lock_plancha_for_update(self, id_plancha: int) -> PlanchaData | None:
        session = self._require_session()
        row = session.execute(
            select(Plancha)
            .where(Plancha.id_plancha == id_plancha)
            .with_for_update()
        ).scalar_one_or_none()
        return self._to_plancha(row) if row is not None else None

    def has_manual_writeoff_plancha(self, id_plancha: int) -> bool:
        session = self._require_session()
        return session.query(
            session.query(MovimientoInventario.id_movimiento)
            .filter(
                MovimientoInventario.id_plancha == id_plancha,
                MovimientoInventario.tipo_evento.in_(_MANUAL_WRITEOFF_EVENTS),
            )
            .exists()
        ).scalar()

    def create_plancha_writeoff_movement(
        self, id_plancha: int, *, tipo_evento: str, motivo: str,
        observacion: str | None, id_usuario: int, cantidad_afectada: int,
    ) -> MovimientoInventarioData:
        return self._create_writeoff_movement(
            id_plancha=id_plancha, id_retazo=None, tipo_evento=tipo_evento,
            motivo=motivo, observacion=observacion, id_usuario=id_usuario, cantidad_afectada=cantidad_afectada,
        )

    def _create_writeoff_movement(
        self, *, id_plancha: int | None, id_retazo: int | None,
        tipo_evento: str, motivo: str, observacion: str | None, id_usuario: int, cantidad_afectada: int,
    ) -> MovimientoInventarioData:
        # NULL is readable history, never a valid new application write.
        if type(cantidad_afectada) is not int or cantidad_afectada <= 0:
            raise InventoryValidationError("cantidad_afectada debe ser un entero positivo.")
        if id_retazo is not None and cantidad_afectada != 1:
            raise InventoryValidationError("La baja de retazo afecta exactamente una unidad.")
        session = self._require_session()
        row = MovimientoInventario(
            id_plancha=id_plancha,
            id_retazo=id_retazo,
            tipo_evento=tipo_evento,
            motivo=motivo,
            observacion=observacion,
            id_usuario=id_usuario,
            id_optimizacion=None,
            cantidad_afectada=cantidad_afectada,
        )
        session.add(row)
        session.flush()
        session.refresh(row)
        return self._to_movement(row)

    def create_plancha(self, *, ancho_mm: Decimal, alto_mm: Decimal,
                       espesor_mm: Decimal, cantidad: int, estado: bool,
                       fecha_registro: datetime, id_tipo_vidrio: int) -> PlanchaData:
        session = self._require_session()
        row = Plancha(
            ancho_mm=ancho_mm, alto_mm=alto_mm, espesor_mm=espesor_mm,
            cantidad=cantidad, estado=estado, fecha_registro=fecha_registro,
            id_tipo_vidrio=id_tipo_vidrio,
        )
        session.add(row)
        session.flush()
        return self._to_plancha(row)

    def list_planchas(self) -> list[PlanchaData]:
        session = self._require_session()
        return [self._to_plancha(row) for row in session.query(Plancha).order_by(
            (Plancha.estado & (Plancha.cantidad > 0)).desc(),
            Plancha.fecha_registro.desc(), Plancha.id_plancha.desc(),
        ).all()]

    def list_plancha_movements(self, id_plancha: int) -> list[MovimientoInventarioData] | None:
        """Lista del más antiguo al más reciente; el ID ordena fechas iguales."""
        session = self._require_session()
        if session.get(Plancha, id_plancha) is None:
            return None
        rows = session.execute(
            select(MovimientoInventario)
            .where(MovimientoInventario.id_plancha == id_plancha)
            .order_by(MovimientoInventario.fecha.asc(), MovimientoInventario.id_movimiento.asc())
        ).scalars().all()
        return [self._to_movement(row) for row in rows]

    def save_plancha(self, data: PlanchaData) -> PlanchaData:
        session = self._require_session()
        row = session.get(Plancha, data.id_plancha)
        if row is None:
            raise InventoryNotFoundError(f"Plancha {data.id_plancha} no encontrada.")
        row.ancho_mm = data.ancho_mm
        row.alto_mm = data.alto_mm
        row.espesor_mm = data.espesor_mm
        row.cantidad = data.cantidad
        row.estado = data.estado
        row.id_tipo_vidrio = data.id_tipo_vidrio
        session.flush()
        return self._to_plancha(row)

    # ------------------------------------------------------------------ #
    # Retazo                                                              #
    # ------------------------------------------------------------------ #

    def get_retazo(self, id_retazo: int) -> RetazoData | None:
        session = self._require_session()
        row = session.get(Retazo, id_retazo)
        return self._to_retazo(row) if row is not None else None

    def lock_retazo_for_update(self, id_retazo: int) -> RetazoData | None:
        session = self._require_session()
        row = session.execute(
            select(Retazo)
            .where(Retazo.id_retazo == id_retazo)
            .with_for_update()
        ).scalar_one_or_none()
        return self._to_retazo(row) if row is not None else None

    def has_manual_writeoff_retazo(self, id_retazo: int) -> bool:
        session = self._require_session()
        return session.query(
            session.query(MovimientoInventario.id_movimiento)
            .filter(
                MovimientoInventario.id_retazo == id_retazo,
                MovimientoInventario.tipo_evento.in_(_MANUAL_WRITEOFF_EVENTS),
            )
            .exists()
        ).scalar()

    def create_retazo_writeoff_movement(
        self, id_retazo: int, *, tipo_evento: str, motivo: str,
        observacion: str | None, id_usuario: int,
    ) -> MovimientoInventarioData:
        cantidad_afectada = 1
        return self._create_writeoff_movement(
            id_plancha=None, id_retazo=id_retazo, tipo_evento=tipo_evento,
            motivo=motivo, observacion=observacion, id_usuario=id_usuario, cantidad_afectada=cantidad_afectada,
        )

    def retazo_codigo_exists(self, codigo: str, exclude_id: int | None = None) -> bool:
        session = self._require_session()
        query = session.query(Retazo).filter(Retazo.codigo == codigo)
        if exclude_id is not None:
            query = query.filter(Retazo.id_retazo != exclude_id)
        return session.query(query.exists()).scalar()

    def create_retazo(self, *, codigo: str, espesor_mm: Decimal,
                      geometria: dict[str, object], area_mm2: Decimal, estado: bool,
                      fecha_registro: datetime, id_tipo_vidrio: int,
                      id_ejecucion_origen: int | None) -> RetazoData:
        session = self._require_session()
        row = Retazo(
            codigo=codigo, espesor_mm=espesor_mm, geometria=deepcopy(self._encode_geometria(geometria)), # type: ignore
            area_mm2=area_mm2, estado=estado, fecha_registro=fecha_registro,
            id_tipo_vidrio=id_tipo_vidrio, id_ejecucion_origen=id_ejecucion_origen,
        )
        session.add(row)
        session.flush()
        return self._to_retazo(row)

    def list_retazos(self) -> list[RetazoData]:
        session = self._require_session()
        return [self._to_retazo(row) for row in session.query(Retazo).order_by(
            Retazo.estado.desc(), Retazo.fecha_registro.desc(), Retazo.id_retazo.desc(),
        ).all()]

    def get_retazo_origin(self, id_retazo: int) -> dict | None:
        from app.models import EjecucionOptimizacion, OptimizacionPedido
        session = self._require_session()
        row = session.get(Retazo, id_retazo)
        if row is None:
            return None
        result = dict(id_ejecucion_origen=row.id_ejecucion_origen,
                      id_optimizacion=None, order_ids=[], source=None)
        if row.id_ejecucion_origen is None:
            return result
        execution = session.get(EjecucionOptimizacion, row.id_ejecucion_origen)
        if execution is None:
            return result
        result['id_optimizacion'] = execution.id_optimizacion
        result['order_ids'] = [value[0] for value in session.query(OptimizacionPedido.id_pedido)
            .filter(OptimizacionPedido.id_optimizacion == execution.id_optimizacion)
            .order_by(OptimizacionPedido.id_pedido).all()]
        snapshot = execution.patron_resultado if isinstance(execution.patron_resultado, dict) else {}
        receipt = snapshot.get('confirmation', {}).get('receipt', {})
        created = next((r for r in receipt.get('remnants_created', []) if r.get('remnant_id') == row.id_retazo), None)
        if created:
            source = created['source']
            result['source'] = dict(material_source=source['source'], material_id=source['material_id'],
                                    stock_unit_index=source['physical_unit_index'])
        return result

    def list_retazo_movements(self, id_retazo: int) -> list[MovimientoInventarioData] | None:
        """Lista del más antiguo al más reciente; el ID ordena fechas iguales."""
        session = self._require_session()
        if session.get(Retazo, id_retazo) is None:
            return None
        rows = session.execute(
            select(MovimientoInventario)
            .where(MovimientoInventario.id_retazo == id_retazo)
            .order_by(MovimientoInventario.fecha.asc(), MovimientoInventario.id_movimiento.asc())
        ).scalars().all()
        return [self._to_movement(row) for row in rows]

    def save_retazo(self, data: RetazoData) -> RetazoData:
        session = self._require_session()
        row = session.get(Retazo, data.id_retazo)
        if row is None:
            raise InventoryNotFoundError(f"Retazo {data.id_retazo} no encontrado.")
        row.codigo = data.codigo
        row.espesor_mm = data.espesor_mm
        row.geometria = deepcopy(self._encode_geometria(data.geometria)) # type: ignore
        row.area_mm2 = data.area_mm2
        row.estado = data.estado
        row.id_tipo_vidrio = data.id_tipo_vidrio
        # Preserve: id_retazo, fecha_registro, id_ejecucion_origen
        session.flush()
        return self._to_retazo(row)
