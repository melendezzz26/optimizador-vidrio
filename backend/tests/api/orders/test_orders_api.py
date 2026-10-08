from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from sqlalchemy import func, select, update

from app.models import Pedido, Pieza, TipoVidrio, Usuario
from app.shared.security.tokens import ALGORITHM, SECRET_KEY


PAYLOAD = {"id_tipo_vidrio": 7, "espesor_mm": 5.5, "piezas": [
    {"tipo_forma": "POLIGONO_CONVEXO", "cantidad": 1,
     "vertices_mm": [[0, 0], [500, 0], [500, 300], [0, 300]]},
    {"tipo_forma": "RECTANGULO", "cantidad": 2, "width_mm": 100, "height_mm": 200},
    {"tipo_forma": "CIRCUNFERENCIA", "cantidad": 1, "radius_mm": 10},
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
        assert float(order.espesor_mm) == 5.5
        pieces = db.scalars(select(Pieza).where(Pieza.id_pedido == order.id_pedido).order_by(Pieza.id_pieza)).all()
        assert len(pieces) == 3
        assert pieces[0].dimensiones is None
        assert pieces[0].geometria == {"type": "POLIGONO_CONVEXO", "vertices_mm": PAYLOAD["piezas"][0]["vertices_mm"]}
        assert float(pieces[0].area_mm2) == 150000
        assert float(pieces[1].area_mm2) == 20000
        assert float(pieces[2].area_mm2) == 314.16


@pytest.mark.parametrize("token", [None, "invalid.jwt.token"])
def test_create_order_401(client, token):
    response = client.post("/api/orders", json=PAYLOAD, headers={"Authorization": f"Bearer {token}"} if token else {})
    assert response.status_code == 401


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
    assert client.post("/api/orders", json=PAYLOAD, headers=headers).status_code == expected


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


@pytest.mark.parametrize("change", [
    {"cantidad": 0}, {"cantidad": 1.5}, {"cantidad": True}, {"cantidad": 2147483648},
    {"vertices_mm": [[0, 0], [10, 10], [10, 0], [0, 10]]},
    {"vertices_mm": [[0, 0], [10, 0], [5, 5], [10, 10], [0, 10]]},
    {"vertices_mm": [[0, 0], [10, 0], [20, 0]]},
    {"vertices_mm": [[0, 0], [10, 0], [10, 0], [0, 10]]},
    {"vertices_mm": [[0, 0], [10, 0], ["NaN", 10]]},
    {"vertices_mm": [[0, 0], [10, 0], [True, 10]]},
    {"vertices_mm": [[0, 0], [1e200, 0], [0, 1e200]]},
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
    payload = ('{"id_tipo_vidrio":7,"espesor_mm":5.5,"piezas":['
               '{"tipo_forma":"POLIGONO_CONVEXO","cantidad":1,'
               '"vertices_mm":[[0,0],[10,0],[' + coordinate + ',10]]}]}')
    response = client.post("/api/orders", content=payload,
                           headers=authenticated[1] | {"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "finite_number"
