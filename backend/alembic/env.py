from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from dotenv import load_dotenv

from app.database import Base
from app import models


# Cargar variables del archivo .env
load_dotenv()

# Objeto de configuración de Alembic
config = context.config

# Obtener la URL de conexión desde .env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No se encontró DATABASE_URL en el archivo .env")

# Reemplazar la URL definida en alembic.ini
config.set_main_option("sqlalchemy.url", DATABASE_URL)


# Configuración de logs
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Metadata de SQLAlchemy para que Alembic detecte los modelos
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Ejecuta las migraciones en modo offline.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecuta las migraciones conectándose directamente
    a PostgreSQL.
    """

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()