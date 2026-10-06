"""Casos de uso de gestión de usuarios, con un repositorio en memoria."""
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.modules.users.application.dto import CreateUserData, UpdateUserData
from app.modules.users.application.use_cases import (
    create_user,
    get_user,
    list_roles,
    list_users,
    update_user,
)
from app.modules.users.domain.errors import (
    DuplicateDniError,
    InvalidUserDataError,
    RoleNotFoundError,
    SelfModificationError,
    UserNotFoundError,
)
from app.modules.users.domain.user import Role, User

ADMIN_ROLE, OPERATOR_ROLE = Role(1, "Administrador"), Role(3, "Operario")
FIXED_NOW = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


class InMemoryUserRepository:
    """Implementa UserRepository sin base de datos."""

    def __init__(self):
        self.roles = {ADMIN_ROLE.role_id: ADMIN_ROLE, OPERATOR_ROLE.role_id: OPERATOR_ROLE}
        self.users: dict[int, User] = {}
        self.password_hashes: dict[int, str] = {}
        self.created_at: dict[int, datetime] = {}

    def list_roles(self):
        return list(self.roles.values())

    def role_exists(self, role_id):
        return role_id in self.roles

    def list_users(self):
        return list(self.users.values())

    def find_by_id(self, user_id):
        return self.users.get(user_id)

    def dni_exists(self, dni):
        return any(user.dni == dni for user in self.users.values())

    def add(self, new_user):
        user_id = len(self.users) + 1
        self.users[user_id] = User(
            user_id=user_id,
            dni=new_user.dni,
            first_names=new_user.first_names,
            last_names=new_user.last_names,
            username=new_user.username,
            is_active=True,
            role_id=new_user.role_id,
            role_name=self.roles[new_user.role_id].name,
        )
        self.password_hashes[user_id] = new_user.password_hash
        self.created_at[user_id] = new_user.created_at
        return self.users[user_id]

    def update(self, user_id, changes):
        user = self.users[user_id]
        if changes.first_names is not None:
            user = replace(user, first_names=changes.first_names)
        if changes.last_names is not None:
            user = replace(user, last_names=changes.last_names)
        if changes.role_id is not None:
            user = replace(user, role_id=changes.role_id, role_name=self.roles[changes.role_id].name)
        if changes.is_active is not None:
            user = replace(user, is_active=changes.is_active)
        if changes.password_hash is not None:
            self.password_hashes[user_id] = changes.password_hash
        self.users[user_id] = user
        return user


def fake_hash(password: str) -> str:
    return f"hash({password})"


def valid_data(**changes) -> CreateUserData:
    data = {
        "first_names": "Fabricio",
        "last_names": "Aguilar",
        "dni": "71234567",
        "password": "clave-segura-1",
        "role_id": OPERATOR_ROLE.role_id,
    }
    data.update(changes)
    return CreateUserData(**data)


@pytest.fixture
def repository():
    return InMemoryUserRepository()


def create(repository, **changes) -> User:
    return create_user(valid_data(**changes), repository=repository, hash_password=fake_hash, now=lambda: FIXED_NOW)


def update(repository, user_id, acting_user_id=999, **changes) -> User:
    return update_user(
        user_id,
        UpdateUserData(**changes),
        acting_user_id=acting_user_id,
        repository=repository,
        hash_password=fake_hash,
    )


# --- Alta ---

def test_create_generates_the_username_and_stores_an_active_user(repository):
    user = create(repository, first_names="  Álvaro ", last_names=" Quispe  Rojas ")
    assert user.username == "A71234567"
    assert user.first_names == "Álvaro"
    assert user.last_names == "Quispe Rojas"
    assert user.is_active is True
    assert user.role_name == "Operario"


def test_create_stores_the_hash_and_never_the_plain_password(repository):
    user = create(repository)
    assert repository.password_hashes[user.user_id] == "hash(clave-segura-1)"
    assert "clave-segura-1" not in repr(user)


def test_create_records_the_creation_time(repository):
    user = create(repository)
    assert repository.created_at[user.user_id] == FIXED_NOW


def test_create_rejects_a_duplicate_dni_and_keeps_a_single_user(repository):
    create(repository)
    with pytest.raises(DuplicateDniError):
        create(repository, first_names="Otra", last_names="Persona")
    assert len(repository.users) == 1


def test_create_rejects_an_unknown_role_without_saving(repository):
    with pytest.raises(RoleNotFoundError):
        create(repository, role_id=99)
    assert repository.users == {}


@pytest.mark.parametrize(
    "changes",
    [
        {"dni": "1234"},
        {"first_names": "   "},
        {"first_names": "9lvaro"},
        {"last_names": ""},
        {"password": "corta"},
        {"password": "a" * 73},
    ],
)
def test_create_rejects_invalid_data_without_saving(repository, changes):
    with pytest.raises(InvalidUserDataError):
        create(repository, **changes)
    assert repository.users == {}


