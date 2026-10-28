"""Explicit visual-v2 contracts. Frozen V1 models and consumers stay unchanged."""
from typing import Annotated, Literal, Union

from pydantic import Field, create_model, model_validator

from . import run_schemas as v1


class PieceKeyV2(v1.ContractV1):
    id_pedido: v1.PositiveId
    id_pieza: v1.PositiveId


class MaskDescriptorV2(v1.ContractV1):
    id_optimizacion: v1.PositiveId
    available: bool
    mask_ref: Annotated[str, Field(pattern=r'^[a-f0-9]{32}$')] | None
    kind: Literal['PIECE', 'MATERIAL']
    resolution_mm: v1.PositiveDecimal
    rotation_deg: Annotated[v1.NonnegativeDecimal, Field(lt=360)]
    columns: Annotated[int, Field(strict=True, gt=0, le=4000)]
    row_count: Annotated[int, Field(strict=True, gt=0, le=4000)]
    occupied_cells: Annotated[v1.Count, Field(le=16_000_000)]
    piece: PieceKeyV2 | None = None
    source: v1.StockRefV1 | None = None
    reason: Literal['VISUAL_BUDGET_EXCEEDED'] | None = None

    @model_validator(mode='after')
    def coherent(self):
        if self.available != (self.mask_ref is not None) or self.available != (self.reason is None):
            raise ValueError('Availability must match the retained reference.')
        if (self.kind == 'PIECE') != (self.piece is not None) or (self.kind == 'MATERIAL') != (self.source is not None):
            raise ValueError('Mask identity must match its kind.')
        if self.occupied_cells > self.columns * self.row_count:
            raise ValueError('Occupied cells exceed dimensions.')
        return self


class VisualPolicyV2(v1.ContractV1):
    profile: Literal['visual-v2'] = 'visual-v2'
    representative_orientations: Literal[True] = True
    max_extra_samples: Literal[128] = 128
    max_extra_samples_per_second: Literal[10] = 10
    retention_max_seconds: Literal[300] = 300
    retention_may_end_earlier: Literal[True] = True


class StartedV2(v1.StartedDataV1):
    visual: VisualPolicyV2


class ProcessedV2(v1.ProgressV1):
    processed_units: v1.Count

    @model_validator(mode='after')
    def processed(self):
        if not self.placed_units <= self.processed_units <= self.total_units:
            raise ValueError('Processed/placed units are incoherent.')
        return self


class PieceStartedV2(v1.PieceStartedDataV1, ProcessedV2):
    pass


class PiecePlacedV2(v1.PiecePlacedDataV1, ProcessedV2):
    pass


class CompletedV2(v1.CompletedDataV1, ProcessedV2):
    @model_validator(mode='after')
    def all_processed(self):
        if self.processed_units != self.total_units:
            raise ValueError('A completed search processes every unit.')
        return self


class PreparationStartedV2(v1.ContractV1):
    metodo: Literal['FF']
    configuracion: v1.ConfigV1
    unique_pieces: v1.Index
    material_bases: v1.Count
    total_units: v1.Index


class PreparationCompletedV2(v1.ContractV1):
    unique_pieces: v1.Index
    material_bases: v1.Count
    total_units: v1.Index


class PieceRasterizingV2(v1.MaterialKeyV1, PieceKeyV2):
    cantidad: v1.Index


class PieceReadyV2(PieceRasterizingV2):
    mask: MaskDescriptorV2


class OrientationTestingV2(v1.UnitRefV1, ProcessedV2):
    source: v1.StockRefV1
    mask: MaskDescriptorV2
    evaluation_index: v1.Index
    sampled: Literal[True]


class SourceSelectedV2(v1.UnitRefV1, ProcessedV2):
    source: v1.StockRefV1
    mask: MaskDescriptorV2
    material_mask: MaskDescriptorV2
    score_name: Literal['remaining_free_cells_after_placement'] | None
    score: v1.Count | None

    @model_validator(mode='after')
    def real_score(self):
        if (self.score is None) != (self.score_name is None):
            raise ValueError('A score needs a name and value.')
        return self


class PieceUnplacedV2(v1.UnitRefV1, ProcessedV2):
    reason: Literal['NO_FIT']


class EventV2(v1.EventV1):
    schema_version: Literal[2]


DATA_TYPES = {
    'optimization_started': StartedV2, 'group_started': v1.GroupStartedDataV1,
    'piece_started': PieceStartedV2, 'piece_placed': PiecePlacedV2,
    'group_completed': v1.GroupCompletedDataV1, 'metrics_calculated': v1.MetricsDataV1,
    'optimization_completed': CompletedV2, 'optimization_failed': v1.FailedDataV1,
    'preparation_started': PreparationStartedV2, 'preparation_completed': PreparationCompletedV2,
    'piece_rasterizing': PieceRasterizingV2, 'piece_ready': PieceReadyV2,
    'orientation_testing': OrientationTestingV2, 'source_selected': SourceSelectedV2,
    'piece_unplaced': PieceUnplacedV2,
}
EVENT_TYPES = {name: create_model(name.title().replace('_', '') + 'V2', __base__=EventV2,
    event=(Literal[name], ...), data=(data_type, ...)) for name, data_type in DATA_TYPES.items()}
OptimizationEventV2 = Annotated[Union[tuple(EVENT_TYPES.values())], Field(discriminator='event')]


class VisualManifestV2(v1.ContractV1):
    schema_version: Literal[2]
    id_optimizacion: v1.PositiveId
    revision: v1.Count
    items: Annotated[list[MaskDescriptorV2], Field(max_length=64)]
    next_offset: v1.Count | None
    preparation_completed: bool
    evaluations: v1.Count
    processed_units: v1.Count


class WindowV2(v1.ContractV1):
    row_start: v1.Count
    row_count: Annotated[v1.Index, Field(le=256)]
    column_start: v1.Count
    column_count: Annotated[v1.Index, Field(le=1024)]


class SpansV2(v1.ContractV1):
    row: v1.Count
    runs: list[tuple[v1.Count, v1.Index]]


class VisualMaskV2(MaskDescriptorV2):
    schema_version: Literal[2]
    geometria_original: v1.Geometry
    geometria: v1.Geometry
    window: WindowV2
    spans_by_row: list[SpansV2]

    @model_validator(mode='after')
    def valid_window(self):
        w = self.window
        if not self.available or w.row_start + w.row_count > self.row_count or w.column_start + w.column_count > self.columns:
            raise ValueError('Window exceeds the retained mask.')
        if len(self.spans_by_row) != w.row_count:
            raise ValueError('Every requested row must be represented.')
        for index, row in enumerate(self.spans_by_row):
            end = w.column_start
            if row.row != w.row_start + index:
                raise ValueError('Rows must match their absolute offset.')
            for start, stop in row.runs:
                if not end <= start < stop <= w.column_start + w.column_count:
                    raise ValueError('Ranges must be ordered within the window.')
                end = stop
        return self
