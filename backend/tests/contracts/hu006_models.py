from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    BigInteger,
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


class TipoVidrioEspesor(Base):
    __tablename__ = "tipos_vidrio_espesores"
    __table_args__ = (
        PrimaryKeyConstraint("id_tipo_vidrio", "espesor_mm", name="pk_tipos_vidrio_espesores"),
        CheckConstraint("espesor_mm > 0", name="ck_tipos_vidrio_espesores_espesor_positivo"),
    )

    id_tipo_vidrio: Mapped[int] = mapped_column(
        ForeignKey("tipos_vidrio.id_tipo_vidrio", name="fk_tipos_vidrio_espesores_tipo_vidrio"),
        nullable=False,
    )
    espesor_mm: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)


class Plancha(Base):
    __tablename__ = "planchas"
    __table_args__ = (
        CheckConstraint("ancho_mm > 0", name="ck_planchas_ancho_positivo"),
        CheckConstraint("alto_mm > 0", name="ck_planchas_alto_positivo"),
        ForeignKeyConstraint(
            ["id_tipo_vidrio", "espesor_mm"],
            ["tipos_vidrio_espesores.id_tipo_vidrio", "tipos_vidrio_espesores.espesor_mm"],
            name="fk_planchas_tipo_espesor",
        ),
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
        ForeignKeyConstraint(
            ["id_tipo_vidrio", "espesor_mm"],
            ["tipos_vidrio_espesores.id_tipo_vidrio", "tipos_vidrio_espesores.espesor_mm"],
            name="fk_retazos_tipo_espesor",
        ),
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
    id_ejecucion_origen: Mapped[int | None] = mapped_column(
        ForeignKey("ejecuciones_optimizacion.id_ejecucion"), nullable=True
    )

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
        Index("ix_pedidos_estado_fecha", "estado", "fecha_registro"),
    )

    id_pedido: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_registro: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")

    id_usuario_registro: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"),
        nullable=False
    )


class Pieza(Base):
    __tablename__ = "piezas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_tipo_vidrio", "espesor_mm"],
            ["tipos_vidrio_espesores.id_tipo_vidrio", "tipos_vidrio_espesores.espesor_mm"],
            name="fk_piezas_tipo_espesor",
        ),
        CheckConstraint(
            "tipo_forma IN ('RECTANGULO', 'CIRCUNFERENCIA', 'POLIGONO_CONVEXO')",
            name="ck_piezas_tipo_forma",
        ),
        CheckConstraint("cantidad > 0", name="ck_piezas_cantidad"),
        CheckConstraint("area_mm2 > 0", name="ck_piezas_area_positiva"),
    )

    id_tipo_vidrio: Mapped[int] = mapped_column(Integer, nullable=False)
    espesor_mm: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)

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
    __table_args__ = (
        UniqueConstraint("version", name="configuraciones_version_key"),
        CheckConstraint("version > 0", name="ck_configuraciones_version"),
        CheckConstraint("separacion_mm >= 0", name="ck_configuraciones_separacion"),
        CheckConstraint("margen_mm >= 0", name="ck_configuraciones_margen"),
        CheckConstraint("resolucion_raster_mm > 0", name="ck_configuraciones_resolucion"),
        CheckConstraint(
            "paso_angular_grados > 0 AND paso_angular_grados <= 360",
            name="ck_configuraciones_paso_angular",
        ),
        CheckConstraint("ancho_min_retazo_mm >= 0", name="ck_configuraciones_ancho_retazo"),
        CheckConstraint("alto_min_retazo_mm >= 0", name="ck_configuraciones_alto_retazo"),
    )

    id_configuracion: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    separacion_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    margen_mm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    resolucion_raster_mm: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    paso_angular_grados: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    ancho_min_retazo_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    alto_min_retazo_mm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    id_usuario_creacion: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id_usuario"), nullable=False
    )
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Optimizacion(Base):
    __tablename__ = "optimizaciones"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('EN_EJECUCION', 'COMPLETADA', 'SIN_SOLUCION', 'FALLIDA')",
            name="ck_optimizaciones_estado",
        ),
        Index("ix_optimizaciones_pedido_fecha", "id_pedido", "fecha_inicio"),
    )

    id_optimizacion: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedidos.id_pedido"), nullable=False)
    id_configuracion: Mapped[int] = mapped_column(
        ForeignKey("configuraciones.id_configuracion"), nullable=False
    )
    id_usuario_ejecutor: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario"), nullable=False)
    criterio_seleccion_version: Mapped[str] = mapped_column(String(20), nullable=False)
    id_ejecucion_seleccionada: Mapped[int | None] = mapped_column(
        ForeignKey(
            "ejecuciones_optimizacion.id_ejecucion",
            name="fk_optimizaciones_ejecucion_seleccionada",
            use_alter=True,
        ),
        nullable=True,
    )


