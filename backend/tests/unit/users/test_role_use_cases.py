"""S1-RBAC: reglas del reemplazo de permisos de un rol (RN-05, RN-06), sin base de datos."""
import pytest

from app.core.permissions import CATALOGO, CODIGOS
from app.modules.users.application.role_use_cases import replace_role_permissions
from app.modules.users.domain.errors import (
    ProtectedPermissionError,
    RoleNotRegisteredError,
    UnknownPermissionError,
)
from app.modules.users.domain.role_permissions import PermissionInfo, RoleWithPermissions


class InMemoryRolePermissionRepository:
    def __init__(self):
        self.roles = {
            1: RoleWithPermissions(1, "Administrador", CODIGOS),
            2: RoleWithPermissions(2, "Almacenero", frozenset({"inventory.view"})),
        }
        self.writes = 0

    def list_roles(self):
        return list(self.roles.values())

    def find_role(self, role_id):
        return self.roles.get(role_id)

    def list_permissions(self):
        return [PermissionInfo(p.code, p.module, p.description) for p in CATALOGO]

    def replace_permissions(self, role_id, codes):
        self.writes += 1
        role = self.roles[role_id]
        self.roles[role_id] = RoleWithPermissions(role.role_id, role.name, frozenset(codes))
        return self.roles[role_id]


@pytest.fixture
def repository():
    return InMemoryRolePermissionRepository()


def test_replaces_the_whole_set_and_removes_duplicates(repository):
    role = replace_role_permissions(
        2, ["inventory.manage", "orders.view", "inventory.manage"], repository=repository,
    )
    assert role.permissions == {"inventory.manage", "orders.view"}


def test_an_empty_list_leaves_the_role_without_permissions(repository):
    assert replace_role_permissions(2, [], repository=repository).permissions == frozenset()


@pytest.mark.parametrize("codes", [["inventory.view", "inventario.ver"], ["GESTIONAR_USUARIOS"], ["users.delete"]])
def test_unknown_codes_are_rejected_without_writing(repository, codes):
    with pytest.raises(UnknownPermissionError):
        replace_role_permissions(2, codes, repository=repository)
    assert repository.writes == 0
    assert repository.roles[2].permissions == {"inventory.view"}


def test_unknown_role_is_rejected(repository):
    with pytest.raises(RoleNotRegisteredError):
        replace_role_permissions(99, ["inventory.view"], repository=repository)
    assert repository.writes == 0


@pytest.mark.parametrize("removed", ["roles.view", "roles.manage"])
def test_administrator_keeps_role_management_permissions(repository, removed):
    with pytest.raises(ProtectedPermissionError):
        replace_role_permissions(1, sorted(CODIGOS - {removed}), repository=repository)
    assert repository.writes == 0
    assert repository.roles[1].permissions == CODIGOS


def test_administrator_can_lose_other_permissions(repository):
    role = replace_role_permissions(1, ["roles.view", "roles.manage"], repository=repository)
    assert role.permissions == {"roles.view", "roles.manage"}


def test_other_roles_may_receive_or_lose_role_management(repository):
    role = replace_role_permissions(2, ["roles.view", "roles.manage"], repository=repository)
    assert role.permissions == {"roles.view", "roles.manage"}