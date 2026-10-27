"""Single-process, lock-protected retention of immutable engine masks (DG-01)."""
from threading import RLock
from time import monotonic
from uuid import uuid4
from decimal import Decimal

from ..application.admission import OptimizerBusy
from ..application.errors import RunError
from ..application.visual import MaskRecord
from ..domain.rotation import INTERNAL_CACHE_BYTES, Orientation, oriented_geometry


class VisualSession:
    def __init__(self, store):
        self.store, self.run_id, self.finished_at = store, None, None
        self.resolution = None
        self.records, self.keys, self.mask_ids = {}, {}, set()
        self.charged_bytes = 0

    def bind(self, run_id, resolution=None):
        with self.store.lock:
            self.run_id = run_id
            self.resolution = resolution

    def register(self, kind, owner, orientation):
        with self.store.lock:
            identity = (owner.order_id, owner.piece_id) if kind == 'PIECE' else owner.identity
            mask = orientation.mask
            key = (kind, identity, mask.resolution_mm, orientation.rotation_deg)
            if key in self.keys:
                return self.records[self.keys[key]]
            charged = 0 if id(mask) in self.mask_ids else (
                mask.row_count * (40 + 4 * ((mask.columns + 29) // 30)) + 4096
                + len(orientation.geometry.get('vertices_mm', ())) * 512)
            if len(self.records) >= self.store.max_records or self.charged_bytes + charged > self.store.max_bytes:
                return None
            reference = uuid4().hex
            record = MaskRecord(reference, kind, owner, orientation)
            self.records[reference] = record
            self.keys[key] = reference
            self.mask_ids.add(id(mask))
            self.charged_bytes += charged
            return record

    def material(self, stock, mask):
        return self.register('MATERIAL', stock, Orientation(Decimal(0), oriented_geometry(stock.geometry, 0), mask))

    def finish(self):
        with self.store.lock:
            if self.finished_at is None:
                self.finished_at = self.store.clock()

    def abort(self):
        with self.store.lock:
            self.store._drop(self)

    def manifest(self, offset=0, limit=64):
        with self.store.lock:
            values = list(self.records.values())
            if type(offset) is not int or offset < 0 or not 1 <= limit <= 64:
                raise RunError('INVALID_INPUT', 'La página visual no es válida.')
            items = values[offset:offset + limit]
            next_offset = offset + len(items)
            return items, len(values), next_offset if next_offset < len(values) else None

    def get(self, reference):
        with self.store.lock:
            if reference not in self.records:
                raise RunError('NOT_FOUND', 'La máscara no pertenece a esta corrida.')
            return self.records[reference]


class InMemoryVisualStore:
    def __init__(self, *, clock=monotonic, max_contexts=2, max_bytes=INTERNAL_CACHE_BYTES,
                 max_records=1024, ttl=300):
        self.clock, self.max_contexts, self.max_bytes = clock, max_contexts, max_bytes
        self.max_records, self.ttl, self.lock = max_records, ttl, RLock()
        self.contexts = []

    def _drop(self, session):
        if session in self.contexts:
            self.contexts.remove(session)
        session.records.clear()
        session.keys.clear()
        session.mask_ids.clear()
        session.charged_bytes = 0

    def _prune(self):
        now = self.clock()
        for session in self.contexts[:]:
            if session.finished_at is not None and now - session.finished_at >= self.ttl:
                self._drop(session)

    def reserve(self):
        with self.lock:
            self._prune()
            if len(self.contexts) >= self.max_contexts:
                completed = [session for session in self.contexts if session.finished_at is not None]
                if not completed:
                    raise OptimizerBusy('active_runs', self.max_contexts, len(self.contexts))
                self._drop(min(completed, key=lambda session: session.finished_at))
            session = VisualSession(self)
            self.contexts.append(session)
            return session

    def get(self, run_id):
        with self.lock:
            self._prune()
            for session in self.contexts:
                if session.run_id == run_id:
                    return session
        raise RunError('VISUAL_DATA_UNAVAILABLE', 'El detalle visual ya no está disponible. Consulta el resultado guardado.')
