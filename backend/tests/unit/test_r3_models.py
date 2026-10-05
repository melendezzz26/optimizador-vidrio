"""Contrato vigente R3 y preservación estructural de las entidades anteriores."""

import importlib.util

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from tests.model_contracts import BACKEND, historical_metadata

R3 = "a3c4d5e6f7b8"
EXPECTED = {
    "optimizaciones": {
        "id_optimizacion": "INTEGER", "fecha_inicio": "TIMESTAMP WITH TIME ZONE",
        "fecha_fin": "TIMESTAMP WITH TIME ZONE", "estado": "VARCHAR(20)",
        "id_pedido": "INTEGER", "id_configuracion": "INTEGER", "id_usuario_ejecutor": "INTEGER",
        "criterio_seleccion_version": "VARCHAR(20)", "id_ejecucion_seleccionada": "INTEGER",
    },
    "ejecuciones_optimizacion": {
        "id_ejecucion": "INTEGER", "id_optimizacion": "INTEGER", "metodo": "VARCHAR(10)",
        "fecha_inicio": "TIMESTAMP WITH TIME ZONE", "fecha_fin": "TIMESTAMP WITH TIME ZONE",
        "estado": "VARCHAR(20)", "completo": "BOOLEAN", "patron_resultado": "JSONB",
    },
    "materiales_utilizados": {
        "id_material_utilizado": "INTEGER", "id_ejecucion": "INTEGER", "id_plancha": "INTEGER",
        "id_retazo": "INTEGER", "cantidad_utilizada": "INTEGER",
    },
}


@pytest.fixture(scope="module")
def metadata():
    return historical_metadata(R3)


@pytest.mark.parametrize("name", EXPECTED)
def test_r3_columns_types_nullability_defaults_and_primary_keys(metadata, name):
    table = metadata.tables[name]
    assert {c.name: c.type.compile(dialect=postgresql.dialect()) for c in table.c} == EXPECTED[name]
    nullable = {
        "optimizaciones": {"fecha_fin", "id_ejecucion_seleccionada"},
        "ejecuciones_optimizacion": {"fecha_fin", "patron_resultado"},
        "materiales_utilizados": {"id_plancha", "id_retazo"},
    }
    assert {c.name for c in table.c if c.nullable} == nullable[name]
    assert list(table.primary_key.columns.keys()) == [next(iter(EXPECTED[name]))]
    assert all(c.default is None and c.onupdate is None for c in table.c)
    assert {c.name for c in table.c if c.server_default is not None} == (
        {"cantidad_utilizada"} if name == "materiales_utilizados" else set()
    )
    if name == "materiales_utilizados":
        assert table.c.cantidad_utilizada.server_default.arg == "1"


@pytest.mark.parametrize("name", EXPECTED)
def test_r3_exact_constraints_and_indexes(metadata, name):
    table = metadata.tables[name]
    fks = {
        "optimizaciones": {
            ("id_pedido", "pedidos.id_pedido"), ("id_configuracion", "configuraciones.id_configuracion"),
            ("id_usuario_ejecutor", "usuarios.id_usuario"), ("id_ejecucion_seleccionada", "ejecuciones_optimizacion.id_ejecucion"),
        },
        "ejecuciones_optimizacion": {("id_optimizacion", "optimizaciones.id_optimizacion")},
        "materiales_utilizados": {
            ("id_ejecucion", "ejecuciones_optimizacion.id_ejecucion"),
            ("id_plancha", "planchas.id_plancha"), ("id_retazo", "retazos.id_retazo"),
        },
    }
    checks = {
        "optimizaciones": {"estado IN ('EN_EJECUCION', 'COMPLETADA', 'SIN_SOLUCION', 'FALLIDA')"},
        "ejecuciones_optimizacion": {"metodo IN ('FF', 'BF', 'WF')", "estado IN ('EN_EJECUCION', 'COMPLETADA', 'FALLIDA')"},
        "materiales_utilizados": {"cantidad_utilizada > 0", "(id_plancha IS NOT NULL) <> (id_retazo IS NOT NULL)"},
    }
    indexes = {"optimizaciones": {("id_pedido", "fecha_inicio")}, "materiales_utilizados": {("id_ejecucion",)}}
    assert {(f.parent.name, f.target_fullname) for f in table.foreign_keys} == fks[name]
    assert all(f.ondelete is None and f.onupdate is None and f.deferrable is None for f in table.foreign_keys)
    assert {str(c.sqltext) for c in table.constraints if isinstance(c, sa.CheckConstraint)} == checks[name]
    assert {tuple(c.columns.keys()) for c in table.constraints if isinstance(c, sa.UniqueConstraint)} == (
        {("id_optimizacion", "metodo")} if name == "ejecuciones_optimizacion" else set()
    )
    assert {tuple(i.columns.keys()) for i in table.indexes} == indexes.get(name, set())
    assert all(not i.unique for i in table.indexes)


