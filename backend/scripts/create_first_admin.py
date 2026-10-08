"""Crea la primera cuenta de Administrador.

La pantalla de gestión de usuarios exige una sesión de Administrador, así que
la primera cuenta no puede crearse desde ella. Este comando la crea una sola
vez, con las mismas reglas que la pantalla. Uso, desde ``backend/``::

    python -m scripts.create_first_admin

Los datos se piden por teclado: la contraseña nunca queda escrita en un
archivo ni en el historial de la terminal.
"""
import getpass
import sys
from datetime import datetime, timezone

from app.modules.users.application import use_cases
from app.modules.users.application.dto import CreateUserData
from app.modules.users.application.ports import Clock, PasswordHasher, UserRepository
from app.modules.users.domain.errors import DuplicateDniError, InvalidUserDataError
from app.modules.users.domain.user import User

ADMIN_ROLE_NAME = "Administrador"
CONFIRMATION_WORD = "CREAR"


class FirstAdminError(Exception):
    """La primera cuenta de Administrador no se puede crear en este momento."""


def create_first_admin(
    data: CreateUserData,
    *,
    repository: UserRepository,
    hash_password: PasswordHasher,
    now: Clock,
) -> User:
    """Crea un Administrador solo si todavía no existe ninguno activo.

    Ignora el rol que traiga ``data`` y asigna siempre el de Administrador.
    """
    admin_role = next(
        (role for role in repository.list_roles() if role.name == ADMIN_ROLE_NAME), None
    )
    if admin_role is None:
        raise FirstAdminError(
            "No existe el rol Administrador. Carga primero los roles con seed.py."
        )

    has_active_admin = any(
        user.role_id == admin_role.role_id and user.is_active
        for user in repository.list_users()
    )
    if has_active_admin:
        raise FirstAdminError(
            "Ya existe un Administrador activo. Crea las demás cuentas desde la pantalla."
        )

    return use_cases.create_user(
        CreateUserData(
            first_names=data.first_names,
            last_names=data.last_names,
            dni=data.dni,
            password=data.password,
            role_id=admin_role.role_id,
        ),
        repository=repository,
        hash_password=hash_password,
        now=now,
    )


def _ask_password() -> str:
    password = getpass.getpass("Contraseña (mínimo 8 caracteres, no se muestra): ")
    if getpass.getpass("Repite la contraseña: ") != password:
        raise FirstAdminError("Las contraseñas no coinciden.")
    return password


def main() -> int:
    # Imports diferidos: la base se abre solo al ejecutar el comando.
    from app.modules.users.infrastructure.sqlalchemy_user_repository import (
        SqlAlchemyUserRepository,
    )
    from app.shared.database import SessionLocal, engine
    from app.shared.security import hash_password

    print("Se creará la primera cuenta de Administrador en esta base de datos:")
    print(f"  servidor: {engine.url.host or 'archivo local'}")
    print(f"  base:     {engine.url.database}")
    if input(f"Escribe {CONFIRMATION_WORD} para continuar: ").strip() != CONFIRMATION_WORD:
        print("Cancelado. No se modificó nada.")
        return 1

    try:
        data = CreateUserData(
            first_names=input("Nombres: "),
            last_names=input("Apellidos: "),
            dni=input("DNI (8 dígitos): ").strip(),
            password=_ask_password(),
            role_id=0,  # se reemplaza por el rol Administrador
        )
        with SessionLocal() as session:
            user = create_first_admin(
                data,
                repository=SqlAlchemyUserRepository(session),
                hash_password=hash_password,
                now=lambda: datetime.now(timezone.utc),
            )
    except FirstAdminError as error:
        print(f"No se creó la cuenta: {error}")
        return 1
    except InvalidUserDataError as error:
        print(f"No se creó la cuenta: {error}")
        return 1
    except DuplicateDniError:
        print("No se creó la cuenta: ya existe un usuario con ese DNI.")
        return 1

    print(f"Administrador creado. Usuario de acceso: {user.username}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
