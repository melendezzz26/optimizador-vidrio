"""Six-engine benchmark with synthetic input and an owned loopback PostgreSQL.

From backend: python -m scripts.benchmark_comparison 6 18 46
Requires the test dependencies and NEWGLASS_TEST_PG_BIN/NEWGLASS_REQUIRE_POSTGRES=1.
Emits JSON lines to stdout; never reads dotenv or a shared database, confirms a
comparison, or consumes inventory. Timings overlap (raster is part of preparation
and search; UoWs can overlap worker time). Wall times are not CPU measurements.
The 46-unit case is comparable to order #69, not its original snapshot.
"""
import os
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = 'synthetic-local-benchmark-only-key'
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal as D
from functools import partial
from pathlib import Path
import sys
import tempfile
import time
from app.modules.optimization.domain.problem import MaterialGroup, MaterialSource, OptimizationConfig, OptimizationProblem, PieceUnit, StockCandidate
from app.modules.optimization.domain.preparation import prepare_group_units
from sqlalchemy import select, func
from app.models import Usuario, Configuracion, Plancha, MovimientoInventario
from app.modules.orders.infrastructure.repositories import SQLAlchemyOrderRepository
from app.modules.optimization.application.comparison_v2_contracts import ExecutionPayloadV2
from app.modules.optimization.infrastructure.sequential_worker import calculation_worker_v2
from app.modules.optimization.infrastructure.sequential_runner import SequentialProcessRunner
from app.modules.optimization.infrastructure.comparison_v2_uow import SqlComparisonPersistenceUnitOfWork
from app.modules.optimization.infrastructure.in_process_admission import InProcessRunAdmission
from app.modules.optimization.presentation.comparison_supervision_v2 import ComparisonV2Coordinator
from app.modules.optimization.presentation.comparison_v2_serialization import comparison_response_v2, execution_response_v2
from app.modules.optimization.infrastructure.comparison_v2_snapshot import encode_result_v3
from app.modules.optimization.infrastructure.run_snapshot import json_value
from tests.integration.postgres_support import temporary_postgres, new_database, upgrade
from tests.orders_support import session_factory as seed_factory


