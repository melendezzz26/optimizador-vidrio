"""Metadata aislada: contratos históricos fijos y ORM vigente, sin motor de BD."""

from pathlib import Path
import runpy
import sys
from types import ModuleType
from unittest.mock import patch

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

BACKEND = Path(__file__).resolve().parents[1]


def _load(path):
    database = ModuleType("app.shared.database")
    database.Base = declarative_base()
    with patch.dict(sys.modules, {"app.shared.database": database}):
        runpy.run_path(str(path))
    return database.Base.metadata


def current_metadata():
    return _load(BACKEND / "app/models.py")


def historical_metadata(revision):
    if revision not in {
        "e1a2b3c4d5f6",
        "f2b3c4d5e6a7",
        "a3c4d5e6f7b8",
        "b4d5e6f7a8c9",
        "1c8754481a08",
        "d6e7f8a9b0c1",
    }:
        raise ValueError("No hay contrato histórico para esta revisión")

    if revision == "d6e7f8a9b0c1":
        return _load(BACKEND / "tests/contracts/hu006_models.py")

    if revision == "1c8754481a08":
        return _load(BACKEND / "tests/contracts/ta013_models.py")

    if revision == "b4d5e6f7a8c9":
        return _load(BACKEND / "tests/contracts/r4_models.py")

    if revision == "a3c4d5e6f7b8":
        return _load(BACKEND / "tests/contracts/r3_models.py")

    r1 = _load(BACKEND / "tests/contracts/r1_models.py")

    if revision == "e1a2b3c4d5f6":
        return r1

    # Contrato CONFIGURACION R2 del commit e1edde3.
    r2 = sa.MetaData()
    sa.Table(
        "configuraciones", r2,
        sa.Column("id_configuracion", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("separacion_mm", sa.Numeric(8, 2), nullable=False),
        sa.Column("margen_mm", sa.Numeric(8, 2), nullable=False),
        sa.Column("resolucion_raster_mm", sa.Numeric(8, 3), nullable=False),
        sa.Column("paso_angular_grados", sa.Numeric(6, 2), nullable=True),
        sa.Column("ancho_min_retazo_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("alto_min_retazo_mm", sa.Numeric(10, 2), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "id_usuario_creacion",
            sa.Integer(),
            sa.ForeignKey("usuarios.id_usuario"),
            nullable=False,
        ),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("version", name="configuraciones_version_key"),
        sa.CheckConstraint("version > 0", name="ck_configuraciones_version"),
        sa.CheckConstraint("separacion_mm >= 0", name="ck_configuraciones_separacion"),
        sa.CheckConstraint("margen_mm >= 0", name="ck_configuraciones_margen"),
        sa.CheckConstraint(
            "resolucion_raster_mm > 0",
            name="ck_configuraciones_resolucion",
        ),
        sa.CheckConstraint(
            "paso_angular_grados > 0 AND paso_angular_grados <= 360",
            name="ck_configuraciones_paso_angular",
        ),
        sa.CheckConstraint(
            "ancho_min_retazo_mm >= 0",
            name="ck_configuraciones_ancho_retazo",
        ),
        sa.CheckConstraint(
            "alto_min_retazo_mm >= 0",
            name="ck_configuraciones_alto_retazo",
        ),
    )

    for table in r1.tables.values():
        if table.name != "configuraciones":
            table.to_metadata(r2)

    return r2
