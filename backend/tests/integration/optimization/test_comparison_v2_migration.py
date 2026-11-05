"""T-02 migration: real PostgreSQL, fixed historical schemas and protected downgrade."""
from functools import partial

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
import sqlalchemy as sa

from app.models import EjecucionOptimizacion
from app.modules.optimization.application.comparisons import AcceptComparison
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.infrastructure.comparison_uow import SqlComparisonUnitOfWork
from app.modules.optimization.infrastructure.comparison_v2_uow import SqlComparisonPersistenceUnitOfWork
from tests.integration.postgres_support import new_database, upgrade, schema_snapshot
from tests.integration.test_s1_rbac_migration import downgrade
from tests.model_contracts import current_metadata, historical_metadata
from tests.comparison_history import history_bytes, revision
from .test_runs import prepared  # noqa: F401
from .test_comparison_persistence import save, finish
from .test_comparison_v2_persistence import frozen_input

PREVIOUS = "s2cmp01a1b2c"
REVISION = "s2cmp02d4e6f8"


def test_empty_upgrade_changes_only_method_check_and_matches_current_orm(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, PREVIOUS).returncode == 0
        tables = sorted(sa.inspect(engine).get_table_names())
        before = schema_snapshot(engine, tables)
        with engine.connect() as c:
            assert compare_metadata(MigrationContext.configure(c), historical_metadata(PREVIOUS)) == []
        assert upgrade(engine, "head").returncode == 0
        assert revision(engine) == REVISION
        after = schema_snapshot(engine, tables)
        assert sorted(sa.inspect(engine).get_table_names()) == tables
        for table in tables:
            if table == "ejecuciones_optimizacion":
                for field in ("columns", "pk", "fk", "unique", "indexes"):
                    assert after[table][field] == before[table][field]
                check = next(c["sqltext"] for c in after[table]["check"] if c["name"] == "ck_ejecuciones_metodo")
                assert all(code in check for code in ("FF", "BF", "WF", "HF", "M5", "M6-BS"))
            else:
                assert after[table] == before[table]
        with engine.connect() as c:
            assert compare_metadata(MigrationContext.configure(c, opts={"compare_type": True,
                "compare_server_default": True}), current_metadata()) == []
        assert downgrade(engine, PREVIOUS).returncode == 0
        assert schema_snapshot(engine, tables) == before
        assert upgrade(engine, REVISION).returncode == 0


def test_history_created_before_upgrade_preserves_ff_snapshot1_and_comparison_snapshot2(session_factory, prepared, monkeypatch):
    engine = session_factory.kw["bind"]
    assert downgrade(engine, PREVIOUS).returncode == 0
    actor, ids, run_factory = prepared
    comparison_factory = partial(SqlComparisonUnitOfWork, session_factory)
    # Different orders; no synthetic expansion of the historical three-method record.
    run = AcceptRun(run_factory).execute(ids[:1], actor)
    from app.modules.optimization.application.calculation import CalculateRun
    from app.modules.inventory.infrastructure.repository import SqlAlchemyInventoryRepository
    from app.modules.optimization.infrastructure.stock_adapter import InventoryStockAdapter
    run = CalculateRun(run_factory, InventoryStockAdapter(SqlAlchemyInventoryRepository(session_factory))).execute(run.optimization_id)
    assert run.result.complete
    current = AcceptComparison(comparison_factory).execute(ids[1:], actor, "b02-before-upgrade")
    for method in ("FF", "BF", "WF"):
        current = save(comparison_factory, current, method)
    current = finish(comparison_factory, current)
    with run_factory() as tx:
        original_ff = tx.runs.get(run.optimization_id)
    before = history_bytes(engine)
    assert upgrade(engine, REVISION).returncode == 0
    from app.modules.optimization.application.comparison_catalog import CATALOG_V2
    def forbidden(*args, **kwargs):
        pytest.fail("Historical reads cannot recalculate")
    for method in CATALOG_V2:
        monkeypatch.setattr(method.optimizer_type, "optimize", forbidden)
    factory = partial(SqlComparisonPersistenceUnitOfWork, session_factory)
    with factory() as tx:
        assert tx.comparisons_v2.get_compatible(current.comparison_id) == current
        assert tx.comparisons_v2.get_compatible(run.optimization_id) == original_ff
        assert len(tx.comparisons.get(current.comparison_id).executions) == 3
    assert history_bytes(engine) == before
    assert downgrade(engine, PREVIOUS).returncode == 0  # Compatible three-engine history is allowed.
    assert history_bytes(engine) == before and revision(engine) == PREVIOUS
    assert upgrade(engine, REVISION).returncode == 0


@pytest.mark.parametrize("incompatible", ["aggregate_v2", "new_method", "result_v3"])
def test_downgrade_rejects_incompatible_data_before_any_schema_change(session_factory, prepared, incompatible):
    actor, ids, _ = prepared
    engine = session_factory.kw["bind"]
    assert upgrade(engine, REVISION).returncode == 0
    factory = partial(SqlComparisonPersistenceUnitOfWork, session_factory)
    if incompatible == "aggregate_v2":
        setup = actor, ids, factory
        with factory() as tx:
            tx.comparisons_v2.create(frozen_input(setup), actor, "b02-v2-downgrade")
    else:
        old = AcceptComparison(factory).execute(ids, actor, "b02-compatible-parent")
        with session_factory() as s:
            execution = s.get(EjecucionOptimizacion, old.executions[0].execution_id)
            if incompatible == "new_method":
                execution.metodo = "HF"
            else:
                execution.patron_resultado = {"snapshot": {"snapshot_version": 3}}
            s.commit()
    tables = ["optimizaciones", "ejecuciones_optimizacion", "optimizacion_pedidos"]
    before_schema, before_data = schema_snapshot(engine, tables), history_bytes(engine)
    result = downgrade(engine, PREVIOUS)
    assert result.returncode != 0 and "antes de DDL" in result.stderr
    assert revision(engine) == REVISION
    assert schema_snapshot(engine, tables) == before_schema and history_bytes(engine) == before_data
