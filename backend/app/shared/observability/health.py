"""Health público sin detalles internos ni cola de comprobaciones ilimitada."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])
READINESS_TIMEOUT_SECONDS = 3
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="readiness")
_available = BoundedSemaphore(1)


def check_database() -> bool:
    # Import diferido: live no carga persistencia ni necesita DATABASE_URL.
    from app.shared.database import engine

    with engine.connect() as connection:
        if engine.dialect.name == "postgresql":
            connection.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": str(int(READINESS_TIMEOUT_SECONDS * 1000))},
            )
        return connection.execute(text("SELECT 1")).scalar_one() == 1


def _check_and_release() -> bool:
    try:
        return check_database()
    finally:
        _available.release()


def _consume_result(future):
    # Un fallo posterior al plazo tampoco debe generar logs con datos de BD.
    if not future.cancelled():
        future.exception()


@router.get("/live")
def live():
    return {"status": "ok"}


@router.get("/ready", responses={503: {"description": "Dependencia no disponible"}})
async def ready():
    if _available.acquire(blocking=False):
        try:
            future = _executor.submit(_check_and_release)
        except Exception:
            _available.release()
        else:
            pending = asyncio.wrap_future(future)
            pending.add_done_callback(_consume_result)
            try:
                # No bloquear la respuesta durante checkout, conexión o consulta.
                # El trabajador conserva el permiso hasta terminar, incluso tras
                # timeout/cancelación HTTP: nunca se acumulan probes en la cola.
                if await asyncio.wait_for(asyncio.shield(pending), READINESS_TIMEOUT_SECONDS):
                    return {"status": "ready"}
            except Exception:
                pass
    return JSONResponse(status_code=503, content={"status": "not_ready"})
