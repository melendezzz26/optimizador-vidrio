"""Pruebas de RasterMask (SPEC-TA-005-TA-006, CA-09)."""
import dataclasses

import pytest

from app.modules.optimization.domain.raster_mask import RasterMask, RasterizationError


def test_from_spans_builds_one_bit_per_occupied_column():
    mask = RasterMask.from_spans(5.0, 4, [(0, 4), (1, 3)])

    assert mask.rows == (0b1111, 0b0110)
    assert mask.to_text() == "####\n.##."


def test_exposes_size_cells_and_area():
    mask = RasterMask.from_spans(5.0, 4, [(0, 4), (1, 3)])

    assert (mask.row_count, mask.columns) == (2, 4)
    assert (mask.width_mm, mask.height_mm) == (20.0, 10.0)
    assert mask.occupied_cells == 6
    assert mask.area_mm2 == 150.0


def test_is_occupied_reads_a_single_cell():
    mask = RasterMask.from_spans(5.0, 4, [(1, 3)])

    assert [mask.is_occupied(0, column) for column in range(4)] == [False, True, True, False]


@pytest.mark.parametrize("row, column", [(-1, 0), (1, 0), (0, -1), (0, 4)])
def test_is_occupied_rejects_cells_outside_the_mask(row, column):
    mask = RasterMask.from_spans(5.0, 4, [(0, 4)])

    with pytest.raises(IndexError):
        mask.is_occupied(row, column)


def test_mask_is_immutable():
    mask = RasterMask(5.0, 2, [0b11])

    assert isinstance(mask.rows, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        mask.columns = 3


@pytest.mark.parametrize("resolution", [0, -5, float("nan"), float("inf"), True, "5"])
def test_rejects_invalid_resolution(resolution):
    with pytest.raises(RasterizationError):
        RasterMask(resolution, 2, (0b11,))


@pytest.mark.parametrize("columns, rows", [(0, (0,)), (2, ()), (2, (0b100,)), (2, (-1,))])
def test_rejects_rows_outside_the_mask(columns, rows):
    with pytest.raises(RasterizationError):
        RasterMask(5.0, columns, rows)


def test_from_spans_rejects_span_outside_columns():
    with pytest.raises(RasterizationError):
        RasterMask.from_spans(5.0, 4, [(2, 5)])
        
def test_row_runs_lists_occupied_spans_from_left_to_right():
    mask = RasterMask(5.0, 8, [0b1110_0110, 0, 0b1111_1111])

    assert mask.row_runs(0) == ((1, 3), (5, 8))
    assert mask.row_runs(1) == ()
    assert mask.row_runs(2) == ((0, 8),)


def test_row_runs_rejects_rows_outside_the_mask():
    with pytest.raises(IndexError):
        RasterMask(5.0, 2, [0b11]).row_runs(1)