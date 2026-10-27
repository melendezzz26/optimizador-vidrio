"""The demo seed runs on migrated, exclusively owned PostgreSQL databases."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Configuracion, Optimizacion
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.infrastructure.configuration_seed import (
    ConfigurationSeedError, DEMO_PARAMETERS, seed_demo_configuration,
)
from tests.integration.optimization.test_runs import prepared  # noqa: F401


def test_empty_database_seed_twice_preserves_one_complete_version_and_real_actor(session_factory, create_user):
    create_user("O73000080", active=False)  # The responsible account is deliberately not ID 1.
    actor = create_user("O73000081")
    with session_factory() as db:
        first = seed_demo_configuration(db, "O73000081")
        first_id, created = first.id_configuracion, first.fecha_creacion
        second = seed_demo_configuration(db, "O73000081")
        assert second.id_configuracion == first_id
        assert second.fecha_creacion == created
        assert second.id_usuario_creacion == actor
        assert actor != 1
        assert second.version == 1 and second.vigente
        assert {field: getattr(second, field) for field in DEMO_PARAMETERS} == {
            "separacion_mm": Decimal("0"), "margen_mm": Decimal("0"),
            "resolucion_raster_mm": Decimal("1"), "paso_angular_grados": Decimal("5"),
            "ancho_min_retazo_mm": Decimal("10"), "alto_min_retazo_mm": Decimal("10"),
        }
        assert db.scalar(select(func.count()).select_from(Configuracion)) == 1
        assert db.scalar(select(func.count()).select_from(Configuracion).where(Configuracion.vigente.is_(True))) == 1


@pytest.mark.parametrize("username", [None, "missing", "O73000082"])
def test_no_valid_responsible_account_fails_without_fabricating_data(session_factory, create_user, username):
    create_user("O73000082", active=False)
    with session_factory() as db:
        with pytest.raises(ConfigurationSeedError, match="cuenta activa existente"):
            seed_demo_configuration(db, username)
        assert db.scalar(select(func.count()).select_from(Configuracion)) == 0


def test_existing_complete_configuration_is_kept_even_with_different_values(session_factory, prepared):
    _, ids, uow = prepared
    run = AcceptRun(uow).execute(ids, prepared[0])
    with session_factory() as db:
        config = db.scalar(select(Configuracion))
        original = {column.name: getattr(config, column.name) for column in Configuracion.__table__.columns}
        kept = seed_demo_configuration(db, None)
        assert {field: getattr(kept, field) for field in original} == original
        assert kept.ancho_min_retazo_mm == 1  # Do not replace with the demo's 10 mm.
        assert db.get(Optimizacion, run.optimization_id).id_configuracion == kept.id_configuracion


def test_new_version_never_changes_a_used_historical_configuration(session_factory, prepared):
    actor, ids, uow = prepared
    run = AcceptRun(uow).execute(ids, actor)
    with session_factory() as db:
        old = db.scalar(select(Configuracion))
        old.vigente = False
        old.version = 7
        db.commit()
        original = {column.name: getattr(old, column.name) for column in Configuracion.__table__.columns}
        new = seed_demo_configuration(db, "O73000001")
        assert new.version == 8 and new.vigente
        assert new.id_configuracion != old.id_configuracion
        assert {field: getattr(old, field) for field in original} == original
        assert db.get(Optimizacion, run.optimization_id).id_configuracion == old.id_configuracion


def test_incomplete_current_version_is_not_silently_repaired(session_factory, prepared):
    with session_factory() as db:
        config = db.scalar(select(Configuracion))
        config.paso_angular_grados = None
        db.commit()
        with pytest.raises(ConfigurationSeedError, match="incompleta"):
            seed_demo_configuration(db, "O73000001")
        assert db.get(Configuracion, config.id_configuracion).paso_angular_grados is None
        assert db.scalar(select(func.count()).select_from(Configuracion)) == 1


def test_multiple_current_versions_are_reported_without_selecting_one(session_factory, prepared):
    with session_factory() as db:
        db.add(Configuracion(version=2, **DEMO_PARAMETERS, vigente=True,
                             id_usuario_creacion=prepared[0], fecha_creacion=db.scalar(select(Configuracion.fecha_creacion))))
        db.commit()
        with pytest.raises(ConfigurationSeedError, match="varias configuraciones vigentes"):
            seed_demo_configuration(db, "O73000001")
        assert db.scalar(select(func.count()).select_from(Configuracion).where(Configuracion.vigente.is_(True))) == 2


def test_concurrent_bootstrap_still_creates_one_version(session_factory, create_user):
    create_user("O73000083")

    def seed():
        with session_factory() as db:
            return seed_demo_configuration(db, "O73000083").id_configuracion

    with ThreadPoolExecutor(max_workers=2) as executor:
        ids = list(executor.map(lambda _: seed(), range(2)))
    assert ids[0] == ids[1]
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Configuracion)) == 1
