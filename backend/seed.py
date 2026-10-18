import argparse

from app.shared.database import SessionLocal
from app.models import Rol
from app.modules.authentication.infrastructure.permission_seed import seed_permissions


def crear_roles():
    db = SessionLocal()

    try:
        roles = [
            ("Administrador", "Administración general del sistema"),
            ("Almacenero", "Gestión de planchas y retazos"),
            ("Operario", "Registro de pedidos y ejecución de optimizaciones"),
        ]

        for nombre, descripcion in roles:
            existe = db.query(Rol).filter(Rol.nombre == nombre).first()

            if not existe:
                db.add(
                    Rol(
                        nombre=nombre,
                        descripcion=descripcion
                    )
                )

        db.commit()
        print("Roles registrados correctamente.")
        
        seed_permissions(db)
        print("Permisos de roles registrados correctamente.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga reproducible de datos iniciales de NewGlass.")
    parser.add_argument("--optimization-demo", action="store_true", help="Carga inicial optativa de parámetros de corte para desarrollo/demo.")
    parser.add_argument("--responsable", help="Usuario activo existente al que se atribuye la configuración inicial.")
    args = parser.parse_args()
    crear_roles()
    if args.optimization_demo:
        from app.modules.optimization.infrastructure.configuration_seed import (
            ConfigurationSeedError, seed_demo_configuration,
        )

        try:
            with SessionLocal() as session:
                configuration = seed_demo_configuration(session, args.responsable)
                print(f"Configuración de corte disponible: versión {configuration.version} (vigente).")
        except ConfigurationSeedError as error:
            parser.exit(1, f"No se pudo preparar la configuración: {error}\n")
