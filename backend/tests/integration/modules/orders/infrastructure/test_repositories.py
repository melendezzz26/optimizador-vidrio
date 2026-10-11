from copy import deepcopy
from unittest.mock import patch

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Pedido, Pieza
from app.modules.orders.application.ports import OrderMutationResult
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository


PIECE = {"id_tipo_vidrio": 7, "espesor_mm": 6, "tipo_forma": "POLIGONO_CONVEXO", "cantidad": 2, "dimensiones": None,
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
    identifier = repo.create_order(setup_data, [PIECE, PIECE])
    with session_factory() as reader:
        assert reader.get(Pedido, identifier).estado == "PENDIENTE"
        pieces = reader.scalars(select(Pieza).where(Pieza.id_pedido == identifier)).all()
        assert len(pieces) == 2
        assert all(p.id_tipo_vidrio == 7 and p.espesor_mm == 6 and p.cantidad == 2 and p.area_mm2 == 50 and p.dimensiones is None for p in pieces)
        assert reader.scalar(text("SELECT bool_and(dimensiones IS NULL) FROM piezas")) is True


@pytest.mark.parametrize("failure", ["header", "second_piece", "missing_field", "invalid_pair"])
def test_create_order_rolls_back_every_row(db_session, session_factory, setup_data, failure):
    repo = SQLAlchemyOrderRepository(db_session)
    second = deepcopy(PIECE)
    if failure == "second_piece":
        second["cantidad"] = 0  # Actual PostgreSQL CHECK violation after header flush.
    if failure == "invalid_pair":
        second["espesor_mm"] = 99
    if failure == "missing_field":
        second.pop("area_mm2")
    with pytest.raises((IntegrityError, KeyError)):
        repo.create_order(-1 if failure == "header" else setup_data, [PIECE, second])
    with session_factory() as reader:
        assert reader.scalar(select(func.count()).select_from(Pedido)) == 0
        assert reader.scalar(select(func.count()).select_from(Pieza)) == 0
    # The session remains usable after rollback.
    assert repo.validate_catalog(7, 6)


def create_pending_order(session, setup_data):
    return SQLAlchemyOrderRepository(session).create_order(setup_data, [PIECE])


def test_update_order_locks_pending_header_and_replaces_pieces(db_session, session_factory, setup_data):
    identifier = create_pending_order(db_session, setup_data)
    replacement = deepcopy(PIECE) | {"cantidad": 4}

    result = SQLAlchemyOrderRepository(db_session).update_order(identifier, [replacement, replacement])

    assert result is OrderMutationResult.UPDATED
    with session_factory() as reader:
        assert reader.get(Pedido, identifier).estado == "PENDIENTE"
        pieces = reader.scalars(select(Pieza).where(Pieza.id_pedido == identifier)).all()
        assert len(pieces) == 2
        assert all(piece.cantidad == 4 and piece.id_tipo_vidrio == 7 and piece.espesor_mm == 6 for piece in pieces)


def test_update_order_returns_not_found(db_session):
    result = SQLAlchemyOrderRepository(db_session).update_order(999999, [PIECE])
    assert result is OrderMutationResult.NOT_FOUND


def test_update_order_rechecks_state_under_row_lock(db_session, setup_data):
    identifier = create_pending_order(db_session, setup_data)
    db_session.execute(
        text("UPDATE pedidos SET estado = 'OPTIMIZADO' WHERE id_pedido = :id"),
        {"id": identifier},
    )
    db_session.commit()

    result = SQLAlchemyOrderRepository(db_session).update_order(identifier, [PIECE | {"cantidad": 9}])

    assert result is OrderMutationResult.STATE_CONFLICT
    order = db_session.get(Pedido, identifier)
    pieces = db_session.scalars(select(Pieza).where(Pieza.id_pedido == identifier)).all()
    assert order.estado == "OPTIMIZADO"
    assert len(pieces) == 1 and pieces[0].cantidad == 2


def test_update_order_failure_after_delete_rolls_back_replacement(db_session, session_factory, setup_data):
    identifier = create_pending_order(db_session, setup_data)
    repo = SQLAlchemyOrderRepository(db_session)

    with patch.object(db_session, "add", side_effect=RuntimeError("insert failed")):
        with pytest.raises(RuntimeError, match="insert failed"):
            repo.update_order(identifier, [PIECE | {"cantidad": 5}])

    with session_factory() as reader:
        order = reader.get(Pedido, identifier)
        pieces = reader.scalars(select(Pieza).where(Pieza.id_pedido == identifier)).all()
        assert order.estado == "PENDIENTE"
        assert len(pieces) == 1 and pieces[0].cantidad == 2


def test_cancel_order_is_logical_and_keeps_pieces(db_session, session_factory, setup_data):
    identifier = create_pending_order(db_session, setup_data)

    result = SQLAlchemyOrderRepository(db_session).cancel_order(identifier)

    assert result is OrderMutationResult.UPDATED
    with session_factory() as reader:
        assert reader.get(Pedido, identifier).estado == "CANCELADO"
        assert reader.scalar(select(func.count()).select_from(Pedido).where(Pedido.id_pedido == identifier)) == 1
        assert reader.scalar(select(func.count()).select_from(Pieza).where(Pieza.id_pedido == identifier)) == 1


def test_cancel_order_returns_not_found(db_session):
    assert SQLAlchemyOrderRepository(db_session).cancel_order(999999) is OrderMutationResult.NOT_FOUND


def test_cancel_order_rechecks_state_under_row_lock(db_session, setup_data):
    identifier = create_pending_order(db_session, setup_data)
    db_session.execute(
        text("UPDATE pedidos SET estado = 'OPTIMIZADO' WHERE id_pedido = :id"),
        {"id": identifier},
    )
    db_session.commit()

    result = SQLAlchemyOrderRepository(db_session).cancel_order(identifier)

    assert result is OrderMutationResult.STATE_CONFLICT
    assert db_session.get(Pedido, identifier).estado == "OPTIMIZADO"


def test_cancel_order_commit_failure_rolls_back(db_session, session_factory, setup_data):
    identifier = create_pending_order(db_session, setup_data)
    repo = SQLAlchemyOrderRepository(db_session)

    with patch.object(db_session, "commit", side_effect=RuntimeError("commit failed")):
        with pytest.raises(RuntimeError, match="commit failed"):
            repo.cancel_order(identifier)

    with session_factory() as reader:
        assert reader.get(Pedido, identifier).estado == "PENDIENTE"
        assert reader.scalar(select(func.count()).select_from(Pieza).where(Pieza.id_pedido == identifier)) == 1
