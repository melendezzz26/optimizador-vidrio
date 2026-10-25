"""Real repositories -> snapshots/stock -> WF, on isolated SQLite without Alembic.

This slice verifies orchestration of the real read adapters, not PostgreSQL
constraints, concurrency or confirmation. Only cloned test metadata is adapted.
"""
from datetime import datetime, timezone
from decimal import Decimal as D

import pytest
from sqlalchemy import CheckConstraint, JSON, MetaData, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker

from app.models import Base, Cliente, Pedido, Plancha, Retazo, Rol, TipoVidrio, TipoVidrioEspesor, Usuario
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.application.stock import with_compatible_stock
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource, OptimizationConfig, OptimizationResult
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from tests.integration.optimization.test_first_fit_slice import (
    test_persisted_multiorder_pieces_produce_real_placements_without_db_mutations as existing_first_fit_slice,
)


@pytest.fixture
def sqlite_slice():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    # Never mutate ORM metadata or connect to the developer's configured DB.
    for table in Base.metadata.tables.values():
        cloned = table.to_metadata(metadata)
        for constraint in list(cloned.constraints):
            if isinstance(constraint, CheckConstraint):
                cloned.constraints.discard(constraint)
        for column in cloned.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)
    with factory() as session:
        session.add(Rol(id_rol=1, nombre="Operario"))
        session.add(Usuario(id_usuario=1, id_rol=1, dni="70000001", usuario="O70000001",
                            nombres="Prueba", apellidos="Slice", password_hash="unused-test-hash",
                            estado=True, fecha_creacion=now))
        session.add(Cliente(id_cliente=41, nombre_razon_social="Cliente de prueba", estado=True, fecha_registro=now))
        session.add_all([TipoVidrio(id_tipo_vidrio=i, nombre=f"Vidrio {i}", estado=True) for i in (7, 8)])
        session.add_all([TipoVidrioEspesor(id_tipo_vidrio=i, espesor_mm=6) for i in (7, 8)])
        session.commit()
    try:
        yield factory
    finally:
        engine.dispose()


def database_snapshot(factory):
    with factory() as session:
        return {name: session.execute(select(table).order_by(*table.primary_key.columns)).all()
                for name, table in Base.metadata.tables.items()}


def test_real_multiorder_multimaterial_stock_to_wf_without_any_database_writes(sqlite_slice):
    factory = sqlite_slice
    pieces = [dict(tipo_forma="RECTANGULO", cantidad=1, dimensiones={"width_mm": 2, "height_mm": 2},
                   geometria={"type": "RECTANGULO", "width_mm": 2, "height_mm": 2},
                   id_tipo_vidrio=glass, espesor_mm=6, area_mm2=4) for glass in (7, 8)]
    now = datetime.now(timezone.utc)
    with factory() as session:
        orders = SQLAlchemyOrderRepository(session)
        ids = [orders.create_order(1, pieces, id_cliente=41) for _ in range(2)]
        session.add_all([Plancha(id_plancha=identifier, id_tipo_vidrio=glass, ancho_mm=4, alto_mm=4,
                                espesor_mm=6, cantidad=2, estado=True, fecha_registro=now)
                         for identifier, glass in ((5, 7), (6, 8))])
        session.add(Retazo(id_retazo=9, codigo="WF-TEST-9", id_tipo_vidrio=7, espesor_mm=6,
                           geometria={"type": "RECTANGULO", "width_mm": 3, "height_mm": 3},
                           area_mm2=9, estado=True, fecha_registro=now, id_ejecucion_origen=None))
        session.commit()
        snapshots = [p for identifier in ids for p in orders.get_order(identifier)["piezas"]]
    before = database_snapshot(factory)
    cfg = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=90)
    prepared = prepare_persisted_problem(ids[::-1], snapshots[::-1], cfg)
    provider = InventoryStockAdapter(SqlAlchemyInventoryRepository(factory))
    problem = with_compatible_stock(prepared, provider)
    events = []
    result = WorstFitOptimizer().optimize(problem, events.append)
    assert isinstance(result, OptimizationResult) and result.method == "WF" and result.complete
    assert result.total_units == result.placed_units == 4
    assert {p.piece.order_id for p in result.placements} == set(ids)
    assert all(p.piece.material_key == p.stock.material_key for p in result.placements)
    assert [(p.stock.source, p.stock.material_id, p.stock.physical_unit_index) for p in result.placements] == [
        (MaterialSource.REMNANT, 9, 1), (MaterialSource.SHEET, 5, 1),
        (MaterialSource.SHEET, 6, 1), (MaterialSource.SHEET, 6, 2),
    ]
    assert [(p.x_mm, p.y_mm) for p in result.placements] == [(0, 0)] * 4
    assert [e.placed_units for e in events if e.kind == "piece_placed"] == [1, 2, 3, 4]
    assert result == WorstFitOptimizer().optimize(with_compatible_stock(prepared, provider))
    measured, residuals = calculate_metrics(result, D(1), D(1))
    assert measured.method == "WF" and measured.metrics.new_sheets_used == 3
    assert measured.metrics.material_area_mm2 == 57 and measured.metrics.placed_piece_area_mm2 == 16
    assert len(residuals) == 4
    assert database_snapshot(factory) == before
    with factory() as session:
        assert all(session.get(Pedido, i).estado == "PENDIENTE" for i in ids)


def test_existing_first_fit_slice_still_passes_without_migrations(sqlite_slice):
    # Reuse the unchanged real-repository regression with a migration-free fixture.
    existing_first_fit_slice(sqlite_slice, lambda username: 1)
