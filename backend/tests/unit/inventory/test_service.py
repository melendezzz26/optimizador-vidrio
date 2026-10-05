"""Casos de uso de Inventory con repositorio en memoria, sin infraestructura."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import fields, is_dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import subprocess
import sys

import pytest

from app.modules.inventory.application.dto import (
    CreatePlancha, CreateRetazo, CreateTipoVidrio, PlanchaData, RetazoData,
    TipoVidrioData, UpdatePlancha, UpdateRetazo,
)
from app.modules.inventory.application.ports import InventoryRepository
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import (
    InvalidGeometryError, InventoryConflictError, InventoryNotFoundError,
    InventoryValidationError,
)
from app.modules.inventory.domain.geometry import calculate_area_mm2


NOW = datetime(2026, 10, 4, 15, 30, tzinfo=timezone.utc)


class FakeInventoryRepository(InventoryRepository):
    """Devuelve snapshots; simula atomicidad y registra intentos de escritura."""

    def __init__(self):
        self.tipos = {
            1: TipoVidrioData(id_tipo_vidrio=1, nombre="Claro", descripcion=None, estado=True),
            2: TipoVidrioData(id_tipo_vidrio=2, nombre="Inactivo", descripcion=None, estado=False),
        }
        self.planchas = {}
        self.retazos = {}
        self.writes = []
        self.code_checks = []
        self.commits = 0
        self.rollbacks = 0
        self.in_transaction = False
        self.fail_write = False
        self.fail_commit = False

    @contextmanager
    def transaction(self):
        assert not self.in_transaction
        before = deepcopy((self.tipos, self.planchas, self.retazos))
        self.in_transaction = True
        try:
            yield
            if self.fail_commit:
                raise RuntimeError("simulated commit failure")
            self.commits += 1
        except Exception:
            self.tipos, self.planchas, self.retazos = before
            self.rollbacks += 1
            raise
        finally:
            self.in_transaction = False

    def _write(self, table, key, value):
        assert self.in_transaction
        self.writes.append(deepcopy(value))
        table[key] = deepcopy(value)
        if self.fail_write:
            raise RuntimeError("simulated adapter failure")
        return deepcopy(value)

    def get_tipo_vidrio(self, id_tipo_vidrio):
        return deepcopy(self.tipos.get(id_tipo_vidrio))

    def tipo_nombre_exists(self, nombre):
        return any(item.nombre == nombre for item in self.tipos.values())

    def create_tipo_vidrio(self, **values):
        item = TipoVidrioData(id_tipo_vidrio=max(self.tipos, default=0) + 1, **values)
        return self._write(self.tipos, item.id_tipo_vidrio, item)

    def list_tipos_vidrio(self):
        return deepcopy(list(self.tipos.values()))

    def get_plancha(self, id_plancha):
        return deepcopy(self.planchas.get(id_plancha))

    def create_plancha(self, **values):
        item = PlanchaData(id_plancha=max(self.planchas, default=0) + 1, **values)
        return self._write(self.planchas, item.id_plancha, item)

    def list_planchas(self):
        return deepcopy(list(self.planchas.values()))

    def save_plancha(self, data):
        return self._write(self.planchas, data.id_plancha, data)

    def get_retazo(self, id_retazo):
        return deepcopy(self.retazos.get(id_retazo))

    def retazo_codigo_exists(self, codigo, exclude_id=None):
        self.code_checks.append((codigo, exclude_id))
        return any(item.codigo == codigo and item.id_retazo != exclude_id
                   for item in self.retazos.values())

    def create_retazo(self, **values):
        item = RetazoData(id_retazo=max(self.retazos, default=0) + 1, **values)
        return self._write(self.retazos, item.id_retazo, item)

    def list_retazos(self):
        return deepcopy(list(self.retazos.values()))

    def save_retazo(self, data):
        return self._write(self.retazos, data.id_retazo, data)


@pytest.fixture
def inventory():
    repo = FakeInventoryRepository()
    return InventoryService(repo, now=lambda: NOW), repo


def plancha_command(**changes):
    values = dict(ancho_mm=Decimal("1000.25"), alto_mm=Decimal("500"),
                  espesor_mm=Decimal("5.5"), cantidad=2, id_tipo_vidrio=1)
    return CreatePlancha(**(values | changes))


def retazo_command(**changes):
    values = dict(codigo="R-001", espesor_mm=Decimal("4"), id_tipo_vidrio=1,
                  geometria={"type": "RECTANGULO", "width_mm": 10, "height_mm": 20})
    return CreateRetazo(**(values | changes))


def assert_rejected_without_write(repo, error, action):
    before = deepcopy((repo.tipos, repo.planchas, repo.retazos, repo.writes))
    with pytest.raises(error):
        action()
    assert (repo.tipos, repo.planchas, repo.retazos, repo.writes) == before


def test_create_tipo_and_list_preserve_all_states(inventory):
    service, repo = inventory
    result = service.create_tipo_vidrio(CreateTipoVidrio(nombre="  Bronce  ", descripcion="Tinte"))
    assert result == TipoVidrioData(id_tipo_vidrio=3, nombre="Bronce", descripcion="Tinte", estado=True)
    assert repo.writes == [result]
    assert service.list_tipos_vidrio() == list(repo.tipos.values())
    assert service.list_tipos_vidrio()[1].estado is False


@pytest.mark.parametrize("nombre", ["", "   ", "x" * 101, None, True])
def test_invalid_tipo_name_does_not_write(inventory, nombre):
    service, repo = inventory
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: service.create_tipo_vidrio(CreateTipoVidrio(nombre=nombre)))


def test_duplicate_tipo_does_not_write(inventory):
    service, repo = inventory
    assert_rejected_without_write(repo, InventoryConflictError,
        lambda: service.create_tipo_vidrio(CreateTipoVidrio(nombre=" Claro ")))


def test_tipo_optional_description_and_maximum_name(inventory):
    service, _ = inventory
    assert service.create_tipo_vidrio(CreateTipoVidrio(nombre="x" * 100)).descripcion is None


def test_tipo_invalid_description(inventory):
    service, repo = inventory
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: service.create_tipo_vidrio(CreateTipoVidrio(nombre="Nuevo", descripcion=123)))


def test_create_plancha_sends_normalized_data_and_utc_date(inventory):
    service, repo = inventory
    result = service.create_plancha(plancha_command(ancho_mm=1000))
    assert type(result) is PlanchaData and is_dataclass(result)
    assert result == PlanchaData(id_plancha=1, ancho_mm=Decimal("1000"), alto_mm=Decimal("500"),
        espesor_mm=Decimal("5.5"), cantidad=2, id_tipo_vidrio=1, estado=True, fecha_registro=NOW)
    assert all(isinstance(getattr(result, field), Decimal) for field in ("ancho_mm", "alto_mm", "espesor_mm"))
    assert result.fecha_registro.tzinfo is timezone.utc
    assert repo.writes == [result] and repo.commits == 1


INVALID_PLANCHA_FIELDS = [
    ("ancho_mm", 0), ("ancho_mm", -1), ("alto_mm", 0), ("alto_mm", -1),
    ("espesor_mm", Decimal("5")), ("ancho_mm", True), ("alto_mm", False),
    ("espesor_mm", True), ("cantidad", True), ("cantidad", -1), ("cantidad", Decimal("2")),
    ("ancho_mm", Decimal("NaN")), ("alto_mm", Decimal("Infinity")),
    ("espesor_mm", Decimal("sNaN")), ("ancho_mm", 1.5), ("alto_mm", "10"),
    ("id_tipo_vidrio", True), ("id_tipo_vidrio", 0),
]


@pytest.mark.parametrize("field,value", INVALID_PLANCHA_FIELDS + [("cantidad", 0)])
def test_invalid_plancha_create_does_not_write(inventory, field, value):
    service, repo = inventory
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: service.create_plancha(plancha_command(**{field: value})))


@pytest.mark.parametrize("thickness", ["3", "4", "5.5", "6", "8"])
def test_all_catalog_thicknesses_are_accepted(inventory, thickness):
    service, _ = inventory
    assert service.create_plancha(plancha_command(espesor_mm=Decimal(thickness))).espesor_mm == Decimal(thickness)
    assert service.create_retazo(retazo_command(espesor_mm=Decimal(thickness))).espesor_mm == Decimal(thickness)


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
@pytest.mark.parametrize("tipo,error", [(999, InventoryNotFoundError), (2, InventoryValidationError)])
def test_create_with_missing_or_inactive_tipo_does_not_write(inventory, kind, tipo, error):
    service, repo = inventory
    command = plancha_command(id_tipo_vidrio=tipo) if kind == "plancha" else retazo_command(id_tipo_vidrio=tipo)
    assert_rejected_without_write(repo, error, lambda: getattr(service, f"create_{kind}")(command))


def test_update_plancha_preserves_id_date_and_accepts_zero_false(inventory):
    service, repo = inventory
    original = service.create_plancha(plancha_command())
    repo.tipos[3] = TipoVidrioData(id_tipo_vidrio=3, nombre="Otro", descripcion=None, estado=True)
    result = service.update_plancha(original.id_plancha, UpdatePlancha(
        ancho_mm=1200, alto_mm=600, espesor_mm=Decimal("6"), cantidad=0, estado=False, id_tipo_vidrio=3))
    assert result == replace(original, ancho_mm=Decimal("1200"), alto_mm=Decimal("600"),
                             espesor_mm=Decimal("6"), cantidad=0, estado=False, id_tipo_vidrio=3)
    assert repo.writes[-1] == result
    assert service.list_planchas() == [result]


@pytest.mark.parametrize("field,value", INVALID_PLANCHA_FIELDS + [("estado", 0)])
def test_invalid_plancha_update_does_not_write(inventory, field, value):
    service, repo = inventory
    original = service.create_plancha(plancha_command())
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: service.update_plancha(original.id_plancha, UpdatePlancha(**{field: value})))


@pytest.mark.parametrize("kind,command", [("plancha", UpdatePlancha()), ("retazo", UpdateRetazo())])
def test_empty_patch_is_rejected(inventory, kind, command):
    service, repo = inventory
    getattr(service, f"create_{kind}")(plancha_command() if kind == "plancha" else retazo_command())
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: getattr(service, f"update_{kind}")(1, command))


@pytest.mark.parametrize("kind,command", [("plancha", UpdatePlancha(estado=False)), ("retazo", UpdateRetazo(estado=False))])
def test_missing_resource_on_update(inventory, kind, command):
    service, repo = inventory
    assert_rejected_without_write(repo, InventoryNotFoundError,
        lambda: getattr(service, f"update_{kind}")(999, command))


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
@pytest.mark.parametrize("tipo,error", [(999, InventoryNotFoundError), (2, InventoryValidationError)])
def test_update_to_invalid_tipo_does_not_write(inventory, kind, tipo, error):
    service, repo = inventory
    getattr(service, f"create_{kind}")(plancha_command() if kind == "plancha" else retazo_command())
    patch = UpdatePlancha(id_tipo_vidrio=tipo) if kind == "plancha" else UpdateRetazo(id_tipo_vidrio=tipo)
    assert_rejected_without_write(repo, error, lambda: getattr(service, f"update_{kind}")(1, patch))


def test_create_retazo_uses_domain_area_and_sends_manual_origin(inventory):
    service, repo = inventory
    command = retazo_command(codigo=" R-001 ")
    result = service.create_retazo(command)
    assert type(result) is RetazoData and is_dataclass(result)
    assert result == RetazoData(id_retazo=1, codigo="R-001", espesor_mm=Decimal("4"),
        geometria=command.geometria, area_mm2=calculate_area_mm2(command.geometria),
        id_tipo_vidrio=1, estado=True, fecha_registro=NOW, id_ejecucion_origen=None)
    assert result.area_mm2 == Decimal("200.00") and result.area_mm2.as_tuple().exponent == -2
    assert result.fecha_registro.tzinfo is timezone.utc
    assert repo.writes == [result]
    command.geometria["width_mm"] = 999
    assert repo.retazos[1].geometria["width_mm"] == 10
    assert result.geometria["width_mm"] == 10


@pytest.mark.parametrize("changes", [
    {"codigo": ""}, {"codigo": "   "}, {"codigo": "x" * 41}, {"codigo": None},
    {"espesor_mm": Decimal("5")}, {"espesor_mm": True}, {"espesor_mm": 5.5},
    {"espesor_mm": Decimal("NaN")}, {"id_tipo_vidrio": True},
])
def test_invalid_retazo_create_does_not_write(inventory, changes):
    service, repo = inventory
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: service.create_retazo(retazo_command(**changes)))


def test_retazo_maximum_code_and_duplicate(inventory):
    service, repo = inventory
    assert service.create_retazo(retazo_command(codigo="x" * 40)).codigo == "x" * 40
    assert_rejected_without_write(repo, InventoryConflictError,
        lambda: service.create_retazo(retazo_command(codigo="x" * 40)))


@pytest.mark.parametrize("geometry", [
    {"type": "TRIANGULO"}, {"type": "RECTANGULO", "width_mm": 0, "height_mm": 1},
    {"type": "CIRCUNFERENCIA", "radius_mm": Decimal("0.001")},
])
def test_invalid_geometry_propagates_without_writes(inventory, geometry):
    service, repo = inventory
    assert_rejected_without_write(repo, InvalidGeometryError,
        lambda: service.create_retazo(retazo_command(geometria=geometry)))
    original = service.create_retazo(retazo_command())
    assert_rejected_without_write(repo, InvalidGeometryError,
        lambda: service.update_retazo(original.id_retazo, UpdateRetazo(geometria=geometry)))


@pytest.mark.parametrize("extra_field", ["extra", "area_mm2"])
def test_retazo_geometry_with_additional_property_does_not_write(inventory, extra_field):
    service, repo = inventory
    geometry = {"type": "RECTANGULO", "width_mm": 10, "height_mm": 20,
                extra_field: 99999}
    original_geometry = deepcopy(geometry)
    assert_rejected_without_write(repo, InvalidGeometryError,
        lambda: service.create_retazo(retazo_command(geometria=geometry)))
    original = service.create_retazo(retazo_command())
    assert_rejected_without_write(repo, InvalidGeometryError,
        lambda: service.update_retazo(original.id_retazo, UpdateRetazo(geometria=geometry)))
    assert geometry == original_geometry


def test_update_retazo_recalculates_area_and_preserves_identity_date_origin(inventory):
    service, repo = inventory
    original = service.create_retazo(retazo_command())
    repo.retazos[1] = replace(original, id_ejecucion_origen=17)
    repo.tipos[3] = TipoVidrioData(id_tipo_vidrio=3, nombre="Otro", descripcion=None, estado=True)
    geometry = {"type": "CIRCUNFERENCIA", "radius_mm": 2}
    result = service.update_retazo(1, UpdateRetazo(codigo=" R-002 ", geometria=geometry,
        espesor_mm=Decimal("8"), estado=False, id_tipo_vidrio=3))
    assert result == replace(original, codigo="R-002", geometria=geometry,
        area_mm2=Decimal("12.57"), espesor_mm=Decimal("8"), estado=False,
        id_tipo_vidrio=3, id_ejecucion_origen=17)
    assert repo.writes[-1] == result
    assert service.list_retazos() == [result]


def test_retazo_patch_without_geometry_preserves_area_and_excludes_own_code(inventory):
    service, repo = inventory
    original = service.create_retazo(retazo_command())
    # Un registro persistido se conserva; no se recalcula si se omite geometría.
    repo.retazos[1] = replace(original, area_mm2=Decimal("199.99"))
    result = service.update_retazo(1, UpdateRetazo(codigo="R-001", estado=False))
    assert result.area_mm2 == Decimal("199.99")
    assert result.geometria == original.geometria and result.estado is False
    assert repo.code_checks[-1] == ("R-001", 1)
    service.create_retazo(retazo_command(codigo="R-002"))
    assert_rejected_without_write(repo, InventoryConflictError,
        lambda: service.update_retazo(1, UpdateRetazo(codigo="R-002")))
    assert repo.code_checks[-1] == ("R-002", 1)


@pytest.mark.parametrize("changes", [
    {"codigo": " "}, {"codigo": "x" * 41}, {"espesor_mm": Decimal("7")},
    {"espesor_mm": False}, {"estado": 0}, {"id_tipo_vidrio": True},
])
def test_invalid_retazo_update_does_not_write(inventory, changes):
    service, repo = inventory
    service.create_retazo(retazo_command())
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: service.update_retazo(1, UpdateRetazo(**changes)))


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_omission_preserves_fields_and_unchanged_inactive_tipo_is_allowed(inventory, kind):
    service, repo = inventory
    original = getattr(service, f"create_{kind}")(plancha_command() if kind == "plancha" else retazo_command())
    repo.tipos[1] = replace(repo.tipos[1], estado=False)
    patch = UpdatePlancha(ancho_mm=None, estado=False, id_tipo_vidrio=1) if kind == "plancha" else UpdateRetazo(geometria=None, estado=False, id_tipo_vidrio=1)
    assert getattr(service, f"update_{kind}")(1, patch) == replace(original, estado=False)


@pytest.mark.parametrize("command,protected", [
    (CreateRetazo, "area_mm2"), (CreateRetazo, "id_ejecucion_origen"),
    (UpdateRetazo, "area_mm2"), (UpdateRetazo, "id_ejecucion_origen"),
    (UpdateRetazo, "id_retazo"), (UpdateRetazo, "fecha_registro"),
    (UpdatePlancha, "id_plancha"), (UpdatePlancha, "fecha_registro"),
])
def test_commands_do_not_accept_protected_fields(command, protected):
    assert protected not in {field.name for field in fields(command)}
    with pytest.raises(TypeError):
        command(**{protected: 1})


def test_output_dtos_match_inventory_model_fields_without_orm():
    assert {f.name for f in fields(TipoVidrioData)} == {"id_tipo_vidrio", "nombre", "descripcion", "estado"}
    assert {f.name for f in fields(PlanchaData)} == {
        "id_plancha", "ancho_mm", "alto_mm", "espesor_mm", "cantidad", "estado", "fecha_registro", "id_tipo_vidrio"}
    assert {f.name for f in fields(RetazoData)} == {
        "id_retazo", "codigo", "espesor_mm", "geometria", "area_mm2", "estado", "fecha_registro", "id_tipo_vidrio", "id_ejecucion_origen"}
    assert all(not hasattr(dto, "__table__") for dto in (TipoVidrioData, PlanchaData, RetazoData))


def test_empty_lists(inventory):
    service, repo = inventory
    repo.tipos.clear()
    assert service.list_tipos_vidrio() == []
    assert service.list_planchas() == []
    assert service.list_retazos() == []


def test_default_clock_is_utc():
    service = InventoryService(FakeInventoryRepository())
    before = datetime.now(timezone.utc)
    result = service.create_plancha(plancha_command())
    assert before <= result.fecha_registro <= datetime.now(timezone.utc)
    assert result.fecha_registro.tzinfo is timezone.utc


def test_injected_aware_clock_is_normalized_to_utc():
    local = NOW.astimezone(timezone(timedelta(hours=-5)))
    service = InventoryService(FakeInventoryRepository(), now=lambda: local)
    assert service.create_retazo(retazo_command()).fecha_registro == NOW
    assert service.create_plancha(plancha_command()).fecha_registro.tzinfo is timezone.utc


def test_naive_clock_does_not_write():
    repo = FakeInventoryRepository()
    service = InventoryService(repo, now=lambda: NOW.replace(tzinfo=None))
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: service.create_plancha(plancha_command()))


@pytest.mark.parametrize("kind", ["tipo_vidrio", "plancha", "retazo"])
def test_adapter_failure_rolls_back_and_propagates(inventory, kind):
    service, repo = inventory
    repo.fail_write = True
    command = {"tipo_vidrio": CreateTipoVidrio(nombre="Nuevo"),
               "plancha": plancha_command(), "retazo": retazo_command()}[kind]
    before = deepcopy((repo.tipos, repo.planchas, repo.retazos))
    with pytest.raises(RuntimeError, match="simulated adapter failure"):
        getattr(service, f"create_{kind}")(command)
    assert (repo.tipos, repo.planchas, repo.retazos) == before
    assert repo.rollbacks == 1 and repo.commits == 0


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_adapter_failure_on_update_preserves_persisted_record(inventory, kind):
    service, repo = inventory
    original = getattr(service, f"create_{kind}")(plancha_command() if kind == "plancha" else retazo_command())
    repo.fail_write = True
    patch = UpdatePlancha(estado=False) if kind == "plancha" else UpdateRetazo(estado=False)
    with pytest.raises(RuntimeError, match="simulated adapter failure"):
        getattr(service, f"update_{kind}")(1, patch)
    assert getattr(repo, f"get_{kind}")(1) == original
    assert repo.rollbacks == 1 and repo.commits == 1


def test_commit_failure_does_not_return_success(inventory):
    service, repo = inventory
    repo.fail_commit = True
    with pytest.raises(RuntimeError, match="simulated commit failure"):
        service.create_retazo(retazo_command())
    assert repo.retazos == {}
    assert repo.rollbacks == 1 and repo.commits == 0


def test_application_imports_without_infrastructure():
    script = '''
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    forbidden = ("sqlalchemy", "fastapi", "pydantic", "app.models", "app.shared.database")
    if any(name == item or name.startswith(item + ".") for item in forbidden):
        raise AssertionError("Forbidden dependency: " + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from app.modules.inventory.application.service import InventoryService
'''
    result = subprocess.run([sys.executable, "-B", "-c", script],
        cwd=Path(__file__).resolve().parents[3], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
