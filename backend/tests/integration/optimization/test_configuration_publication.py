"""Publicación de una versión de configuración con 5° sobre PostgreSQL real."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Configuracion, Optimizacion
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.runs import AcceptRun
from app.modules.optimization.infrastructure.configuration_publication import (
    ConfigurationPublicationError, publish_angular_step_version,
)
from tests.integration.optimization.test_runs import prepared  # noqa: F401

COPIED = ("separacion_mm", "margen_mm", "resolucion_raster_mm", "ancho_min_retazo_mm", "alto_min_retazo_mm")


def snapshot(config):
    return {column.name: getattr(config, column.name) for column in Configuracion.__table__.columns}


def make_legacy(session_factory, step=Decimal(90)):
    """La configuración vigente queda como en una base anterior a TA-016."""
    with session_factory() as db:
        config = db.scalar(select(Configuracion).where(Configuracion.vigente.is_(True)))
        config.paso_angular_grados = step
        config.separacion_mm, config.margen_mm = Decimal("2.5"), Decimal("4")
        db.commit()


def current(db):
    return db.scalars(select(Configuracion).where(Configuracion.vigente.is_(True))).all()


def test_legacy_configuration_blocks_every_run(prepared, session_factory):
    """Reproduce el 409 de Staging."""
    actor, ids, uow = prepared
    make_legacy(session_factory)
    with pytest.raises(RunError) as error:
        AcceptRun(uow).execute(ids, actor)
    assert error.value.code == "CONFIG_CONFLICT"
    assert "paso angular de 5°" in str(error.value)


def test_publication_creates_a_5_degree_version_and_unblocks_runs(prepared, session_factory):
    actor, ids, uow = prepared
    make_legacy(session_factory)
    with session_factory() as db:
        old = current(db)[0]
        before = snapshot(old)
        result = publish_angular_step_version(db, "O73000001")
        assert (result.previous_version, result.current_version, result.changed) == (1, 2, True)
        [new] = current(db)
        assert new.version == 2 and new.paso_angular_grados == Decimal(5)
        assert {f: getattr(new, f) for f in COPIED} == {f: before[f] for f in COPIED}
        assert new.id_usuario_creacion == actor
        db.refresh(old)
        assert snapshot(old) == {**before, "vigente": False}  # solo cambia la marca de vigencia
    run = AcceptRun(uow).execute(ids, actor)
    with session_factory() as db:
        assert db.get(Optimizacion, run.optimization_id).id_configuracion == new.id_configuracion


def test_repeating_the_publication_changes_nothing(prepared, session_factory):
    make_legacy(session_factory)
    with session_factory() as db:
        publish_angular_step_version(db, "O73000001")
        again = publish_angular_step_version(db, "O73000001")
        assert (again.current_version, again.changed) == (2, False)
        assert db.scalar(select(func.count()).select_from(Configuracion)) == 2


def test_history_used_by_previous_runs_is_preserved(prepared, session_factory):
    actor, ids, uow = prepared
    old_run = AcceptRun(uow).execute(ids, actor)  # usa la versión 1 (5°)
    with session_factory() as db:
        used = db.get(Optimizacion, old_run.optimization_id).id_configuracion
    make_legacy(session_factory)
    with session_factory() as db:
        publish_angular_step_version(db, "O73000001")
        assert db.get(Optimizacion, old_run.optimization_id).id_configuracion == used


@pytest.mark.parametrize("username", [None, "missing", "O73000099"])
def test_without_active_responsible_nothing_changes(prepared, session_factory, create_user, username):
    create_user("O73000099", active=False)
    make_legacy(session_factory)
    with session_factory() as db:
        before = [snapshot(c) for c in db.scalars(select(Configuracion))]
        with pytest.raises(ConfigurationPublicationError, match="cuenta activa"):
            publish_angular_step_version(db, username)
        assert [snapshot(c) for c in db.scalars(select(Configuracion))] == before


@pytest.mark.parametrize("vigentes", [0, 2])
def test_zero_or_several_current_versions_are_not_resolved_automatically(prepared, session_factory, vigentes):
    with session_factory() as db:
        if vigentes == 0:
            current(db)[0].vigente = False
        else:
            db.add(Configuracion(version=9, separacion_mm=0, margen_mm=0, resolucion_raster_mm=1,
                                 paso_angular_grados=90, ancho_min_retazo_mm=1, alto_min_retazo_mm=1,
                                 vigente=True, id_usuario_creacion=prepared[0],
                                 fecha_creacion=datetime.now(timezone.utc)))
        db.commit()
        count = db.scalar(select(func.count()).select_from(Configuracion))
        with pytest.raises(ConfigurationPublicationError, match=f"hay {vigentes}"):
            publish_angular_step_version(db, "O73000001")
        assert db.scalar(select(func.count()).select_from(Configuracion)) == count
        assert len(current(db)) == vigentes


def test_script_requires_confirmation(prepared, session_factory, monkeypatch, capsys):
    from scripts import publish_configuration
    import app.shared.database as database
    make_legacy(session_factory)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr("builtins.input", lambda _: "no")
    assert publish_configuration.main(["--responsable", "O73000001"]) == 1
    assert "Cancelado" in capsys.readouterr().out
    monkeypatch.setattr("builtins.input", lambda _: "PUBLICAR")
    assert publish_configuration.main(["--responsable", "O73000001"]) == 0
    assert "Publicada la versión 2" in capsys.readouterr().out
    with session_factory() as db:
        assert [c.version for c in current(db)] == [2]