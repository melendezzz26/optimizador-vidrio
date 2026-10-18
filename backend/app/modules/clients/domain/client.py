from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewClient:
    name: str
    document_type: str | None
    document_number: str | None
    phone: str | None
    created_at: datetime


@dataclass(frozen=True)
class Client:
    client_id: int
    name: str
    document_type: str | None
    document_number: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
