"""Contrato vigente R4 de METRICA_EJECUCION y modelo v1.1 completo."""

import importlib.util

from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from tests.model_contracts import BACKEND, current_metadata, historical_metadata


R3 = "a3c4d5e6f7b8"
R4 = "b4d5e6f7a8c9"

EXPECTED_METRICA = {
    "id_metrica": "INTEGER",
    "id_ejecucion": "INTEGER",
    "area_material_total_mm2": "NUMERIC(18, 2)",
    "area_piezas_colocadas_mm2": "NUMERIC(18, 2)",
    "aprovechamiento_pct": "NUMERIC(6, 3)",
    "merma_mm2": "NUMERIC(18, 2)",
    "retazo_recuperable_mm2": "NUMERIC(18, 2)",
    "planchas_nuevas_usadas": "INTEGER",
    "tiempo_computacional_ms": "BIGINT",
    "memoria_pico_mb": "NUMERIC(12, 3)",
    "tiempo_cpu_ms": "BIGINT",
}

EXPECTED_CHECKS = {
    "area_material_total_mm2 > 0",
    "area_piezas_colocadas_mm2 >= 0",
    "aprovechamiento_pct >= 0 AND aprovechamiento_pct <= 100",
    "merma_mm2 >= 0",
    "retazo_recuperable_mm2 >= 0",
    "planchas_nuevas_usadas >= 0",
    "tiempo_computacional_ms >= 0",
    "memoria_pico_mb >= 0",
    "tiempo_cpu_ms >= 0",
}


@pytest.fixture(scope="module")
def metadata():
    return current_metadata()


def _default(column):
    arg = getattr(column.default, "arg", None)
    return getattr(arg, "__name__", arg)


def _signature(table):
    return {
        "columns": [
            (
                column.name,
                column.type.compile(dialect=postgresql.dialect()),
                column.nullable,
                column.primary_key,
                _default(column),
                str(column.server_default.arg)
                if column.server_default is not None
                else None,
                column.onupdate,
            )
            for column in table.c
        ],
        "checks": {
            (constraint.name, str(constraint.sqltext))
            for constraint in table.constraints
            if isinstance(constraint, sa.CheckConstraint)
        },
        "uniques": {
            tuple(constraint.columns.keys())
            for constraint in table.constraints
            if isinstance(constraint, sa.UniqueConstraint)
        },
        "fks": {
            (
                fk.parent.name,
                fk.target_fullname,
                fk.ondelete,
                fk.onupdate,
                fk.deferrable,
            )
            for fk in table.foreign_keys
        },
        "indexes": {
            (index.name, tuple(index.columns.keys()), index.unique)
            for index in table.indexes
        },
    }


def test_r4_metric_columns_types_and_count(metadata):
    table = metadata.tables["metricas_ejecucion"]

    assert {
        column.name: column.type.compile(dialect=postgresql.dialect())
        for column in table.c
    } == EXPECTED_METRICA

    assert len(table.c) == 11


def test_r4_metric_nullability_primary_key_and_defaults(metadata):
    table = metadata.tables["metricas_ejecucion"]

    assert {
        column.name for column in table.c if column.nullable
    } == {
        "memoria_pico_mb",
        "tiempo_cpu_ms",
    }

    assert list(table.primary_key.columns.keys()) == ["id_metrica"]

    assert all(column.default is None for column in table.c)
    assert all(column.server_default is None for column in table.c)
    assert all(column.onupdate is None for column in table.c)


def test_r4_metric_fk_and_unique(metadata):
    table = metadata.tables["metricas_ejecucion"]

    assert {
        (fk.parent.name, fk.target_fullname)
        for fk in table.foreign_keys
    } == {
        ("id_ejecucion", "ejecuciones_optimizacion.id_ejecucion"),
    }

    fk = next(iter(table.foreign_keys))

    assert fk.ondelete is None
    assert fk.onupdate is None
    assert fk.deferrable is None

    assert {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, sa.UniqueConstraint)
    } == {
        ("id_ejecucion",),
    }


def test_r4_metric_exact_checks_and_no_indexes(metadata):
    table = metadata.tables["metricas_ejecucion"]

    assert {
        str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, sa.CheckConstraint)
    } == EXPECTED_CHECKS

    assert len(
        [
            constraint
            for constraint in table.constraints
            if isinstance(constraint, sa.CheckConstraint)
        ]
    ) == 9

    assert not table.indexes


def test_r4_completes_v11_metadata(metadata):
    assert len(metadata.tables) == 12
    assert sum(len(table.c) for table in metadata.tables.values()) == 90
    assert len(metadata.tables["metricas_ejecucion"].c) == 11


def test_r4_changes_only_metricas(metadata):
    r3 = historical_metadata(R3)

    assert set(metadata.tables) == set(r3.tables)

    for name, historical_table in r3.tables.items():
        if name == "metricas_ejecucion":
            continue

        assert _signature(metadata.tables[name]) == _signature(historical_table)


def test_r4_removed_metric_names_are_absent(metadata):
    table = metadata.tables["metricas_ejecucion"]

    assert "planchas_utilizadas" not in table.c
    assert "area_recuperable_mm2" not in table.c

    assert "planchas_nuevas_usadas" in table.c
    assert "retazo_recuperable_mm2" in table.c


def test_r4_has_no_float_metrics(metadata):
    table = metadata.tables["metricas_ejecucion"]

    assert all(
        not isinstance(column.type, sa.Float)
        for column in table.c
    )


def test_r4_is_linear_head_and_downgrade_fails_explicitly():
    config = Config()
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    scripts = ScriptDirectory.from_config(config)

    assert scripts.get_heads() == [R4]

    revision = scripts.get_revision(R4)

    assert revision is not None
    assert revision.down_revision == R3

    assert [item.revision for item in scripts.walk_revisions()] == [
        R4,
        R3,
        "f2b3c4d5e6a7",
        "e1a2b3c4d5f6",
        "c4e8a1f2b3d5",
        "9b9f04eb67f6",
    ]

    spec = importlib.util.spec_from_file_location(
        "r4_revision",
        revision.path,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with pytest.raises(
        RuntimeError,
        match="no admite reversión automática",
    ):
        module.downgrade()