def problem(count, resolution=1):
    if count < 2:
        raise ValueError('The benchmark requires at least two units for its two material groups')
    shapes = [(dict(type='RECTANGULO', width_mm=600, height_mm=800), D(480000)),
              (dict(type='CIRCUNFERENCIA', radius_mm=260), D(str(math.pi * 260**2)).quantize(D('.001'))),
              (dict(type='POLIGONO_CONVEXO', vertices_mm=((0, 0), (500, 0), (620, 400), (250, 700), (0, 400))), D(317000))]
    # Polygon shoelace area: 317000 mm2.
    groups = []
    for glass, n in ((1, count//2), (2, count-count//2)):
        units = tuple(PieceUnit(order_id=900069, piece_id=glass*100+i%3, unit_index=i//3+1,
            glass_type_id=glass, thickness_mm=6, geometry=shapes[i%3][0], area_mm2=shapes[i%3][1]) for i in range(n))
        stocks = tuple(StockCandidate(source=MaterialSource.SHEET, material_id=glass, physical_unit_index=i+1,
            glass_type_id=glass, thickness_mm=6, geometry=dict(type='RECTANGULO', width_mm=2140, height_mm=3300),
            area_mm2=7062000) for i in range(4))
        groups.append(MaterialGroup(glass_type_id=glass, thickness_mm=6, units=prepare_group_units(units), stock_candidates=stocks))
    return OptimizationProblem(order_ids=(900069,), config=OptimizationConfig(resolution_mm=resolution, margin_mm=3,
        separation_mm=3, angular_step_deg=5), groups=tuple(groups))


def timed_worker(*args):
    from app.modules.optimization.domain import packing, beam_search, rotation, placement
    from app.modules.optimization.application import engine_execution
    totals = defaultdict(float)
    def wrap(obj, name, label):
        original = getattr(obj, name)
        def call(*a, **k):
            began = time.monotonic()
            try: return original(*a, **k)
            finally: totals[label] += time.monotonic()-began
        setattr(obj, name, call)
    wrap(packing, 'prepare_run_geometry', 'preparation_s')
    wrap(beam_search, 'prepare_run_geometry', 'preparation_s')
    wrap(rotation.RasterCache, '_raster', 'raster_s')
    wrap(placement.SheetLayout, 'first_position', 'position_s')
    wrap(engine_execution, 'calculate_metrics', 'metrics_s')
    original = args[3]
    class Connection:
        def send_bytes(self, raw):
            value = json.loads(raw)
            if value['kind'] == 'result':
                value['data']['measurement'] = dict(totals)
                raw = json.dumps(value).encode()
            begin = time.monotonic()
            original.send_bytes(raw)
            totals['send_s'] += time.monotonic()-begin
        def close(self): original.close()
    values = list(args)
    values[3] = Connection()
    calculation_worker_v2(*values)

class TimedUow(SqlComparisonPersistenceUnitOfWork):
    totals = defaultdict(float)
    def __enter__(self):
        self.began = time.monotonic()
        super().__enter__()
        self.phase = 'read_or_accept'
        def tag(name):
            original = getattr(self.comparisons_v2, name)
            def call(*a, **k):
                self.phase = name
                return original(*a, **k)
            setattr(self.comparisons_v2, name, call)
        for name in ('save_execution', 'save_visual_references', 'record_worker', 'set_dispatch_state'):
            tag(name)
        return self
    def __exit__(self, *args):
        try: return super().__exit__(*args)
        finally:
            elapsed = time.monotonic()-self.began
            self.totals['uow_s'] += elapsed
            self.totals[self.phase + '_s'] += elapsed

def measure(engine, count):
    factory = seed_factory.__wrapped__(engine)
    case = problem(count)
    now = datetime.now(timezone.utc)
    with factory() as session:
        actor = Usuario(dni='73000999', nombres='Synthetic', apellidos='Benchmark', usuario='O73000999',
            password_hash='synthetic-unusable-hash', id_rol=3, estado=True, fecha_creacion=now)
        session.add(actor); session.flush(); actor_id = actor.id_usuario
        session.add(Configuracion(version=1, separacion_mm=3, margen_mm=3, resolucion_raster_mm=1,
            paso_angular_grados=5, ancho_min_retazo_mm=10, alto_min_retazo_mm=10, vigente=True,
            id_usuario_creacion=actor_id, fecha_creacion=now))
        pieces = []
        for group, glass in zip(case.groups, (7, 9)):
            session.add(Plancha(id_plancha=glass, ancho_mm=2140, alto_mm=3300, espesor_mm=6, cantidad=4,
                estado=True, fecha_registro=now, id_tipo_vidrio=glass))
            for piece_id in sorted({u.piece_id for u in group.units}):
                units = [u for u in group.units if u.piece_id==piece_id]
                unit = units[0]; geometry=json_value(unit.geometry)
                pieces.append(dict(tipo_forma=unit.shape_type, cantidad=len(units), dimensiones=None if unit.shape_type=='POLIGONO_CONVEXO'
                    else {k:v for k,v in geometry.items() if k!='type'}, geometria=geometry,
                    id_tipo_vidrio=glass, espesor_mm=6, area_mm2=unit.area_mm2))
        session.commit()
        order = SQLAlchemyOrderRepository(session).create_order(actor_id, pieces, id_cliente=41)
    TimedUow.totals.clear()
    coordinator = ComparisonV2Coordinator(partial(TimedUow, factory), InProcessRunAdmission(),
        runner_factory=partial(SequentialProcessRunner, worker_target=timed_worker))
    started = time.monotonic()
    accepted = coordinator.start([order], actor_id, f'benchmark-{count}-isolated')
    accepted_s = time.monotonic()-started
    job = coordinator.job
    if not job.closed.wait(240):
        coordinator.shutdown()
        raise RuntimeError('supervisor did not close')
    job.thread.join(2); job.reaper.join(2)
    elapsed_s = time.monotonic()-started
    assert not job.unsafe and job.runner.last_report['all_workers_stopped']
    assert coordinator.admission.active()==0
    with coordinator.uow() as tx: current=tx.comparisons_v2.get(accepted.comparison_id)
    with factory() as session:
        assert all(s.cantidad==4 for s in session.scalars(select(Plancha)))
        assert session.scalar(select(func.count()).select_from(MovimientoInventario))==0
    encoded = {}
    serialize_start = time.monotonic()
    # Durable snapshots compare all placements, contours, metrics and diagnostics.
    for e in current.executions:
        encoded[e.method] = encode_result_v3(ExecutionPayloadV2(method=e.method, result=e.result, diagnostic=e.diagnostic))
    serialize_s = time.monotonic()-serialize_start
    projection_start = time.monotonic()
    responses = [comparison_response_v2(current), *(execution_response_v2(current, e) for e in current.executions)]
    response_bytes = sum(len(response.model_dump_json().encode()) for response in responses)
    projection_s = time.monotonic()-projection_start
    print(json.dumps(dict(count=count, accepted_s=accepted_s, elapsed_s=elapsed_s, serialize_s=serialize_s,
        projection_s=projection_s, response_bytes=response_bytes,
        timings=dict(TimedUow.totals), runner=job.runner.last_report,
        results=encoded, event_bytes=job.event_bytes,
        visual_bytes=sum(s.charged_bytes for s in job.sessions.values()))), flush=True)
    job.dispose()

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='newglass-perf-') as root:
        with temporary_postgres(Path(root)) as cluster, new_database(cluster) as engine:
            migrated = upgrade(engine, 'head')
            assert migrated.returncode==0, migrated.stderr
            for count in map(int, sys.argv[1:] or (6, 18, 46)): measure(engine, count)
