"""Compatibilidad por catálogo y composición de PATCH TA-013."""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.modules.inventory.application.catalog import validate_tipo_espesor
from app.modules.inventory.application.dto import TipoVidrioData, UpdatePlancha, UpdateRetazo
from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import InventoryNotFoundError, InventoryValidationError
from tests.catalog_contract import EXPECTED_CATALOG
from tests.unit.inventory.test_service import (
    FakeInventoryRepository, NOW, assert_rejected_without_write, plancha_command, retazo_command,
)


@pytest.fixture
def catalog():
    repo = FakeInventoryRepository()
    repo.tipos = {
        index: TipoVidrioData(id_tipo_vidrio=index, nombre=name, descripcion=None,
                             estado=True, espesores_mm=thicknesses)
        for index, (name, thicknesses) in enumerate(EXPECTED_CATALOG.items(), start=1)
    }
    ids = {tipo.nombre: tipo.id_tipo_vidrio for tipo in repo.tipos.values()}
    return InventoryService(repo, now=lambda: NOW), repo, ids


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
@pytest.mark.parametrize("name,thickness,valid", [
    ("Incoloro", "12", True), ("Incoloro", "2", False),
    ("Espejo", "2", True), ("Espejo", "8", False),
    ("Catedral", "3.5", True), ("Catedral", "4", False),
])
def test_create_uses_catalog(catalog, kind, name, thickness, valid):
    service, repo, ids = catalog
    command = (plancha_command if kind == "plancha" else retazo_command)(
        id_tipo_vidrio=ids[name], espesor_mm=Decimal(thickness))
    action = lambda: getattr(service, f"create_{kind}")(command)
    if valid:
        assert action().espesor_mm == Decimal(thickness)
    else:
        assert_rejected_without_write(repo, InventoryValidationError, action)


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
@pytest.mark.parametrize("changes,valid", [
    ({"id_tipo_vidrio": "Espejo"}, True),
    ({"id_tipo_vidrio": "Catedral"}, False),
    ({"espesor_mm": Decimal("12")}, True),
    ({"espesor_mm": Decimal("2")}, False),
    ({"id_tipo_vidrio": "Catedral", "espesor_mm": Decimal("3.5")}, True),
    ({"id_tipo_vidrio": "Espejo", "espesor_mm": Decimal("8")}, False),
])
def test_patch_validates_resulting_pair(catalog, kind, changes, valid):
    service, repo, ids = catalog
    original = getattr(service, f"create_{kind}")(
        (plancha_command if kind == "plancha" else retazo_command)(id_tipo_vidrio=ids["Incoloro"], espesor_mm=4))
    values = dict(changes)
    if "id_tipo_vidrio" in values:
        values["id_tipo_vidrio"] = ids[values["id_tipo_vidrio"]]
    patch = (UpdatePlancha if kind == "plancha" else UpdateRetazo)(**values)
    identifier = getattr(original, f"id_{kind}")
    action = lambda: getattr(service, f"update_{kind}")(identifier, patch)
    if valid:
        assert action() == replace(original, **values)
    else:
        assert_rejected_without_write(repo, InventoryValidationError, action)


def test_validator_is_reusable_and_observes_catalog_changes(catalog):
    _, repo, ids = catalog
    identifier = ids["Incoloro"]
    assert validate_tipo_espesor(repo, identifier, 12) == Decimal("12")
    repo.tipos[identifier] = replace(repo.tipos[identifier], espesores_mm=(Decimal("9"),))
    assert validate_tipo_espesor(repo, identifier, 9) == Decimal("9")
    with pytest.raises(InventoryValidationError):
        validate_tipo_espesor(repo, identifier, 12)


@pytest.mark.parametrize("value", [0, -1, True, Decimal("NaN"), Decimal("Infinity"), 3.5, "3.5"])
def test_validator_rejects_invalid_numbers(catalog, value):
    _, repo, ids = catalog
    with pytest.raises(InventoryValidationError):
        validate_tipo_espesor(repo, ids["Catedral"], value)


def test_validator_handles_missing_inactive_and_empty_catalog(catalog):
    _, repo, ids = catalog
    with pytest.raises(InventoryNotFoundError):
        validate_tipo_espesor(repo, 999, 4)
    identifier = ids["Espejo"]
    repo.tipos[identifier] = replace(repo.tipos[identifier], estado=False)
    with pytest.raises(InventoryValidationError):
        validate_tipo_espesor(repo, identifier, 4)
    assert validate_tipo_espesor(repo, identifier, 4, require_active=False) == Decimal("4")
    repo.tipos[identifier] = replace(repo.tipos[identifier], estado=True, espesores_mm=())
    with pytest.raises(InventoryValidationError):
        validate_tipo_espesor(repo, identifier, 4)


@pytest.mark.parametrize("kind", ["plancha", "retazo"])
def test_thickness_change_requires_active_type_but_stock_changes_do_not(catalog, kind):
    service, repo, ids = catalog
    identifier = ids["Incoloro"]
    original = getattr(service, f"create_{kind}")(
        (plancha_command if kind == "plancha" else retazo_command)(id_tipo_vidrio=identifier, espesor_mm=4))
    repo.tipos[identifier] = replace(repo.tipos[identifier], estado=False)
    patch_type = UpdatePlancha if kind == "plancha" else UpdateRetazo
    record_id = getattr(original, f"id_{kind}")
    assert_rejected_without_write(repo, InventoryValidationError,
        lambda: getattr(service, f"update_{kind}")(record_id, patch_type(espesor_mm=12)))
    assert getattr(service, f"update_{kind}")(record_id, patch_type(estado=False)).estado is False
