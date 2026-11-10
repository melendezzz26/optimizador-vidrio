"""Visual reads preserve ownership without loading all six persisted results."""
import pytest

from .test_comparisons_v2_api import api, start, completed, prepared  # noqa: F401
from app.modules.optimization.infrastructure.comparison_v2_uow import SqlComparisonV2Repository


def test_visual_reads_do_not_decode_results_and_enforce_execution_ownership(api,monkeypatch):
    client,actor,ids,headers,coordinator,uow=api
    path,_=start(api)
    current=completed(api,path)
    execution=current.executions[0]
    def forbidden(*args,**kwargs):
        raise AssertionError('Visual-only request loaded the whole comparison')
    monkeypatch.setattr(SqlComparisonV2Repository,'get',forbidden)
    manifest=client.get(f'{path}/executions/{execution.execution_id}/visual',headers=headers)
    assert manifest.status_code==200,manifest.text
    assert manifest.json()['items']
    reference=manifest.json()['items'][0]['mask_ref']
    mask=client.get(f'{path}/executions/{execution.execution_id}/visual/masks/{reference}',headers=headers)
    assert mask.status_code==200,mask.text
    foreign=client.get(f'{path}/executions/2147483647/visual',headers=headers)
    assert foreign.status_code==404


def test_visual_reference_write_requires_current_supervisor_without_full_result_reads(api,monkeypatch):
    client,actor,ids,headers,coordinator,uow=api
    path,_=start(api)
    current=completed(api,path)
    with uow() as tx:
        with pytest.raises(Exception) as error:
            tx.comparisons_v2.save_supervised_visual_references(current.comparison_id,
                current.executions[0].execution_id,(),'wrong-owner-token')
        assert getattr(error.value,'code',None)=='STATE_CONFLICT'
