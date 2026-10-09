from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import jwt
import pytest
from sqlalchemy import func, select, update

from app.models import Pedido, Pieza, TipoVidrio, Usuario
from app.shared.security.tokens import ALGORITHM, SECRET_KEY


PAYLOAD = {"piezas": [
    {"id_tipo_vidrio": 7, "espesor_mm": 5.5, "tipo_forma": "POLIGONO_CONVEXO", "cantidad": 3,
     "vertices_mm": [[0, 0], [500, 0], [500, 300], [0, 300]]},
    {"id_tipo_vidrio": 8, "espesor_mm": 4, "tipo_forma": "RECTANGULO", "cantidad": 2, "width_mm": 100, "height_mm": 200},
    {"id_tipo_vidrio": 9, "espesor_mm": 6, "tipo_forma": "CIRCUNFERENCIA", "cantidad": 1, "radius_mm": 10},
]}


@pytest.fixture
def authenticated(client, create_user, password):
    identifier = create_user("O70000001")
    response = client.post("/api/auth/login", json={"username": "O70000001", "password": password})
    assert response.status_code == 200
    return identifier, {"Authorization": "Bearer " + response.json()["access_token"]}


def test_create_order_201_persists_all_pieces(client, authenticated, session_factory):
    identifier, headers = authenticated
    response = client.post("/api/orders", json=PAYLOAD, headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["estado"] == "PENDIENTE"
    with session_factory() as db:
        order = db.get(Pedido, response.json()["id_pedido"])
        assert order.id_usuario_registro == identifier
        pieces = db.scalars(select(Pieza).where(Pieza.id_pedido == order.id_pedido).order_by(Pieza.id_pieza)).all()
        assert len(pieces) == 3
        assert [(p.id_tipo_vidrio, p.espesor_mm, p.cantidad) for p in pieces] == [(7, Decimal("5.5"), 3), (8, Decimal("4"), 2), (9, Decimal("6"), 1)]
        assert pieces[0].dimensiones is None
        assert pieces[0].geometria == {"type": "POLIGONO_CONVEXO", "vertices_mm": PAYLOAD["piezas"][0]["vertices_mm"]}
        assert float(pieces[0].area_mm2) == 150000
        assert float(pieces[1].area_mm2) == 20000
        assert float(pieces[2].area_mm2) == 314.16
        expected = [{"id_pieza": p.id_pieza, "id_pedido": p.id_pedido,
                     "id_tipo_vidrio": p.id_tipo_vidrio, "espesor_mm": str(p.espesor_mm),
                     "tipo_forma": p.tipo_forma, "cantidad": p.cantidad,
                     "dimensiones": p.dimensiones, "geometria": p.geometria, "area_mm2": str(p.area_mm2)}
                    for p in pieces]
    recovered = client.get(f"/api/orders/{response.json()['id_pedido']}", headers=headers)
    assert recovered.status_code == 200, recovered.text
    result = recovered.json()
    assert result["piezas"] == expected
    assert result["id_usuario_registro"] == identifier
    assert result["estado"] == "PENDIENTE"
    assert datetime.fromisoformat(result["fecha_registro"].replace("Z", "+00:00")).tzinfo is not None
    assert "id_tipo_vidrio" not in result and "espesor_mm" not in result
    # La lectura histórica sigue disponible aunque el catálogo se desactive.
    with session_factory() as db:
        db.execute(update(TipoVidrio).where(TipoVidrio.id_tipo_vidrio == 7).values(estado=False))
        db.commit()
    assert client.get(f"/api/orders/{result['id_pedido']}", headers=headers).json()["piezas"] == expected


@pytest.mark.parametrize("token", [None, "invalid.jwt.token"])
def test_create_order_401(client, token):
    response = client.post("/api/orders", json=PAYLOAD, headers={"Authorization": f"Bearer {token}"} if token else {})
    assert response.status_code == 401
    assert client.get("/api/orders/1", headers={"Authorization": f"Bearer {token}"} if token else {}).status_code == 401


def test_expired_token(client, authenticated):
    identifier, _ = authenticated
    token = jwt.encode({"sub": str(identifier), "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}, SECRET_KEY, algorithm=ALGORITHM)
    assert client.post("/api/orders", json=PAYLOAD, headers={"Authorization": f"Bearer {token}"}).status_code == 401


@pytest.mark.parametrize("role, expected", [("Almacenero", 403), ("Administrador", 201)])
def test_current_database_role_controls_permission(client, authenticated, session_factory, role, expected):
    identifier, headers = authenticated
    with session_factory() as db:
        db.execute(update(Usuario).where(Usuario.id_usuario == identifier).values(id_rol=2 if role == "Almacenero" else 1))
        db.commit()
    result = client.post("/api/orders", json=PAYLOAD, headers=headers)
    assert result.status_code == expected
    order_id = result.json()["id_pedido"] if expected == 201 else 1
    assert client.get(f"/api/orders/{order_id}", headers=headers).status_code == (200 if expected == 201 else 403)


def test_inactive_user(client, authenticated, session_factory):
    identifier, headers = authenticated
    with session_factory() as db:
        db.execute(update(Usuario).where(Usuario.id_usuario == identifier).values(estado=False))
        db.commit()
    assert client.post("/api/orders", json=PAYLOAD, headers=headers).status_code == 401


@pytest.mark.parametrize("change", [
    {"piezas": []}, {"id_tipo_vidrio": 999}, {"espesor_mm": 99},
    {"id_usuario_registro": 999}, {"espesor_mm": True}, {"id_tipo_vidrio": "7"},
])
def test_invalid_order_422_no_writes(client, authenticated, session_factory, change):
    response = client.post("/api/orders", json=PAYLOAD | change, headers=authenticated[1])
    assert response.status_code == 422, response.text
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Pedido)) == 0
        assert db.scalar(select(func.count()).select_from(Pieza)) == 0


@pytest.mark.parametrize("change", [
    {"cantidad": 0}, {"cantidad": -1}, {"cantidad": 1.5}, {"cantidad": True}, {"cantidad": 2147483648},
    {"vertices_mm": [[0, 0], [10, 10], [10, 0], [0, 10]]},
    {"vertices_mm": [[0, 0], [10, 0], [5, 5], [10, 10], [0, 10]]},
    {"vertices_mm": [[0, 0], [10, 0], [20, 0]]},
    {"vertices_mm": [[0, 0], [10, 0], [10, 0], [0, 10]]},
    {"vertices_mm": [[0, 0], [10, 0], ["NaN", 10]]},
    {"vertices_mm": [[0, 0], [10, 0], [True, 10]]},
    {"vertices_mm": [[0, 0], [1e200, 0], [0, 1e200]]},
    {"id_tipo_vidrio": 999}, {"espesor_mm": 99}, {"espesor_mm": True}, {"espesor_mm": "5.5"},
    {"id_tipo_vidrio": True}, {"id_tipo_vidrio": "7"}, {"tipo_forma": "TRIANGULO"},
    {"area_mm2": 1}, {"dimensiones": None}, {"geometria": {}}, {"tipo_forma": "OTHER"},
])
def test_invalid_piece_422(client, authenticated, session_factory, change):
    payload = deepcopy(PAYLOAD)
    payload["piezas"][0].update(change)
    response = client.post("/api/orders", json=payload, headers=authenticated[1])
    assert response.status_code == 422, response.text
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Pedido)) == 0


