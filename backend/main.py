from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.shared.database import engine
from app.modules.authentication.presentation.router import router as authentication_router

app = FastAPI(
    title="Optimizador de Corte de Vidrio",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rutas de autenticación (HU-001)
app.include_router(authentication_router)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend del optimizador de vidrio funcionando"
    }


@app.get("/db-test")
def probar_base_datos():
    with engine.connect() as conexion:
        resultado = conexion.execute(
            text("SELECT version();")
        )

        version = resultado.scalar()

    return {
        "conexion": "correcta",
        "postgresql": version
    }