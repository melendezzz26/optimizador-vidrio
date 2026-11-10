"""TA-QA-006: matriz de seguridad rol × ruta protegida (SPEC §5.2, CA-01 a CA-03).

Cubre las 59 rutas protegidas con los tres roles reales y sus permisos de la
asignación inicial (ASIGNACION_INICIAL), leídos en memoria:
- cada ruta declara el permiso de la matriz (RN-06);
- sin token responde 401 (RN-01);
- el rol sin permiso recibe 403 y el rol con permiso pasa la autorización (RN-02);
- ante un 401 o 403 no se invoca ningún servicio ni repositorio (RN-03);
- los cuerpos 401 y 403 solo traen el mensaje fijo (RN-05).

Los servicios y repositorios se sustituyen por espías sin datos: cuando la
autorización deja pasar, la respuesta puede ser 404, 422 o 500 seguro (D-02).
Corre en Windows: no necesita PostgreSQL.
"""
import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from starlette.routing import compile_path

from app.core.permissions import ASIGNACION_INICIAL, CODIGOS
from app.modules.authentication.presentation.dependencies import (
    FORBIDDEN_MESSAGE,
    get_current_user,
    get_permission_reader,
    get_user_reader,
)
from main import app
from tests.auth_support import token_for, use_in_memory_accounts

ADMIN, WAREHOUSE, OPERATOR = "Administrador", "Almacenero", "Operario"
ROLES = (ADMIN, WAREHOUSE, OPERATOR)
LOGIN_REQUIRED_MESSAGE = "Debes iniciar sesión."
MASK = "0" * 32
KEY = "solicitud-0001"
OPT = "/api/optimization"

# (método, ruta concreta, permiso exigido o None si solo exige sesión, ruta crítica)
ROUTES = [
    ("GET", "/api/auth/me", None, False),
    # Usuarios y roles
    ("GET", "/api/users", "users.view", True),
    ("GET", "/api/users/roles", "users.view", True),
    ("GET", "/api/users/1", "users.view", True),
    ("POST", "/api/users", "users.manage", True),
    ("PATCH", "/api/users/1", "users.manage", True),
    ("GET", "/api/roles", "roles.view", True),
    ("GET", "/api/permissions", "roles.view", True),
    ("PUT", "/api/roles/1/permissions", "roles.manage", True),
    # Inventario: lectura
    ("GET", "/api/inventory/tipos-vidrio", "inventory.view", False),
    ("GET", "/api/inventory/planchas", "inventory.view", False),
    ("GET", "/api/inventory/planchas/1/movimientos", "inventory.view", False),
    ("GET", "/api/inventory/retazos", "inventory.view", False),
    ("GET", "/api/inventory/retazos/1/movimientos", "inventory.view", False),
    ("GET", "/api/inventory/retazos/1/origen", "inventory.view", False),
    # Inventario: escritura y bajas
    ("POST", "/api/inventory/tipos-vidrio", "inventory.manage", True),
    ("POST", "/api/inventory/planchas", "inventory.manage", True),
    ("PATCH", "/api/inventory/planchas/1", "inventory.manage", True),
    ("POST", "/api/inventory/planchas/1/baja", "inventory.manage", True),
    ("POST", "/api/inventory/retazos", "inventory.manage", True),
    ("PATCH", "/api/inventory/retazos/1", "inventory.manage", True),
    ("POST", "/api/inventory/retazos/1/baja", "inventory.manage", True),
    # Pedidos y clientes
    ("GET", "/api/orders", "orders.view", False),
    ("GET", "/api/orders/1", "orders.view", False),
    ("GET", "/api/clients", "orders.view", False),
    ("POST", "/api/orders", "orders.create", True),
    ("POST", "/api/orders/import/preview", "orders.create", True),
    ("POST", "/api/orders/import/validate", "orders.create", True),
    ("POST", "/api/clients", "orders.create", True),
    ("PUT", "/api/orders/1", "orders.update", True),
    ("DELETE", "/api/orders/1", "orders.cancel", True),
    # Optimización: inicio
    ("POST", f"{OPT}/start", "optimization.execute", False),
    ("POST", f"{OPT}/rasterize", "optimization.execute", False),
    ("POST", f"{OPT}/runs", "optimization.execute", False),
    ("POST", f"{OPT}/comparisons", "optimization.execute", False),
    ("POST", f"{OPT}/comparisons-v2", "optimization.execute", False),
    # Selección y liberación
    ("PUT", f"{OPT}/comparisons/1/selection", "optimization.execute", True),
    ("PUT", f"{OPT}/comparisons-v2/1/selection", "optimization.execute", True),
    ("POST", f"{OPT}/comparisons/1/release", "optimization.execute", True),
    ("POST", f"{OPT}/comparisons-v2/1/release", "optimization.execute", True),
    # Confirmación de cortes
    ("POST", f"{OPT}/runs/1/confirm", "optimization.confirm", True),
    ("POST", f"{OPT}/comparisons/1/confirm", "optimization.confirm", True),
    ("POST", f"{OPT}/comparisons-v2/1/confirm", "optimization.confirm", True),
    # Resultados: lectura
    ("GET", f"{OPT}/runs/1", "optimization.view", False),
    ("GET", f"{OPT}/runs/1/visual", "optimization.view", False),
    ("GET", f"{OPT}/runs/1/visual/masks/{MASK}", "optimization.view", False),
    ("GET", f"{OPT}/comparisons/requests/{KEY}", "optimization.view", False),
    ("GET", f"{OPT}/comparisons/1", "optimization.view", False),
    ("GET", f"{OPT}/comparisons/1/executions/1", "optimization.view", False),
    ("GET", f"{OPT}/comparisons/1/events", "optimization.view", False),
    ("GET", f"{OPT}/comparisons/1/executions/1/visual", "optimization.view", False),
    ("GET", f"{OPT}/comparisons/1/executions/1/visual/masks/{MASK}", "optimization.view", False),
    ("GET", f"{OPT}/comparisons-v2/requests/{KEY}", "optimization.view", False),
    ("GET", f"{OPT}/comparisons-v2/history", "optimization.view", False),
    ("GET", f"{OPT}/comparisons-v2/1", "optimization.view", False),
    ("GET", f"{OPT}/comparisons-v2/1/executions/1", "optimization.view", False),
    ("GET", f"{OPT}/comparisons-v2/1/events", "optimization.view", False),
    ("GET", f"{OPT}/comparisons-v2/1/executions/1/visual", "optimization.view", False),
    ("GET", f"{OPT}/comparisons-v2/1/executions/1/visual/masks/{MASK}", "optimization.view", False),
]

