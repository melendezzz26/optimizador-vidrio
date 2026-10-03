from app.shared.database import SessionLocal
from app.models import Rol


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

    finally:
        db.close()


if __name__ == "__main__":
    crear_roles()