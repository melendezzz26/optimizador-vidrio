"""Measure the final B04 process primitive; no services, DB or admission release."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def tables(target, early, final):
    lines=['# Mediciones B04 — caso pequeño WSL2','',
        f"Entrada SHA256: `{final['input_sha256']}`.",'',
        'Una muestra por modalidad; no es una garantía para otras cargas o plataformas.','']
    for seq in early['sequences']:
        lines += [f"## Ensayo temprano — observación {'ON' if seq['observed'] else 'OFF'}",'',
            '| Motor | Arranque ms | Preparación exclusiva ms | Cuerpo exclusivo ms | Callback ms | Métricas ms | Serialización resultado ms | RSS pico MiB | VM final MiB | Eventos / bytes |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in seq['records']:
            t=r['timings_ms']
            lines.append(f"| {r['method']} | {r['startup_ms']:.3f} | {r['preparation_exclusive_ms']:.3f} | {r['engine_body_exclusive_ms']:.3f} | {t['observation']:.3f} | {t['metrics']:.3f} | {t['result_serialization']:.3f} | {r['maxrss_bytes']/1048576:.2f} | {r['memory']['virtual']/1048576:.2f} | {r['events']} / {r['observation_bytes']} |")
        lines += ['',f"Total {seq['total_ms']:.3f} ms; agregado muestreado más reserva {seq['sampled_maximum_aggregate_rss']/1048576:.2f} MiB; máximo de workers {seq['maximum_active_workers']}. Todos completos/COMPLETED.",'']
    lines += ['Preparación corresponde a prepare_run_geometry; orientaciones lazy pertenecen al cuerpo. El callback incluye serialización de observaciones, no sumarla otra vez. JSON conserva tiempos inclusivos y exclusivos; una muestra ON/OFF no permite inferir costo causal.','']
    for seq in final['sequences']:
        r=seq['resources']
        lines += [f"## Primitiva final — observación {'ON' if seq['observed'] else 'OFF'}",'',
            '| Motor | Cola ms | Arranque ms | Ejecución externa ms | Cierre ms | RSS pico worker MiB | VM máxima muestreada MiB | Estado / causa |',
            '|---|---:|---:|---:|---:|---:|---:|---|']
        for method,s in r['executions'].items():
            lines.append(f"| {method} | {s['queue_ms']:.3f} | {s['startup_ms']:.3f} | {s['execution_external_wall_ms']:.3f} | {s['cleanup_ms']:.3f} | {s['worker_report']['maxrss_bytes']/1048576:.2f} | {s.get('peak_virtual',0)/1048576:.2f} | COMPLETO / {s['reason']} |")
        lines += ['',f"Total {r['elapsed_ms']:.3f} ms; agregado máximo muestreado más reserva {r['maximum_aggregate_rss']/1048576:.2f} MiB; intervalo máximo de muestra {r['maximum_sample_gap_ms']:.3f} ms; workers máximos {r['maximum_active_workers']}; muestras {r['samples']}.",'']
    lines += ['Ejecución externa incluye callbacks, métricas e IPC desde el inicio del adaptador hasta recepción. No incluye cola/arranque/cierre; no equivale al cuerpo exclusivo.','']
    target.write_text('\n'.join(lines),encoding='utf-8')


def main():
    from app.modules.optimization.application.comparison_catalog import METHODS_V2
    from app.modules.optimization.application.engine_execution import ExecutionScope
    from app.modules.optimization.infrastructure.comparison_snapshot import decode_problem, canonical_json, problem_fingerprint
    from app.modules.optimization.infrastructure.comparison_v2_snapshot import encode_result_v3
    from app.modules.optimization.infrastructure.sequential_runner import SequentialProcessRunner
    fixture=json.loads((ROOT/'docs/evidence/sprint-02/TA-043/B03/adapter-validation.json').read_text())
    problem=decode_problem(fixture['problem'])
    scopes=tuple(ExecutionScope(comparison_id=43,execution_id=4301+i,method=method) for i,method in enumerate(METHODS_V2))
    sequences=[]
    for observed in (False,True):
        service=SequentialProcessRunner()
        values=service.calculate(scopes,problem,(1,1),observed=observed)
        parity=[]
        for value,native in zip(values,fixture['records']):
            normalized=replace(value.payload,result=replace(value.payload.result,computation_time_ms=0)) if value.payload.result else value.payload
            digest=hashlib.sha256(canonical_json(encode_result_v3(normalized)).encode()).hexdigest()
            parity.append(dict(method=value.scope.method,complete=bool(value.payload.result and value.payload.result.complete),
                reason=value.payload.diagnostic.public(),dispatched=value.dispatched,engine_started=value.engine_started,
                normalized_snapshot_sha256=digest,equals_b03_direct=digest==native['direct_sha256']))
        report=service.last_report
        passed=(len(values)==6 and all(r['complete'] and r['equals_b03_direct'] for r in parity)
            and report['all_workers_stopped'] and report['maximum_active_workers']==1
            and report['elapsed_ms']<180000 and report['maximum_worker_virtual']<=256*1024*1024
            and report['maximum_aggregate_rss']<=1024*1024*1024)
        sequences.append(dict(observed=observed,result='PASS' if passed else 'FAIL',executions=parity,resources=report))
    result=dict(decision='VIABLE' if all(s['result']=='PASS' for s in sequences) else 'NO VIABLE',
        scope='B04 process primitive only, not B05 or public v2',fixture=fixture['problem'],
        input_sha256=problem_fingerprint(problem),sequences=sequences)
    from app.modules.optimization.application.comparison_catalog import CATALOG_V2
    from app.modules.optimization.domain.beam_search import BeamSearchLimits
    from app.modules.optimization.domain.hole_filling import HoleFillingLimits
    result['engine_configuration']={d.code:dict(label=d.label,optimizer=d.optimizer_type.__name__,
        native_defaults=asdict(BeamSearchLimits()) if d.code=='M6-BS' else
            asdict(HoleFillingLimits()) if d.code=='HF' else {},
        residual_selector_cells=dict(width=1,height=1) if d.code=='M5' else None) for d in CATALOG_V2}
    target=ROOT/'docs/evidence/sprint-02/TA-043/B04/final-process-measurements.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n')
    if result['decision']=='VIABLE':
        tables(target.with_name('measurements.md'),json.loads(target.with_name('early-feasibility.json').read_text()),result)
    print(json.dumps(dict(decision=result['decision'],sequences=[dict(observed=s['observed'],result=s['result'],
        elapsed_ms=s['resources']['elapsed_ms'],peak_rss=s['resources']['maximum_aggregate_rss'],
        maximum_active_workers=s['resources']['maximum_active_workers']) for s in sequences])))
    return 0 if result['decision']=='VIABLE' else 1


if __name__=='__main__': raise SystemExit(main())
