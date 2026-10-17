import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, expect, test, vi } from 'vitest';
import { PlacementCanvas } from '../PlacementCanvas';
import { fixturePlacements, prepareFixture } from '../firstFitFixture';
import { DEFAULT_YAW } from '../placementScene';

beforeEach(() => {
  vi.stubGlobal('PointerEvent', class extends MouseEvent {
    constructor(type, properties) { super(type, properties); this.pointerId = properties.pointerId; this.isPrimary = properties.isPrimary ?? true; }
  });
});
const data = () => {
  const snapshot = prepareFixture([21, 22]);
  return { snapshot, placements: fixturePlacements(snapshot) };
};
function open3D() { fireEvent.click(screen.getByRole('button', { name: 'Ver en 3D' })); return screen.getByRole('slider', { name: 'Giro horizontal de la vista 3D' }); }

test('view switch only appears once a visualizable placement exists, defaults to precise 2D', () => {
  const { snapshot, placements } = data();
  const view = render(<PlacementCanvas snapshot={snapshot} placements={[]} />);
  expect(screen.queryByRole('group', { name: 'Vista del resultado' })).not.toBeInTheDocument();
  expect(screen.getByRole('img', { name: 'Colocaciones en plancha #15' })).toBeVisible();
  view.rerender(<PlacementCanvas snapshot={snapshot} placements={placements.slice(0, 1)} />);
  expect(screen.getByRole('button', { name: 'Ver en 2D' })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('button', { name: 'Ver en 3D' })).toBeVisible();
});
test('switching view keeps material, yaw and immutable placements; each piece is identified', () => {
  const props = data(); const before = JSON.stringify(props);
  render(<PlacementCanvas {...props} />);
  fireEvent.change(screen.getByLabelText('Vidrio del resultado'), { target: { value: '2:5.5' } });
  const slider = open3D();
  expect(screen.getByLabelText('Plancha o retazo')).toHaveValue('PLANCHA:16:1');
  expect(screen.getByRole('list', { name: 'Piezas en la vista 3D' })).toHaveTextContent('Pieza #103 · unidad 1');
  fireEvent.keyDown(slider, { key: 'ArrowRight' });
  fireEvent.click(screen.getByRole('button', { name: 'Ver en 2D' }));
  expect(screen.getByRole('img', { name: 'Colocaciones en plancha #16' }).querySelector('circle')).toHaveAttribute('r', '240');
  expect(open3D()).toHaveAttribute('aria-valuenow', String(DEFAULT_YAW + 5));
  expect(JSON.stringify(props)).toBe(before);
});
test('keyboard clamps yaw and reset restores only the visual camera', () => {
  render(<PlacementCanvas {...data()} />); const slider = open3D(); slider.focus();
  expect(slider).toHaveFocus();
  fireEvent.keyDown(slider, { key: 'End' }); fireEvent.keyDown(slider, { key: 'ArrowRight' });
  expect(slider).toHaveAttribute('aria-valuenow', '90');
  fireEvent.keyDown(slider, { key: 'Home' }); fireEvent.keyDown(slider, { key: 'ArrowLeft' });
  expect(slider).toHaveAttribute('aria-valuenow', '-90');
  fireEvent.click(screen.getByRole('button', { name: 'Restablecer vista' }));
  expect(slider).toHaveAttribute('aria-valuenow', String(DEFAULT_YAW));
  expect(document.querySelectorAll('[data-piece-3d]')).toHaveLength(3);
});
test('horizontal pointer drag clamps, ignores vertical motion and stops on cancel', () => {
  render(<PlacementCanvas {...data()} />); const slider = open3D();
  fireEvent.pointerDown(slider, { pointerId: 1, clientX: 100, clientY: 100, button: 0 });
  fireEvent.pointerMove(slider, { pointerId: 1, clientX: 100, clientY: 500 });
  expect(slider).toHaveAttribute('aria-valuenow', String(DEFAULT_YAW));
  fireEvent.pointerMove(slider, { pointerId: 1, clientX: 3000 }); expect(slider).toHaveAttribute('aria-valuenow', '90');
  fireEvent.pointerMove(slider, { pointerId: 1, clientX: -3000 }); expect(slider).toHaveAttribute('aria-valuenow', '-90');
  fireEvent.pointerCancel(slider, { pointerId: 1 });
  fireEvent.pointerMove(slider, { pointerId: 1, clientX: 400 }); expect(slider).toHaveAttribute('aria-valuenow', '-90');
});
test('legend colors are stable across progressive updates and expose received rotations', () => {
  const props = data(); const view = render(<PlacementCanvas {...props} placements={props.placements.slice(0, 1)} />); open3D();
  const firstColor = document.querySelector('.placement-3d-swatch').style.backgroundColor;
  view.rerender(<PlacementCanvas {...props} />);
  const legend = screen.getByRole('list', { name: 'Piezas en la vista 3D' });
  expect(within(legend).getAllByRole('listitem')).toHaveLength(3);
  expect(legend).toHaveTextContent('Pedido #21 · rotación aplicada: 90°');
  expect(legend).toHaveTextContent('Pedido #22 · rotación aplicada: 30°');
  expect(document.querySelector('.placement-3d-swatch').style.backgroundColor).toBe(firstColor);
  expect(screen.getByText(/no retazos reutilizables calculados/)).toBeVisible();
});
