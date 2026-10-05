from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.routers import auth
from app.modules.inventory.presentation.router import router as inventory_router

app = FastAPI(
    title="Optimizador de Corte de Vidrio",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas de autenticación (HU-001)
app.include_router(auth.router)
app.include_router(inventory_router)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend del optimizador de vidrio funcionando"
    }


@app.get("/db-test")
def probar_base_datos():
    from app.shared.database import engine
    with engine.connect() as conexion:
        resultado = conexion.execute(
            text("SELECT version();")
        )

        version = resultado.scalar()

    return {
        "conexion": "correcta",
        "postgresql": version
    }