"""B06 typed projection over B05's single retained window; no calculation/lifecycle policy."""
from datetime import datetime, timezone
from decimal import Decimal
from itertools import islice
from threading import Condition
import time

from ..application.errors import RunError
from ..application.visual import MAX_COMPARISON_EVENT_BYTES as MAX_EVENT_BYTES
from ..domain.problem import Placement
from .comparison_supervision_v2 import SupervisedJob
from .comparison_v2_schemas import ComparisonEventV2, ComparisonMaskV2
from .comparison_v2_serialization import execution_summary_v2
from .comparison_serialization import plain
from .run_serialization import unit_reference, placement_response, stock_response, progress_response
from .visual_serialization import VisualProjection, describe_record


class HttpComparisonJob(SupervisedJob):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.condition=Condition(self.lock)
        self.sequence=0
        self.method_sequences={m:0 for m in self.comparison.methods}
        self.by_method={e.method:e for e in self.comparison.executions}
        self.units={(u.piece_id,u.unit_index):u for u in self.comparison.problem.units}
        self.stocks={(s.source.value,s.material_id,s.physical_unit_index):s
            for g in self.comparison.problem.groups for s in g.stock_candidates}
        self.group_totals={g.key:len(g.units) for g in self.comparison.problem.groups}
        self.group_bases={m:{} for m in self.comparison.methods}
        self.orders={m:[] for m in self.comparison.methods}
        self.phases={m:'PREPARING' for m in self.comparison.methods}
        self.current={m:None for m in self.comparison.methods}
        self.last_orientation={m:None for m in self.comparison.methods}
        self.projections={m:VisualProjection(self.sessions[e.execution_id],
            lambda kind,data,method=m:self.project(method,kind,data)) for m,e in self.by_method.items()}
        self.presentation={m:'OBSERVED' for m in self.comparison.methods}
        self.finished=False
        self.finished_at=None
        self.disposed=False
        self.observers=0
        self.emit(None,'comparison_accepted',dict(version=self.comparison.version,methods=list(self.comparison.methods),
            executions=[dict(execution_id=e.execution_id,method=e.method) for e in self.comparison.executions]))

    def envelope(self,method,kind,data,sequence,execution_sequence=None):
        return ComparisonEventV2(comparison_id=self.comparison.comparison_id,sequence=sequence,
            timestamp=datetime.now(timezone.utc),execution_id=self.by_method[method].execution_id if method else None,
            method=method,execution_sequence=execution_sequence,
            presentation=self.presentation[method] if method else None,event=kind,data=plain(data))

    def emit(self,method,kind,data):
        with self.condition:
            seq=self.sequence+1
            own=self.method_sequences[method]+1 if method else None
            raw=self.envelope(method,kind,data,seq,own).model_dump_json().encode()+b'\n'
            if len(raw)>MAX_EVENT_BYTES:
                raise RunError('INTERNAL_ERROR','El evento visual excede su presupuesto.')
            self.sequence=seq
            if method: self.method_sequences[method]=own
            self.events.append((seq,raw)); self.event_bytes+=len(raw)
            while self.event_bytes>self.event_limit or len(self.events)>4096:
                self.event_bytes-=len(self.events.popleft()[1])
            self.condition.notify_all()

    def descriptor(self,method,data):
        return ComparisonMaskV2(**data,comparison_id=self.comparison.comparison_id,
            execution_id=self.by_method[method].execution_id,method=method).model_dump(mode='json')

    def project(self,method,kind,data):
        data=dict(data)
        if 'metodo' in data: data['metodo']=method
        for name in ('mask','material_mask'):
            if name in data: data[name]=self.descriptor(method,data[name])
        if kind in ('piece_rasterizing','piece_ready','orientation_testing','source_selected','piece_unplaced'):
            self.current[method]=plain(dict(kind=kind,**data))
        if kind in ('orientation_testing','source_selected','piece_unplaced'): self.phases[method]='CALCULATING'
        if kind in ('orientation_testing','source_selected'): self.last_orientation[method]=plain(dict(kind=kind,**data))
        self.emit(method,kind,data)

    def record(self,signal,sanitized):
        # Replaces the base recording slot: never keeps another 8/32 MiB window.
        method,kind,data=signal.method,signal.kind,signal.payload
        if kind=='observation':
            self.presentation[method]=data['presentation']
            if data['kind']=='search_progress':
                self.phases[method]='CALCULATING'
                self.emit(method,'search_progress',data['fact'])
            elif data['kind']=='milestone': self.milestone(method,data['fact'])
            return
        self.presentation[method]='OBSERVED'
        with self.uow() as tx: current=tx.comparisons_v2.get(signal.comparison_id)
        execution=next(e for e in current.executions if e.execution_id==signal.execution_id)
        summary=execution_summary_v2(current,execution)
        if kind in ('dispatching','spawned','started'):
            self.emit(method,'execution_state',summary)
        if kind=='ready': self.emit(method,'engine_ready',{})
        elif kind=='started': self.emit(method,'engine_started',{})
        elif kind in ('result_persisted','execution_failed'):
            self.phases[method]='RESULT' if kind=='result_persisted' else 'FAILED'
            self.emit(method,kind,summary)

    def record_visual(self, signal, data, fact):
        method = signal.method
        self.presentation[method] = data['presentation']
        if fact.kind=='ordering_ready':
            self.orders[method]=[unit_reference(u) for u in fact.ordered_units]
            self.phases[method]='ORDERING'
            self.emit(method,'ordering_ready',dict(criterion='area_desc_max_side_desc_order_piece_unit_asc',
                units=self.orders[method]))
        else: self.projections[method](fact)

    def milestone(self,method,data):
        kind=data['kind']; key=(data['group_key'][0],Decimal(data['group_key'][1]))
        progress=progress_response(data['placed_units'],data['total_units'])
        if kind=='group_started':
            self.group_bases[method][key]=data['placed_units']
            body=dict(id_tipo_vidrio=key[0],espesor_mm=key[1],total_units=self.group_totals[key])
        elif kind=='group_completed':
            body=dict(id_tipo_vidrio=key[0],espesor_mm=key[1],**progress_response(
                data['placed_units']-self.group_bases[method][key],self.group_totals[key]))
            body['result_url']=f'/api/optimization/comparisons-v2/{self.comparison.comparison_id}/executions/{self.by_method[method].execution_id}'
        else:
            unit=self.units[(data['unit']['piece_id'],data['unit']['unit_index'])]
            body=dict(**unit_reference(unit),**progress,processed_units=self.sessions[self.by_method[method].execution_id].processed)
            if kind=='piece_placed':
                p=data['placement']; s=p['stock']
                stock=self.stocks[(s['source'],s['material_id'],s['physical_unit_index'])]
                placement=Placement(piece=unit,stock=stock,geometry=p['geometry'],
                    **{k:Decimal(p[k]) for k in ('x_mm','y_mm','rotation_deg')})
                body.update(placement_response(placement,self.comparison.problem.config).model_dump(),
                    material=stock_response(stock))
        self.emit(method,kind,body)

    def mark(self,kind):
        super().mark(kind)
        if kind=='safe_close_committed':
            with self.condition:
                if not self.finished:
                    c=self.comparison
                    for execution in c.executions:
                        self.phases[execution.method]='RESULT' if execution.result is not None else 'FAILED'
                    self.emit(None,'comparison_finished',dict(version=c.version,status=c.status,
                        incomplete=c.incomplete,supervisor_stopped=True))
                    self.finished=True; self.finished_at=time.monotonic()
                    self.condition.notify_all()

    def session(self,execution_id):
        e=next((e for e in self.comparison.executions if e.execution_id==execution_id),None)
        if e is None: raise RunError('NOT_FOUND','La ejecución no pertenece a esta comparación.')
        return e.method,self.sessions[execution_id]

    def manifest(self,execution_id,offset):
        with self.condition:
            method,session=self.session(execution_id)
            items,total,next_offset=session.manifest(offset)
            return dict(profile='comparison-v2',schema_version=2,comparison_id=self.comparison.comparison_id,
                execution_id=execution_id,method=method,revision=session.revision,
                execution_sequence=self.method_sequences[method],preparation_completed=session.preparation_completed,
                processed_units=session.processed,evaluations=session.evaluations,phase=self.phases[method],
                current=self.current[method],last_orientation=self.last_orientation[method],
                ordered_units=plain(self.orders[method]),total=total,next_offset=next_offset,
                items=[self.descriptor(method,describe_record(session,r)) for r in items])

    def check_cursor(self,cursor):
        with self.condition:
            if cursor>self.sequence: raise RunError('INVALID_INPUT','El cursor está por delante del trabajo.')
            if self.events and cursor<self.events[0][0]-1:
                raise RunError('EVENT_CURSOR_EXPIRED','Recupera el snapshot persistido de la comparación.',
                    details={'latest_sequence':self.sequence})

    def observe(self):
        with self.condition:
            if self.observers>=2: raise RunError('OPTIMIZER_BUSY','Ya hay dos vistas de avance abiertas.')
            self.observers+=1
            return HttpObservation(self)

    def lines(self,cursor,observer):
        while not observer.closed:
            with self.condition:
                if self.disposed: return
                if self.events and cursor<self.events[0][0]-1:
                    cursor=self.sequence
                    batch=[(cursor,self.envelope(None,'snapshot_required',{'latest_sequence':cursor},cursor).model_dump_json().encode()+b'\n')]
                else: batch=list(islice(((s,r) for s,r in self.events if s>cursor),16))
                if not batch:
                    if self.finished: return
                    if self.condition.wait(timeout=10): continue
                    batch=[(cursor,self.envelope(None,'heartbeat',{},max(1,cursor)).model_dump_json().encode()+b'\n')]
            for sequence,raw in batch:
                cursor=sequence
                yield raw

    def dispose(self):
        with self.condition:
            super().dispose()
            self.disposed=True
            self.condition.notify_all()


class HttpObservation:
    def __init__(self,job): self.job,self.closed=job,False

    def release(self):
        with self.job.condition:
            if not self.closed:
                self.closed=True; self.job.observers-=1
                self.job.condition.notify_all()