def test_inactive_material(client, authenticated, session_factory):
    with session_factory() as db:
        db.execute(update(TipoVidrio).where(TipoVidrio.id_tipo_vidrio == 7).values(estado=False))
        db.commit()
    assert client.post("/api/orders", json=PAYLOAD, headers=authenticated[1]).status_code == 422


def test_commit_failure_is_safe_and_rolls_back(client, authenticated, session_factory):
    with patch("sqlalchemy.orm.Session.commit", side_effect=RuntimeError("private database error")):
        response = client.post("/api/orders", json=PAYLOAD, headers=authenticated[1])
    assert response.status_code == 500
    assert "private" not in response.text
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Pedido)) == 0
        assert db.scalar(select(func.count()).select_from(Pieza)) == 0


@pytest.mark.parametrize("coordinate", ["1e400", "NaN", "Infinity"])
def test_non_finite_json_coordinate_returns_serializable_422(client, authenticated, coordinate):
    payload = ('{"piezas":['
               '{"id_tipo_vidrio":7,"espesor_mm":5.5,"tipo_forma":"POLIGONO_CONVEXO","cantidad":1,'
               '"vertices_mm":[[0,0],[10,0],[' + coordinate + ',10]]}]}')
    response = client.post("/api/orders", content=payload,
                           headers=authenticated[1] | {"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "finite_number"


@pytest.mark.parametrize("index, field", [(0, "id_tipo_vidrio"), (1, "espesor_mm"), (0, "vertices_mm"),
                                         (1, "width_mm"), (2, "radius_mm"), (2, "cantidad")])
def test_missing_piece_field_returns_422_without_writes(client, authenticated, session_factory, index, field):
    payload = deepcopy(PAYLOAD)
    del payload["piezas"][index][field]
    result = client.post("/api/orders", json=payload, headers=authenticated[1])
    assert result.status_code == 422
    assert any(error["loc"][-1] == field for error in result.json()["detail"])
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Pedido)) == 0
        assert db.scalar(select(func.count()).select_from(Pieza)) == 0


def test_valid_pieces_before_invalid_last_piece_do_not_persist(client, authenticated, session_factory):
    payload = deepcopy(PAYLOAD)
    payload["piezas"][-1]["radius_mm"] = -10
    assert client.post("/api/orders", json=payload, headers=authenticated[1]).status_code == 422
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Pedido)) == 0
        assert db.scalar(select(func.count()).select_from(Pieza)) == 0


def test_get_not_found(client, authenticated):
    result = client.get("/api/orders/999", headers=authenticated[1])
    assert result.status_code == 404
    assert result.json()["detail"] == "Pedido no encontrado."


@pytest.mark.parametrize("identifier", ["0", "-1", "2147483648", "abc"])
def test_get_invalid_identifier(client, authenticated, identifier):
    assert client.get(f"/api/orders/{identifier}", headers=authenticated[1]).status_code == 422


def test_get_database_failure_is_safe(client, authenticated):
    with patch("app.modules.orders.infrastructure.repositories.SQLAlchemyOrderRepository.get_order",
               side_effect=RuntimeError("private database error")):
        result = client.get("/api/orders/1", headers=authenticated[1])
    assert result.status_code == 500
    assert "private" not in result.text
