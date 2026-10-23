from unittest.mock import patch

import pytest
from sqlalchemy import delete, func, select, update

from app.models import (Pedido, Pieza, Usuario, Optimizacion, EjecucionOptimizacion,
                        MovimientoInventario, Plancha, Retazo, MetricaEjecucion)
from app.modules.optimization.application.resource_policy import MAX_RASTER_PAYLOAD_BYTES

PREFIX = "/api/optimization"


def start(client, headers, order_id):
    return client.post(PREFIX + "/start", json={"id_pedido": order_id}, headers=headers)


def raster(client, headers, order_id, piece_id, resolution=5):
    return client.post(PREFIX + "/rasterize", json={"id_pedido": order_id, "id_pieza": piece_id,
                                                  "resolution_mm": resolution}, headers=headers)


def excluded_counts(factory):
    with factory() as db:
        return tuple(db.scalar(select(func.count()).select_from(model)) for model in (
            Optimizacion, EjecucionOptimizacion, MovimientoInventario, Plancha, Retazo, MetricaEjecucion))


def test_start_then_three_shapes_contract_quantity_and_no_excluded_writes(client, authenticated, order, session_factory):
    headers, order_id = authenticated[1], order["id_pedido"]
    before = excluded_counts(session_factory)
    assert client.get(f"/api/orders/{order_id}", headers=headers).json()["estado"] == "PENDIENTE"
    response = start(client, headers, order_id)
    assert response.status_code == 200, response.text
    assert response.json() == {"id_pedido": order_id, "estado": "PENDIENTE"}
    repeated = start(client, headers, order_id)
    assert repeated.status_code == 200
    assert repeated.json() == response.json()
    for piece in order["piezas"]:
        response = raster(client, headers, order_id, piece["id_pieza"])
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["geometria"] == piece["geometria"]
        assert data["cantidad"] == piece["cantidad"]
        assert data["espesor_mm"] == piece["espesor_mm"]
        assert len(data["spans_by_row"]) == data["row_count"]
        assert [row["row"] for row in data["spans_by_row"]] == list(range(data["row_count"]))
        assert sum(end - begin for row in data["spans_by_row"] for begin, end in row["runs"]) == data["occupied_cells"]
        assert all(0 <= a < b <= data["columns"] for row in data["spans_by_row"] for a, b in row["runs"])
        assert len(response.content) <= MAX_RASTER_PAYLOAD_BYTES
        if piece["tipo_forma"] == "RECTANGULO":
            assert (data["row_count"], data["columns"], data["occupied_cells"]) == (120, 160, 19200)
    assert excluded_counts(session_factory) == before
    current = client.get(f"/api/orders/{order_id}", headers=headers).json()
    assert current["estado"] == "PENDIENTE" and current["piezas"] == order["piezas"]


@pytest.mark.parametrize("path,body", [("/start", {"id_pedido": 10}),
                                      ("/rasterize", {"id_pedido": 10, "id_pieza": 25, "resolution_mm": 5})])
def test_both_operations_require_authentication(client, path, body):
    assert client.post(PREFIX + path, json=body).status_code == 401


@pytest.mark.parametrize("state", ["PENDIENTE", "EN_OPTIMIZACION"])
def test_raster_without_start_preserves_order_and_all_effects(client, authenticated, order, session_factory, state):
    with session_factory() as db:
        db.get(Pedido, order["id_pedido"]).estado = state
        db.commit()
    before = excluded_counts(session_factory)
    response = raster(client, authenticated[1], order["id_pedido"], order["piezas"][0]["id_pieza"])
    assert response.status_code == 200, response.text
    assert excluded_counts(session_factory) == before
    with session_factory() as db:
        assert db.get(Pedido, order["id_pedido"]).estado == state


def test_preview_leaves_pending_order_editable_and_raster_reloads_pieces(client, authenticated, order):
    headers, identifier = authenticated[1], order["id_pedido"]
    old_piece = order["piezas"][0]["id_pieza"]
    assert start(client, headers, identifier).status_code == 200
    assert raster(client, headers, identifier, old_piece).status_code == 200
    edited = client.put(f"/api/orders/{identifier}", headers=headers, json={"piezas": [
        dict(tipo_forma="RECTANGULO", id_tipo_vidrio=7, espesor_mm=6, cantidad=2, width_mm=20, height_mm=10)
    ]})
    assert edited.status_code == 200, edited.text
    current = client.get(f"/api/orders/{identifier}", headers=headers).json()
    assert current["estado"] == "PENDIENTE"
    assert raster(client, headers, identifier, old_piece).status_code == 404
    fresh = raster(client, headers, identifier, current["piezas"][0]["id_pieza"])
    assert fresh.status_code == 200
    assert fresh.json()["geometria"] == {"type": "RECTANGULO", "width_mm": 20, "height_mm": 10}


