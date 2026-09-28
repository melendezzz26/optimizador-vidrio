from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine

app = FastAPI(
    title="Optimizador de Corte de Vidrio",
    version="1.0.0"
)


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