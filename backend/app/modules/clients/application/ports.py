from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from app.modules.clients.domain.client import Client, NewClient

Clock = Callable[[], datetime]


class ClientRepository(Protocol):
    """El adaptador confirma cada alta o la revierte, como Orders.

    La restricción de documento decide duplicados, incluso con concurrencia.
    Se devuelven datos desconectados del ORM. El listado incluye ambos estados,
    ordenado por ID; los filtros simultáneos se combinan con AND.
    """

    def add(self, client: NewClient) -> Client:
        """Puede lanzar DuplicateClientDocumentError por la pareja documental."""
        ...

    def list_clients(self, *, document: str | None, query: str | None) -> list[Client]:
        """Documento exacto; nombre parcial literal sin distinguir mayúsculas."""
        ...
