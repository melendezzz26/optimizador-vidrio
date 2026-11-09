"""Exact placement oracle for reordered/redundant raster row constraints."""
import random

import pytest

from app.modules.optimization.domain.placement import LayoutQueryMemo, SheetLayout
from app.modules.optimization.domain.raster_mask import RasterMask


def exhaustive(layout, piece):
    return next(((r, c)
                 for r in range(layout.material.row_count - piece.row_count + 1)
                 for c in range(layout.material.columns - piece.columns + 1)
                 if layout.check(piece, r, c).is_valid), None)


@pytest.mark.parametrize('seed', range(8))
def test_exact_scan_with_repeated_irregular_rows_margins_and_separation(seed):
    rng = random.Random(seed)
    for _ in range(80):
        columns, rows = rng.randrange(4, 19), rng.randrange(4, 19)
        palette = [rng.getrandbits(columns) for _ in range(4)]
        material = RasterMask(0.5, columns, tuple(rng.choice(palette) for _ in range(rows)))
        layout = SheetLayout.empty(material, margin_mm=rng.choice((0, 0.5)),
                                   separation_mm=rng.choice((0, 0.5, 1)))
        for _ in range(3):
            width, height = rng.randrange(1, columns + 2), rng.randrange(1, rows + 2)
            # Disconnected masks and empty rows also obey the public bit contract.
            piece = RasterMask(0.5, width, tuple(rng.getrandbits(width) for _ in range(height)))
            expected = exhaustive(layout, piece)
            assert layout.first_position(piece) == expected
            if expected is not None:
                layout = layout.place(piece, *expected)


def test_same_free_rows_require_union_of_disconnected_shape_rows():
    material = RasterMask(1, 9, (0b111011111,) * 8)
    piece = RasterMask(1, 5, (0b00111, 0b11100, 0, 0b01010))
    layout = SheetLayout.empty(material)
    assert layout.first_position(piece) == exhaustive(layout, piece)


def test_repeated_constraints_do_not_hide_later_row_or_leftmost_column():
    material = RasterMask(1, 10, (0b1111000000,) * 4 + (0b1111111111,) * 6)
    piece = RasterMask(1, 5, (0b00100, 0b11111, 0b01110, 0b00100))
    layout = SheetLayout.empty(material)
    assert layout.first_position(piece) == exhaustive(layout, piece) == (3, 4)


def test_empty_piece_rows_retain_grid_bounds_and_original_first_origin():
    layout = SheetLayout.empty(RasterMask(1, 5, (0,) * 5))
    piece = RasterMask(1, 3, (0, 0))
    assert layout.first_position(piece) == exhaustive(layout, piece) == (0, 0)
    assert layout.first_position(RasterMask(1, 6, (0,))) is None


def test_constant_shape_crosses_material_bands_at_first_legal_origin():
    material = RasterMask(1, 12, (0b11110000,) * 5 + (0b11111100,) * 6 + (0b1111,) * 4)
    layout = SheetLayout.empty(material)
    piece = RasterMask(1, 5, (0b11111,) * 5)
    assert layout.first_position(piece) == exhaustive(layout, piece) == (5, 2)


def test_exact_memo_does_not_reuse_the_position_after_placement():
    material = RasterMask(1, 8, (255,) * 6)
    layout = SheetLayout.empty(material)
    piece = RasterMask(1, 4, (15,) * 3)
    memo = LayoutQueryMemo()
    assert memo.find(layout, piece) == (0, 0)
    changed = layout.place(piece, 0, 0)
    assert memo.find(changed, piece) == exhaustive(changed, piece) == (0, 4)
    assert memo.find(layout, piece) == (0, 0)
