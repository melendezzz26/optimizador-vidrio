from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Rol(Base):
    __tablename__ = "roles"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombres: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    correo: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

    id_rol: Mapped[int] = mapped_column(
        ForeignKey("roles.id_rol"),
        nullable=False
    )


class TipoVidrio(Base):
    __tablename__ = "tipos_vidrio"

    id_tipo_vidrio: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)


class Plancha(Base):
    __tablename__ = "planchas"

    id_plancha: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    ancho_mm: Mapped[float] = mapped_column(Float, nullable=False)
    alto_mm: Mapped[float] = mapped_column(Float, nullable=False)
    espesor_mm: Mapped[float] = mapped_column(Float, nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

    id_tipo_vidrio: Mapped[int] = mapped_column(
        ForeignKey("tipos_vidrio.id_tipo_vidrio"),
        nullable=False
    )


class Retazo(Base):
    __tablename__ = "retazos"

    id_retazo: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    espesor_mm: Mapped[float] = mapped_column(Float, nullable=False)
    geometria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    area_mm2: Mapped[float] = mapped_column(Float, nullable=False)
    estado: Mapped[bool] = mapped_column(Boolean, default=True)

    id_tipo_vidrio: Mapped[int] = mapped_column(
        ForeignKey("tipos_vidrio.id_tipo_vidrio"),
        nullable=False
    )


class Pedido(Base):
    __tablename__ = "pedidos"

    id_pedido: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now
    )
    estado: Mapped[str] = mapped_column(String(30), default="PENDIENTE")
    espesor_mm: Mapped[float] = mapped_column(Float, nullable=False)

    id_tipo_vidrio: Mapped[int] = mapped_column(
        ForeignKey("tipos_vidrio.id_tipo_vidrio"),
        nullable=False
    )

    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"),
        nullable=False
    )


class Pieza(Base):
    __tablename__ = "piezas"

    id_pieza: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo_forma: Mapped[str] = mapped_column(String(50), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    dimensiones: Mapped[dict | None] = mapped_column(JSONB)
    geometria: Mapped[dict | None] = mapped_column(JSONB)
    area_mm2: Mapped[float | None] = mapped_column(Float)

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