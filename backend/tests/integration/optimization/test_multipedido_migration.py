"""Linear migration on local PostgreSQL: history, constraints and safe rollback."""
import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from tests.integration.postgres_support import BACKEND, new_database, upgrade
from tests.integration.test_s1_rbac_migration import downgrade
from tests.model_contracts import current_metadata
from app.models import OptimizacionPedido

PREVIOUS = 's1rbac01a2b3'
REVISION = 's1opt02b4c6d'


def test_linear_head():
    config = Config(str(BACKEND / 'alembic.ini'))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == [REVISION]
    assert scripts.get_revision(REVISION).down_revision == PREVIOUS


def test_upgrade_matches_orm_and_empty_downgrade(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        result = upgrade(engine, REVISION)
        assert result.returncode == 0, result.stderr
        with engine.connect() as c:
            assert compare_metadata(MigrationContext.configure(c, opts={'compare_type': True, 'compare_server_default': True}), current_metadata()) == []
        assert downgrade(engine, PREVIOUS).returncode == 0
        assert 'optimizacion_pedidos' not in sa.inspect(engine).get_table_names()
        assert upgrade(engine, REVISION).returncode == 0


def test_legacy_backfill_and_safe_downgrade(session_factory, prepared):
    from app.models import Optimizacion
    from datetime import datetime, timezone
    actor, ids, _ = prepared
    engine = session_factory.kw['bind']
    assert downgrade(engine, PREVIOUS).returncode == 0
    with session_factory() as s:
        row = Optimizacion(fecha_inicio=datetime.now(timezone.utc), estado='FALLIDA', id_pedido=ids[0],
                          id_configuracion=1, id_usuario_ejecutor=actor, criterio_seleccion_version='legacy')
        s.add(row)
        s.commit()
        identifier = row.id_optimizacion
    assert upgrade(engine, REVISION).returncode == 0
    with session_factory() as s:
        assert s.get(OptimizacionPedido, (identifier, ids[0])) is not None
    assert downgrade(engine, PREVIOUS).returncode == 0
    assert upgrade(engine, REVISION).returncode == 0


@pytest.mark.parametrize('kind', ['unique', 'fk_order', 'fk_run', 'downgrade'])
def test_constraints_and_no_loss(session_factory, prepared, kind):
    from app.modules.optimization.application.runs import AcceptRun
    actor, ids, uow = prepared
    run = AcceptRun(uow).execute(ids, actor)
    engine = session_factory.kw['bind']
    if kind == 'downgrade':
        result = downgrade(engine, PREVIOUS)
        assert result.returncode != 0 and 'Downgrade perdería' in result.stderr
        with engine.connect() as c:
            assert c.scalar(sa.text('SELECT count(*) FROM optimizacion_pedidos')) == 2
            assert c.scalar(sa.text('SELECT version_num FROM alembic_version')) == REVISION
        return
    with session_factory() as s, pytest.raises(sa.exc.IntegrityError):
        s.add(OptimizacionPedido(id_optimizacion=9999 if kind == 'fk_run' else run.optimization_id,
                                id_pedido=9999 if kind == 'fk_order' else ids[0]))
        s.commit()


# Reuse synthetic data without coupling production modules.
from .test_runs import prepared  # noqa: E402,F401
