"""Creación de la primera cuenta de Administrador sobre una base de prueba."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete

from app.models import Rol
from app.modules.users.application.dto import CreateUserData
from app.modules.users.domain.errors import DuplicateDniError, InvalidUserDataError
from app.modules.users.infrastructure.sqlalchemy_user_repository import SqlAlchemyUserRepository
from app.shared.security import hash_password
from scripts import create_first_admin as script
from scripts.create_first_admin import FirstAdminError, create_first_admin

PASSWORD = "clave-segura-1"


def data(**changes) -> CreateUserData:
    values = {
        "first_names": "Álvaro",
        "last_names": "Rojas Paz",
        "dni": "71234567",
        "password": PASSWORD,
        "role_id": 0,
    }
    values.update(changes)
    return CreateUserData(**values)


@pytest.fixture
def repository(db_session):
    return SqlAlchemyUserRepository(db_session)


def create(repository, **changes):
    return create_first_admin(
        data(**changes),
        repository=repository,
        hash_password=hash_password,
        now=lambda: datetime.now(timezone.utc),
    )


def test_creates_an_active_administrator_with_the_generated_username(repository):
    user = create(repository)

    assert user.username == "A71234567"
    assert user.role_name == "Administrador"
    assert user.is_active is True


def test_always_assigns_the_administrator_role(repository):
    # Aunque los datos traigan otro rol, la cuenta creada es de Administrador.
    assert create(repository, role_id=3).role_name == "Administrador"


def test_created_administrator_can_sign_in_and_manage_users(repository, client):
    create(repository)

    login = client.post("/api/auth/login", json={"username": "a71234567", "password": PASSWORD})
    assert login.status_code == 200
    assert login.json()["usuario"]["rol"] == "Administrador"

    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/api/users", headers=headers).status_code == 200


def test_refuses_when_an_active_administrator_already_exists(repository, create_user):
    create_user("F70000001", "Administrador")

    with pytest.raises(FirstAdminError, match="Ya existe un Administrador activo"):
        create(repository)
    assert len(repository.list_users()) == 1


def test_allows_creation_when_the_only_administrator_is_inactive(repository, create_user):
    create_user("F70000001", "Administrador", active=False)
    assert create(repository).is_active is True


def test_other_roles_do_not_count_as_administrators(repository, create_user):
    create_user("B70000002", "Almacenero")
    assert create(repository).role_name == "Administrador"


def test_fails_when_the_administrator_role_is_missing(repository, db_session):
    db_session.execute(delete(Rol).where(Rol.nombre == "Administrador"))
    db_session.commit()

    with pytest.raises(FirstAdminError, match="seed.py"):
        create(repository)
    assert repository.list_users() == []


@pytest.mark.parametrize("changes", [{"dni": "123"}, {"first_names": "9lvaro"}, {"password": "corta"}])
def test_applies_the_same_rules_as_the_users_screen(repository, changes):
    with pytest.raises(InvalidUserDataError):
        create(repository, **changes)
    assert repository.list_users() == []


def test_rejects_a_dni_that_is_already_registered(repository, create_user):
    create_user("B71234567", "Almacenero")
    with pytest.raises(DuplicateDniError):
        create(repository)


# --- Comando interactivo ---

@pytest.fixture
def command(monkeypatch, session_factory):
    """Ejecuta main() contra la base de prueba con respuestas simuladas."""
    import app.shared.database as database

    def run(answers, passwords):
        answers, passwords = iter(answers), iter(passwords)
        monkeypatch.setattr(database, "SessionLocal", session_factory)
        monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
        monkeypatch.setattr(script.getpass, "getpass", lambda prompt="": next(passwords))
        return script.main()

    return run


def stored_users(session_factory):
    with session_factory() as db:
        return SqlAlchemyUserRepository(db).list_users()


def test_command_creates_the_account_after_confirmation(command, session_factory, capsys):
    exit_code = command(["CREAR", "Álvaro", "Rojas", "71234567"], [PASSWORD, PASSWORD])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "A71234567" in output
    assert PASSWORD not in output
    assert [user.username for user in stored_users(session_factory)] == ["A71234567"]


def test_command_does_nothing_without_the_confirmation_word(command, session_factory, capsys):
    assert command(["no"], []) == 1
    assert "Cancelado" in capsys.readouterr().out
    assert stored_users(session_factory) == []


def test_command_stops_when_the_passwords_do_not_match(command, session_factory, capsys):
    exit_code = command(["CREAR", "Álvaro", "Rojas", "71234567"], [PASSWORD, "otra-clave-22"])

    assert exit_code == 1
    assert "no coinciden" in capsys.readouterr().out
    assert stored_users(session_factory) == []


def test_command_reports_invalid_data_without_a_traceback(command, session_factory, capsys):
    exit_code = command(["CREAR", "Álvaro", "Rojas", "123"], [PASSWORD, PASSWORD])

    assert exit_code == 1
    assert "8 dígitos" in capsys.readouterr().out
    assert stored_users(session_factory) == []
