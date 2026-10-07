import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Pedido, Pieza, TipoVidrio, TipoVidrioEspesor, Rol, Usuario
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository

@pytest.fixture
def repo(db_session: Session):
    return SQLAlchemyOrderRepository(db_session)

@pytest.fixture
def setup_data(db_session: Session):
    rol = Rol(nombre="TestRole")
    db_session.add(rol)
    db_session.commit()

    user = Usuario(dni="12345678", nombres="Test", apellidos="User", usuario="T12345678", password_hash="hash", id_rol=rol.id_rol)
    tipo = TipoVidrio(nombre="Claro Test")
    db_session.add_all([user, tipo])
    db_session.commit()

    espesor = TipoVidrioEspesor(id_tipo_vidrio=tipo.id_tipo_vidrio, espesor_mm=6.0)
    db_session.add(espesor)
    db_session.commit()
    
    return {
        "id_usuario": user.id_usuario,
        "id_tipo_vidrio": tipo.id_tipo_vidrio,
        "espesor_mm": 6.0
    }

def test_validate_catalog_valid(repo, setup_data):
    assert repo.validate_catalog(setup_data["id_tipo_vidrio"], 6.0) is True

def test_validate_catalog_invalid(repo, setup_data):
    assert repo.validate_catalog(setup_data["id_tipo_vidrio"], 99.0) is False
    assert repo.validate_catalog(99, 6.0) is False

def test_create_order_success(repo, db_session, setup_data):
    piezas = [
        {
            "tipo_forma": "POLIGONO_CONVEXO",
            "cantidad": 2,
            "dimensiones": None,
            "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0,0], [10,0], [0,10]]},
            "area_mm2": 50.0
        }
    ]
    id_pedido = repo.create_order(setup_data["id_usuario"], setup_data["id_tipo_vidrio"], 6.0, piezas)
    
    pedido = db_session.query(Pedido).filter_by(id_pedido=id_pedido).first()
    assert pedido is not None
    assert pedido.estado == 'PENDIENTE'
    
    piezas_db = db_session.query(Pieza).filter_by(id_pedido=id_pedido).all()
    assert len(piezas_db) == 1
    assert piezas_db[0].cantidad == 2
    assert piezas_db[0].tipo_forma == 'POLIGONO_CONVEXO'

def test_create_order_rollback(repo, db_session, setup_data):
    piezas = [
        {
            "tipo_forma": "POLIGONO_CONVEXO",
            "cantidad": 2,
            # Faltan datos requeridos para forzar excepcion (e.g. area_mm2)
            "dimensiones": None,
            "geometria": {"type": "POLIGONO_CONVEXO", "vertices_mm": [[0,0], [10,0], [0,10]]}
        }
    ]
    with pytest.raises(Exception):
        repo.create_order(setup_data["id_usuario"], setup_data["id_tipo_vidrio"], 6.0, piezas)
    
    # Confirmar rollback (el pedido no se guardó)
    pedidos = db_session.query(Pedido).filter_by(id_usuario_registro=setup_data["id_usuario"]).all()
    assert len(pedidos) == 0
