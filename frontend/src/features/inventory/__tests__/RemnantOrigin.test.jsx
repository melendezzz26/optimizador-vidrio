import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import { RemnantOrigin } from '../RemnantOrigin';
import { getRetazoOrigin } from '../inventoryApi';

vi.mock('../inventoryApi', () => ({ getRetazoOrigin: vi.fn() }));
const resource = { id_retazo: 7, codigo: 'REM-7', id_tipo_vidrio: 2, espesor_mm: '6.0', area_mm2: '1000', fecha_registro: '2026-10-16T12:00:00Z', geometria: { type: 'RECTANGULO', width_mm: 50, height_mm: 20 } };

test.each([
  { type: 'RECTANGULO', width_mm: 50, height_mm: 20 },
  { type: 'POLIGONO_CONVEXO', vertices_mm: [[-20, -10], [40, -10], [20, 30], [-10, 20]] },
  { type: 'CIRCUNFERENCIA', radius_mm: 20 },
  { type: 'RECTANGULO', width_mm: '2140.000', height_mm: '900.000' },
  { type: 'POLIGONO_CONVEXO', vertices_mm: [['-20.0', '-10.0'], ['40.0', '-10.0'], ['20.0', '30.0']] },
  { type: 'CIRCUNFERENCIA', radius_mm: '20.000' },
])('manual/historical geometry %j has a responsive preview and no invented run', geometria => {
  const original = JSON.stringify(geometria);
  render(<RemnantOrigin resource={{ ...resource, geometria }} glassName="Bronce" canViewCut />);
  expect(screen.getByText('Registro manual o histórico')).toBeVisible();
  expect(screen.getByRole('img', { name: 'Vista previa 2D del retazo REM-7' })).toHaveAttribute('preserveAspectRatio', 'xMidYMid meet');
  expect(screen.queryByRole('button', { name: 'Ver corte de origen' })).not.toBeInTheDocument();
  expect(getRetazoOrigin).not.toHaveBeenCalled();
  expect(JSON.stringify(geometria)).toBe(original);
});

test('real origin references the execution, orders and physical source; opens its durable result', async () => {
  getRetazoOrigin.mockResolvedValue({ id_ejecucion_origen: 4, id_optimizacion: 64, order_ids: [64, 16], source: { material_source: 'PLANCHA', material_id: 9, stock_unit_index: 2 } });
  const open = vi.fn();
  render(<RemnantOrigin resource={{ ...resource, id_ejecucion_origen: 4 }} glassName="Bronce" canViewCut onOpenCut={open} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Ver corte de origen' }));
  expect(open).toHaveBeenCalledExactlyOnceWith(64);
  expect(screen.getByText('#64, #16')).toBeVisible();
  expect(screen.getByText('Plancha #9 · unidad 2')).toBeVisible();
  expect(getRetazoOrigin).toHaveBeenCalledWith(7, expect.objectContaining({ signal: expect.any(AbortSignal) }));
});

test('origin fetch can retry and cannot expose the result action without optimization.view', async () => {
  getRetazoOrigin.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ id_optimizacion: 64, order_ids: [64] });
  render(<RemnantOrigin resource={{ ...resource, id_ejecucion_origen: 4 }} onOpenCut={vi.fn()} canViewCut={false} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Reintentar origen' }));
  await waitFor(() => expect(screen.getByText('Trabajo/Optimización').nextElementSibling).toHaveTextContent('#64'));
  expect(screen.queryByRole('button', { name: 'Ver corte de origen' })).not.toBeInTheDocument();
});
