from dataclasses import replace
from decimal import Decimal
import pytest

from app.modules.optimization.application.confirmation import require_confirmable
from app.modules.optimization.application.dto import OptimizationRun, RunStatus
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.domain.confirmation import consumption_groups, validate_stored_geometry
from app.modules.optimization.domain.metrics import calculate_metrics
from app.modules.optimization.domain.problem import MaterialSource
from tests.unit.optimization.test_first_fit import optimize, stock, config
from tests.unit.optimization.test_preparation import piece


def test_four_placements_consume_two_physical_sheets_not_four():
    result = optimize([piece(width=2,height=2,quantity=4)],
        [stock(5,width=4,height=2,physical=1),stock(5,width=4,height=2,physical=2)])
    group, = consumption_groups(result)
    assert result.placed_units == 4
    assert group.quantity == 2 and group.unit_indices == (1,2)


def test_multiple_pieces_in_remnant_consume_exactly_one():
    result = optimize([piece(width=2,height=2,quantity=2)],
        [stock(9,width=4,height=2,source=MaterialSource.REMNANT)])
    group, = consumption_groups(result)
    assert group.quantity == 1 and group.unit_indices == (1,)


def test_consumption_lock_order_is_sheets_ids_then_remnants_ids():
    result = optimize([piece(width=2,height=2,quantity=4)], [
        stock(12,width=2,height=2,source=MaterialSource.REMNANT),
        stock(3,width=2,height=2,source=MaterialSource.REMNANT),
        stock(9,width=2,height=2), stock(2,width=2,height=2)])
    assert [(c.stock.source.value,c.stock.material_id) for c in consumption_groups(result)] == [
        ('PLANCHA',2),('PLANCHA',9),('RETAZO',3),('RETAZO',12)]


@pytest.mark.parametrize('status',[RunStatus.NO_SOLUTION,RunStatus.FAILED,RunStatus.RUNNING])
def test_incomplete_or_nonterminal_cannot_confirm(status):
    result = optimize([piece(width=200,height=200)])
    with pytest.raises(RunError) as error:
        require_confirmable(OptimizationRun(optimization_id=1,status=status,result=result))
    assert error.value.code == 'NOT_CONFIRMABLE'
    with pytest.raises(ValueError):
        consumption_groups(result)


def test_second_confirmation_is_explicit_409_code():
    run = OptimizationRun(optimization_id=1,status=RunStatus.COMPLETED,result=optimize(),confirmed=True)
    with pytest.raises(RunError) as error:
        require_confirmable(run)
    assert error.value.code == 'ALREADY_CONFIRMED'


def test_complete_geometry_and_residual_proof_revalidate_without_search(monkeypatch):
    result = optimize([piece(width=3,height=1,quantity=2)],[stock(5,width=2,height=4)])
    result,residuals = calculate_metrics(result,Decimal(1),Decimal(1))
    monkeypatch.setattr('app.modules.optimization.domain.first_fit.FirstFitOptimizer.optimize',lambda *a,**k:pytest.fail('No First Fit during confirmation'))
    assert validate_stored_geometry(result,Decimal(1),Decimal(1),residuals) == residuals
    assert all(p.rotation_deg==90 for p in result.placements)


@pytest.mark.parametrize('corruption',['contour','overlap','rotation','residual','metric'])
def test_persisted_geometric_corruption_rejected(corruption):
    result = optimize([piece(width=2,height=2,quantity=2)],[stock(5,width=6,height=2)])
    result,residuals = calculate_metrics(result,Decimal(1),Decimal(1))
    placements = list(result.placements)
    if corruption=='contour': placements[0]=replace(placements[0],geometry={'type':'RECTANGULO','width_mm':1,'height_mm':1})
    if corruption=='overlap': placements[1]=replace(placements[1],x_mm=0,y_mm=0)
    if corruption=='rotation': placements[0]=replace(placements[0],rotation_deg=Decimal(1))
    if corruption=='residual': residuals=tuple(replace(r,x_mm=0) for r in residuals)
    if corruption=='metric': result=replace(result,metrics=replace(result.metrics,utilization_pct=1))
    result=replace(result,placements=tuple(placements))
    with pytest.raises(ValueError):
        validate_stored_geometry(result,Decimal(1),Decimal(1),residuals)