# Matriz §5.2 de la SPEC: roles que pasan la autorización con cada permiso.
EVERYONE = frozenset(ROLES)
ADMIN_ONLY = frozenset({ADMIN})
ADMIN_AND_WAREHOUSE = frozenset({ADMIN, WAREHOUSE})
ADMIN_AND_OPERATOR = frozenset({ADMIN, OPERATOR})
EXPECTED_ROLES = {
    None: EVERYONE,
    "users.view": ADMIN_ONLY,
    "users.manage": ADMIN_ONLY,
    "roles.view": ADMIN_ONLY,
    "roles.manage": ADMIN_ONLY,
    "inventory.view": EVERYONE,
    "inventory.manage": ADMIN_AND_WAREHOUSE,
    "orders.view": ADMIN_AND_OPERATOR,
    "orders.create": ADMIN_AND_OPERATOR,
    "orders.update": ADMIN_AND_OPERATOR,
    "orders.cancel": ADMIN_AND_OPERATOR,
    "optimization.view": EVERYONE,
    "optimization.execute": ADMIN_AND_OPERATOR,
    "optimization.confirm": ADMIN_AND_OPERATOR,
}

# Marcas de información interna que nunca deben llegar al cliente (RN-05).
INTERNAL_MARKERS = ("Traceback", 'File "', "sqlalchemy", "psycopg", "SELECT ")


def route_id(route) -> str:
    method, path, *_ = route
    return f"{method} {path}"


def uses_run_permission(path: str) -> bool:
    """Las rutas de runs y comparisons usan run_permission y el formato de RunRoute."""
    return path.startswith((f"{OPT}/runs", f"{OPT}/comparisons"))


def expected_error(path: str, code: str, message: str) -> dict:
    """Cuerpo exacto de un 401/403 según el camino de autorización (RN-04)."""
    if uses_run_permission(path):
        return {"detail": {"code": code, "message": message}}
    return {"detail": message}