class EjecucionOptimizacion(Base):
    __tablename__ = "ejecuciones_optimizacion"
    __table_args__ = (
        CheckConstraint("metodo IN ('FF', 'BF', 'WF')", name="ck_ejecuciones_metodo"),
        CheckConstraint(
            "estado IN ('EN_EJECUCION', 'COMPLETADA', 'FALLIDA')",
            name="ck_ejecuciones_estado",
        ),
        UniqueConstraint("id_optimizacion", "metodo", name="ejecuciones_optimizacion_metodo_key"),
    )

    id_ejecucion: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_optimizacion: Mapped[int] = mapped_column(
        ForeignKey(
            "optimizaciones.id_optimizacion",
            name="ejecuciones_optimizacion_id_optimizacion_fkey",
        ), nullable=False
    )
    metodo: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    completo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    patron_resultado: Mapped[dict | None] = mapped_column(JSONB)


class MaterialUtilizado(Base):
    __tablename__ = "materiales_utilizados"
    __table_args__ = (
        CheckConstraint("cantidad_utilizada > 0", name="ck_materiales_cantidad"),
        CheckConstraint(
            "(id_plancha IS NOT NULL) <> (id_retazo IS NOT NULL)",
            name="ck_materiales_fuente",
        ),
        Index("ix_materiales_ejecucion", "id_ejecucion"),
    )

    id_material_utilizado: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_ejecucion: Mapped[int] = mapped_column(
        ForeignKey("ejecuciones_optimizacion.id_ejecucion"), nullable=False
    )
    id_plancha: Mapped[int | None] = mapped_column(ForeignKey("planchas.id_plancha"), nullable=True)
    id_retazo: Mapped[int | None] = mapped_column(ForeignKey("retazos.id_retazo"), nullable=True)
    cantidad_utilizada: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")


class MetricaEjecucion(Base):
    __tablename__ = "metricas_ejecucion"
    __table_args__ = (
        CheckConstraint(
            "area_material_total_mm2 > 0",
            name="ck_metricas_area_material_total",
        ),
        CheckConstraint(
            "area_piezas_colocadas_mm2 >= 0",
            name="ck_metricas_area_piezas_colocadas",
        ),
        CheckConstraint(
            "aprovechamiento_pct >= 0 AND aprovechamiento_pct <= 100",
            name="ck_metricas_aprovechamiento",
        ),
        CheckConstraint(
            "merma_mm2 >= 0",
            name="ck_metricas_merma",
        ),
        CheckConstraint(
            "retazo_recuperable_mm2 >= 0",
            name="ck_metricas_retazo_recuperable",
        ),
        CheckConstraint(
            "planchas_nuevas_usadas >= 0",
            name="ck_metricas_planchas_nuevas",
        ),
        CheckConstraint(
            "tiempo_computacional_ms >= 0",
            name="ck_metricas_tiempo_computacional",
        ),
        CheckConstraint(
            "memoria_pico_mb >= 0",
            name="ck_metricas_memoria_pico",
        ),
        CheckConstraint(
            "tiempo_cpu_ms >= 0",
            name="ck_metricas_tiempo_cpu",
        ),
    )

    id_metrica: Mapped[int] = mapped_column(Integer, primary_key=True)

    id_ejecucion: Mapped[int] = mapped_column(
        ForeignKey("ejecuciones_optimizacion.id_ejecucion"),
        unique=True,
        nullable=False,
    )

    area_material_total_mm2: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    area_piezas_colocadas_mm2: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    aprovechamiento_pct: Mapped[Decimal] = mapped_column(
        Numeric(6, 3),
        nullable=False,
    )

    merma_mm2: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    retazo_recuperable_mm2: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    planchas_nuevas_usadas: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    tiempo_computacional_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    memoria_pico_mb: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3),
        nullable=True,
    )

    tiempo_cpu_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
