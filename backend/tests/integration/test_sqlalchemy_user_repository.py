"""Repositorio de usuarios sobre una base SQLite en memoria (SPEC-HU-003, sección 10).

No usa PostgreSQL ni la base compartida: las tablas se crean en cada prueba.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models import Usuario
from app.modules.users.domain.errors import DuplicateDniError, UserNotFoundError
from app.modules.users.domain.user import NewUser, Role, UserChanges
from app.modules.users.infrastructure.sqlalchemy_user_repository import SqlAlchemyUserRepository

CREATED_AT = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)


def new_user(**changes) -> NewUser:
    data = {
        "dni": "71234567",
        "first_names": "Fabricio",
        "last_names": "Aguilar",
        "username": "F71234567",
        "password_hash": "hash-de-prueba",
        "role_id": 3,
        "created_at": CREATED_AT,
    }
    data.update(changes)
    return NewUser(**data)


@pytest.fixture
def repository(db_session):
    return SqlAlchemyUserRepository(db_session)


def stored(db_session, user_id) -> Usuario:
    db_session.expire_all()
    return db_session.execute(select(Usuario).where(Usuario.id_usuario == user_id)).scalar_one()


def test_list_roles_returns_the_roles_in_order(repository):
    assert repository.list_roles() == [
        Role(1, "Administrador"),
        Role(2, "Almacenero"),
        Role(3, "Operario"),
    ]


def test_role_exists(repository):
    assert repository.role_exists(1) is True
    assert repository.role_exists(99) is False


def test_add_stores_an_active_user_and_returns_it_with_its_role(repository, db_session):
    user = repository.add(new_user())

    assert user.user_id > 0
    assert (user.dni, user.username) == ("71234567", "F71234567")
    assert (user.first_names, user.last_names) == ("Fabricio", "Aguilar")
    assert user.is_active is True
    assert (user.role_id, user.role_name) == (3, "Operario")

    row = stored(db_session, user.user_id)
    assert row.password_hash == "hash-de-prueba"
    assert row.estado is True
    assert row.fecha_creacion.replace(tzinfo=timezone.utc) == CREATED_AT


def test_add_rejects_a_duplicate_dni_and_leaves_the_session_usable(repository):
    repository.add(new_user())
    with pytest.raises(DuplicateDniError):
        repository.add(new_user(first_names="Otra", username="O71234567"))
    # Tras el error la sesión sigue sirviendo y solo existe el primer usuario.
    assert [user.username for user in repository.list_users()] == ["F71234567"]


def test_dni_exists(repository):
    repository.add(new_user())
    assert repository.dni_exists("71234567") is True
    assert repository.dni_exists("70000000") is False


def test_find_by_id_returns_none_for_an_unknown_user(repository):
    assert repository.find_by_id(404) is None


def test_list_users_returns_every_user_in_creation_order(repository):
    first = repository.add(new_user())
    second = repository.add(new_user(dni="70000002", username="A70000002", first_names="Ana", role_id=1))
    assert repository.list_users() == [first, second]
    assert repository.find_by_id(second.user_id).role_name == "Administrador"


def test_update_changes_only_the_fields_that_were_sent(repository, db_session):
    user = repository.add(new_user())

    updated = repository.update(user.user_id, UserChanges(first_names="Fabio", role_id=2))

    assert (updated.first_names, updated.last_names) == ("Fabio", "Aguilar")
    assert (updated.role_id, updated.role_name) == (2, "Almacenero")
    assert (updated.dni, updated.username, updated.is_active) == ("71234567", "F71234567", True)
    assert stored(db_session, user.user_id).password_hash == "hash-de-prueba"


def test_update_replaces_the_password_hash_and_the_state(repository, db_session):
    user = repository.add(new_user())

    updated = repository.update(user.user_id, UserChanges(password_hash="hash-nuevo", is_active=False))

    assert updated.is_active is False
    row = stored(db_session, user.user_id)
    assert row.password_hash == "hash-nuevo"
    assert row.estado is False


def test_update_without_changes_returns_the_same_user(repository):
    user = repository.add(new_user())
    assert repository.update(user.user_id, UserChanges()) == user


def test_update_unknown_user_raises_not_found(repository):
    with pytest.raises(UserNotFoundError):
        repository.update(404, UserChanges(first_names="Nadie"))


def test_domain_user_never_carries_the_password_hash(repository):
    user = repository.add(new_user())
    assert "hash-de-prueba" not in repr(user)
    assert not hasattr(user, "password_hash")
