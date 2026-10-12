from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from app.shared.config import database_engine_options, database_url

from app.shared.database import Base
from app import models


# Objeto de configuración de Alembic
config = context.config

# El entorno prevalece sobre el .env opcional de desarrollo.
DATABASE_URL = database_url()

# Reemplazar la URL definida en alembic.ini
# Escapar solo la representación de ConfigParser, nunca la URL del entorno.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))


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
        **database_engine_options(DATABASE_URL, pooled=False),
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
