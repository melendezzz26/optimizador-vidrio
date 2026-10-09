"""Pruebas de la estructura de persistencia sin conexiones a bases de datos."""
import json
import os
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

import pytest


@pytest.fixture(scope="module")
def database_structure():
    # Un proceso nuevo evita reutilizar imports o alterar otras pruebas.
    script = dedent("""\
        import json
        from unittest.mock import patch

        from sqlalchemy import MetaData
        from sqlalchemy.engine import Engine
        from sqlalchemy.orm import sessionmaker

        with (
            patch("dotenv.load_dotenv", return_value=False),
            patch.object(Engine, "connect", side_effect=AssertionError("Conexion no permitida")),
            patch.object(Engine, "raw_connection", side_effect=AssertionError("Conexion no permitida")),
        ):
            from app.shared.database import Base, SessionLocal, engine
            from app import models

            print(json.dumps({
                "base_exported": isinstance(Base.metadata, MetaData),
                "session_factory_exported": isinstance(SessionLocal, sessionmaker),
                "engine_exported": isinstance(engine, Engine),
                "same_base": models.Base is Base,
                "tables": sorted(Base.metadata.tables),
            }))
        """)
    environment = {**os.environ, "DATABASE_URL": "sqlite:///:memory:"}
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


def test_database_exports_are_available(database_structure):
    assert database_structure["base_exported"]
    assert database_structure["session_factory_exported"]
    assert database_structure["engine_exported"]


def test_models_use_the_exported_base(database_structure):
    assert database_structure["same_base"]


def test_importing_models_registers_all_current_tables(database_structure):
    assert set(database_structure["tables"]) == {
        "clientes",
        "configuraciones",
        "ejecuciones_optimizacion",
        "metricas_ejecucion",
        "optimizaciones",
        "materiales_utilizados",
        "pedidos",
        "piezas",
        "planchas",
        "retazos",
        "roles",
        "tipos_vidrio",
        "tipos_vidrio_espesores",
        "usuarios",
    }
