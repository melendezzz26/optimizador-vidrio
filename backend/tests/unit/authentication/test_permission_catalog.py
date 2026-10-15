"""S1-RBAC: el catálogo de permisos y la asignación inicial son coherentes."""
from pathlib import Path
import re
import runpy

from app.core.permissions import (
    ASIGNACION_INICIAL,
    CATALOGO,
    CODIGOS,
    PERMISOS_PROTEGIDOS_ADMINISTRADOR,
)

MIGRATION = Path(__file__).resolve().parents[3] / "alembic/versions/s1rbac01a2b3_s1_rbac_permisos.py"


def test_catalog_codes_are_unique_and_follow_module_action_format():
    codes = [permission.code for permission in CATALOGO]
    assert len(codes) == len(set(codes)) == len(CODIGOS) == 13
    for permission in CATALOGO:
        # Mismas reglas que los CHECK de la tabla permisos.
        assert re.fullmatch(r"[a-z]+\.[a-z]+", permission.code)
        assert permission.code.startswith(permission.module + ".")
        assert 0 < len(permission.description) <= 150


def test_initial_assignment_uses_only_catalog_codes_and_known_roles():
    assert set(ASIGNACION_INICIAL) == {"Administrador", "Almacenero", "Operario"}
    for codes in ASIGNACION_INICIAL.values():
        assert codes <= CODIGOS


def test_administrator_starts_with_every_permission_including_protected_ones():
    assert ASIGNACION_INICIAL["Administrador"] == CODIGOS
    assert PERMISOS_PROTEGIDOS_ADMINISTRADOR <= ASIGNACION_INICIAL["Administrador"]


def test_initial_assignment_keeps_previous_access_of_each_role():
    """Equivale a la matriz anterior: nadie gana ni pierde acceso al migrar."""
    assert ASIGNACION_INICIAL["Almacenero"] == {"inventory.view", "inventory.manage", "optimization.view"}
    assert ASIGNACION_INICIAL["Operario"] == {
        "inventory.view",
        "orders.view", "orders.create", "orders.update", "orders.cancel",
        "optimization.view", "optimization.execute", "optimization.confirm",
    }
    for role in ("Almacenero", "Operario"):
        assert not ASIGNACION_INICIAL[role] & {"users.view", "users.manage", "roles.view", "roles.manage"}


def test_migration_data_matches_catalog_and_initial_assignment():
    """La migración guarda sus datos literales; aquí se comprueba que no se desalineen."""
    migration = runpy.run_path(str(MIGRATION))
    assert {(p.code, p.module, p.description) for p in CATALOGO} == set(migration["PERMISOS"])
    assert {role: set(codes) for role, codes in migration["ASIGNACION_INICIAL"].items()} == {
        role: set(codes) for role, codes in ASIGNACION_INICIAL.items()
    }