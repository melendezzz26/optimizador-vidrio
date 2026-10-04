"""Contrato R1 contra v1.1: metadata PostgreSQL, sin abrir conexiones."""

from pathlib import Path
import runpy
import sys
from types import ModuleType
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base


@pytest.fixture(scope="module")
def metadata():
    database = ModuleType("app.shared.database")
    database.Base = declarative_base()
    with patch.dict(sys.modules, {"app.shared.database": database}):
        runpy.run_path(str(Path(__file__).resolve().parents[2] / "app/models.py"))
    return database.Base.metadata


# Tipo SQL exacto; solo estos campos admiten NULL en las siete entidades.
EXPECTED = {
    "roles": {"id_rol": "INTEGER", "nombre": "VARCHAR(30)", "descripcion": "VARCHAR(150)"},
    "usuarios": {
        "id_usuario": "INTEGER", "dni": "CHAR(8)", "nombres": "VARCHAR(100)",
        "apellidos": "VARCHAR(100)", "usuario": "VARCHAR(9)", "password_hash": "VARCHAR(255)",
        "estado": "BOOLEAN", "id_rol": "INTEGER", "fecha_creacion": "TIMESTAMP WITH TIME ZONE",
    },
    "tipos_vidrio": {"id_tipo_vidrio": "INTEGER", "nombre": "VARCHAR(100)", "descripcion": "TEXT", "estado": "BOOLEAN"},
    "planchas": {
        "id_plancha": "INTEGER", "ancho_mm": "NUMERIC(10, 2)", "alto_mm": "NUMERIC(10, 2)",
        "espesor_mm": "NUMERIC(4, 1)", "cantidad": "INTEGER", "estado": "BOOLEAN",
        "id_tipo_vidrio": "INTEGER", "fecha_registro": "TIMESTAMP WITH TIME ZONE",
    },
    "retazos": {
        "id_retazo": "INTEGER", "codigo": "VARCHAR(40)", "espesor_mm": "NUMERIC(4, 1)",
        "geometria": "JSONB", "area_mm2": "NUMERIC(18, 2)", "estado": "BOOLEAN",
        "id_tipo_vidrio": "INTEGER", "fecha_registro": "TIMESTAMP WITH TIME ZONE",
    },
    "pedidos": {
        "id_pedido": "INTEGER", "fecha_registro": "TIMESTAMP WITH TIME ZONE", "estado": "VARCHAR(20)",
        "espesor_mm": "NUMERIC(4, 1)", "id_tipo_vidrio": "INTEGER", "id_usuario_registro": "INTEGER",
    },
    "piezas": {
        "id_pieza": "INTEGER", "tipo_forma": "VARCHAR(30)", "cantidad": "INTEGER",
        "dimensiones": "JSONB", "geometria": "JSONB", "area_mm2": "NUMERIC(18, 2)", "id_pedido": "INTEGER",
    },
}
UNIQUES = {
    "roles": {("nombre",)}, "usuarios": {("dni",), ("usuario",)},
    "tipos_vidrio": {("nombre",)}, "retazos": {("codigo",)},
}
FKS = {
    "usuarios": {("id_rol", "roles.id_rol")},
    "planchas": {("id_tipo_vidrio", "tipos_vidrio.id_tipo_vidrio")},
    "retazos": {("id_tipo_vidrio", "tipos_vidrio.id_tipo_vidrio")},
    "pedidos": {("id_tipo_vidrio", "tipos_vidrio.id_tipo_vidrio"), ("id_usuario_registro", "usuarios.id_usuario")},
    "piezas": {("id_pedido", "pedidos.id_pedido")},
}
CHECKS = {
    "usuarios": {"dni ~ '^[0-9]{8}$'", "usuario ~ '^[A-Za-z][0-9]{8}$'"},
    "planchas": {"ancho_mm > 0", "alto_mm > 0", "espesor_mm IN (3, 4, 5.5, 6, 8)", "cantidad >= 0"},
    "retazos": {"espesor_mm IN (3, 4, 5.5, 6, 8)", "area_mm2 > 0"},
    "pedidos": {"espesor_mm IN (3, 4, 5.5, 6, 8)", "estado IN ('PENDIENTE', 'EN_OPTIMIZACION', 'OPTIMIZADO', 'CONFIRMADO', 'CANCELADO')"},
    "piezas": {"cantidad > 0", "area_mm2 > 0", "tipo_forma IN ('RECTANGULO', 'CIRCUNFERENCIA', 'POLIGONO_CONVEXO')"},
}