@pytest.mark.parametrize("role,status", [(2, 403), (1, 200), (3, 200)])
def test_roles_use_current_database_role(client, authenticated, order, session_factory, role, status):
    with session_factory() as db:
        db.execute(update(Usuario).where(Usuario.id_usuario == authenticated[0]).values(id_rol=role))
        db.commit()
    assert start(client, authenticated[1], order["id_pedido"]).status_code == status
    response = raster(client, authenticated[1], order["id_pedido"], order["piezas"][0]["id_pieza"])
    assert response.status_code == status


def test_missing_order_and_piece_and_foreign_piece(client, authenticated, order):
    headers, order_id = authenticated[1], order["id_pedido"]
    assert start(client, headers, 2147483647).status_code == 404
    assert raster(client, headers, 2147483647, 1).status_code == 404
    assert start(client, headers, order_id).status_code == 200
    assert raster(client, headers, order_id, 2147483647).status_code == 404
    other = client.post("/api/orders", json={"id_cliente": 41, "piezas": [
        dict(tipo_forma="RECTANGULO", id_tipo_vidrio=7, espesor_mm=6, cantidad=1, width_mm=10, height_mm=10)
    ]}, headers=headers).json()["id_pedido"]
    other_piece = client.get(f"/api/orders/{other}", headers=headers).json()["piezas"][0]
    response = raster(client, headers, order_id, other_piece["id_pieza"])
    assert response.status_code == 404
    assert "geometria" not in response.json()


@pytest.mark.parametrize("state", ["EN_OPTIMIZACION", "OPTIMIZADO", "CONFIRMADO", "CANCELADO"])
def test_start_wrong_state_conflict(client, authenticated, order, session_factory, state):
    with session_factory() as db:
        db.execute(update(Pedido).where(Pedido.id_pedido == order["id_pedido"]).values(estado=state))
        db.commit()
    assert start(client, authenticated[1], order["id_pedido"]).status_code == 409
    assert client.get(f"/api/orders/{order['id_pedido']}", headers=authenticated[1]).json()["estado"] == state


@pytest.mark.parametrize("state", ["OPTIMIZADO", "CONFIRMADO", "CANCELADO"])
def test_raster_wrong_state_does_not_transition(client, authenticated, order, session_factory, state):
    with session_factory() as db:
        db.execute(update(Pedido).where(Pedido.id_pedido == order["id_pedido"]).values(estado=state))
        db.commit()
    assert raster(client, authenticated[1], order["id_pedido"], order["piezas"][0]["id_pieza"]).status_code == 409
    assert client.get(f"/api/orders/{order['id_pedido']}", headers=authenticated[1]).json()["estado"] == state


@pytest.mark.parametrize("change", ["empty", "corrupt", "large"])
def test_invalid_start_does_not_mutate(client, authenticated, order, session_factory, change):
    with session_factory() as db:
        if change == "empty":
            db.execute(delete(Pieza).where(Pieza.id_pedido == order["id_pedido"]))
        else:
            geometry = ({"type": "OTHER"} if change == "corrupt" else
                        dict(type="RECTANGULO", width_mm=10000, height_mm=10000))
            db.execute(update(Pieza).where(Pieza.id_pieza == order["piezas"][0]["id_pieza"]).values(geometria=geometry))
        db.commit()
    response = start(client, authenticated[1], order["id_pedido"])
    assert response.status_code == 422, response.text
    assert client.get(f"/api/orders/{order['id_pedido']}", headers=authenticated[1]).json()["estado"] == "PENDIENTE"


@pytest.mark.parametrize("resolution", [0, -1, True, "5", None])
def test_invalid_resolution_schema(client, authenticated, resolution):
    assert raster(client, authenticated[1], 10, 25, resolution).status_code == 422


@pytest.mark.parametrize("value", ["1e400", "NaN", "Infinity"])
def test_nonfinite_json_is_safe_422(client, authenticated, value):
    response = client.post(PREFIX + "/rasterize", content='{"id_pedido":10,"id_pieza":25,"resolution_mm":' + value + '}',
                           headers=authenticated[1] | {"Content-Type": "application/json"})
    assert response.status_code == 422, response.text
    assert "input" not in response.json()["detail"][0]


@pytest.mark.parametrize("body", [{"id_pedido": True}, {"id_pedido": "10"}, {"id_pedido": 0},
                                   {"id_pedido": 2147483648}, {"id_pedido": 10, "estado": "PENDIENTE"}])
def test_start_strict_schema(client, authenticated, body):
    assert client.post(PREFIX + "/start", json=body, headers=authenticated[1]).status_code == 422


def test_raster_rejects_geometry_in_request(client, authenticated):
    body = dict(id_pedido=10, id_pieza=25, resolution_mm=5, geometria={})
    assert client.post(PREFIX + "/rasterize", json=body, headers=authenticated[1]).status_code == 422


