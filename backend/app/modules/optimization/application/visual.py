"""Bounded visual artefact contracts and sampling; no HTTP/database dependencies."""
from dataclasses import dataclass
from time import monotonic

from .errors import RunError
from ..domain.problem import PieceUnit, StockCandidate
from ..domain.rotation import Orientation

MAX_EVENT_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 256 * 1024


@dataclass(frozen=True)
class MaskRecord:
    reference: str
    kind: str
    owner: PieceUnit | StockCandidate
    orientation: Orientation


class OrientationSampler:
    def __init__(self, *, clock=monotonic, max_extra=128, interval=0.1):
        self.clock, self.max_extra, self.interval = clock, max_extra, interval
        self.seen, self.extra, self.last_extra = set(), 0, None

    def accept(self, unit):
        key = (unit.order_id, *unit.identity)
        if key not in self.seen:
            self.seen.add(key)
            return True
        now = self.clock()
        if self.extra >= self.max_extra or self.last_extra is not None and now - self.last_extra < self.interval - 1e-12:
            return False
        self.extra += 1
        self.last_extra = now
        return True


def mask_window(record, *, row_start=0, row_count=None, column_start=0, column_count=None):
    mask = record.orientation.mask
    row_count = min(256, mask.row_count - row_start) if row_count is None else row_count
    column_count = min(1024, mask.columns - column_start) if column_count is None else column_count
    if (any(type(value) is not int for value in (row_start, row_count, column_start, column_count))
            or row_start < 0 or column_start < 0 or not 1 <= row_count <= 256 or not 1 <= column_count <= 1024
            or row_start + row_count > mask.row_count or column_start + column_count > mask.columns):
        raise RunError('INVALID_INPUT', 'La ventana de la máscara no es válida.')
    rows = []
    for row in range(row_start, row_start + row_count):
        bits = (mask.rows[row] >> column_start) & ((1 << column_count) - 1)
        runs = []
        while bits:
            start = (bits & -bits).bit_length() - 1
            tail = bits >> start
            length = (tail ^ (tail + 1)).bit_length() - 1
            runs.append((column_start + start, column_start + start + length))
            bits &= ~(((1 << length) - 1) << start)
        rows.append(dict(row=row, runs=runs))
    return dict(row_start=row_start, row_count=row_count, column_start=column_start,
                column_count=column_count, spans_by_row=rows)
