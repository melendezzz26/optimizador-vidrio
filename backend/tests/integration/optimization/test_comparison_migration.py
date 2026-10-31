"""Migración aditiva y rechazo de downgrade con historia comparativa.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
"""
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import sqlalchemy as sa

from tests.integration.postgres_support import new_database, upgrade
from tests.integration.test_s1_rbac_migration import downgrade
from tests.model_contracts import current_metadata, historical_metadata
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.application.comparisons import AcceptComparison
from app.modules.optimization.infrastructure.comparison_uow import SqlComparisonUnitOfWork
from functools import partial
from .test_runs import prepared  # noqa: F401

PREVIOUS, REVISION = "s1opt02b4c6d", "s2cmp01a1b2c"


def test_schema_matches_orm_empty_downgrade_and_reupgrade(isolated_postgres):
    with new_database(isolated_postgres) as engine:
        assert upgrade(engine, REVISION).returncode == 0
        with engine.connect() as c:
            context = MigrationContext.configure(c, opts={"compare_type": True, "compare_server_default": True})
            assert compare_metadata(context, current_metadata()) == []
        assert downgrade(engine, PREVIOUS).returncode == 0
        with engine.connect() as c:
            context = MigrationContext.configure(c, opts={"compare_type": True, "compare_server_default": True})
            assert compare_metadata(context, historical_metadata(PREVIOUS)) == []
        assert upgrade(engine, REVISION).returncode == 0


def test_legacy_run_survives_roundtrip_without_reinterpretation(session_factory, prepared):
    actor, ids, uow = prepared
    run = AcceptRun(uow).execute(ids, actor)
    engine = session_factory.kw["bind"]
    assert downgrade(engine, PREVIOUS).returncode == 0
    assert upgrade(engine, REVISION).returncode == 0
    with uow() as tx:
        assert tx.runs.get(run.optimization_id) == run
    with engine.connect() as c:
        assert c.execute(sa.text("SELECT comparison_key, comparison_snapshot, comparison_version FROM optimizaciones")).one() == (None, None, 1)


def test_comparative_history_blocks_downgrade_before_any_ddl(session_factory, prepared):
    actor, ids, _ = prepared
    factory = partial(SqlComparisonUnitOfWork, session_factory)
    original = AcceptComparison(factory).execute(ids, actor, "migration-test-key")
    engine = session_factory.kw["bind"]
    result = downgrade(engine, PREVIOUS)
    assert result.returncode != 0 and "Downgrade perdería snapshots comparativos" in result.stderr
    with engine.connect() as c:
        assert c.scalar(sa.text("SELECT version_num FROM alembic_version")) == REVISION
    with factory() as tx:
        assert tx.comparisons.get(original.comparison_id) == original
