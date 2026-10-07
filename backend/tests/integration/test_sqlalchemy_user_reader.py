"""Lector de cuentas sobre una base SQLite en memoria (SPEC-HU-001, sección 10).

No usa PostgreSQL ni la base compartida: las tablas se crean en cada prueba.
"""
from sqlalchemy import delete

from app.models import Rol
from app.modules.authentication.domain.username import Username
from app.modules.authentication.infrastructure.sqlalchemy_user_reader import SqlAlchemyUserReader


def test_find_by_username_returns_the_account_with_its_role(db_session, create_user, password_hash):
    user_id = create_user("F71234567", "Administrador", first_names="Fabiola", last_names="Quispe")

    account = SqlAlchemyUserReader(db_session).find_by_username(Username("F71234567"))

    assert account.user_id == user_id
    assert account.username == "F71234567"
    assert account.full_name == "Fabiola Quispe"
    assert account.role == "Administrador"
    assert account.is_active is True
    assert account.password_hash == password_hash


def test_find_by_username_returns_none_when_the_user_does_not_exist(db_session, create_user):
    create_user("F71234567")
    assert SqlAlchemyUserReader(db_session).find_by_username(Username("A70000000")) is None


def test_username_stored_in_lowercase_is_not_found(db_session, create_user):
    # Nota N-02 de la SPEC: una cuenta registrada en minúsculas no puede iniciar sesión.
    create_user("f71234567")
    assert SqlAlchemyUserReader(db_session).find_by_username(Username("F71234567")) is None


def test_find_by_username_reports_an_inactive_account(db_session, create_user):
    create_user("I70000004", active=False)
    account = SqlAlchemyUserReader(db_session).find_by_username(Username("I70000004"))
    assert account.is_active is False


def test_find_by_id_returns_the_account(db_session, create_user):
    user_id = create_user("O70000003", "Operario")
    account = SqlAlchemyUserReader(db_session).find_by_id(user_id)
    assert account.username == "O70000003"
    assert account.role == "Operario"


def test_find_by_id_returns_none_when_the_user_does_not_exist(db_session):
    assert SqlAlchemyUserReader(db_session).find_by_id(999) is None


def test_account_without_an_existing_role_is_not_returned(db_session, create_user):
    user_id = create_user("O70000003", "Operario")
    db_session.execute(delete(Rol).where(Rol.nombre == "Operario"))
    db_session.commit()

    reader = SqlAlchemyUserReader(db_session)
    assert reader.find_by_username(Username("O70000003")) is None
    assert reader.find_by_id(user_id) is None


def test_reader_picks_only_the_requested_account(db_session, create_user):
    create_user("A70000001", "Administrador")
    create_user("B70000002", "Almacenero")
    account = SqlAlchemyUserReader(db_session).find_by_username(Username("B70000002"))
    assert account.username == "B70000002"
    assert account.role == "Almacenero"
