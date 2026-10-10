from typing import List, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select, null, func, cast, Date
from datetime import datetime, timezone, date
from app.models import Pedido, Pieza, TipoVidrio, TipoVidrioEspesor, Cliente
from ..application.ports import OrderRepositoryPort

class SQLAlchemyOrderRepository(OrderRepositoryPort):
    def __init__(self, session: Session):
        self.session = session

    def validate_catalog(self, id_tipo_vidrio: int, espesor_mm: Decimal) -> bool:
        stmt = select(TipoVidrioEspesor).join(TipoVidrio).where(
            TipoVidrio.estado.is_(True),
            TipoVidrioEspesor.id_tipo_vidrio == id_tipo_vidrio,
            TipoVidrioEspesor.espesor_mm == espesor_mm
        )
        result = self.session.execute(stmt).scalars().first()
        return result is not None

    def create_order(self, id_usuario: int, piezas: List[Dict[str, Any]]) -> int:
        try:
            nuevo_pedido = Pedido(
                fecha_registro=datetime.now(timezone.utc),
                estado='PENDIENTE',
                id_usuario_registro=id_usuario
            )
            self.session.add(nuevo_pedido)
            self.session.flush()

            for p in piezas:
                nueva_pieza = Pieza(
                    id_tipo_vidrio=p['id_tipo_vidrio'],
                    espesor_mm=p['espesor_mm'],
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

    def get_order(self, id_pedido: int) -> Dict[str, Any] | None:
        # Un SELECT ofrece una vista consistente de cabecera e hijos, sin lazy
        # loading ni objetos ORM escapando del adaptador de persistencia.
        rows = self.session.execute(
            select(Pedido, Pieza).outerjoin(Pieza, Pieza.id_pedido == Pedido.id_pedido)
            .where(Pedido.id_pedido == id_pedido).order_by(Pieza.id_pieza)
        ).all()
        if not rows:
            return None
        order = rows[0][0]
        return {
            "id_pedido": order.id_pedido,
            "fecha_registro": order.fecha_registro,
            "estado": order.estado,
            "id_usuario_registro": order.id_usuario_registro,
            "piezas": [{
                "id_pieza": piece.id_pieza, "id_pedido": piece.id_pedido,
                "id_tipo_vidrio": piece.id_tipo_vidrio, "espesor_mm": piece.espesor_mm,
                "tipo_forma": piece.tipo_forma, "cantidad": piece.cantidad,
                "dimensiones": piece.dimensiones, "geometria": piece.geometria,
                "area_mm2": piece.area_mm2,
            } for _, piece in rows if piece is not None],
        }

    def list_orders(self, limit: int, offset: int, estado: str | None = None, cliente: str | None = None, fecha: date | None = None) -> dict:
        
        conditions = []
        if estado:
            conditions.append(Pedido.estado == estado)
        if fecha:
            conditions.append(cast(Pedido.fecha_registro, Date) == fecha)
        if cliente:
            conditions.append(Cliente.nombre_razon_social.ilike(f"%{cliente}%"))

        # Consulta base
        stmt = select(Pedido, Cliente.nombre_razon_social).outerjoin(Cliente, Pedido.id_cliente == Cliente.id_cliente)
        count_stmt = select(func.count(Pedido.id_pedido)).outerjoin(Cliente, Pedido.id_cliente == Cliente.id_cliente)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        # 1. Obtenemos el total de registros (para la paginación)
        total = self.session.execute(count_stmt).scalar() or 0

        # 2. Obtenemos los registros con límite y offset
        stmt = stmt.order_by(Pedido.fecha_registro.desc()).offset(offset).limit(limit)
        rows = self.session.execute(stmt).all()

        items = []
        for order, cliente_nombre in rows:
            items.append({
                "id_pedido": order.id_pedido,
                "fecha_registro": order.fecha_registro,
                "estado": order.estado,
                "cliente": cliente_nombre or "Consumidor Final" # Por si el id_cliente es nulo
            })

        return {"total": total, "items": items}
