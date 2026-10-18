import { test } from 'node:test';
import assert from 'node:assert/strict';
import { clampYaw, DEFAULT_YAW, placedOutline, createPlacementScene, projectPoint, extrudedSides, sceneViewBox } from '../../src/features/optimization/placementScene.js';

const rectangle = { type: 'RECTANGULO', width_mm: 600, height_mm: 400 };
const scene = { width: 3300, height: 2140 };
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-8, `${a} != ${b}`);

test('3D translates oriented geometry once and never reapplies received rotation', () => {
  const points = placedOutline(rectangle, { x_mm: 1400, y_mm: 80, rotation_deg: 90 });
  [[1400, 80], [2000, 80], [2000, 480], [1400, 480]].forEach((p, i) => p.forEach((value, axis) => close(points[i][axis], value)));
});
test('arbitrary piece rotation preserves lengths and does not mutate negative polygon coordinates', () => {
  const geometry = Object.freeze({ type: 'POLIGONO_CONVEXO', vertices_mm: Object.freeze([Object.freeze([-10, -20]), Object.freeze([90, -20]), Object.freeze([-10, 80])]) });
  const before = JSON.stringify(geometry);
  for (const rotation_deg of [-37, 30, 270, 450]) {
    const points = placedOutline(geometry, { x_mm: 200, y_mm: 300, rotation_deg });
    close(points[0][0], 200); close(points[0][1], 300);
    close(Math.hypot(points[1][0] - points[0][0], points[1][1] - points[0][1]), 100);
  }
  assert.equal(JSON.stringify(geometry), before);
});
test('circle display contour is centered at its normalized radius, with 96 bounded samples', () => {
  const points = placedOutline({ type: 'CIRCUNFERENCIA', radius_mm: 240 }, { x_mm: 60, y_mm: 60, rotation_deg: 0 });
  assert.equal(points.length, 96);
  for (const [x, y] of points) close(Math.hypot(x - 300, y - 300), 240);
});
test('yaw supports a complete 360 degree orbit and projection remains finite at limits', () => {
  assert.equal(clampYaw(-2000), -180); assert.equal(clampYaw(2000), 180); assert.equal(clampYaw(NaN), DEFAULT_YAW);
  for (const yaw of [-900, -90, -24, 0, 90, 900]) {
    const point = projectPoint([3300, 2140], 25, scene, yaw);
    assert.ok(Object.values(point).every(Number.isFinite));
    assert.deepEqual(point, projectPoint([3300, 2140], 25, scene, clampYaw(yaw)));
  }
});
test('projection preserves physical proportions under common scaling of all dimensions', () => {
  for (const camera of [{ elevation: 5 }, { elevation: 48 }, { elevation: 90, panX: 120, panY: -40 }]) {
    const a = projectPoint([800, 600], 18, scene, 30, camera);
    const b = projectPoint([1600, 1200], 18, { width: 6600, height: 4280 }, 30, camera);
    close(a.x, b.x); close(a.y, b.y); close(a.depth, b.depth);
  }
  const top = { elevation: 90 };
  const center = projectPoint([500, 500], 0, { width: 1000, height: 1000 }, 0, top);
  const x = projectPoint([600, 500], 0, { width: 1000, height: 1000 }, 0, top);
  const y = projectPoint([500, 600], 0, { width: 1000, height: 1000 }, 0, top);
  close(x.x - center.x, 100); close(x.y, center.y);
  close(y.y - center.y, 100); close(y.x, center.x);
});
test('scene filters material source plus ID, keeps colors stable and leaves snapshot untouched', () => {
  const container = { material_source: 'PLANCHA', stock_unit_index: 1, material_id: 1, material_width_mm: 3300, material_height_mm: 2140, geometry: { type: 'RECTANGULO', width_mm: 3300, height_mm: 2140 } };
  const unit = { id_pedido: 21, id_pieza: 101, unit_index: 1 };
  const snapshot = { groups: [{ units: [unit] }], orders: [{ id_pedido: 21, piezas: [{ id_pieza: 101, geometria: rectangle }] }] };
  const placement = { ...unit, material_source: 'PLANCHA', stock_unit_index: 1, material_id: 1, geometria: rectangle, x_mm: 100, y_mm: 100, rotation_deg: 30 };
  const original = JSON.stringify({ snapshot, container, placement });
  const first = createPlacementScene(snapshot, container, [placement]);
  const second = createPlacementScene(snapshot, container, [{ ...placement, material_source: 'RETAZO', stock_unit_index: 1 }, placement]);
  assert.equal(first.pieces.length, 1); assert.deepEqual(first.pieces, second.pieces);
  assert.equal(first.gridStep, 500);
  assert.equal(JSON.stringify({ snapshot, container, placement }), original);
});
test('extrusion includes closed side faces ordered by camera depth, not optimization order', () => {
  const sides = extrudedSides(placedOutline(rectangle), 0, 18, scene, DEFAULT_YAW);
  assert.equal(sides.length, 4);
  assert.ok(sides.every(side => side.path.endsWith(' Z') && !side.path.includes('NaN')));
  assert.deepEqual(sides.map(s => s.depth), sides.map(s => s.depth).sort((a, b) => a - b));
});
test('missing geometry or invalid dimensions do not produce fabricated scene data', () => {
  assert.deepEqual(placedOutline(null), []);
  assert.deepEqual(placedOutline(rectangle, { x_mm: 0, y_mm: 0, rotation_deg: Infinity }), []);
  assert.equal(createPlacementScene({}, { material_width_mm: 0, material_height_mm: 100 }, []), null);
});

test('stable frame contains square and narrow inventory at every permitted yaw', () => {
  for (const dimensions of [{ width: 1000, height: 1000 }, { width: 100, height: 5000 }, { width: 5000, height: 100 }]) {
    const input = { ...dimensions, gridStep: Math.max(dimensions.width, dimensions.height) / 10 };
    const [left, top, width, height] = sceneViewBox(input);
    for (let yaw = -180; yaw <= 180; yaw++) for (const elevation of [5, 48, 90]) for (const point of [[0, 0], [input.width, 0], [input.width, input.height], [0, input.height]]) {
      const projected = projectPoint(point, 18, input, yaw, { elevation });
      assert.ok(projected.x >= left && projected.x <= left + width);
      assert.ok(projected.y >= top && projected.y <= top + height);
    }
  }
});
