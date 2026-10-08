from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, null
from datetime import datetime, timezone
from app.models import Pedido, Pieza, TipoVidrio, TipoVidrioEspesor
from ..application.ports import OrderRepositoryPort

class SQLAlchemyOrderRepository(OrderRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    def validate_catalog(self, id_tipo_vidrio: int, espesor_mm: float) -> bool:
        stmt = select(TipoVidrioEspesor).join(TipoVidrio).where(
            TipoVidrio.estado.is_(True),
            TipoVidrioEspesor.id_tipo_vidrio == id_tipo_vidrio,
            TipoVidrioEspesor.espesor_mm == espesor_mm
        )
        result = self.session.execute(stmt).scalars().first()
        return result is not None

    def create_order(self, id_usuario: int, id_tipo_vidrio: int, espesor_mm: float, piezas: List[Dict[str, Any]]) -> int:
        try:
            nuevo_pedido = Pedido(
                fecha_registro=datetime.now(timezone.utc),
                estado='PENDIENTE',
                espesor_mm=espesor_mm,
                id_tipo_vidrio=id_tipo_vidrio,
                id_usuario_registro=id_usuario
            )
            self.session.add(nuevo_pedido)
            self.session.flush()

            for p in piezas:
                nueva_pieza = Pieza(
                    tipo_forma=p['tipo_forma'],
                    cantidad=p['cantidad'],
                    dimensiones=p['dimensiones'] if p['dimensiones'] is not None else null(),
                    geometria=p['geometria'],
                    area_mm2=p['area_mm2'],
                    id_pedido=nuevo_pedido.id_pedido
                )
                self.session.add(nueva_pieza)

            # Capture before commit expires ORM attributes: no second DB read
            # may turn a successful commit into a reported failure.
            id_pedido = nuevo_pedido.id_pedido
            self.session.commit()
            return id_pedido
        except Exception:
            self.session.rollback()
            raise
