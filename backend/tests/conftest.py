"""Configuración común de las pruebas: nunca usan la base ni la clave reales."""
import os
import secrets

# Se fijan antes de importar la aplicación. Como load_dotenv() no reemplaza
# variables ya definidas, ninguna prueba llega a leer el backend/.env local.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["TOKEN_MINUTOS"] = "480"

from datetime import datetime, timezone  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import CheckConstraint, MetaData, create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

ROLE_IDS = {"Administrador": 1, "Almacenero": 2, "Operario": 3}


@pytest.fixture(scope="session")
def password() -> str:
    """Contraseña aleatoria de las cuentas de prueba; cambia en cada ejecución."""
    return secrets.token_urlsafe(16)


@pytest.fixture(scope="session")
def password_hash(password) -> str:
    # Se calcula una sola vez: bcrypt es lento a propósito.
    from app.shared.security import hash_password

    return hash_password(password)


@pytest.fixture
def session_factory():
    """Base SQLite en memoria con las tablas usuarios y roles del modelo real.

    Las tablas se copian de app.models para que las pruebas sigan al modelo.
    Se omiten las restricciones CHECK porque usan sintaxis propia de PostgreSQL.
    """
    from app.models import Rol, Usuario

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata = MetaData()
    for table in (Rol.__table__, Usuario.__table__):
        copy = table.to_metadata(metadata)
        for constraint in [c for c in copy.constraints if isinstance(c, CheckConstraint)]:
            copy.constraints.discard(constraint)
    metadata.create_all(engine)

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        db.add_all([Rol(id_rol=role_id, nombre=name) for name, role_id in ROLE_IDS.items()])
        db.commit()
    yield factory
    engine.dispose()


@pytest.fixture
def db_session(session_factory) -> Session:
    with session_factory() as db:
        yield db


@pytest.fixture
def create_user(session_factory, password_hash):
    """Crea una cuenta de prueba y devuelve su id."""
    from app.models import Usuario

    def _create_user(
        username: str,
        role: str = "Operario",
        *,
        active: bool = True,
        first_names: str = "Persona",
        last_names: str = "De Prueba",
        stored_hash: str | None = None,
    ) -> int:
        with session_factory() as db:
            user = Usuario(
                dni=username[1:],
                nombres=first_names,
                apellidos=last_names,
                usuario=username,
                password_hash=stored_hash or password_hash,
                estado=active,
                fecha_creacion=datetime.now(timezone.utc),
                id_rol=ROLE_IDS[role],
            )
            db.add(user)
            db.commit()
            return user.id_usuario

    return _create_user


@pytest.fixture
def client(session_factory):
    """Cliente HTTP de la aplicación conectado a la base de prueba."""
    from fastapi.testclient import TestClient

    from app.modules.authentication.presentation.dependencies import get_database_session
    from main import app

    def override_database_session():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_database_session] = override_database_session
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_database_session, None)