def test_limit_prevents_raster_call_and_leaves_pending_state(client, authenticated, order):
    headers, order_id = authenticated[1], order["id_pedido"]
    assert start(client, headers, order_id).status_code == 200
    with patch("app.modules.optimization.application.use_cases.rasterize_geometry") as domain:
        response = raster(client, headers, order_id, order["piezas"][0]["id_pieza"], 0.01)
    assert response.status_code == 422 and isinstance(response.json()["detail"], str)
    domain.assert_not_called()
    assert client.get(f"/api/orders/{order_id}", headers=headers).json()["estado"] == "PENDIENTE"


def test_start_never_needs_a_commit(client, authenticated, order, session_factory):
    with patch("sqlalchemy.orm.Session.commit", side_effect=AssertionError("Preview must not commit")) as commit:
        response = start(client, authenticated[1], order["id_pedido"])
    assert response.status_code == 200, response.text
    commit.assert_not_called()
    with session_factory() as db:
        assert db.get(Pedido, order["id_pedido"]).estado == "PENDIENTE"


def test_start_read_failure_is_safe_and_does_not_change_state(client, authenticated, order, session_factory):
    with patch("app.modules.optimization.infrastructure.orders_adapter.OrdersOptimizationAdapter.get_order",
               side_effect=RuntimeError("private sql error")):
        response = start(client, authenticated[1], order["id_pedido"])
    assert response.status_code == 500 and "private" not in response.text
    with session_factory() as db:
        assert db.get(Pedido, order["id_pedido"]).estado == "PENDIENTE"


def test_openapi_documents_both_contracts(client):
    schema = client.get("/openapi.json").json()
    for path in ("/start", "/rasterize"):
        operation = schema["paths"][PREFIX + path]["post"]
        assert "200" in operation["responses"]
        assert operation["security"] == [{"HTTPBearer": []}]


@pytest.mark.parametrize("geometry", [
    {"type": "OTHER"},
    {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [10, 0], [5, 5], [10, 10], [0, 10]]},
    {"type": "RECTANGULO", "width_mm": -1, "height_mm": 10},
    {"type": "RECTANGULO", "width_mm": 10, "height_mm": 10, "vertices_mm": 42},
])
def test_corrupt_geometry_after_start_is_safe_422(client, authenticated, order, session_factory, geometry):
    assert start(client, authenticated[1], order["id_pedido"]).status_code == 200
    piece = order["piezas"][0]
    with session_factory() as db:
        db.execute(update(Pieza).where(Pieza.id_pieza == piece["id_pieza"]).values(
            geometria=geometry, tipo_forma=geometry["type"] if geometry["type"] != "OTHER" else "RECTANGULO"))
        db.commit()
    response = raster(client, authenticated[1], order["id_pedido"], piece["id_pieza"])
    assert response.status_code == 422 and "Traceback" not in response.text


def test_domain_error_returns_safe_422_without_changing_pending_order(client, authenticated, order):
    from app.modules.optimization.domain.raster_mask import RasterizationError
    assert start(client, authenticated[1], order["id_pedido"]).status_code == 200
    with patch("app.modules.optimization.application.use_cases.rasterize_geometry",
               side_effect=RasterizationError("La geometría no se puede rasterizar.")):
        response = raster(client, authenticated[1], order["id_pedido"], order["piezas"][0]["id_pieza"])
    assert response.status_code == 422
    assert client.get(f"/api/orders/{order['id_pedido']}", headers=authenticated[1]).json()["estado"] == "PENDIENTE"


def test_fractional_circle_has_safe_result_without_changing_state(client, authenticated, order, session_factory):
    piece = order["piezas"][1]
    with session_factory() as db:
        db.execute(update(Pieza).where(Pieza.id_pieza == piece["id_pieza"]).values(
            geometria={"type": "CIRCUNFERENCIA", "radius_mm": 10.0000002}))
        db.commit()
    assert start(client, authenticated[1], order["id_pedido"]).status_code == 200
    response = raster(client, authenticated[1], order["id_pedido"], piece["id_pieza"])
    # El defecto preexistente no es un requisito: una futura corrección del
    # dominio puede devolver 200. HU-015 garantiza respuesta segura y estado.
    assert response.status_code in (200, 422), response.text
    if response.status_code == 200:
        assert response.json()["geometria"] == {"type": "CIRCUNFERENCIA", "radius_mm": 10.0000002}
        assert response.json()["row_count"] > 0
    else:
        assert isinstance(response.json()["detail"], str)
        assert "Traceback" not in response.text
    assert client.get(f"/api/orders/{order['id_pedido']}", headers=authenticated[1]).json()["estado"] == "PENDIENTE"
