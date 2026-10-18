import { getRasterDrawLayout, rasterSpanRectangles } from './visualizationGeometry';

export function drawRasterMask(context, raster, frame, size, colors) {
  const layout = getRasterDrawLayout(frame, raster.columns, raster.row_count, size.width, size.height, raster.resolution_mm);
  context.fillStyle = colors.background;
  context.fillRect(0, 0, size.width, size.height);
  context.fillStyle = colors.occupied;
  let runCount = 0;
  for (const rectangle of rasterSpanRectangles(raster.spans_by_row, layout.cellSize)) {
    context.fillRect(layout.x + rectangle.x, layout.y + rectangle.y, rectangle.width, rectangle.height);
    runCount += 1;
  }

  if (layout.cellSize >= 8 && raster.columns <= 40 && raster.row_count <= 40) {
    context.fillStyle = colors.grid;
    for (let column = 0; column <= raster.columns; column += 1) {
      const x = layout.x + column * layout.cellSize;
      context.fillRect(x, layout.y, 1, layout.maskHeight);
    }
    for (let row = 0; row <= raster.row_count; row += 1) {
      const y = layout.y + row * layout.cellSize;
      context.fillRect(layout.x, y, layout.maskWidth, 1);
    }
  }
  return { ...layout, runCount };
}
