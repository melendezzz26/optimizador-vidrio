from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Cliente
from app.modules.clients.domain.client import Client, NewClient
from app.modules.clients.domain.errors import DuplicateClientDocumentError


class SqlAlchemyClientRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, client: NewClient) -> Client:
        row = Cliente(
            nombre_razon_social=client.name,
            tipo_documento=client.document_type,
            numero_documento=client.document_number,
            telefono=client.phone,
            estado=True,
            fecha_registro=client.created_at,
        )
        try:
            self._session.add(row)
            self._session.flush()
            # Capturar antes de commit: la expiración del ORM no debe generar
            # otra consulta capaz de reportar como fallida un alta ya confirmada.
            result = self._to_client(row)
            self._session.commit()
            return result
        except IntegrityError as error:
            self._session.rollback()
            original = error.orig
            constraint = getattr(getattr(original, "diag", None), "constraint_name", None)
            if (getattr(original, "sqlstate", None) == "23505"
                    and constraint == "uq_clientes_tipo_numero_documento"):
                raise DuplicateClientDocumentError() from error
            raise
        except Exception:
            self._session.rollback()
            raise

    def list_clients(self, *, document: str | None = None, query: str | None = None) -> list[Client]:
        statement = select(Cliente).order_by(Cliente.id_cliente)
        if document is not None:
            statement = statement.where(Cliente.numero_documento == document)
        if query is not None:
            statement = statement.where(Cliente.nombre_razon_social.icontains(query, autoescape=True))
        return [self._to_client(row) for row in self._session.scalars(statement)]

    @staticmethod
    def _to_client(row: Cliente) -> Client:
        return Client(
            client_id=row.id_cliente,
            name=row.nombre_razon_social,
            document_type=row.tipo_documento,
            document_number=row.numero_documento,
            phone=row.telefono,
            is_active=row.estado,
            created_at=row.fecha_registro,
        )
