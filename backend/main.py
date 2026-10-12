from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.shared.config import cors_origins
from app.shared.observability.health import router as health_router

from app.modules.authentication.presentation.router import router as authentication_router
from app.modules.inventory.presentation.router import router as inventory_router
from app.modules.users.presentation.router import router as users_router
from app.modules.orders.presentation.router import router as orders_router
from app.modules.clients.presentation.router import router as clients_router

app = FastAPI(
    title="Optimizador de Corte de Vidrio",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "PUT"],
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
# Rutas de consulta y alta de clientes (HU-012 T02)
app.include_router(clients_router)
app.include_router(health_router)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend del optimizador de vidrio funcionando"
    }
