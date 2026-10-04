"""Contrato CONFIGURACION v1.1: metadata sin motor ni conexión a BD."""

import importlib.util
from pathlib import Path
import runpy
import sys
from types import ModuleType
from unittest.mock import patch

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base

BACKEND = Path(__file__).resolve().parents[2]
R2 = "f2b3c4d5e6a7"


@pytest.fixture(scope="module")
def metadata():
    database = ModuleType("app.shared.database")
    database.Base = declarative_base()
    with patch.dict(sys.modules, {"app.shared.database": database}):
        runpy.run_path(str(BACKEND / "app/models.py"))
    return database.Base.metadata


def test_r2_exact_columns_types_nullability_and_defaults(metadata):
    table = metadata.tables["configuraciones"]
    dialect = postgresql.dialect()
    expected = {
        "id_configuracion": "INTEGER", "version": "INTEGER",
        "separacion_mm": "NUMERIC(8, 2)", "margen_mm": "NUMERIC(8, 2)",
        "resolucion_raster_mm": "NUMERIC(8, 3)", "paso_angular_grados": "NUMERIC(6, 2)",
        "ancho_min_retazo_mm": "NUMERIC(10, 2)", "alto_min_retazo_mm": "NUMERIC(10, 2)",
        "vigente": "BOOLEAN", "id_usuario_creacion": "INTEGER",
        "fecha_creacion": "TIMESTAMP WITH TIME ZONE",
    }
    assert {c.name: c.type.compile(dialect=dialect) for c in table.c} == expected
    assert len(table.c) == 11
    assert {c.name for c in table.c if c.nullable} == {"paso_angular_grados"}
    assert {c.name for c in table.c if c.server_default is not None} == {"vigente"}
    assert str(table.c.vigente.server_default.arg.compile(dialect=dialect)) == "true"
    assert all(c.default is None and c.onupdate is None for c in table.c)
    assert not {"resolucion_raster", "paso_angular", "area_minima_retazo",
                "dimension_minima_retazo", "fecha_actualizacion"} & set(table.c.keys())


def test_r2_exact_constraints_without_additional_indexes(metadata):
    table = metadata.tables["configuraciones"]
    assert list(table.primary_key.columns.keys()) == ["id_configuracion"]
    assert {tuple(c.columns.keys()) for c in table.constraints if isinstance(c, sa.UniqueConstraint)} == {("version",)}
    assert {(fk.parent.name, fk.target_fullname) for fk in table.foreign_keys} == {("id_usuario_creacion", "usuarios.id_usuario")}
    assert all(fk.ondelete is None and fk.onupdate is None for fk in table.foreign_keys)
    assert not table.indexes
    assert {str(c.sqltext) for c in table.constraints if isinstance(c, sa.CheckConstraint)} == {
        "version > 0", "separacion_mm >= 0", "margen_mm >= 0", "resolucion_raster_mm > 0",
        "paso_angular_grados > 0 AND paso_angular_grados <= 360",
        "ancho_min_retazo_mm >= 0", "alto_min_retazo_mm >= 0",
    }


def test_r2_metadata_scope_and_incoming_reference(metadata):
    assert len(metadata.tables) == 10
    assert sum(len(t.c) for t in metadata.tables.values()) == 71
    incoming = {(t.name, fk.parent.name) for t in metadata.tables.values()
                for fk in t.foreign_keys if fk.target_fullname == "configuraciones.id_configuracion"}
    assert incoming == {("ejecuciones_optimizacion", "id_configuracion")}
    assert "id_ejecucion_origen" not in metadata.tables["retazos"].c


def test_r2_has_one_linear_head_and_explicit_irreversible_downgrade():
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == [R2]
    assert [r.revision for r in scripts.walk_revisions()] == [
        R2, "e1a2b3c4d5f6", "c4e8a1f2b3d5", "9b9f04eb67f6",
    ]
    spec = importlib.util.spec_from_file_location(
        "r2_revision", BACKEND / "alembic/versions/f2b3c4d5e6a7_r2_configuracion_versionada.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Llamada Python sin contexto/conexión Alembic: debe fallar antes de tocar BD.
    with pytest.raises(RuntimeError, match="no admite reversión automática"):
        module.downgrade()
