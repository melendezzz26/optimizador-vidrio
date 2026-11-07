"""S2 load review (04/11/2026): ordering_ready follows L-03 = 300 units in v1 and v2."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.optimization.application.load_budget import DEFAULT_RUN_LOAD_BUDGET
from app.modules.optimization.application.visual import MAX_EVENT_BYTES
from app.modules.optimization.presentation.comparison_schemas import ComparisonEvent
from app.modules.optimization.presentation.comparison_v2_schemas import ComparisonEventV2

CRITERION = "area_desc_max_side_desc_order_piece_unit_asc"


def units(count):
    # Large identifiers and a decimal thickness approximate the worst real wire size.
    return [dict(id_tipo_vidrio=2147483647, espesor_mm="10.5", id_pedido=2147483647,
                 id_pieza=2147483600 + i % 40, unit_index=i + 1) for i in range(count)]


def v1_event(count):
    return dict(comparison_id=7, sequence=3, execution_id=71, method="WF", execution_sequence=2,
                timestamp=datetime.now(timezone.utc).isoformat(), event="ordering_ready",
                data=dict(criterion=CRITERION, units=units(count)))


def v2_event(count):
    return dict(v1_event(count), method="M6-BS", presentation="OBSERVED")


def test_ordering_limit_matches_l03():
    assert DEFAULT_RUN_LOAD_BUDGET.max_units == 300


@pytest.mark.parametrize("schema,build", [(ComparisonEvent, v1_event), (ComparisonEventV2, v2_event)],
                         ids=["v1", "v2"])
def test_ordering_ready_accepts_300_units_and_rejects_301(schema, build):
    event = schema.model_validate(build(300))
    assert len(event.data["units"]) == 300
    with pytest.raises(ValidationError):
        schema.model_validate(build(301))


def test_300_unit_ordering_event_stays_below_the_event_byte_budget():
    raw = ComparisonEventV2.model_validate(v2_event(300)).model_dump_json().encode() + b"\n"
    assert len(raw) < MAX_EVENT_BYTES