def test_invalid_password_is_not_hashed(repository):
    calls = []

    def tracking_hash(password):
        calls.append(password)
        return "hash"

    with pytest.raises(InvalidUserDataError):
        create_user(valid_data(password="corta"), repository=repository, hash_password=tracking_hash, now=lambda: FIXED_NOW)
    assert calls == []


def test_password_data_is_hidden_from_repr():
    assert "clave-segura-1" not in repr(valid_data())
    assert "nueva-clave-1" not in repr(UpdateUserData(password="nueva-clave-1"))


# --- Consulta ---

def test_list_and_get_return_the_stored_users(repository):
    user = create(repository)
    assert list_users(repository=repository) == [user]
    assert get_user(user.user_id, repository=repository) == user


def test_get_unknown_user_raises_not_found(repository):
    with pytest.raises(UserNotFoundError):
        get_user(404, repository=repository)


def test_list_roles_returns_the_available_roles(repository):
    assert list_roles(repository=repository) == [ADMIN_ROLE, OPERATOR_ROLE]


# --- Modificación ---

def test_update_changes_names_and_role_but_never_dni_or_username(repository):
    user = create(repository)
    updated = update(repository, user.user_id, first_names="Zoila", last_names="Paz", role_id=ADMIN_ROLE.role_id)
    assert (updated.first_names, updated.last_names, updated.role_name) == ("Zoila", "Paz", "Administrador")
    # RN-04: aunque el nombre ahora empiece con Z, el usuario de acceso no cambia.
    assert updated.username == user.username == "F71234567"
    assert updated.dni == user.dni


def test_update_without_password_keeps_the_previous_hash(repository):
    user = create(repository)
    update(repository, user.user_id, first_names="Fabio")
    assert repository.password_hashes[user.user_id] == "hash(clave-segura-1)"


def test_update_with_password_replaces_the_hash(repository):
    user = create(repository)
    update(repository, user.user_id, password="nueva-clave-1")
    assert repository.password_hashes[user.user_id] == "hash(nueva-clave-1)"


def test_update_can_deactivate_and_reactivate_another_user(repository):
    user = create(repository)
    assert update(repository, user.user_id, is_active=False).is_active is False
    assert update(repository, user.user_id, is_active=True).is_active is True


def test_update_unknown_user_raises_not_found(repository):
    with pytest.raises(UserNotFoundError):
        update(repository, 404, first_names="Nadie")


def test_update_rejects_an_unknown_role_without_saving(repository):
    user = create(repository)
    with pytest.raises(RoleNotFoundError):
        update(repository, user.user_id, role_id=99)
    assert repository.users[user.user_id] == user


@pytest.mark.parametrize("changes", [{"first_names": " "}, {"last_names": "a" * 101}, {"password": "corta"}])
def test_update_rejects_invalid_data_without_saving(repository, changes):
    user = create(repository)
    with pytest.raises(InvalidUserDataError):
        update(repository, user.user_id, **changes)
    assert repository.users[user.user_id] == user
    assert repository.password_hashes[user.user_id] == "hash(clave-segura-1)"


# --- RN-07: el Administrador no puede dejarse sin acceso ---

def test_administrator_cannot_deactivate_their_own_account(repository):
    admin = create(repository, role_id=ADMIN_ROLE.role_id)
    with pytest.raises(SelfModificationError):
        update(repository, admin.user_id, acting_user_id=admin.user_id, is_active=False)
    assert repository.users[admin.user_id].is_active is True


def test_administrator_cannot_change_their_own_role(repository):
    admin = create(repository, role_id=ADMIN_ROLE.role_id)
    with pytest.raises(SelfModificationError):
        update(repository, admin.user_id, acting_user_id=admin.user_id, role_id=OPERATOR_ROLE.role_id)
    assert repository.users[admin.user_id].role_name == "Administrador"


def test_administrator_can_edit_their_own_names_and_password(repository):
    admin = create(repository, role_id=ADMIN_ROLE.role_id)
    updated = update(
        repository,
        admin.user_id,
        acting_user_id=admin.user_id,
        first_names="Fabio",
        password="nueva-clave-1",
        role_id=ADMIN_ROLE.role_id,
        is_active=True,
    )
    assert updated.first_names == "Fabio"
    assert repository.password_hashes[admin.user_id] == "hash(nueva-clave-1)"


def test_administrator_can_deactivate_another_administrator(repository):
    admin = create(repository, role_id=ADMIN_ROLE.role_id)
    other = create(repository, dni="70000002", role_id=ADMIN_ROLE.role_id)
    assert update(repository, other.user_id, acting_user_id=admin.user_id, is_active=False).is_active is False
