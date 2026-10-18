from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.shared.config import database_engine_options, database_url

DATABASE_URL = database_url()

engine = create_engine(DATABASE_URL, **database_engine_options(DATABASE_URL))

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Iterator[Session]:
    """Entrega una sesión por petición y la cierra al terminar, incluso si hay error."""
    with SessionLocal() as db:
        yield db
