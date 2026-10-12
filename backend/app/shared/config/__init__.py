"""Configuración desde el entorno; .env es opcional y solo complementa desarrollo."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)


def required_value(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Configura {name} en el entorno o en backend/.env.")
    return value


def integer_value(name: str, *, minimum: int = 1, default: int | None = None) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    message = f"{name} debe ser un entero mayor o igual a {minimum}."
    try:
        value = int(raw)
    except ValueError:
        raise RuntimeError(message) from None
    if value < minimum:
        raise RuntimeError(message)
    return value


def token_minutes() -> int:
    minutes = integer_value("TOKEN_MINUTOS", default=480)
    try:
        datetime.now(timezone.utc) + timedelta(minutes=minutes)
    except OverflowError:
        raise RuntimeError("TOKEN_MINUTOS excede el rango de fechas admitido.") from None
    return minutes


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS")
    if raw is None:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    origins = []
    for entry in raw.split(","):
        origin = entry.strip()
        if not origin:
            continue
        message = "CORS_ORIGINS debe contener orígenes HTTP/HTTPS sin wildcard, credenciales, ruta, query ni fragmento."
        try:
            parsed = urlsplit(origin)
            port = parsed.port  # Valida puertos malformados o fuera de rango.
            invalid = (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path or parsed.query or parsed.fragment
                or "*" in origin or "\\" in origin
                or any(character.isspace() for character in origin)
                or "?" in origin or "#" in origin
                or parsed.netloc.endswith(":") or port == 0
            )
        except ValueError:
            raise RuntimeError(message) from None
        if invalid:
            raise RuntimeError(message)
        if origin not in origins:
            origins.append(origin)
    return origins


def database_url() -> str:
    value = required_value("DATABASE_URL")
    try:
        make_url(value)
    except (ArgumentError, ValueError):
        raise RuntimeError("DATABASE_URL debe ser una URL válida de SQLAlchemy.") from None
    return value


def database_engine_options(url: str, *, pooled: bool = True) -> dict:
    """Una configuración por engine; no abre conexiones ni altera la URL/TLS."""
    options = {"pool_pre_ping": True}
    pool_options = {
        "pool_size": integer_value("DB_POOL_SIZE"),
        "max_overflow": integer_value("DB_MAX_OVERFLOW", minimum=0),
        "pool_timeout": integer_value("DB_POOL_TIMEOUT"),
    }
    connect_timeout = integer_value("DB_CONNECT_TIMEOUT")
    # SQLite de pruebas usa otro pool y no admite connect_timeout de psycopg.
    if make_url(url).get_backend_name() == "postgresql":
        if pooled:
            options.update({key: value for key, value in pool_options.items() if value is not None})
        if connect_timeout is not None:
            options["connect_args"] = {"connect_timeout": connect_timeout}
    return options
