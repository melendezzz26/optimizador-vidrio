"""HU-018 CA-09: un pedido creado con piezas importadas se procesa con FF, BF y WF.

Recorre el camino real: archivo CSV -> lectura -> vista previa -> registro del pedido
con el mismo caso de uso que POST /api/orders -> snapshots -> los tres métodos.
No mide capacidad ni tiempos (eso es TA-044): solo que las piezas importadas sirven.
"""
from datetime import datetime, timezone

from app.models import Pedido, Plancha
from app.modules.clients.infrastructure.sqlalchemy_client_repository import SqlAlchemyClientRepository
from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
from app.modules.optimization.application.best_fit import calculate_best_fit
from app.modules.optimization.application.first_fit import calculate_first_fit
from app.modules.optimization.application.preparation import prepare_persisted_problem
from app.modules.optimization.application.stock import with_compatible_stock
from app.modules.optimization.domain.problem import OptimizationConfig
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
from app.modules.orders.application.bulk_import import PreviewImportUseCase
from app.modules.orders.application.use_cases import CreateOrderUseCase
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.orders.infrastructure.spreadsheet_reader import read_rows
from tests.integration.optimization.test_worst_fit_slice import database_snapshot, sqlite_slice  # noqa: F401

CSV = ("tipo,cantidad,medidas\n"
       "R,2,300,200\n"
       "C,1,100\n"
       "P,1,{{300,},{400,},{500,}}\n"
       "P,1,{{120,60},{160,120},{120,60},{160,120}}\n").encode("utf-8")


def imported_pieces():
    preview = PreviewImportUseCase().execute("piezas.csv", read_rows("piezas.csv", CSV))
    assert preview["resumen"] == {"total": 4, "validas": 4, "observadas": 0}
    # Igual que el formulario: material elegido en pantalla + medidas de la vista previa.
    return [{"tipo_forma": row["tipo_forma"], "cantidad": row["cantidad"], "id_tipo_vidrio": 7, "espesor_mm": 6,
             **row["medidas"]} for row in preview["filas"]]


def test_imported_order_is_processed_by_first_best_and_worst_fit(sqlite_slice):
    factory = sqlite_slice
    with factory() as session:
        repository = SQLAlchemyOrderRepository(session)
        order_id = CreateOrderUseCase(repository, SqlAlchemyClientRepository(session)).execute(
            1, imported_pieces(), id_cliente=41)
        session.add(Plancha(id_plancha=5, id_tipo_vidrio=7, ancho_mm=1000, alto_mm=1000, espesor_mm=6,
                            cantidad=2, estado=True, fecha_registro=datetime.now(timezone.utc)))
        session.commit()
        snapshots = repository.get_order(order_id)["piezas"]
    assert [(p["tipo_forma"], p["cantidad"]) for p in snapshots] == [
        ("RECTANGULO", 2), ("CIRCUNFERENCIA", 1), ("POLIGONO_CONVEXO", 1), ("POLIGONO_CONVEXO", 1)]

    before = database_snapshot(factory)
    cfg = OptimizationConfig(resolution_mm=1, margin_mm=0, separation_mm=0, angular_step_deg=90)
    provider = InventoryStockAdapter(SqlAlchemyInventoryRepository(factory))
    problem = with_compatible_stock(prepare_persisted_problem([order_id], snapshots, cfg), provider)
    results = {
        "FF": lambda: calculate_first_fit([order_id], snapshots, cfg, provider),
        "BF": lambda: calculate_best_fit([order_id], snapshots, cfg, provider),
        "WF": lambda: WorstFitOptimizer().optimize(problem),
    }
    for method, run in results.items():
        result = run()
        assert result.method == method
        assert result.complete and result.placed_units == result.total_units == 5, method
        assert {p.piece.order_id for p in result.placements} == {order_id}
        assert result == run(), f"{method} debe ser determinístico"
    assert database_snapshot(factory) == before
    with factory() as session:
        assert session.get(Pedido, order_id).estado == "PENDIENTE"