from ..application.ports import RasterizedPiece
from .schemas import RasterizeResponse


def raster_response(result: RasterizedPiece) -> RasterizeResponse:
    piece, mask = result.piece, result.mask
    return RasterizeResponse(
        **{key: piece[key] for key in (
            "id_pedido", "id_pieza", "tipo_forma", "geometria",
            "id_tipo_vidrio", "espesor_mm", "cantidad",
        )},
        resolution_mm=mask.resolution_mm, row_count=mask.row_count,
        columns=mask.columns, occupied_cells=mask.occupied_cells,
        spans_by_row=[{"row": row, "runs": [list(run) for run in mask.row_runs(row)]}
                      for row in range(mask.row_count)],
    )
