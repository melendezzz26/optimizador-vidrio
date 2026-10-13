from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace

from app.modules.inventory.application.stock_compatibility import StockCompatibilityService


class FakeInventoryRepository:
    def __init__(self, stock_by_material):
        self.stock_by_material = stock_by_material
        self.lookups = []

    def read_transaction(self):
        return nullcontext()

    def get_compatible_stock(self, material_id, thickness):
        key = (material_id, thickness)
        self.lookups.append(key)
        return self.stock_by_material.get(key, ([], []))


def plancha(width, height, *, quantity=1):
    return SimpleNamespace(
        ancho_mm=Decimal(str(width)), alto_mm=Decimal(str(height)), cantidad=quantity,
    )


def retazo(geometry):
    return SimpleNamespace(geometria=geometry)


def rectangle(width, height, *, material=7, thickness=Decimal("5.5"), quantity=1):
    return {
        "id_tipo_vidrio": material,
        "espesor_mm": thickness,
        "tipo_forma": "RECTANGULO",
        "cantidad": quantity,
        "dimensiones": {"width_mm": width, "height_mm": height},
    }


def test_plancha_exact_fit_and_quantity_do_not_mean_joint_reservation():
    repository = FakeInventoryRepository({
        (7, Decimal("5.5")): ([plancha(100, 50, quantity=1)], []),
    })
    service = StockCompatibilityService(repository)

    assert service.find_missing_candidate_indexes([rectangle(100, 50, quantity=20)]) == []


def test_plancha_rotation_and_too_large_piece():
    repository = FakeInventoryRepository({
        (7, Decimal("5.5")): ([plancha(100, 60)], []),
    })
    service = StockCompatibilityService(repository)
    pieces = [rectangle(60, 100), rectangle(101, 61)]

    assert service.find_missing_candidate_indexes(pieces) == [1]


def test_each_material_pair_is_queried_once_and_incompatible_pairs_have_no_candidate():
    repository = FakeInventoryRepository({
        (7, Decimal("5.5")): ([plancha(500, 500)], []),
    })
    service = StockCompatibilityService(repository)

    missing = service.find_missing_candidate_indexes([
        rectangle(10, 10),
        rectangle(20, 20),
        rectangle(10, 10, material=8),
        rectangle(10, 10, thickness=Decimal("6")),
    ])

    assert missing == [2, 3]
    assert repository.lookups == [(7, Decimal("5.5")), (8, Decimal("5.5")), (7, Decimal("6"))]


def test_retazo_rectangle_is_an_individual_candidate():
    repository = FakeInventoryRepository({
        (7, Decimal("5.5")): ([], [retazo({"type": "RECTANGULO", "width_mm": 100, "height_mm": 50})]),
    })

    assert StockCompatibilityService(repository).find_missing_candidate_indexes([rectangle(100, 50)]) == []


def test_retazo_circle_and_convex_polygon_use_their_bounding_boxes():
    circle = {
        "id_tipo_vidrio": 7, "espesor_mm": Decimal("5.5"), "tipo_forma": "CIRCUNFERENCIA",
        "cantidad": 1, "dimensiones": {"radius_mm": 20},
    }
    polygon = {
        "id_tipo_vidrio": 7, "espesor_mm": Decimal("5.5"), "tipo_forma": "POLIGONO_CONVEXO",
        "cantidad": 1, "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [30, 0], [30, 50], [0, 50]]},
    }
    repository = FakeInventoryRepository({
        (7, Decimal("5.5")): ([], [
            retazo({"type": "RECTANGULO", "width_mm": 40, "height_mm": 40}),
            retazo({"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [50, 0], [50, 30], [0, 30]]}),
        ]),
    })

    assert StockCompatibilityService(repository).find_missing_candidate_indexes([circle, polygon]) == []


def test_retazo_that_is_too_small_is_not_a_candidate():
    repository = FakeInventoryRepository({
        (7, Decimal("5.5")): ([], [retazo({"type": "CIRCUNFERENCIA", "radius_mm": 10})]),
    })

    assert StockCompatibilityService(repository).find_missing_candidate_indexes([rectangle(25, 25)]) == [0]
