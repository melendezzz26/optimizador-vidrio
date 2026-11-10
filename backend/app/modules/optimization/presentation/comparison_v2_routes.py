"""Explicit comparison-v2 HTTP surface with versioned manual confirmation."""
import json
import time
from typing import Annotated
from pydantic import Field

from fastapi import APIRouter, Depends, Header, Path, Query, Response

from ..application.errors import RunError
from ..application.comparison_confirmation import ConfirmComparisonV2
from ..application.visual import MAX_RESPONSE_BYTES, mask_window
from .comparison_routes import ObservationResponse
from .comparison_supervision_v2 import get_comparison_v2_coordinator
from .comparison_v2_schemas import ComparisonSummaryV2, ExecutionResponseV2, ComparisonReleaseV2, ComparisonMaskPayloadV2, PositiveIdV2
from .comparison_v2_schemas import ComparisonSelectionV2, ComparisonConfirmationV2
from .comparison_v2_schemas import ComparisonHistoryV2
from .confirmation_serialization import confirmation_response
from .comparison_v2_serialization import comparison_response_v2, execution_response_v2
from .run_auth import run_permission
from .run_routes import RunRoute, visual_response
from .run_schemas import RunRequestV1
from .visual_serialization import describe_record

Id=Annotated[int,Path(gt=0,le=2147483647)]
Key=Annotated[str,Header(alias='Idempotency-Key',min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')]
router=APIRouter(prefix='/comparisons-v2',route_class=RunRoute)


class ComparisonRequestV2(RunRequestV1):
    order_ids: Annotated[list[PositiveIdV2],Field(min_length=1)]


def get_comparison_v2_uow(coordinator=Depends(get_comparison_v2_coordinator)):
    return coordinator.uow


def load(identifier,actor_id,uow,coordinator,*,response=None,allow_blocked=False):
    with uow() as tx: current=tx.comparisons_v2.get_owned(identifier,actor_id)
    if not current.terminal:
        proven=coordinator.reconcile(identifier)
        with uow() as tx: current=tx.comparisons_v2.get_owned(identifier,actor_id)
        if not proven and not current.terminal:
            if allow_blocked:
                response.headers['X-Comparison-Recovery']='BLOCKED'
            else:
                raise RunError('RECOVERY_BLOCKED','No se puede acreditar el cierre seguro; el trabajo sigue bloqueado.',
                    details={'comparison_id':identifier})
    return current


def execution_in(current,identifier):
    execution=next((e for e in current.executions if e.execution_id==identifier),None)
    if execution is None: raise RunError('NOT_FOUND','La ejecución no pertenece a esta comparación.')
    return execution


def load_visual_owner(identifier, actor_id, uow, coordinator, execution_id=None):
    with uow() as tx:
        terminal = tx.comparisons_v2.visual_scope_owned(identifier, actor_id, execution_id)
    if not terminal and not coordinator.reconcile(identifier):
        raise RunError('RECOVERY_BLOCKED', 'No se puede acreditar el cierre seguro; el trabajo sigue bloqueado.',
            details={'comparison_id':identifier})


def retained_job(coordinator,identifier):
    with coordinator.lock:
        job=coordinator.job
        if (job is not None and job.comparison.comparison_id==identifier and hasattr(job,'sequence')
            and job.finished_at is not None and time.monotonic()-job.finished_at>=job.store.ttl
            and job.closed.is_set()):
            job.dispose()
        if (job is None or job.comparison.comparison_id!=identifier or not hasattr(job,'sequence')
            or job.disposed or job.finished_at is not None and time.monotonic()-job.finished_at>=job.store.ttl):
            raise RunError('VISUAL_DATA_UNAVAILABLE','El avance visual expiró. Recupera los resultados persistidos.')
        return job


@router.post('',status_code=201,response_model=ComparisonSummaryV2)
def start(request:ComparisonRequestV2,response:Response,key:Key,
          user=Depends(run_permission('optimization.execute')),
          uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    with uow() as tx:
        previous=tx.comparisons_v2.find_by_key(user.user_id,key)
        if previous is not None: tx.comparisons_v2.get_owned(previous.comparison_id,user.user_id)
    accepted=coordinator.start(request.order_ids,user.user_id,key)
    # An ambiguous recovered request must not masquerade as a successful new start.
    current=load(accepted.comparison_id,user.user_id,uow,coordinator)
    response.headers['Location']=f'/api/optimization/comparisons-v2/{current.comparison_id}'
    return comparison_response_v2(current)


@router.get('/requests/{key}',response_model=ComparisonSummaryV2)
def request_status(key:Annotated[str,Path(min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')],
                   user=Depends(run_permission('optimization.view')),
                   uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    with uow() as tx: current=tx.comparisons_v2.find_by_key(user.user_id,key)
    if current is None: raise RunError('NOT_FOUND','No se encontró la solicitud comparativa.')
    return comparison_response_v2(load(current.comparison_id,user.user_id,uow,coordinator))


@router.get('/history', response_model=ComparisonHistoryV2)
def history(before_id: Annotated[int | None, Query(gt=0, le=2147483647)] = None,
            limit: Annotated[int, Query(ge=1, le=20)] = 20,
            user=Depends(run_permission('optimization.view')), uow=Depends(get_comparison_v2_uow)):
    with uow() as tx:
        return tx.comparisons_v2.history_owned(user.user_id, before_id=before_id, limit=limit)


@router.get('/{comparison_id}',response_model=ComparisonSummaryV2)
def get_comparison(comparison_id:Id,user=Depends(run_permission('optimization.view')),
                   uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    return comparison_response_v2(load(comparison_id,user.user_id,uow,coordinator))


@router.get('/{comparison_id}/executions/{execution_id}',response_model=ExecutionResponseV2)
def get_execution(comparison_id:Id,execution_id:Id,response:Response,
                  user=Depends(run_permission('optimization.view')),
                  uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    current=load(comparison_id,user.user_id,uow,coordinator,response=response,allow_blocked=True)
    return execution_response_v2(current,execution_in(current,execution_id))


@router.put('/{comparison_id}/selection', response_model=ComparisonSummaryV2)
def select_execution(comparison_id: Id, request: ComparisonSelectionV2,
                     user=Depends(run_permission('optimization.execute')),
                     uow=Depends(get_comparison_v2_uow), coordinator=Depends(get_comparison_v2_coordinator)):
    load(comparison_id, user.user_id, uow, coordinator)
    with uow() as tx:
        current = tx.comparisons_v2.select(comparison_id, request.execution_id, request.expected_version, user.user_id)
    return comparison_response_v2(current)


@router.post('/{comparison_id}/confirm', response_model=ComparisonConfirmationV2)
def confirm(comparison_id: Id, request: ComparisonSelectionV2, key: Key,
            user=Depends(run_permission('optimization.confirm')),
            uow=Depends(get_comparison_v2_uow), coordinator=Depends(get_comparison_v2_coordinator)):
    load(comparison_id, user.user_id, uow, coordinator)
    receipt = ConfirmComparisonV2(uow).execute(comparison_id, request.execution_id, request.expected_version, key, user.user_id)
    with uow() as tx:
        current = tx.comparisons_v2.get_owned(comparison_id, user.user_id)
    return ComparisonConfirmationV2(comparison_id=comparison_id, execution_id=request.execution_id,
        version=current.version, receipt=confirmation_response(receipt))


@router.get('/{comparison_id}/events')
def events(comparison_id:Id,after_sequence:Annotated[int,Query(ge=0)]=0,
           user=Depends(run_permission('optimization.view')),
           uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    load_visual_owner(comparison_id,user.user_id,uow,coordinator)
    job=retained_job(coordinator,comparison_id)
    job.check_cursor(after_sequence)
    observer=job.observe()
    return ObservationResponse(job.lines(after_sequence,observer),observer)


@router.get('/{comparison_id}/executions/{execution_id}/visual')
def manifest(comparison_id:Id,execution_id:Id,offset:Annotated[int,Query(ge=0,le=1024)]=0,
             user=Depends(run_permission('optimization.view')),
             uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    load_visual_owner(comparison_id,user.user_id,uow,coordinator,execution_id)
    data=json.dumps(retained_job(coordinator,comparison_id).manifest(execution_id,offset),
        separators=(',',':'),allow_nan=False)
    if len(data.encode())>MAX_RESPONSE_BYTES: raise RunError('INTERNAL_ERROR','El manifiesto excede su presupuesto.')
    return Response(data,media_type='application/json')


@router.get('/{comparison_id}/executions/{execution_id}/visual/masks/{mask_ref}')
def mask(comparison_id:Id,execution_id:Id,mask_ref:Annotated[str,Path(pattern=r'^[a-f0-9]{32}$')],
         row_start:Annotated[int,Query(ge=0)]=0,column_start:Annotated[int,Query(ge=0)]=0,
         row_count:Annotated[int|None,Query(gt=0,le=256)]=None,column_count:Annotated[int|None,Query(gt=0,le=1024)]=None,
         user=Depends(run_permission('optimization.view')),
         uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    load_visual_owner(comparison_id,user.user_id,uow,coordinator,execution_id)
    with uow() as tx: tx.comparisons_v2.get_visual_reference(comparison_id,execution_id,mask_ref)
    job=retained_job(coordinator,comparison_id)
    with job.condition:
        method,session=job.session(execution_id)
        record=session.get(mask_ref)
        data=mask_window(record,row_start=row_start,column_start=column_start,row_count=row_count,column_count=column_count)
        spans=data.pop('spans_by_row')
        return visual_response(ComparisonMaskPayloadV2(**job.descriptor(method,describe_record(session,record)),
            geometria_original=dict(record.owner.geometry),geometria=dict(record.orientation.geometry),
            window=data,spans_by_row=spans))


@router.post('/{comparison_id}/release',response_model=ComparisonSummaryV2)
def release(comparison_id:Id,request:ComparisonReleaseV2,user=Depends(run_permission('optimization.execute')),
            uow=Depends(get_comparison_v2_uow),coordinator=Depends(get_comparison_v2_coordinator)):
    load(comparison_id,user.user_id,uow,coordinator)
    with uow() as tx: current=tx.comparisons_v2.release(comparison_id,user.user_id,request.expected_version)
    return comparison_response_v2(current)
