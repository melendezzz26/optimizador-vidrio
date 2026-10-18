import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { GeometryPreview } from '../GeometryPreview';
import { RasterPreview } from '../RasterPreview';
import { drawRasterMask } from '../rasterCanvas';
import { getGeometryBounds, getRasterComparisonFrame, getRasterDrawLayout, rasterSpanRectangles } from '../visualizationGeometry';

const rectangle = { type: 'RECTANGULO', width_mm: 800, height_mm: 600 };
const circle = { type: 'CIRCUNFERENCIA', radius_mm: 20 };
const polygon = { type: 'POLIGONO_CONVEXO', vertices_mm: [[-30, -10], [20, -10], [25, 5], [0, 20], [-35, 10]] };
const raster = {
  tipo_forma: 'RECTANGULO', cantidad: 5, resolution_mm: 5, row_count: 2, columns: 3,
  occupied_cells: 2, spans_by_row: [{ row: 0, runs: [] }, { row: 1, runs: [[1, 3]] }],
};
const frame = getRasterComparisonFrame(rectangle, raster);
let context;

beforeEach(() => {
  context = { fillRect: vi.fn(), setTransform: vi.fn() };
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(context);
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ width: 480, height: 320, top: 0, right: 480, bottom: 320, left: 0, x: 0, y: 0, toJSON() {} });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

test.each([
  ['RECTANGULO', rectangle],
  ['CIRCUNFERENCIA', circle],
  ['POLIGONO_CONVEXO', polygon],
])('geometría original %s tiene nombre accesible y conserva sus medidas', (shape, geometry) => {
  const previewFrame = getRasterComparisonFrame(geometry);
  render(<GeometryPreview geometry={geometry} pieceId={51} frame={previewFrame} />);
  const svg = screen.getByRole('img', { name: 'Geometría original de la pieza #51' });
  expect(svg).toHaveAttribute('viewBox', previewFrame.viewBox);
  if (shape === 'RECTANGULO') {
    expect(svg.querySelector('rect')).toHaveAttribute('width', '800');
    expect(svg.querySelector('rect')).toHaveAttribute('height', '600');
  }
  if (shape === 'CIRCUNFERENCIA') {
    expect(svg.querySelector('circle')).toHaveAttribute('r', '20');
    expect(svg.querySelector('circle')).toHaveAttribute('cx', '0');
    expect(svg.querySelector('circle')).toHaveAttribute('cy', '0');
  }
  if (shape === 'POLIGONO_CONVEXO') {
    expect(svg.querySelector('polygon')).toHaveAttribute('points', '-30,-10 20,-10 25,5 0,20 -35,10');
    expect(svg.querySelector('g')).toHaveAttribute('transform', 'translate(35 10)');
  }
});

test('el bbox negativo se traslada solo para dibujar y comparte extensión física con la rejilla', () => {
  expect(getGeometryBounds(polygon)).toEqual({ minX: -35, minY: -10, width: 60, height: 30 });
  const comparison = getRasterComparisonFrame(polygon, { columns: 14, row_count: 8, resolution_mm: 5 });
  expect(comparison.width).toBe(70);
  expect(comparison.height).toBe(40);
});

test('spans vacíos conservan su índice y el final exclusivo se traduce a ancho de cuatro celdas', () => {
  const rectangles = [...rasterSpanRectangles([
    { row: 0, runs: [] },
    { row: 1, runs: [[3, 7]] },
    { row: 2, runs: [[0, 1], [4, 6]] },
  ], 5)];
  expect(rectangles).toEqual([
    { x: 15, y: 5, width: 20, height: 5 },
    { x: 0, y: 10, width: 5, height: 5 },
    { x: 20, y: 10, width: 10, height: 5 },
  ]);
});

test('el dibujo mantiene escala física común, celdas cuadradas y una llamada por tramo', () => {
  const layout = getRasterDrawLayout(frame, raster.columns, raster.row_count, 480, 320, raster.resolution_mm);
  expect(layout.maskWidth / raster.columns).toBeCloseTo(layout.maskHeight / raster.row_count, 10);
  const pixelsPerMm = Math.min(
    480 / (frame.width + frame.padding * 2),
    320 / (frame.height + frame.padding * 2),
  );
  expect(layout.cellSize).toBeCloseTo(raster.resolution_mm * pixelsPerMm, 10);
  expect(layout.maskWidth).toBeCloseTo(raster.columns * raster.resolution_mm * pixelsPerMm, 10);
  expect(layout.maskHeight).toBeCloseTo(raster.row_count * raster.resolution_mm * pixelsPerMm, 10);
  const result = drawRasterMask(context, raster, frame, { width: 480, height: 320 }, {
    background: '#fff', occupied: '#2563eb', grid: '#64748b',
  });
  expect(result.runCount).toBe(1);
  // One background and one occupied span; the empty row creates no run.
  expect(context.fillRect).toHaveBeenCalledWith(layout.x + layout.cellSize, layout.y + layout.cellSize, layout.cellSize * 2, layout.cellSize);
});

test('un raster de un millón de celdas dibuja por sus 1000 spans y mantiene el backing ligado al viewport', () => {
  const largeRaster = {
    ...raster,
    resolution_mm: 1,
    row_count: 1000,
    columns: 1000,
    occupied_cells: 1000000,
    spans_by_row: Array.from({ length: 1000 }, (_, row) => ({ row, runs: [[0, 1000]] })),
  };
  const largeFrame = getRasterComparisonFrame(rectangle, largeRaster);
  context.fillRect.mockClear();
  const result = drawRasterMask(context, largeRaster, largeFrame, { width: 480, height: 320 }, {
    background: '#fff', occupied: '#2563eb', grid: '#64748b',
  });
  expect(result.runCount).toBe(1000);
  expect(context.fillRect).toHaveBeenCalledTimes(1001);
  expect(largeFrame.width * largeFrame.height).toBe(1000000);
  expect(result.maskWidth).toBeLessThan(480);
  expect(result.maskHeight).toBeLessThan(320);
});

test('raster sin datos ofrece estado vacío; con datos expone resumen accesible y un canvas', () => {
  const { rerender } = render(<RasterPreview raster={null} pieceId={51} frame={frame} />);
  expect(screen.getByRole('status')).toHaveTextContent('Selecciona «Ver pieza»');
  rerender(<RasterPreview raster={{ ...raster, id_pieza: 51 }} pieceId={51} frame={frame} />);
  const canvas = screen.getByRole('img', { name: 'Detalle del corte de la pieza #51' });
  expect(canvas).toBeVisible();
  expect(canvas).toHaveAttribute('aria-labelledby');
  expect(canvas).toHaveAttribute('aria-describedby');
  expect(screen.getByText(/2 filas, 3 columnas, 2 celdas ocupadas; cantidad 5/)).toBeVisible();
  expect(document.querySelectorAll('canvas')).toHaveLength(1);
  expect(document.querySelectorAll('canvas *')).toHaveLength(0);
});
