"""Publica una nueva versión de la configuración de corte con paso angular de 5°.

Se usa una sola vez en una base creada antes de TA-016, donde todo cálculo responde
"Sprint 2 requiere una configuración vigente con paso angular de 5°". Uso, desde
``backend/``::

    python -m scripts.publish_configuration --responsable USUARIO_ADMIN

Copia los demás parámetros de la versión vigente, la deja como histórica y crea
la nueva versión vigente. Si la vigente ya tiene 5°, no cambia nada.
"""
import argparse
import sys

CONFIRMATION_WORD = "PUBLICAR"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--responsable", required=True,
                        help="Usuario activo existente al que se atribuye la nueva versión.")
    args = parser.parse_args(argv)

    # Imports diferidos: la base se abre solo al ejecutar el comando.
    from app.modules.optimization.infrastructure.configuration_publication import (
        ConfigurationPublicationError, publish_angular_step_version,
    )
    from app.shared.database import SessionLocal, engine

    print("Se publicará una nueva versión de configuración con paso angular de 5°")
    print(f"en la base: {engine.url.database}")
    if input(f"Escribe {CONFIRMATION_WORD} para continuar: ").strip() != CONFIRMATION_WORD:
        print("Cancelado. No se modificó nada.")
        return 1
    try:
        with SessionLocal() as session:
            result = publish_angular_step_version(session, args.responsable)
    except ConfigurationPublicationError as error:
        print(f"No se publicó: {error}")
        return 1
    if not result.changed:
        print(f"La versión vigente ({result.current_version}) ya tiene 5°. No se modificó nada.")
    else:
        print(f"Publicada la versión {result.current_version} con 5°. "
              f"La versión {result.previous_version} queda como histórica.")
    return 0


if __name__ == "__main__":
    sys.exit(main())