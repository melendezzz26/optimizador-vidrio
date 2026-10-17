import { test } from 'node:test';
import assert from 'node:assert/strict';
import { detectMaterialGroups, placementMatchesGroup } from '../../src/features/optimization/materialGroups.js';

const piece = (id, material, thickness, cantidad = 1) => ({ id_pieza: id, id_tipo_vidrio: material, espesor_mm: thickness, cantidad });
const orders = [{ id_pedido: 21, piezas: [piece(1, 1, 6, 2), piece(2, 2, 6), piece(3, 1, 5.5)] },
  { id_pedido: 22, piezas: [piece(4, 1, '6.0')] }];
const resolve = id => ({ name: id, containers: [{ material_source: 'PLANCHA', stock_unit_index: 1, material_id: id, id_tipo_vidrio: Number(id.split(':')[0]), espesor_mm: Number(id.split(':')[1]) }] });
const snapshot = () => ({ orders: structuredClone(orders), groups: detectMaterialGroups(orders, resolve).groups });
const placement = { id_pedido: 21, id_pieza: 1, unit_index: 1, group_id: '1:6', material_source: 'PLANCHA', stock_unit_index: 1, material_id: '1:6', x_mm: 0, y_mm: 0, rotation_deg: 0 };

test('grouping separates different material and thickness, merges numeric thickness, preserves input and units', () => {
  const before = JSON.stringify(orders);
  const { groups, unresolved } = detectMaterialGroups(orders, resolve);
  assert.deepEqual(groups.map(g => g.id), ['1:6', '2:6', '1:5.5']);
  assert.equal(groups[0].units.length, 3);
  assert.deepEqual(groups[0].orders, [21, 22]);
  assert.deepEqual(unresolved, []);
  assert.equal(JSON.stringify(orders), before);
});
test('missing details and invalid quantities are unresolved, never silently compatible', () => {
  const result = detectMaterialGroups([{ id_pedido: 1 }, { id_pedido: 2, piezas: [piece(1, null, 6), piece(2, 1, 0), piece(3, 1, 6, -1)] }]);
  assert.deepEqual(result.unresolved, [1, 2]); assert.equal(result.groups.length, 0);
  assert.equal(detectMaterialGroups(orders).groups[0].containers.length, 0);
});
test('a piece cannot be placed in a different compatible-looking group or absent unit', () => {
  assert.equal(placementMatchesGroup(snapshot(), placement), true);
  for (const patch of [{ group_id: '2:6', material_id: '2:6' }, { group_id: '1:5.5', material_id: '1:5.5' }, { id_pedido: 22 }, { unit_index: 5 }]) {
    assert.equal(placementMatchesGroup(snapshot(), { ...placement, ...patch }), false);
  }
});
test('mismatched stock and reuse of a container by incompatible groups are rejected', () => {
  for (const field of ['id_tipo_vidrio', 'espesor_mm']) {
    const data = snapshot(); data.groups[0].containers[0][field] = 999;
    assert.equal(placementMatchesGroup(data, placement), false);
  }
  const data = snapshot(); data.groups[1].containers.push(data.groups[0].containers[0]);
  assert.equal(placementMatchesGroup(data, placement), false);
});
