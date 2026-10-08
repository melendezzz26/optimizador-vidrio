from copy import deepcopy

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Pedido, Pieza
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository


PIECE = {"tipo_forma": "POLIGONO_CONVEXO", "cantidad": 2, "dimensiones": None,
         "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [10, 0], [0, 10]]},
         "area_mm2": 50.0}


@pytest.fixture
def setup_data(create_user):
    return create_user("O70000001")


def test_validate_catalog(db_session):
    repo = SQLAlchemyOrderRepository(db_session)
    assert repo.validate_catalog(7, 5.5)
    assert not repo.validate_catalog(7, 99)
    assert not repo.validate_catalog(99, 6)


def test_create_order_success(db_session, session_factory, setup_data):
    repo = SQLAlchemyOrderRepository(db_session)
    identifier = repo.create_order(setup_data, 7, 6, [PIECE, PIECE])
    with session_factory() as reader:
        assert reader.get(Pedido, identifier).estado == "PENDIENTE"
        pieces = reader.scalars(select(Pieza).where(Pieza.id_pedido == identifier)).all()
        assert len(pieces) == 2
        assert all(p.cantidad == 2 and p.area_mm2 == 50 and p.dimensiones is None for p in pieces)
        assert reader.scalar(text("SELECT bool_and(dimensiones IS NULL) FROM piezas")) is True


@pytest.mark.parametrize("failure", ["header", "second_piece", "missing_field"])
def test_create_order_rolls_back_every_row(db_session, session_factory, setup_data, failure):
    repo = SQLAlchemyOrderRepository(db_session)
    second = deepcopy(PIECE)
    if failure == "second_piece":
        second["cantidad"] = 0  # Actual PostgreSQL CHECK violation after header flush.
    if failure == "missing_field":
        second.pop("area_mm2")
    with pytest.raises((IntegrityError, KeyError)):
        repo.create_order(-1 if failure == "header" else setup_data, 7, 6, [PIECE, second])
    with session_factory() as reader:
        assert reader.scalar(select(func.count()).select_from(Pedido)) == 0
        assert reader.scalar(select(func.count()).select_from(Pieza)) == 0
    # The session remains usable after rollback.
    assert repo.validate_catalog(7, 6)
