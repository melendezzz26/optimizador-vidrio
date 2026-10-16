"""Synthetic data for real browser tests, restricted to our owned local PG.

No HTTP routes, auth overrides or mocked responses. Run while e2e_server owns
the loopback cluster: python -m tests.optimization_e2e_data <scenario>.
"""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import Session



def seed(scenario):
    state = json.loads((Path(tempfile.gettempdir()) / 'newglass-orders-e2e-8017.json').read_text())
    root = Path(state['root']).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith('newglass-orders-e2e-')
    url = sa.make_url(state['database_url'])
    assert url.host == '127.0.0.1' and url.username == 'r1_test' and url.database.startswith('r1_')
    assert (root / 'data' / 'postmaster.pid').exists()
    os.environ['PYTHON_DOTENV_DISABLED'] = '1'
    os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
    os.environ['SECRET_KEY'] = secrets.token_urlsafe(48)  # Hashing only; no tokens minted by this helper.
    from app.core.permissions import CODIGOS
    from app.models import (Configuracion, Permiso, Plancha, Retazo, Rol, RolPermiso,
                            TipoVidrio, TipoVidrioEspesor, Usuario)
    from app.shared.security import hash_password
    engine = sa.create_engine(url)
    now = datetime.now(timezone.utc)
    suffix = secrets.token_hex(5)
    permissions = {
        'all': sorted(CODIGOS),
        'view': ['optimization.view'],
        'execute': ['optimization.view', 'optimization.execute', 'orders.view'],
        'confirm': ['optimization.view', 'optimization.confirm'],
        'none': ['orders.view'],
    }
    with Session(engine) as db, db.begin():
        runtime = dict(database='owned loopback PostgreSQL', dialect=engine.dialect.name,
                       version=db.scalar(sa.text('SHOW server_version')),
                       alembic_heads=list(db.scalars(sa.text('SELECT version_num FROM alembic_version'))))
        # The legacy e2e seed has explicit IDs; advance their sequences safely.
        db.execute(sa.text('SELECT pg_advisory_xact_lock(170015)'))
        for table, column in [('roles', 'id_rol'), ('tipos_vidrio', 'id_tipo_vidrio'), ('planchas', 'id_plancha')]:
            db.execute(sa.text(f"SELECT setval(pg_get_serial_sequence('{table}', '{column}'), GREATEST(COALESCE((SELECT MAX({column}) FROM {table}), 1), 1))"))
        permission_ids = dict(db.execute(sa.select(Permiso.codigo, Permiso.id_permiso)).all())
        actors = {}
        for name, codes in permissions.items():
            role = Rol(nombre=f'E2E-{name}-{suffix}')
            db.add(role); db.flush()
            db.add_all(RolPermiso(id_rol=role.id_rol, id_permiso=permission_ids[code]) for code in codes)
            dni = str(80000000 + secrets.randbelow(19999999))
            user = Usuario(dni=dni, nombres='Integracion', apellidos=name,
                usuario=f'E{dni}', password_hash=hash_password('Integration-test-2026!'),
                id_rol=role.id_rol, fecha_creacion=now)
            db.add(user); db.flush()
            actors[name] = {'username': user.usuario, 'password': 'Integration-test-2026!'}
        if not db.scalar(sa.select(Configuracion.id_configuracion).where(Configuracion.vigente.is_(True))):
            db.add(Configuracion(version=1, separacion_mm=0, margen_mm=0, resolucion_raster_mm=1,
                paso_angular_grados=90, ancho_min_retazo_mm=10, alto_min_retazo_mm=10,
                vigente=True, id_usuario_creacion=user.id_usuario, fecha_creacion=now))
        types, sheets, remnants = [], [], []
        for i in range(2 if scenario in ('multimaterial', 'combined') else 1):
            glass = TipoVidrio(nombre=f'E2E-{scenario}-{suffix}-{i}', estado=True)
            db.add(glass); db.flush()
            thickness = 6 if i == 0 else 4
            db.add(TipoVidrioEspesor(id_tipo_vidrio=glass.id_tipo_vidrio, espesor_mm=thickness))
            db.flush()
            types.append({'id_tipo_vidrio': glass.id_tipo_vidrio, 'espesor_mm': thickness})
            width, height = (40, 70) if scenario == 'rotated' else (50, 50) if scenario == 'incomplete' else (100, 50)
            sheet = Plancha(ancho_mm=width, alto_mm=height, espesor_mm=thickness,
                cantidad=4 if scenario == 'multiunit' else 2 if scenario == 'combined' and i == 0 else 1, estado=True,
                fecha_registro=now, id_tipo_vidrio=glass.id_tipo_vidrio)
            db.add(sheet); db.flush()
            sheets.append(sheet.id_plancha)
            if scenario == 'remnant':
                remnant = Retazo(codigo=f'E2E-{suffix}', espesor_mm=thickness,
                    geometria={'type': 'RECTANGULO', 'width_mm': 100, 'height_mm': 50},
                    area_mm2=5000, estado=True, fecha_registro=now, id_tipo_vidrio=glass.id_tipo_vidrio)
                db.add(remnant); db.flush(); remnants.append(remnant.id_retazo)
    engine.dispose()
    return dict(actors=actors, materials=types, sheets=sheets, remnants=remnants, runtime=runtime)


if __name__ == '__main__':
    assert sys.argv[1] in {'single', 'multiple', 'multimaterial', 'multiunit', 'remnant', 'incomplete', 'conflict', 'rbac', 'rotated', 'combined'}
    print(json.dumps(seed(sys.argv[1])))
