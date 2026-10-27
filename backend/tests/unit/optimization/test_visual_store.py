from dataclasses import replace
from decimal import Decimal as D

import pytest

from app.modules.optimization.application.admission import OptimizerBusy
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.application.visual import mask_window
from app.modules.optimization.infrastructure.visual_store import InMemoryVisualStore
from app.modules.optimization.domain.rotation import RasterCache
from tests.unit.optimization.test_first_fit import problem


def register(session):
    unit = problem().units[0]
    return session.register('PIECE', unit, RasterCache().base(unit, D(1)))


def test_active_contexts_not_evicted_and_completed_contexts_expire_or_make_space():
    now = [0.0]
    store = InMemoryVisualStore(clock=lambda: now[0])
    first, second = store.reserve(), store.reserve()
    first.bind(1); second.bind(2)
    register(first)
    with pytest.raises(OptimizerBusy):
        store.reserve()
    now[0] = 1000
    assert store.get(1) is first
    first.finish()
    third = store.reserve(); third.bind(3)
    with pytest.raises(RunError, match='detalle visual'):
        store.get(1)
    second.finish()
    now[0] += 300
    with pytest.raises(RunError):
        store.get(2)
    assert store.get(3) is third
    third.abort()
    assert not store.contexts


def test_reference_and_bits_are_shared_across_units_and_bounds_are_neutral():
    store = InMemoryVisualStore()
    session = store.reserve(); session.bind(1)
    unit = problem().units[0]
    orientation = RasterCache().base(unit, D(1))
    first = session.register('PIECE', unit, orientation)
    assert session.register('PIECE', replace(unit, unit_index=2), orientation) is first
    charged = session.charged_bytes
    store.max_bytes = charged
    other = session.register('PIECE', replace(unit, piece_id=2), orientation)
    assert other.orientation.mask is first.orientation.mask and session.charged_bytes == charged
    store.max_records = 2
    assert session.register('PIECE', replace(unit, piece_id=3), orientation) is None
    assert session.get(first.reference) is first
    assert orientation.mask.rows == (15, 15)


def test_windows_keep_exact_bits_and_absolute_offsets():
    session = InMemoryVisualStore().reserve(); session.bind(1)
    record = register(session)
    data = mask_window(record, row_start=1, row_count=1, column_start=1, column_count=2)
    assert data['spans_by_row'] == [{'row': 1, 'runs': [(1, 3)]}]
    for kwargs in ({'row_count': 257}, {'column_count': 1025}, {'row_start': -1}, {'row_start': 2}, {'column_count': 0}):
        with pytest.raises(RunError):
            mask_window(record, **kwargs)


def test_mask_budget_exact_and_plus_one():
    first = InMemoryVisualStore().reserve(); first.bind(1)
    register(first)
    exact = InMemoryVisualStore(max_bytes=first.charged_bytes).reserve(); exact.bind(2)
    assert register(exact) is not None
    small = InMemoryVisualStore(max_bytes=first.charged_bytes - 1).reserve(); small.bind(3)
    assert register(small) is None and not small.records


def test_reference_from_another_run_cannot_be_resolved():
    store = InMemoryVisualStore()
    first, second = store.reserve(), store.reserve()
    first.bind(1); second.bind(2)
    reference = register(first).reference
    with pytest.raises(RunError) as error:
        second.get(reference)
    assert error.value.code == 'NOT_FOUND'
