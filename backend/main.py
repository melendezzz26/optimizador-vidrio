from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.modules.authentication.presentation.router import router as authentication_router
from app.modules.inventory.presentation.router import router as inventory_router
from app.modules.users.presentation.router import router as users_router
from app.modules.orders.presentation.router import router as orders_router

app = FastAPI(
    title="Optimizador de Corte de Vidrio",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rutas de autenticaciÃ³n (HU-001)
app.include_router(authentication_router)
# Rutas de inventario (TA-003)
app.include_router(inventory_router)
# Rutas de gestiÃ³n de usuarios (HU-003)
app.include_router(users_router)
# Rutas de pedidos (HU-007)
app.include_router(orders_router)


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
