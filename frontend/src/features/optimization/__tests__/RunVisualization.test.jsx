import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { RunMaskInspection } from '../RunMaskInspection';
import { RunVisualization } from '../RunVisualization';
import { emptyVisual } from '../visualState';

const descriptor = angle => ({ id_optimizacion: 101, available: true, mask_ref: (angle ? 'a' : 'b').repeat(32), kind: 'PIECE',
  resolution_mm: '1', rotation_deg: String(angle), columns: angle ? 2 : 3, row_count: angle ? 3 : 2, occupied_cells: 6,
  piece: { id_pedido: 10, id_pieza: 27 }, source: null, reason: null });
const data = mask => ({ ...mask, schema_version: 2, geometria: { type: 'RECTANGULO', width_mm: mask.columns, height_mm: mask.row_count },
  geometria_original: { type: 'RECTANGULO', width_mm: 3, height_mm: 2 },
  window: { row_start: 0, row_count: mask.row_count, column_start: 0, column_count: mask.columns },
  spans_by_row: Array.from({ length: mask.row_count }, (_, row) => ({ row, runs: [[0, mask.columns]] })) });
const visual = mask => ({ ...emptyVisual(), enabled: true, preparation: 'complete',
  descriptors: { [mask.mask_ref]: mask }, current: { id_pedido: 10, id_pieza: 27, unit_index: 1, mask }, processed: 1 });
const deferred = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return { promise, resolve }; };
beforeEach(() => vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ fillRect: vi.fn(), setTransform: vi.fn() }));

test('loads the authoritative mask with its run, orientation and exact window', async () => {
  const mask = descriptor(90), value = data(mask);
  const adapter = { loadVisualMask: vi.fn().mockResolvedValue(value) };
  render(<RunMaskInspection runId={101} adapter={adapter} visual={visual(mask)} />);
  expect(screen.getByText('Consultando máscara de la corrida…')).toBeVisible();
  expect(await screen.findByRole('img', { name: 'Contorno utilizado de la pieza #27' })).toBeVisible();
  expect(screen.getByRole('img', { name: 'Detalle del corte de la pieza #27' })).toBeVisible();
  expect(document.querySelector('[data-mask-angle]')).toHaveAttribute('data-mask-angle', '90');
  expect(screen.getByText(/Ventana exacta/)).toHaveTextContent('filas 1–3 de 3');
  expect(adapter.loadVisualMask).toHaveBeenCalledExactlyOnceWith(101, mask,
    expect.objectContaining({ row_start: 0, row_count: 3, column_count: 2, signal: expect.any(AbortSignal) }));
});

test('late responses are aborted and never replace a new orientation', async () => {
  const old = descriptor(90), current = descriptor(0), pending = deferred();
  const adapter = { loadVisualMask: vi.fn().mockReturnValueOnce(pending.promise).mockResolvedValueOnce(data(current)) };
  const view = render(<RunMaskInspection runId={101} adapter={adapter} visual={visual(old)} />);
  await waitFor(() => expect(adapter.loadVisualMask).toHaveBeenCalledOnce());
  const signal = adapter.loadVisualMask.mock.calls[0][2].signal;
  view.rerender(<RunMaskInspection runId={101} adapter={adapter} visual={visual(current)} />);
  await waitFor(() => expect(document.querySelector('[data-mask-angle]')).toHaveAttribute('data-mask-angle', '0'));
  expect(signal.aborted).toBe(true);
  await act(async () => pending.resolve(data(old)));
  expect(document.querySelector('[data-mask-angle]')).toHaveAttribute('data-mask-angle', '0');
});

test('expired masks show an honest error and only retry on explicit request', async () => {
  const mask = descriptor(90);
  const adapter = { loadVisualMask: vi.fn().mockRejectedValueOnce(Object.assign(new Error('expired'), { status: 410 })).mockResolvedValueOnce(data(mask)) };
  render(<RunMaskInspection runId={101} adapter={adapter} visual={visual(mask)} />);
  expect(await screen.findByText(/La máscara ya no está disponible/)).toBeVisible();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(adapter.loadVisualMask).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button', { name: 'Reintentar máscara' }));
  await screen.findByRole('img', { name: 'Detalle del corte de la pieza #27' });
  expect(adapter.loadVisualMask).toHaveBeenCalledTimes(2);
});

test('pausing and hiding leave processing live and never restart a run', async () => {
  const first = descriptor(90), next = descriptor(0);
  const adapter = { loadVisualMask: vi.fn(async (_, mask) => data(mask)), createEventSource: vi.fn() };
  const state = { visual: visual(first), placed_units: 0, total_units: 2, optimizationId: 101 };
  const view = render(<RunVisualization state={state} adapter={adapter} />);
  await screen.findByRole('img', { name: 'Detalle del corte de la pieza #27' });
  fireEvent.click(screen.getByRole('button', { name: 'Pausar vista' }));
  view.rerender(<RunVisualization state={{ ...state, visual: { ...visual(next), processed: 2 }, placed_units: 1 }} adapter={adapter} />);
  expect(screen.getByText(/2 \/ 2 piezas procesadas/)).toBeVisible();
  expect(document.querySelector('[data-mask-angle]')).toHaveAttribute('data-mask-angle', '90');
  fireEvent.click(screen.getByRole('button', { name: 'Reanudar vista' }));
  await waitFor(() => expect(document.querySelector('[data-mask-angle]')).toHaveAttribute('data-mask-angle', '0'));
  const hide = screen.getByRole('button', { name: 'Ocultar detalle visual' }); hide.focus(); fireEvent.click(hide);
  expect(screen.getByRole('button', { name: 'Mostrar detalle visual' })).toHaveFocus();
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(adapter.createEventSource).not.toHaveBeenCalled();
});

test('empty and reduced-detail states do not fabricate masks', () => {
  const adapter = { loadVisualMask: vi.fn() };
  render(<RunMaskInspection runId={101} adapter={adapter} visual={emptyVisual()} />);
  expect(screen.getByRole('status')).toHaveTextContent('cuando el servidor prepare');
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(adapter.loadVisualMask).not.toHaveBeenCalled();
});

test('an unavailable current orientation does not silently show an older base mask', () => {
  const base = descriptor(0), unavailable = { ...descriptor(90), available: false,
    mask_ref: null, reason: 'VISUAL_BUDGET_EXCEEDED' };
  const adapter = { loadVisualMask: vi.fn() };
  render(<RunMaskInspection runId={101} adapter={adapter} visual={{ ...visual(base), current: { mask: unavailable } }} />);
  expect(screen.getByRole('status')).toHaveTextContent('presupuesto visual');
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  expect(adapter.loadVisualMask).not.toHaveBeenCalled();
});
