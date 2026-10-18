"""S1-RBAC: migración de permisos en PostgreSQL temporal, solo con datos sintéticos."""
import os
import sys

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from tests.integration.postgres_support import BACKEND, _run, new_database, upgrade
from tests.model_contracts import historical_metadata

PREVIOUS = "ta036a1b2c3d"
REVISION = "s1rbac01a2b3"

ASSIGNMENT_SQL = sa.text(
    "SELECT r.nombre, p.codigo FROM rol_permisos rp "
    "JOIN roles r ON r.id_rol = rp.id_rol JOIN permisos p ON p.id_permiso = rp.id_permiso"
)


def downgrade(engine, revision):
    assert engine.url.host == "127.0.0.1" and engine.url.username == "r1_test"
    environment = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False),
                   "PYTHON_DOTENV_DISABLED": "1", "PYTHONIOENCODING": "utf-8"}
    return _run([sys.executable, "-B", "-m", "alembic", "downgrade", revision], cwd=BACKEND, env=environment)


def assignment(connection):
    result = {}
    for role, code in connection.execute(ASSIGNMENT_SQL):
        result.setdefault(role, set()).add(code)
    return result


def expected_assignment():
    from app.core.permissions import ASIGNACION_INICIAL
    return {role: set(codes) for role, codes in ASIGNACION_INICIAL.items()}


def test_revision_is_chained_after_ta036():
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    assert ScriptDirectory.from_config(config).get_revision(REVISION).down_revision == PREVIOUS


def test_upgrade_with_existing_roles_loads_catalog_and_initial_assignment(isolated_postgres):
    """Caso Supabase: los roles ya existen cuando se aplica la migración."""
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        with engine.begin() as connection:
            connection.execute(sa.text(
                "INSERT INTO roles(nombre) VALUES ('Administrador'), ('Almacenero'), ('Operario')"
            ))
        result = upgrade(engine, REVISION)
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT count(*) FROM permisos")) == 13
            assert assignment(connection) == expected_assignment()


def test_schema_matches_current_models(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, REVISION).returncode == 0
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection, opts={
                "compare_type": True, "compare_server_default": True,
            }), historical_metadata(REVISION)) == []


@pytest.mark.parametrize("code, module", [
    ("Users.View", "users"),       # mayúsculas
    ("users", "users"),            # sin acción
    ("users.view.all", "users"),   # más de un punto
    ("orders.view", "users"),      # el módulo no coincide con el código
])
def test_check_constraints_reject_invalid_codes(isolated_postgres, code, module):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, REVISION).returncode == 0
        with engine.begin() as connection, pytest.raises(sa.exc.IntegrityError):
            connection.execute(sa.text(
                "INSERT INTO permisos(codigo, modulo, descripcion) VALUES (:code, :module, 'Inválido')"
            ), {"code": code, "module": module})


def test_duplicate_assignment_is_rejected_and_deleting_a_role_cascades(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        with engine.begin() as connection:
            connection.execute(sa.text("INSERT INTO roles(nombre) VALUES ('Almacenero')"))
        assert upgrade(engine, REVISION).returncode == 0
        with engine.begin() as connection, pytest.raises(sa.exc.IntegrityError):
            connection.execute(sa.text(
                "INSERT INTO rol_permisos(id_rol, id_permiso) SELECT r.id_rol, p.id_permiso "
                "FROM roles r, permisos p WHERE r.nombre='Almacenero' AND p.codigo='inventory.view'"
            ))
        with engine.begin() as connection:
            connection.execute(sa.text("DELETE FROM roles WHERE nombre='Almacenero'"))
            assert connection.scalar(sa.text("SELECT count(*) FROM rol_permisos")) == 0


def test_empty_database_then_seed_completes_assignment(isolated_postgres, monkeypatch):
    """Base nueva: la migración no encuentra roles; seed.py los crea y asigna los permisos."""
    import seed
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, "head").returncode == 0
        with engine.connect() as connection:
            assert connection.scalar(sa.text("SELECT count(*) FROM permisos")) == 13
            assert connection.scalar(sa.text("SELECT count(*) FROM rol_permisos")) == 0
        monkeypatch.setattr(seed, "SessionLocal", sessionmaker(bind=engine))
        seed.crear_roles()
        seed.crear_roles()
        with engine.connect() as connection:
            assert assignment(connection) == expected_assignment()


def test_downgrade_removes_tables_and_reupgrade_works(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, REVISION).returncode == 0
        result = downgrade(engine, PREVIOUS)
        assert result.returncode == 0, result.stderr
        tables = set(sa.inspect(engine).get_table_names())
        assert not tables & {"permisos", "rol_permisos"}
        assert "roles" in tables
        result = upgrade(engine, REVISION)
        assert result.returncode == 0, result.stderr