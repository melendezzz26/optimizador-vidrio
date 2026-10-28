"""Visual fact projection and references; never computes geometry or placements."""
from decimal import Decimal
from time import monotonic

from ..application.visual import OrientationSampler
from .run_serialization import config_response, progress_response, unit_reference
from .visual_schemas import MaskDescriptorV2


def stock_reference(stock):
    return dict(material_source=stock.source, material_id=stock.material_id,
                stock_unit_index=stock.physical_unit_index)


def describe_mask(session, kind, owner, orientation, record=None):
    mask = orientation.mask
    return MaskDescriptorV2(id_optimizacion=session.run_id, available=record is not None,
        mask_ref=record.reference if record else None, kind=kind,
        resolution_mm=session.resolution if session.resolution is not None else Decimal(str(mask.resolution_mm)), rotation_deg=orientation.rotation_deg,
        columns=mask.columns, row_count=mask.row_count, occupied_cells=mask.occupied_cells,
        piece=dict(id_pedido=owner.order_id, id_pieza=owner.piece_id) if kind == 'PIECE' else None,
        source=stock_reference(owner) if kind == 'MATERIAL' else None,
        reason=None if record else 'VISUAL_BUDGET_EXCEEDED').model_dump()


def describe_record(session, record):
    return describe_mask(session, record.kind, record.owner, record.orientation, record)


class VisualProjection:
    def __init__(self, session, emit, *, clock=monotonic):
        self.session, self.emit = session, emit
        self.sampler, self.processed = OrientationSampler(clock=clock), 0

    def __call__(self, fact):
        kind = fact.kind
        self.session.progress(prepared=True if kind == 'preparation_completed' else None,
            evaluations=fact.evaluation_index if kind == 'orientation_testing' else None,
            processed=fact.processed_units)
        if kind == 'orientation_testing' and not self.sampler.accept(fact.unit):
            return
        self.processed = fact.processed_units
        data = {}
        if kind == 'preparation_started':
            data.update(metodo='FF', configuracion=config_response(fact.config),
                unique_pieces=fact.unique_pieces, material_bases=fact.material_bases, total_units=fact.total_units)
        elif kind == 'preparation_completed':
            data.update(unique_pieces=fact.unique_pieces, material_bases=fact.material_bases, total_units=fact.total_units)
        elif kind in ('piece_rasterizing', 'piece_ready'):
            data.update(id_pedido=fact.unit.order_id, id_pieza=fact.unit.piece_id,
                id_tipo_vidrio=fact.unit.glass_type_id, espesor_mm=fact.unit.thickness_mm, cantidad=fact.quantity)
        else:
            data.update(unit_reference(fact.unit), **progress_response(fact.placed_units, fact.total_units),
                processed_units=fact.processed_units)
        if fact.orientation is not None:
            record = self.session.register('PIECE', fact.unit, fact.orientation)
            data['mask'] = describe_mask(self.session, 'PIECE', fact.unit, fact.orientation, record)
        if fact.stock is not None:
            data['source'] = stock_reference(fact.stock)
        if kind == 'orientation_testing':
            data.update(evaluation_index=fact.evaluation_index, sampled=True)
        elif kind == 'source_selected':
            record = self.session.material(fact.stock, fact.material_mask)
            # The source normalization is also retained when visual memory is full.
            from ..domain.rotation import Orientation, oriented_geometry
            orientation = record.orientation if record else Orientation(Decimal(0), oriented_geometry(fact.stock.geometry, 0), fact.material_mask)
            data.update(material_mask=describe_mask(self.session, 'MATERIAL', fact.stock, orientation, record),
                score=fact.score, score_name='remaining_free_cells_after_placement' if fact.score is not None else None)
        elif kind == 'piece_unplaced':
            data['reason'] = 'NO_FIT'
        self.emit(kind, data)
