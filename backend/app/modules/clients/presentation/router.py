from contextlib import contextmanager
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.modules.authentication.presentation.dependencies import require_permission
from app.modules.clients.application import use_cases
from app.modules.clients.application.dto import CreateClientData
from app.modules.clients.application.ports import ClientRepository
from app.modules.clients.domain.errors import DuplicateClientDocumentError, InvalidClientDataError
from app.modules.clients.presentation.dependencies import get_client_repository
from app.modules.clients.presentation.schemas import ClientCreateRequest, ClientResponse

logger = logging.getLogger(__name__)


class ClientRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validate_request(request):
            try:
                return await handler(request)
            except RequestValidationError as error:
                # Igual que Orders: no reflejar entradas arbitrarias, credenciales
                # rechazadas o números no finitos en la respuesta de validación.
                detail = [{key: item[key] for key in ("loc", "msg", "type")}
                          for item in error.errors()]
                raise HTTPException(status_code=422, detail=detail) from error

        return validate_request


router = APIRouter(
    prefix="/api/clients",
    tags=["Clientes"],
    route_class=ClientRoute,
    # Preparación de pedidos: misma protección vigente que Orders, sin permisos nuevos.
    dependencies=[Depends(require_permission("GESTIONAR_PEDIDOS"))],
)


@contextmanager
def client_errors_as_http():
    try:
        yield
    except InvalidClientDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DuplicateClientDocumentError as error:
        raise HTTPException(
            status_code=409, detail="Ya existe un cliente con ese tipo y número de documento.",
        ) from error
    except Exception as error:
        logger.exception("Client operation failed")
        raise HTTPException(
            status_code=500, detail="No se pudo completar la operación de clientes. Inténtalo otra vez.",
        ) from error


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(data: ClientCreateRequest, repository: ClientRepository = Depends(get_client_repository)):
    with client_errors_as_http():
        client = use_cases.create_client(
            CreateClientData(
                name=data.nombre_razon_social,
                document_type=data.tipo_documento,
                document_number=data.numero_documento,
                phone=data.telefono,
            ),
            repository=repository,
        )
        return ClientResponse.from_domain(client)


@router.get("", response_model=list[ClientResponse])
def list_clients(
    document: str | None = Query(default=None, description="Número de documento exacto."),
    query: str | None = Query(default=None, description="Parte del nombre, sin distinguir mayúsculas."),
    repository: ClientRepository = Depends(get_client_repository),
):
    with client_errors_as_http():
        return [ClientResponse.from_domain(client) for client in use_cases.list_clients(
            repository=repository, document=document, query=query,
        )]