@pytest.mark.parametrize("name", EXPECTED)
def test_exact_r1_columns_types_nullability_defaults_and_keys(metadata, name):
    table = metadata.tables[name]
    dialect = postgresql.dialect()
    assert {c.name: c.type.compile(dialect=dialect) for c in table.c} == EXPECTED[name]
    for c in table.c:
        assert c.nullable == ((name, c.name) in {("roles", "descripcion"), ("tipos_vidrio", "descripcion"), ("piezas", "dimensiones")})
        expected_default = name in {"usuarios", "tipos_vidrio", "planchas", "retazos"} and c.name == "estado"
        assert (c.server_default is not None) == expected_default
        if expected_default:
            assert str(c.server_default.arg.compile(dialect=dialect)) == "true"
        if isinstance(c.type, sa.DateTime):
            assert c.default is None
    assert list(table.primary_key.columns.keys()) == [next(iter(EXPECTED[name]))]
    assert {tuple(c.columns.keys()) for c in table.constraints if isinstance(c, sa.UniqueConstraint)} == UNIQUES.get(name, set())
    assert {(fk.parent.name, fk.target_fullname) for fk in table.foreign_keys} == FKS.get(name, set())
    assert all(fk.ondelete is None and fk.onupdate is None for fk in table.foreign_keys)
    assert {str(c.sqltext) for c in table.constraints if isinstance(c, sa.CheckConstraint)} == CHECKS.get(name, set())
    expected_indexes = {
        "planchas": {("id_tipo_vidrio", "espesor_mm", "estado")},
        "retazos": {("id_tipo_vidrio", "espesor_mm", "estado")},
        "pedidos": {("estado", "fecha_registro")},
    }
    assert {tuple(i.columns.keys()) for i in table.indexes} == expected_indexes.get(name, set())
    assert all(not i.unique for i in table.indexes)
    # Compila todos los tipos/constraints para PostgreSQL; no ejecuta DDL.
    assert str(sa.schema.CreateTable(table).compile(dialect=dialect))


def test_excluded_entities_remain_at_the_previous_schema(metadata):
    expected = {
        "configuraciones": "id_configuracion separacion_mm margen_mm resolucion_raster paso_angular area_minima_retazo dimension_minima_retazo fecha_actualizacion",
        "ejecuciones_optimizacion": "id_ejecucion metodo fecha_ejecucion tiempo_computacional seleccionada patron_resultado id_pedido id_configuracion",
        "metricas_ejecucion": "id_metrica aprovechamiento_pct merma_mm2 planchas_utilizadas area_recuperable_mm2 tiempo_computacional_ms id_ejecucion",
    }
    assert set(metadata.tables) == set(EXPECTED) | set(expected)
    assert sum(len(t.c) for t in metadata.tables.values()) == 68
    for name, fields in expected.items():
        table = metadata.tables[name]
        assert list(table.c.keys()) == fields.split()
        assert not table.indexes
        assert not any(isinstance(c, sa.CheckConstraint) for c in table.constraints)
        assert all(c.server_default is None for c in table.c)
        nullable = {
            "configuraciones": set(),
            "ejecuciones_optimizacion": {"tiempo_computacional", "patron_resultado"},
            "metricas_ejecucion": {"aprovechamiento_pct", "merma_mm2", "planchas_utilizadas", "area_recuperable_mm2", "tiempo_computacional_ms"},
        }
        assert {c.name for c in table.c if c.nullable} == nullable[name]
        expected_fks = {
            "configuraciones": set(),
            "ejecuciones_optimizacion": {("id_pedido", "pedidos.id_pedido"), ("id_configuracion", "configuraciones.id_configuracion")},
            "metricas_ejecucion": {("id_ejecucion", "ejecuciones_optimizacion.id_ejecucion")},
        }
        assert {(fk.parent.name, fk.target_fullname) for fk in table.foreign_keys} == expected_fks[name]
        assert {tuple(c.columns.keys()) for c in table.constraints if isinstance(c, sa.UniqueConstraint)} == ({("id_ejecucion",)} if name == "metricas_ejecucion" else set())
        assert list(table.primary_key.columns.keys()) == [fields.split()[0]]
        for c in table.c:
            if c.name.startswith("id_") or c.name == "planchas_utilizadas":
                assert isinstance(c.type, sa.Integer)
            elif c.name.startswith("fecha_"):
                assert isinstance(c.type, sa.DateTime) and not c.type.timezone
                assert c.default is not None
            elif c.name == "metodo":
                assert isinstance(c.type, sa.String) and c.type.length == 30
            elif c.name == "seleccionada":
                assert isinstance(c.type, sa.Boolean) and c.default.arg is False
            elif c.name == "patron_resultado":
                assert isinstance(c.type, postgresql.JSONB)
            else:
                assert isinstance(c.type, sa.Float)
    assert "optimizaciones" not in metadata.tables and "materiales_utilizados" not in metadata.tables
    assert "id_ejecucion_origen" not in metadata.tables["retazos"].c
