from dataclasses import dataclass


@dataclass(frozen=True)
class CreateClientData:
    name: str
    document_type: str | None = None
    document_number: str | None = None
    phone: str | None = None
