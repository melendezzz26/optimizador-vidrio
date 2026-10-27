"""Opt-in development/demo configuration with Sprint 2 angular granularity."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Configuracion, Usuario
from app.modules.optimization.domain.problem import OptimizationConfig, SPRINT_2_ANGULAR_STEP_DEG
from app.modules.optimization.domain.rotation import discrete_angles


# Shared operational angle; other dimensions retain the demo fixture values.
DEMO_PARAMETERS = dict(
    separacion_mm=Decimal("0"), margen_mm=Decimal("0"),
    resolucion_raster_mm=Decimal("1"), paso_angular_grados=SPRINT_2_ANGULAR_STEP_DEG,
    ancho_min_retazo_mm=Decimal("10"), alto_min_retazo_mm=Decimal("10"),
)


class ConfigurationSeedError(ValueError):
    """The operator must resolve an ambiguous or incomplete configuration."""


def seed_demo_configuration(db: Session, responsible_username: str | None) -> Configuracion:
    """Commit one initial version, or retain a complete current version unchanged.

    Historical rows are never updated/reactivated. PostgreSQL's table lock also
    serializes concurrent bootstrap attempts when the table is initially empty.
    The caller owns this dedicated session; failures roll back the entire seed.
    """
    try:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("LOCK TABLE configuraciones IN SHARE ROW EXCLUSIVE MODE"))
        current = db.scalars(select(Configuracion).where(Configuracion.vigente.is_(True))).all()
        if len(current) > 1:
            raise ConfigurationSeedError(
                "Hay varias configuraciones vigentes. Solicita al administrador resolverlas antes de ejecutar el seed."
            )
        if current:
            configuration = current[0]
            try:
                config = OptimizationConfig(
                    resolution_mm=configuration.resolucion_raster_mm,
                    margin_mm=configuration.margen_mm,
                    separation_mm=configuration.separacion_mm,
                    angular_step_deg=configuration.paso_angular_grados,
                )
                discrete_angles(config.angular_step_deg)
                for field in (configuration.ancho_min_retazo_mm, configuration.alto_min_retazo_mm):
                    if field is None or not field.is_finite() or field < 0:
                        raise ValueError("Invalid residual minimum")
            except ValueError as exc:
                raise ConfigurationSeedError(
                    "La configuración vigente está incompleta o es inválida. No se modificó: revisa sus parámetros con el administrador."
                ) from exc
            db.commit()
            return configuration

        user = db.scalar(select(Usuario).where(
            Usuario.usuario == responsible_username, Usuario.estado.is_(True),
        )) if responsible_username else None
        if user is None:
            raise ConfigurationSeedError(
                "Indica --responsable con el usuario de una cuenta activa existente. No se crearon usuarios ni configuración."
            )
        version = (db.scalar(select(func.max(Configuracion.version))) or 0) + 1
        configuration = Configuracion(
            version=version, **DEMO_PARAMETERS, vigente=True,
            id_usuario_creacion=user.id_usuario, fecha_creacion=datetime.now(timezone.utc),
        )
        db.add(configuration)
        db.commit()
        return configuration
    except Exception:
        db.rollback()
        raise
