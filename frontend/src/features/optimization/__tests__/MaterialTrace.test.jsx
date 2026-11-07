import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import fixture from '../../../../../docs/contracts/optimization/comparison-v2.json';
import { MaterialTrace, InventoryReceipt } from '../MaterialTrace';

const result = () => structuredClone(Object.values(fixture.results)[0].result);

test('physical sources are counted once and show inventory IDs, pieces and real geometry', () => {
  const value = result();
  render(<MaterialTrace result={value} />);
  expect(screen.getByRole('region', { name: 'Materiales propuestos' })).toHaveTextContent('1 planchas comerciales');
  const source = screen.getByText(/Plancha comercial #1 · unidad 1/);
  fireEvent.click(source);
  expect(screen.getByText('12 × 8 mm')).toBeInTheDocument();
  expect(screen.getByLabelText('Piezas en Plancha comercial #1, unidad 1').children).toHaveLength(value.placements.length);
  expect(screen.getByText('Área residual total')).toBeInTheDocument();
  expect(screen.getByText(/solo se registran como nuevos retazos al confirmar/)).toBeInTheDocument();
});

test('partial and empty proposals do not claim definitive inventory consumption', () => {
  const value = structuredClone(fixture.partial_result.result);
  const view = render(<MaterialTrace result={value} compact />);
  expect(screen.getByText(/Propuesta parcial: no puede confirmarse/)).toBeInTheDocument();
  view.rerender(<MaterialTrace result={{ ...value, materials_used: [], placements: [] }} compact />);
  expect(screen.getByText('Este resultado no propone consumir materiales.')).toBeInTheDocument();
});

test('an existing polygon remnant remains distinct from potential new remnants', () => {
  const value = result();
  value.materials_used[0] = { ...value.materials_used[0], material_source: 'RETAZO', material_id: 77,
    geometria: { type: 'POLIGONO_CONVEXO', vertices_mm: [[0, 0], [12, 0], [12, 8], [0, 8]] } };
  value.placements = value.placements.map(p => ({ ...p, material_source: 'RETAZO', material_id: 77 }));
  value.residual_regions = value.residual_regions.map(r => ({ ...r, material_source: 'RETAZO', material_id: 77 }));
  render(<MaterialTrace result={value} />);
  expect(screen.getByText(/0 planchas comerciales · 1 retazos de inventario/)).toBeInTheDocument();
  fireEvent.click(screen.getByText(/Retazo de inventario #77 · unidad 1/));
  expect(screen.getByText(/Polígono · vértices/)).toHaveTextContent('(12, 8)');
  expect(screen.queryByText('Nuevos retazos registrados')).not.toBeInTheDocument();
});

test('registered consumption and new remnants come only from the durable receipt', () => {
  const stock = { source: 'RETAZO', material_id: 77, physical_unit_index: 1 };
  const view = render(<InventoryReceipt confirmation={null} />);
  expect(screen.queryByRole('region', { name: 'Inventario registrado' })).not.toBeInTheDocument();
  view.rerender(<InventoryReceipt confirmation={{ receipt: { materials_consumed: [stock],
    remnants_created: [{ remnant_id: 88, area_mm2: '45', source: stock }] } }} />);
  expect(screen.getByRole('region', { name: 'Inventario registrado' })).toHaveTextContent('Retazo de inventario #77');
  expect(screen.getByText(/Retazo #88/)).toBeInTheDocument();
});
