"""Publica una nueva versión vigente de la configuración con el paso angular de Sprint 2.

Desde TA-016 (PR #64), el cálculo exige una configuración vigente con paso angular
de 5°. Una base creada antes conserva otra versión vigente y todo cálculo responde
409 CONFIG_CONFLICT. Las versiones históricas nunca se editan, porque las
optimizaciones anteriores las referencian: la vigente pasa a no vigente y se crea
otra versión con los mismos parámetros y el nuevo paso, en una sola transacción.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Configuracion, Usuario
from app.modules.optimization.domain.problem import OptimizationConfig, SPRINT_2_ANGULAR_STEP_DEG
from app.modules.optimization.domain.rotation import discrete_angles


class ConfigurationPublicationError(ValueError):
    """La publicación no es posible; el operador debe revisar la situación."""


@dataclass(frozen=True)
class PublicationResult:
    previous_version: int
    current_version: int
    changed: bool


def publish_angular_step_version(db: Session, responsible_username: str | None,
                                 angular_step=SPRINT_2_ANGULAR_STEP_DEG) -> PublicationResult:
    try:
        if db.get_bind().dialect.name == "postgresql":
            # Serializa con el seed y con otra publicación simultánea.
            db.execute(text("LOCK TABLE configuraciones IN SHARE ROW EXCLUSIVE MODE"))
        current = db.scalars(select(Configuracion).where(Configuracion.vigente.is_(True))).all()
        if len(current) != 1:
            raise ConfigurationPublicationError(
                f"Se requiere exactamente una configuración vigente y hay {len(current)}. "
                "Resuélvelo con el equipo antes de publicar. No se modificó nada."
            )
        previous = current[0]
        if previous.paso_angular_grados == angular_step:
            db.commit()  # Repetir el comando no crea versiones duplicadas.
            return PublicationResult(previous.version, previous.version, changed=False)

        user = db.scalar(select(Usuario).where(
            Usuario.usuario == responsible_username, Usuario.estado.is_(True),
        )) if responsible_username else None
        if user is None:
            raise ConfigurationPublicationError(
                "Indica --responsable con el usuario de una cuenta activa existente. No se modificó nada."
            )
        try:
            config = OptimizationConfig(
                resolution_mm=previous.resolucion_raster_mm, margin_mm=previous.margen_mm,
                separation_mm=previous.separacion_mm, angular_step_deg=angular_step,
            )
            discrete_angles(config.angular_step_deg)
            for value in (previous.ancho_min_retazo_mm, previous.alto_min_retazo_mm):
                if value is None or not value.is_finite() or value < 0:
                    raise ValueError("Invalid residual minimum")
        except ValueError as exc:
            raise ConfigurationPublicationError(
                "Los demás parámetros de la versión vigente no son válidos. Revísalos con el equipo. "
                "No se modificó nada."
            ) from exc

        version = db.scalar(select(func.max(Configuracion.version))) + 1
        previous.vigente = False
        db.add(Configuracion(
            version=version,
            separacion_mm=previous.separacion_mm, margen_mm=previous.margen_mm,
            resolucion_raster_mm=previous.resolucion_raster_mm, paso_angular_grados=angular_step,
            ancho_min_retazo_mm=previous.ancho_min_retazo_mm, alto_min_retazo_mm=previous.alto_min_retazo_mm,
            vigente=True, id_usuario_creacion=user.id_usuario, fecha_creacion=datetime.now(timezone.utc),
        ))
        db.commit()
        return PublicationResult(previous.version, version, changed=True)
    except Exception:
        db.rollback()
        raise