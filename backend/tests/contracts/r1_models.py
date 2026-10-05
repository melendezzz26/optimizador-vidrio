"""Snapshot ORM R1 de 9c8c3fb, solo para pruebas históricas; no es código de aplicación."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database import Base


class Rol(Base):
    __tablename__ = "roles"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(150))


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("dni", name="usuarios_dni_key"),
        UniqueConstraint("usuario", name="usuarios_usuario_key"),
        CheckConstraint("dni ~ '^[0-9]{8}$'", name="ck_usuarios_dni_formato"),
        CheckConstraint("usuario ~ '^[A-Za-z][0-9]{8}$'", name="ck_usuarios_usuario_formato"),
    )

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    dni: Mapped[str] = mapped_column(CHAR(8), nullable=False)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario: Mapped[str] = mapped_column(String(9), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    id_rol: Mapped[int] = mapped_column(
        ForeignKey("roles.id_rol"),
        nullable=False
    )


class TipoVidrio(Base):
    __tablename__ = "tipos_vidrio"
    __table_args__ = (UniqueConstraint("nombre", name="tipos_vidrio_nombre_key"),)

    id_tipo_vidrio: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Plancha(Base):
    __tablename__ = "planchas"
    __table_args__ = (
        CheckConstraint("ancho_mm > 0", name="ck_planchas_ancho_positivo"),
        CheckConstraint("alto_mm > 0", name="ck_planchas_alto_positivo"),
        CheckConstraint("espesor_mm IN (3, 4, 5.5, 6, 8)", name="ck_planchas_espesor"),
        CheckConstraint("cantidad >= 0", name="ck_planchas_cantidad"),
        Index("ix_planchas_stock_compatible", "id_tipo_vidrio", "espesor_mm", "estado"),
    )

    id_plancha: Mapped[int] = mapped_column(Integer, primary_key=True)
    ancho_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    alto_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    espesor_mm: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    id_tipo_vidrio: Mapped[int] = mapped_column(
        ForeignKey("tipos_vidrio.id_tipo_vidrio"),
        nullable=False
    )


class Retazo(Base):
    __tablename__ = "retazos"
    __table_args__ = (
        CheckConstraint("espesor_mm IN (3, 4, 5.5, 6, 8)", name="ck_retazos_espesor"),
        CheckConstraint("area_mm2 > 0", name="ck_retazos_area_positiva"),
        Index("ix_retazos_stock_compatible", "id_tipo_vidrio", "espesor_mm", "estado"),
    )

    id_retazo: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    espesor_mm: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    geometria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    area_mm2: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    estado: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    id_tipo_vidrio: Mapped[int] = mapped_column(
        ForeignKey("tipos_vidrio.id_tipo_vidrio"),
        nullable=False
    )


class Pedido(Base):
    __tablename__ = "pedidos"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE', 'EN_OPTIMIZACION', 'OPTIMIZADO', 'CONFIRMADO', 'CANCELADO')",
            name="ck_pedidos_estado",
        ),
        CheckConstraint("espesor_mm IN (3, 4, 5.5, 6, 8)", name="ck_pedidos_espesor"),
        Index("ix_pedidos_estado_fecha", "estado", "fecha_registro"),
    )

    id_pedido: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    espesor_mm: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)

    id_tipo_vidrio: Mapped[int] = mapped_column(
        ForeignKey("tipos_vidrio.id_tipo_vidrio"),
        nullable=False
    )

    id_usuario_registro: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"),
        nullable=False
    )


class Pieza(Base):
    __tablename__ = "piezas"
    __table_args__ = (
        CheckConstraint(
            "tipo_forma IN ('RECTANGULO', 'CIRCUNFERENCIA', 'POLIGONO_CONVEXO')",
            name="ck_piezas_tipo_forma",
        ),
        CheckConstraint("cantidad > 0", name="ck_piezas_cantidad"),
        CheckConstraint("area_mm2 > 0", name="ck_piezas_area_positiva"),
    )

    id_pieza: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_forma: Mapped[str] = mapped_column(String(30), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensiones: Mapped[dict | None] = mapped_column(JSONB)
    geometria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    area_mm2: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedidos.id_pedido"),
        nullable=False
    )


class Configuracion(Base):
    __tablename__ = "configuraciones"

    id_configuracion: Mapped[int] = mapped_column(Integer, primary_key=True)
    separacion_mm: Mapped[float] = mapped_column(Float, nullable=False)
    margen_mm: Mapped[float] = mapped_column(Float, nullable=False)
    resolucion_raster: Mapped[float] = mapped_column(Float, nullable=False)
    paso_angular: Mapped[float] = mapped_column(Float, nullable=False)
    area_minima_retazo: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_minima_retazo: Mapped[float] = mapped_column(Float, nullable=False)
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )


class EjecucionOptimizacion(Base):
    __tablename__ = "ejecuciones_optimizacion"

    id_ejecucion: Mapped[int] = mapped_column(Integer, primary_key=True)
    metodo: Mapped[str] = mapped_column(String(30), nullable=False)
    fecha_ejecucion: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )
    tiempo_computacional: Mapped[float | None] = mapped_column(Float)
    seleccionada: Mapped[bool] = mapped_column(Boolean, default=False)
    patron_resultado: Mapped[dict | None] = mapped_column(JSONB)

    id_pedido: Mapped[int] = mapped_column(
        ForeignKey("pedidos.id_pedido"),
        nullable=False
    )

    id_configuracion: Mapped[int] = mapped_column(
        ForeignKey("configuraciones.id_configuracion"),
        nullable=False
    )


class MetricaEjecucion(Base):
    __tablename__ = "metricas_ejecucion"

    id_metrica: Mapped[int] = mapped_column(Integer, primary_key=True)
    aprovechamiento_pct: Mapped[float | None] = mapped_column(Float)
    merma_mm2: Mapped[float | None] = mapped_column(Float)
    planchas_utilizadas: Mapped[int | None] = mapped_column(Integer)
    area_recuperable_mm2: Mapped[float | None] = mapped_column(Float)
    tiempo_computacional_ms: Mapped[float | None] = mapped_column(Float)

    id_ejecucion: Mapped[int] = mapped_column(
        ForeignKey("ejecuciones_optimizacion.id_ejecucion"),
        unique=True,
        nullable=False
    )
