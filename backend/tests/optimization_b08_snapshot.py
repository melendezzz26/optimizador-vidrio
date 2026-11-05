"""Read-only B08 evidence from the owned E2E cluster; never a shared database."""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

import sqlalchemy as sa


def snapshot(identifier):
    state = json.loads((Path(tempfile.gettempdir()) / 'newglass-orders-e2e-8017.json').read_text())
    root = Path(state['root']).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith('newglass-orders-e2e-')
    url = sa.make_url(state['database_url'])
    assert url.host == '127.0.0.1' and url.username == 'r1_test' and url.database.startswith('r1_')
    assert (root / 'data/postmaster.pid').exists()
    os.environ['PYTHON_DOTENV_DISABLED'] = '1'
    os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
    os.environ['SECRET_KEY'] = secrets.token_urlsafe(48)
    from app.models import Plancha, Retazo, MovimientoInventario, Pedido, OptimizacionPedido, Optimizacion
    engine = sa.create_engine(url)
    try:
        with engine.connect() as connection:
            def rows(query):
                return [dict(row) for row in connection.execute(query).mappings()]
            return dict(
                sheets=rows(sa.select(Plancha.__table__).order_by(Plancha.id_plancha)),
                remnants=rows(sa.select(Retazo.__table__).order_by(Retazo.id_retazo)),
                movements=rows(sa.select(MovimientoInventario.__table__).order_by(MovimientoInventario.id_movimiento)),
                orders=rows(sa.select(Pedido.id_pedido, Pedido.estado).join(OptimizacionPedido,
                    OptimizacionPedido.id_pedido == Pedido.id_pedido).where(OptimizacionPedido.id_optimizacion == identifier).order_by(Pedido.id_pedido)),
                comparison=rows(sa.select(Optimizacion.id_optimizacion, Optimizacion.id_ejecucion_seleccionada,
                    Optimizacion.comparison_version, Optimizacion.comparison_snapshot).where(Optimizacion.id_optimizacion == identifier)))
    finally:
        engine.dispose()


if __name__ == '__main__':
    identifier = int(sys.argv[1])
    assert 0 < identifier <= 2147483647
    print(json.dumps(snapshot(identifier), default=str))