def test_r3_cycle_and_total_metadata(metadata):
    assert len(metadata.tables) == 12
    assert sum(len(t.c) for t in metadata.tables.values()) == 86
    selected = next(iter(metadata.tables["optimizaciones"].c.id_ejecucion_seleccionada.foreign_keys))
    assert selected.name == "fk_optimizaciones_ejecucion_seleccionada"
    assert selected.use_alter
    assert selected.column is metadata.tables["ejecuciones_optimizacion"].c.id_ejecucion
    owner = next(iter(metadata.tables["ejecuciones_optimizacion"].c.id_optimizacion.foreign_keys))
    assert owner.name == "ejecuciones_optimizacion_id_optimizacion_fkey"
    # La ordenación DDL no produce advertencias por un ciclo sin resolver.
    assert len(metadata.sorted_tables) == 12


def _signature(table, omit_origin=False):
    omit = {"id_ejecucion_origen"} if omit_origin else set()
    def default(c):
        arg = getattr(c.default, "arg", None)
        return getattr(arg, "__name__", arg)
    return {
        "columns": [(c.name, str(c.type), c.nullable, c.primary_key, default(c),
                     str(c.server_default.arg) if c.server_default else None, c.onupdate)
                    for c in table.c if c.name not in omit],
        "checks": {(c.name, str(c.sqltext)) for c in table.constraints if isinstance(c, sa.CheckConstraint)},
        "uniques": {tuple(c.columns.keys()) for c in table.constraints if isinstance(c, sa.UniqueConstraint)},
        "fks": {(f.parent.name, f.target_fullname, f.ondelete, f.onupdate) for f in table.foreign_keys if f.parent.name not in omit},
        "indexes": {(i.name, tuple(i.columns.keys()), i.unique) for i in table.indexes},
    }


def test_r3_preserves_other_entities_and_only_adds_retazo_origin(metadata):
    old = historical_metadata("f2b3c4d5e6a7")
    for name, table in old.tables.items():
        if name != "ejecuciones_optimizacion":
            assert _signature(metadata.tables[name], omit_origin=name == "retazos") == _signature(table)
    retazo = metadata.tables["retazos"]
    assert len(retazo.c) == 9
    origin = retazo.c.id_ejecucion_origen
    assert isinstance(origin.type, sa.Integer) and origin.nullable
    assert origin.default is None and origin.server_default is None
    assert {f.target_fullname for f in origin.foreign_keys} == {"ejecuciones_optimizacion.id_ejecucion"}


def test_r3_revision_chain_and_explicit_downgrade_failure():
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    scripts = ScriptDirectory.from_config(config)

    revision = scripts.get_revision(R3)

    assert revision is not None
    assert revision.down_revision == "f2b3c4d5e6a7"

    assert [
        item.revision
        for item in scripts.iterate_revisions(R3, "base")
    ] == [
        R3,
        "f2b3c4d5e6a7",
        "e1a2b3c4d5f6",
        "c4e8a1f2b3d5",
        "9b9f04eb67f6",
    ]

    spec = importlib.util.spec_from_file_location(
        "r3_revision",
        revision.path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(
        RuntimeError,
        match="no admite reversión automática",
    ):
        module.downgrade()