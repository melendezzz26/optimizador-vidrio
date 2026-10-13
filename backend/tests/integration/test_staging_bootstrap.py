"""Ensayo completo local de la cadena aprobada y seed; jamás un destino remoto."""
import os
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from .postgres_support import BACKEND, _run, new_database, upgrade


def test_single_integrated_head_and_complete_history():
    config = Config(str(BACKEND / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["ta036a1b2c3d"]
    chain = list(scripts.walk_revisions())
    assert len(chain) == 11
    assert chain[-1].down_revision is None
    assert all(not revision.is_merge_point for revision in chain)


def test_full_upgrade_current_and_idempotent_roles(isolated_postgres, monkeypatch):
    import seed
    with new_database(isolated_postgres) as engine:
        assert engine.url.host == "127.0.0.1" and engine.url.username == "r1_test"
        environment = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False), "PYTHON_DOTENV_DISABLED": "1"}
        def current():
            result = _run([sys.executable, "-B", "-m", "alembic", "current"], cwd=BACKEND, env=environment)
            assert result.returncode == 0, result.stderr
            return result.stdout.strip()
        assert current() == ""
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        assert current() == "ta036a1b2c3d (head)"
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT count(*) FROM tipos_vidrio").scalar_one() == 6
            assert connection.exec_driver_sql("SELECT count(*) FROM tipos_vidrio_espesores").scalar_one() == 28
            assert connection.exec_driver_sql("SELECT count(*) FROM usuarios").scalar_one() == 0
        monkeypatch.setattr(seed, "SessionLocal", sessionmaker(bind=engine))
        seed.crear_roles()
        with engine.connect() as connection:
            before = connection.execute(sa.text("SELECT id_rol,nombre,descripcion FROM roles ORDER BY id_rol")).all()
        assert {row.nombre for row in before} == {"Administrador", "Almacenero", "Operario"}
        seed.crear_roles()
        result = upgrade(engine, "head")
        assert result.returncode == 0, result.stderr
        with engine.connect() as connection:
            assert connection.execute(sa.text("SELECT id_rol,nombre,descripcion FROM roles ORDER BY id_rol")).all() == before
        assert current() == "ta036a1b2c3d (head)"
