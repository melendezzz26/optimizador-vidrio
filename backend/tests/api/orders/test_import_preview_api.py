"""HU-018: API de previsualización de importación masiva (SPEC-HU-018 §7)."""
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select, update

from app.models import Pedido, Pieza, Usuario

PREVIEW = "/api/orders/import/preview"
VALIDATE = "/api/orders/import/validate"
CSV = ("tipo,cantidad,medidas\n"
       "R,3,800,600\n"
       "C,2,150\n"
       "P,1,{{120,60},{120,60},{120,60}}\n"
       "C,0,150\n"
       "X,1,10\n").encode("utf-8")


@pytest.fixture
def headers(client, create_user, password):
    create_user("O70000018")
    response = client.post("/api/auth/login", json={"username": "O70000018", "password": password})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def upload(client, headers, content, name="piezas.csv"):
    return client.post(PREVIEW, files={"archivo": (name, content, "application/octet-stream")}, headers=headers)


def xlsx(*rows):
    workbook = Workbook()
    for row in rows:
        workbook.active.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def counts(session_factory):
    with session_factory() as db:
        return db.scalar(select(func.count()).select_from(Pedido)), db.scalar(select(func.count()).select_from(Pieza))


def test_csv_preview_classifies_rows_without_saving(client, headers, session_factory):
    before = counts(session_factory)
    response = upload(client, headers, CSV)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["archivo"] == "piezas.csv"
    assert body["resumen"] == {"total": 5, "validas": 3, "observadas": 2}
    rows = {row["fila"]: row for row in body["filas"]}
    assert rows[2]["medidas"] == {"width_mm": 800, "height_mm": 600}
    assert rows[3]["medidas"] == {"radius_mm": 150}
    assert rows[4]["tipo_forma"] == "POLIGONO_CONVEXO" and len(rows[4]["medidas"]["vertices_mm"]) == 3
    assert rows[5]["estado"] == "OBSERVADO" and rows[5]["causas"] == ["Cantidad debe ser un entero mayor a 0"]
    assert rows[6]["causas"] == ["Tipo de pieza desconocido"]
    assert counts(session_factory) == before


def test_xlsx_gives_the_same_result_as_csv(client, headers):
    content = xlsx(("tipo", "cantidad", "medidas"), ("R", 3, 800, 600), ("C", 2, 150),
                   ("P", 1, "{{120", "60}", "{120", "60}", "{120", "60}}"), ("C", 0, 150), ("X", 1, 10))
    from_xlsx = upload(client, headers, content, "piezas.xlsx").json()
    from_csv = upload(client, headers, CSV).json()
    assert from_xlsx["archivo"] == "piezas.xlsx"
    assert from_xlsx["resumen"] == from_csv["resumen"]
    assert [(r["fila"], r["estado"], r["medidas"]) for r in from_xlsx["filas"]] == \
           [(r["fila"], r["estado"], r["medidas"]) for r in from_csv["filas"]]


@pytest.mark.parametrize("name, content, status, message", [
    ("piezas.txt", CSV, 422, "Selecciona un archivo .csv o .xlsx."),
    ("piezas.csv", b"", 422, "El archivo no contiene piezas."),
    ("piezas.csv", b"tipo,cantidad,medidas\n", 422, "El archivo no contiene piezas."),
    ("piezas.csv", "R,1,10,10".encode("utf-16"), 422, "No se pudo leer el archivo. Verifica el formato."),
    ("piezas.xlsx", b"R,1,10,10 secreto", 422, "No se pudo leer el archivo. Verifica el formato."),
    ("piezas.csv", b"C,1,10\n" * 501, 422, "El archivo supera el máximo de 500 filas."),
    ("piezas.csv", b"C,1,10\n" + b" " * (1024 * 1024), 413, "El archivo supera el tamaño máximo de 1 MB."),
], ids=["txt", "empty", "headers-only", "utf16", "fake-xlsx", "501-rows", "over-1mb"])
def test_file_errors_are_clear_and_do_not_echo_content(client, headers, name, content, status, message):
    response = upload(client, headers, content, name)
    assert response.status_code == status
    assert response.json() == {"detail": message}
    assert "secreto" not in response.text and "Traceback" not in response.text


def test_missing_file_is_a_sanitized_422(client, headers):
    response = client.post(PREVIEW, headers=headers)
    assert response.status_code == 422
    assert "Traceback" not in response.text


def test_validate_reinterprets_corrected_rows(client, headers, session_factory):
    before = counts(session_factory)
    payload = {"archivo": "piezas.csv", "filas": [{"fila": 5, "texto": "C,1,150"}, {"fila": 6, "texto": "X,1,10"}]}
    response = client.post(VALIDATE, json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["resumen"] == {"total": 2, "validas": 1, "observadas": 1}
    assert [row["fila"] for row in response.json()["filas"]] == [5, 6]
    assert counts(session_factory) == before


@pytest.mark.parametrize("payload", [
    {"filas": []},
    {"filas": [{"fila": 0, "texto": "C,1,10"}]},
    {"filas": [{"fila": 1, "texto": "C,1," + "1" * 4000}]},
    {"filas": [{"fila": n, "texto": "C,1,10"} for n in range(1, 502)]},
    {"filas": [{"fila": 1, "texto": "C,1,10"}], "extra": True},
], ids=["no-rows", "row-zero", "long-text", "501-rows", "extra-field"])
def test_validate_rejects_invalid_requests(client, headers, payload):
    response = client.post(VALIDATE, json=payload, headers=headers)
    assert response.status_code == 422
    assert "1111" not in response.text


def test_validate_keeps_a_row_without_numbers_as_observed(client, headers):
    response = client.post(VALIDATE, json={"filas": [{"fila": 4, "texto": "circulo"}]}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["resumen"] == {"total": 1, "validas": 0, "observadas": 1}
    assert response.json()["filas"][0]["fila"] == 4


def test_validate_keeps_an_emptied_row_as_observed(client, headers):
    response = client.post(VALIDATE, json={"filas": [{"fila": 1, "texto": " "}, {"fila": 2, "texto": "C,1,10"}]},
                           headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["resumen"] == {"total": 2, "validas": 1, "observadas": 1}
    assert response.json()["filas"][0]["causas"] == [
        "Fila vacía: escribe la pieza o vuelve a cargar el archivo sin esta fila"]


def test_both_endpoints_require_authentication(client):
    assert upload(client, {}, CSV).status_code == 401
    assert client.post(VALIDATE, json={"filas": [{"fila": 1, "texto": "C,1,10"}]}).status_code == 401


def test_both_endpoints_require_orders_create(client, create_user, password, session_factory):
    identifier = create_user("A70000018")
    with session_factory() as db:
        db.execute(update(Usuario).where(Usuario.id_usuario == identifier).values(id_rol=2))  # Almacenero
        db.commit()
    token = client.post("/api/auth/login", json={"username": "A70000018", "password": password}).json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    assert upload(client, headers, CSV).status_code == 403
    assert client.post(VALIDATE, json={"filas": [{"fila": 1, "texto": "C,1,10"}]}, headers=headers).status_code == 403