def assert_safe_error(response, path: str, code: str, message: str) -> None:
    """RN-05: solo el mensaje fijo; sin stack trace, SQL ni código de permiso."""
    assert response.json() == expected_error(path, code, message), response.text
    for marker in INTERNAL_MARKERS:
        assert marker not in response.text
    for permission in CODIGOS:
        assert permission not in response.text


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class Spy:
    """Doble sin datos: registra cualquier uso y falla, como un servicio vacío.

    Construirlo no cuenta como uso (observación O-01 de la SPEC): solo cuenta
    leer un atributo o llamarlo, que es lo que haría una escritura real.
    """

    def __init__(self, name: str, calls: list[str]) -> None:
        self._name = name
        self._calls = calls

    def __getattr__(self, attribute: str):
        if attribute.startswith("__"):
            raise AttributeError(attribute)
        self._calls.append(f"{self._name}.{attribute}")
        raise LookupError("Doble sin datos en esta prueba")

    def __call__(self, *args, **kwargs):
        self._calls.append(f"{self._name}()")
        raise LookupError("Doble sin datos en esta prueba")


def spied_dependencies() -> list:
    """Todas las dependencias de servicio y repositorio de las 59 rutas."""
    from app.modules.clients.presentation.dependencies import get_client_repository
    from app.modules.inventory.presentation.dependencies import get_inventory_service
    from app.modules.optimization.presentation.comparison_routes import (
        get_comparison_runtime,
        get_comparison_uow,
    )
    from app.modules.optimization.presentation.comparison_supervision_v2 import (
        get_comparison_v2_coordinator,
    )
    from app.modules.optimization.presentation.comparison_v2_routes import get_comparison_v2_uow
    from app.modules.optimization.presentation.dependencies import (
        get_rasterize_use_case,
        get_start_use_case,
    )
    from app.modules.optimization.presentation.run_routes import (
        get_run_admission,
        get_run_calculator,
        get_run_unit_of_work,
        get_stock_counter,
        get_visual_store,
    )
    from app.modules.orders.presentation.dependencies import (
        get_cancel_order_use_case,
        get_create_order_use_case,
        get_list_orders_use_case,
        get_order_use_case,
        get_update_order_use_case,
    )
    from app.modules.users.presentation.dependencies import (
        get_role_permission_repository,
        get_user_repository,
    )

    return [
        get_inventory_service, get_user_repository, get_role_permission_repository,
        get_client_repository, get_create_order_use_case, get_order_use_case,
        get_list_orders_use_case, get_update_order_use_case, get_cancel_order_use_case,
        get_start_use_case, get_rasterize_use_case, get_run_unit_of_work, get_run_calculator,
        get_stock_counter, get_run_admission, get_visual_store, get_comparison_uow,
        get_comparison_runtime, get_comparison_v2_uow, get_comparison_v2_coordinator,
    ]


def _spy_factory(name: str, calls: list[str]):
    # Función sin parámetros: FastAPI tomaría cualquier parámetro como dato de la petición.
    def factory():
        return Spy(name, calls)
    return factory


@pytest.fixture
def secured_client():
    """Cliente con cuentas en memoria, permisos de ASIGNACION_INICIAL y espías.

    Devuelve el cliente y la lista de usos de los espías de esa petición.
    """
    from app.modules.optimization.presentation.run_auth import (
        get_run_permission_reader,
        get_run_user_reader,
    )

    previous = dict(app.dependency_overrides)
    calls: list[str] = []
    use_in_memory_accounts(app)
    app.dependency_overrides[get_run_user_reader] = app.dependency_overrides[get_user_reader]
    app.dependency_overrides[get_run_permission_reader] = app.dependency_overrides[get_permission_reader]
    for dependency in spied_dependencies():
        app.dependency_overrides[dependency] = _spy_factory(dependency.__name__, calls)
    try:
        yield TestClient(app, raise_server_exceptions=False), calls
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def resolved_api_routes(routes=None, prefix: str = ""):
    """Recorre las rutas de la aplicación y devuelve (path resuelto, APIRoute), en orden.

    Desde FastAPI 0.141, ``include_router`` guarda cada router incluido como un
    ``_IncludedRouter`` con ``original_router`` (el APIRouter con sus rutas) e
    ``include_context.prefix`` (prefijo que agrega quien lo incluye). Los prefijos
    se concatenan al anidar routers, igual que ``_RouterIncludeContext.combine``,
    y el path resuelto es prefijo + ``route.path`` (``path_for``).
    """
    for route in app.routes if routes is None else routes:
        if isinstance(route, APIRoute):
            yield prefix + route.path, route
            continue
        included_router = getattr(route, "original_router", None)
        if included_router is not None:
            yield from resolved_api_routes(included_router.routes, prefix + route.include_context.prefix)


