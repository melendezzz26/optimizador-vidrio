"""Final policy audit: real HTTP, supervised engines, owned PostgreSQL, no confirmation."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from copy import deepcopy
from dataclasses import replace
import json

import pytest
from sqlalchemy import delete, select

from app.models import Configuracion, MovimientoInventario, Pedido, Pieza, Plancha, Retazo, TipoVidrioEspesor
from app.modules.optimization.domain.first_fit import FirstFitOptimizer
from app.modules.optimization.domain.best_fit import BestFitOptimizer
from app.modules.optimization.domain.worst_fit import WorstFitOptimizer
from app.modules.optimization.infrastructure.comparison_runner import ENGINES, ComparisonProcessRunner
from app.modules.optimization.infrastructure.comparison_snapshot import problem_fingerprint
from app.modules.optimization.infrastructure.run_snapshot import json_value
from tests.api.optimization.test_comparisons_api import api, prepared, completed  # noqa: F401
from tests.optimization.final_audit_support import fixtures, normalized_pattern, trace_policy, verify_geometry_and_metrics


def seed_case(session_factory, original, existing_orders):
    assert session_factory.kw['bind'].url.host == '127.0.0.1'
    assert session_factory.kw['bind'].url.username == 'r1_test'
    data, now = deepcopy(original), datetime(2026, 11, 1, tzinfo=timezone.utc)
    with session_factory() as session:
        config = session.scalar(select(Configuracion))
        for field, key in [('resolucion_raster_mm','resolution_mm'),('margen_mm','margin_mm'),('separacion_mm','separation_mm')]:
            setattr(config, field, D(str(data['config'][key])))
        config.paso_angular_grados = 5
        config.ancho_min_retazo_mm = data['residual_limits']['minimum_width_mm']
        config.alto_min_retazo_mm = data['residual_limits']['minimum_height_mm']
        session.execute(delete(Pieza)); session.execute(delete(Plancha)); session.execute(delete(Retazo))
        order_map = {}
        for index, identifier in enumerate(data['order_ids']):
            if index < len(existing_orders): order_map[identifier] = existing_orders[index]
            else:
                order = Pedido(fecha_registro=now, estado='PENDIENTE', id_usuario_registro=config.id_usuario_creacion, id_cliente=41)
                session.add(order); session.flush(); order_map[identifier] = order.id_pedido
        glass_ids = sorted({row['id_tipo_vidrio'] for row in data['pieces']})
        glass_map = dict(zip(glass_ids, (7, 8, 9)))
        for row in data['pieces']:
            row['id_pedido'] = order_map[row['id_pedido']]
            row['id_tipo_vidrio'] = glass_map[row['id_tipo_vidrio']]
            key = row['id_tipo_vidrio'], D(str(row['espesor_mm']))
            if session.get(TipoVidrioEspesor, key) is None:
                session.add(TipoVidrioEspesor(id_tipo_vidrio=key[0], espesor_mm=key[1])); session.flush()
            values = dict(row, dimensiones={key:value for key,value in row['geometria'].items() if key != 'type'},
                area_mm2=fixtures.loader.area(row['geometria']))
            values.pop('id_pieza')
            unit = Pieza(**values); session.add(unit); session.flush(); row['id_pieza'] = unit.id_pieza
        data['order_ids'] = list(order_map.values())
        for rank, source in enumerate(data['stock']):
            source['glass_type_id'] = glass_map[source['glass_type_id']]
            values = dict(id_tipo_vidrio=source['glass_type_id'], espesor_mm=D(str(source['thickness_mm'])),
                estado=True, fecha_registro=now + timedelta(seconds=len(data['stock']) - rank))
            if source['source'] == 'PLANCHA':
                session.add(Plancha(id_plancha=source['material_id'], ancho_mm=source['geometry']['width_mm'],
                    alto_mm=source['geometry']['height_mm'], cantidad=source['quantity'], **values))
            else:
                session.add(Retazo(id_retazo=source['material_id'], codigo=f"AUDIT-{source['material_id']}",
                    geometria=source['geometry'], area_mm2=fixtures.loader.area(source['geometry']), **values))
        session.commit()
    return data


def inventory(session_factory):
    with session_factory() as session:
        return {model.__tablename__: [json_value({c.name:getattr(row,c.name) for c in model.__table__.columns})
            for row in session.scalars(select(model).order_by(list(model.__table__.primary_key)[0]))]
            for model in (Plancha, Retazo, MovimientoInventario)}


@pytest.mark.parametrize('case_id', fixtures.CASES)
def test_real_persisted_policies_geometry_metrics_and_determinism(api, session_factory, record_property, case_id):
    client, existing_orders, headers, runtime, uow = api
    ready = []
    class ObservedRunner(ComparisonProcessRunner):
        def calculate(self, *args, **kwargs):
            stream = super().calculate(*args, **kwargs)
            try:
                for packet in stream:
                    if packet['kind'] == 'ready': ready.append(packet['payload'])
                    yield packet
            finally:
                stream.close()
    runtime.runner_factory = ObservedRunner
    assert ENGINES == {'FF':FirstFitOptimizer, 'BF':BestFitOptimizer, 'WF':WorstFitOptimizer}
    data = seed_case(session_factory, fixtures.read_case(case_id), existing_orders)
    expected_input = fixtures.build_problem(data)
    before = inventory(session_factory)
    response = client.post('/api/optimization/comparisons', headers={**headers,'Idempotency-Key':'audit-'+case_id},
        json={'order_ids':data['order_ids']})
    assert response.status_code == 201, response.text
    path = response.headers['location']
    done = completed(api, path)
    assert done['status'] == 'COMPLETADA' and not done['incomplete']
    runtime.job.thread.join(timeout=5)
    with uow() as tx:
        current = tx.comparisons.get(done['comparison_id'])
    # PostgreSQL fixes Decimal scales; compare input semantics, then verify the
    # actual persisted fingerprint sent identically to all three workers below.
    assert current.problem == expected_input
    results, details = {}, []
    for execution in current.executions:
        result = execution.result
        assert result.method == execution.method and result.complete
        assert result.problem == expected_input
        masks = verify_geometry_and_metrics(result, execution.residuals,
            (current.minimum_width_mm,current.minimum_height_mm))
        decisions = trace_policy(result)
        # A second independent run retains original method, placement and snapshot.
        direct = ENGINES[execution.method]().optimize(fixtures.build_problem(data))
        assert result.placements == direct.placements and result.unplaced_units == direct.unplaced_units
        assert expected_input == fixtures.build_problem(data)
        read = client.get(f'{path}/executions/{execution.execution_id}', headers=headers)
        assert read.status_code == 200 and read.json()['result']['metodo'] == execution.method
        results[execution.method] = result
        details.append(dict(execution_id=execution.execution_id, method=execution.method,
            result=read.json()['result'], masks=masks, decisions=decisions))
    assert len({e.execution_id for e in current.executions}) == 3
    assert len({e['pid'] for e in ready}) == 3
    assert {e['input_sha256'] for e in ready} == {current.input_sha256}
    if case_id == 'A-coincidence':
        assert normalized_pattern(results['FF']) == normalized_pattern(results['BF'])
        assert results['FF'].placements[0].stock.material_id == 101
    if case_id == 'B-source-counterexample':
        assert results['FF'].placements[0].stock.material_id == 101
        assert results['BF'].placements[0].stock.material_id == 102
        assert results['WF'].placements[0].stock.material_id == 101
        assert details[0]['decisions'][0]['candidates'][0]['score'] == 460000
        assert details[0]['decisions'][0]['candidates'][1]['score'] == 110000
    if case_id.startswith('WF-'):
        assert results['FF'].metrics.new_sheets_used == results['BF'].metrics.new_sheets_used == 1
        # SPEC-TA-019 v2: WF keeps filling the sheet in use (before: 9/10 sheets).
        assert results['WF'].metrics.new_sheets_used == 1
        assert len({p.stock.identity for p in results['WF'].placements}) == results['WF'].metrics.new_sheets_used
    assert inventory(session_factory) == before
    assert runtime.job.runner.last_report['all_workers_stopped']
    record_property('final_policy_audit', json.dumps(json_value(dict(case_id=case_id,
        comparison_id=current.comparison_id,input_sha256=current.input_sha256,input=data,
        ff_bf_same_pattern=normalized_pattern(results['FF'])==normalized_pattern(results['BF']),
        executions=details,worker_report=runtime.job.runner.last_report,inventory_unchanged=True))))
