from datetime import datetime, timezone

from app.modules.clients.application.dto import CreateClientData
from app.modules.clients.application.ports import ClientRepository, Clock
from app.modules.clients.domain.client import Client, NewClient
from app.modules.clients.domain.rules import optional_text, required_text


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_client(
    data: CreateClientData, *, repository: ClientRepository, now: Clock = utc_now,
) -> Client:
    name = required_text(data.name, "nombre_razon_social")
    document_type = optional_text(data.document_type, "tipo_documento")
    document_number = optional_text(data.document_number, "numero_documento")
    phone = optional_text(data.phone, "telefono")
    created_at = now()
    if not isinstance(created_at, datetime) or created_at.utcoffset() is None:
        raise ValueError("El reloj debe devolver una fecha con zona horaria.")
    return repository.add(NewClient(
        name=name,
        document_type=document_type,
        document_number=document_number,
        phone=phone,
        created_at=created_at.astimezone(timezone.utc),
    ))


def list_clients(
    *, repository: ClientRepository, document: str | None = None, query: str | None = None,
) -> list[Client]:
    return repository.list_clients(
        document=None if document is None else required_text(document, "document"),
        query=None if query is None else required_text(query, "query"),
    )