def matching_route(method: str, path: str) -> tuple[str, APIRoute]:
    """Primera ruta que atiende la petición, en el mismo orden que el enrutamiento real."""
    for resolved_path, route in resolved_api_routes():
        path_regex, _, _ = compile_path(resolved_path)
        if path_regex.match(path) and method in route.methods:
            return resolved_path, route
    pytest.fail(f"Ninguna ruta de la aplicación atiende {method} {path}")


def dependency_calls(route) -> list:
    pending, found = list(route.dependant.dependencies), []
    while pending:
        dependency = pending.pop()
        found.append(dependency.call)
        pending.extend(dependency.dependencies)
    return found


def declared_permissions(route) -> set[str]:
    """Permisos que exige la ruta (require_permission y run_permission los exponen)."""
    return {call.permission for call in dependency_calls(route) if hasattr(call, "permission")}


def is_protected(route) -> bool:
    """Exige un permiso o, al menos, una sesión válida."""
    return bool(declared_permissions(route)) or get_current_user in dependency_calls(route)


# --- Coherencia de la matriz con la SPEC y con ASIGNACION_INICIAL ---

def test_matrix_has_the_totals_of_the_spec():
    """SPEC §5.2: 59 rutas, 28 críticas y 44 rechazos (Almacenero 29, Operario 15)."""
    assert len(ROUTES) == 59
    assert len({(method, path) for method, path, *_ in ROUTES}) == 59
    assert sum(critical for *_, critical in ROUTES) == 28
    denied = {role: sum(role not in EXPECTED_ROLES[permission] for _, _, permission, _ in ROUTES)
              for role in ROLES}
    assert denied == {ADMIN: 0, WAREHOUSE: 29, OPERATOR: 15}
    assert {permission for _, _, permission, _ in ROUTES} - {None} == CODIGOS


def test_expected_roles_are_the_initial_assignment():
    """El resultado esperado de la matriz se deriva de ASIGNACION_INICIAL."""
    for code in CODIGOS:
        derived = {role for role in ROLES if code in ASIGNACION_INICIAL[role]}
        assert derived == EXPECTED_ROLES[code], code


# --- RN-06: permiso declarado en cada ruta ---

def test_matrix_covers_exactly_the_protected_routes_of_the_app():
    """La aplicación tiene exactamente 59 rutas protegidas y son las de la matriz."""
    protected = {(method, resolved_path)
                 for resolved_path, route in resolved_api_routes() if is_protected(route)
                 for method in route.methods}
    assert len(protected) == 59, sorted(protected)
    matrix = {(method, matching_route(method, path)[0]) for method, path, *_ in ROUTES}
    assert matrix == protected


@pytest.mark.parametrize("method, path, permission, critical", ROUTES, ids=[route_id(r) for r in ROUTES])
def test_each_route_declares_the_permission_of_the_matrix(method, path, permission, critical):
    _, route = matching_route(method, path)
    if permission is None:
        assert declared_permissions(route) == set()
        assert get_current_user in dependency_calls(route)
    else:
        assert declared_permissions(route) == {permission}


# --- RN-01, RN-03 y RN-05: sin token ---

@pytest.mark.parametrize("method, path, permission, critical", ROUTES, ids=[route_id(r) for r in ROUTES])
def test_without_a_token_every_protected_route_answers_401(secured_client, method, path, permission, critical):
    client, calls = secured_client
    response = client.request(method, path)
    assert response.status_code == 401, response.text
    assert response.headers.get("www-authenticate") == "Bearer"
    assert_safe_error(response, path, "UNAUTHENTICATED", LOGIN_REQUIRED_MESSAGE)
    assert calls == []


# --- RN-02, RN-03 y RN-05: cada rol frente a cada ruta ---

@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("method, path, permission, critical", ROUTES, ids=[route_id(r) for r in ROUTES])
def test_each_role_gets_the_result_of_the_matrix(secured_client, method, path, permission, critical, role):
    client, calls = secured_client
    response = client.request(method, path, headers=bearer(token_for(role)))
    if role in EXPECTED_ROLES[permission]:
        assert response.status_code not in (401, 403), response.text
    else:
        assert response.status_code == 403, response.text
        assert_safe_error(response, path, "FORBIDDEN", FORBIDDEN_MESSAGE)
        assert calls == []
