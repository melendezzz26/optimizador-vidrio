from datetime import datetime

from pydantic import BaseModel, StrictStr

from app.modules.clients.domain.client import Client


class ClientCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    nombre_razon_social: StrictStr
    tipo_documento: StrictStr | None = None
    numero_documento: StrictStr | None = None
    telefono: StrictStr | None = None


class ClientResponse(BaseModel):
    id_cliente: int
    tipo_documento: str | None
    numero_documento: str | None
    nombre_razon_social: str
    telefono: str | None
    estado: bool
    fecha_registro: datetime

    @classmethod
    def from_domain(cls, client: Client) -> "ClientResponse":
        return cls(
            id_cliente=client.client_id,
            tipo_documento=client.document_type,
            numero_documento=client.document_number,
            nombre_razon_social=client.name,
            telefono=client.phone,
            estado=client.is_active,
            fecha_registro=client.created_at,
        )
