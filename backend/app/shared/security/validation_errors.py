"""TA-041: respuesta 422 de validación sin eco de los datos enviados.

Por defecto, FastAPI incluye en cada error el campo "input" (el valor recibido; si
falta un campo, el cuerpo completo) y "ctx". Así, un login o un alta de usuario con
datos inválidos devolvía la contraseña. Solo se conservan "loc", "msg" y "type":
dicen qué campo falló y por qué, sin el valor. Es el mismo formato que ya usan las
rutas de pedidos, clientes y optimización.
"""
from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

SAFE_ERROR_KEYS = ("loc", "msg", "type")


async def sanitized_validation_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    detail = [{key: item[key] for key in SAFE_ERROR_KEYS if key in item} for item in error.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        content={"detail": jsonable_encoder(detail)})