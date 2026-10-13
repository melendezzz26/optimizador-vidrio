import test from 'node:test';
import assert from 'node:assert/strict';
import { buildConstrainedGeometry } from '../../src/features/orders/constrainedGeometry.js';
import { edgeLengths, interiorAngles, scaleVertices } from '../../src/features/orders/polygonMeasurements.js';
import { validateConvexPolygon } from '../../src/features/orders/convexityValidation.js';

const construct = (lengths, config) => buildConstrainedGeometry(lengths.map(lengthMm => ({ lengthMm })), config);
const near = (a, b, tolerance = 1e-7) => assert.ok(Math.abs(a - b) < tolerance, `${a} != ${b}`);
function assertShape(result, lengths) {
  assert.equal(result.status, 'complete', result.error);
  assert.equal(validateConvexPolygon(result.vertices_mm).isValid, true);
  edgeLengths(result.vertices_mm).forEach((length, i) => near(length, lengths[i]));
  near(interiorAngles(result.vertices_mm).reduce((a, b) => a + b), (lengths.length - 2) * 180);
}

test('triangle 50/70/65 closes all three editable sides and derives angles by cosine law', () => {
  const result = construct([50, 70, 65]);
  assertShape(result, [50, 70, 65]);
  near(interiorAngles(result.vertices_mm)[1], Math.acos((50 ** 2 + 70 ** 2 - 65 ** 2) / (2 * 50 * 70)) * 180 / Math.PI);
});
for (const lengths of [[10, 10, 30], [10, 10, 20], [1, 1, 1, 4]]) {
  test(`impossible or degenerate sides ${lengths} cannot produce vertices`, () => {
    assert.deepEqual(construct(lengths), { status: 'error', error: 'inequality', vertices_mm: null });
  });
}
test('fixed quadrilateral angle changes disposition but never any of its four sides', () => {
  const sides = [120, 73, 91, 108];
  const a = construct(sides, { mode: 'angle', angle: 85 });
  const b = construct(sides, { mode: 'angle', angle: 110 });
  assertShape(a, sides); assertShape(b, sides);
  near(interiorAngles(a.vertices_mm)[1], 85);
  near(interiorAngles(b.vertices_mm)[1], 110);
  assert.notDeepEqual(a.vertices_mm, b.vertices_mm);
});
test('incompatible fixed angle fails as configuration, not as impossible lengths', () => {
  const sides = [120, 73, 91, 108];
  assert.equal(construct(sides, { mode: 'angle', angle: 1 }).error, 'angle-configuration');
  assertShape(construct(sides), sides);
});
test('irregular pentagon uses an explicit cyclic constraint and satisfies every closing edge', () => {
  assertShape(construct([80, 115, 63, 92, 71]), [80, 115, 63, 92, 71]);
});
test('cyclic construction handles the longest chord major-arc case', () => {
  for (const lengths of [[8, 2, 3, 4], [2, 3, 8, 4], [4, 3, 2, 8]]) assertShape(construct(lengths), lengths);
});
test('small positive dimensions and large scales preserve corresponding angles', () => {
  const original = construct([50, 70, 65]);
  for (const factor of [1e-6, 1e4]) {
    const result = construct([50, 70, 65].map(x => x * factor));
    assertShape(result, [50, 70, 65].map(x => x * factor));
    interiorAngles(result.vertices_mm).forEach((angle, i) => near(angle, interiorAngles(original.vertices_mm)[i]));
    result.vertices_mm.forEach((point, i) => point.forEach((value, axis) => near(value, scaleVertices(original.vertices_mm, factor)[i][axis])));
  }
});
test('non-finite, non-positive, boolean and incomplete dimensions never become saved geometry', () => {
  for (const invalid of [0, -1, NaN, Infinity, -Infinity, true, null, undefined, 'bad']) {
    assert.equal(construct([50, 70, invalid]).error, 'length');
  }
  for (const value of ['', '50']) {
    const result = buildConstrainedGeometry([{ lengthMm: value, badInput: true }, { lengthMm: 70 }, { lengthMm: 65 }]);
    assert.equal(result.error, 'length');
  }
  assert.equal(construct(['', '', '']).status, 'unscaled');
  assert.equal(construct([50, '', '']).vertices_mm, null);
});
test('invalid angles and unsupported configurations are explicit errors', () => {
  for (const angle of ['', 0, 180, -1, Infinity, NaN, true]) assert.equal(construct([120, 73, 91, 108], { mode: 'angle', angle }).error, 'angle');
  assert.equal(construct([50, 70, 65], { mode: 'unknown' }).error, 'configuration');
});
test('construction does not mutate deeply frozen measurements', () => {
  const input = Object.freeze([80, 115, 63, 92, 71].map(lengthMm => Object.freeze({ lengthMm })));
  const before = JSON.stringify(input);
  assertShape(buildConstrainedGeometry(input), [80, 115, 63, 92, 71]);
  assert.equal(JSON.stringify(input), before);
});

for (const sides of [[50,70,65], [120,73,91,108], [80,115,63,92,71], [80,115,63,92,71,98]]) {
  test(`${sides.length} lados: límite n-3, ángulos fijados, lados y suma angular verificados`, () => {
    const base = construct(sides);
    const angles = interiorAngles(base.vertices_mm);
    const constraints = Array.from({ length: sides.length - 3 }, (_, i) => ({ vertex: i + 1, angle: angles[i + 1] }));
    if (constraints.length) constraints[0].angle -= 5;
    const result = construct(sides, { mode: 'angles', constraints });
    assertShape(result, sides);
    constraints.forEach(({vertex, angle}) => near(interiorAngles(result.vertices_mm)[vertex], angle, 1e-5));
    assert.equal(construct(sides, { mode: 'angles', constraints: [...constraints, {vertex:0,angle:90}] }).error, 'constraint-limit');
    if (constraints.length) assert.notDeepEqual(result.vertices_mm, base.vertices_mm);
  });
}

test('cuadrilátero 75→100 conserva cuatro lados y satisface exactamente el ángulo solicitado', () => {
  for (const angle of [75,100]) {
    const r = construct([120,73,91,108], { mode:'angles', constraints:[{vertex:1,angle}] });
    assertShape(r,[120,73,91,108]); near(interiorAngles(r.vertices_mm)[1],angle,1e-5);
  }
});

test('vértices no consecutivos y V1 también admiten restricciones; liberar no altera lados', () => {
  const sides=[80,115,63,92,71,98]; const original=construct(sides);
  const angles=interiorAngles(original.vertices_mm);
  const constraints=[0,2,4].map(vertex=>({vertex,angle:angles[vertex]-1}));
  for(const selected of [constraints,constraints.slice(1),[]]) {
    const r=construct(sides,{mode:'angles',constraints:selected}); assertShape(r,sides);
    selected.forEach(({vertex,angle})=>near(interiorAngles(r.vertices_mm)[vertex],angle,1e-5));
  }
});

test('ángulos inválidos, repetidos o incompatibles no producen geometría guardable', () => {
  for(const angle of [0,-1,180,181,NaN,Infinity,'',true]) {
    assert.equal(construct([80,115,63,92,71],{mode:'angles',constraints:[{vertex:1,angle}]}).error,'angle');
  }
  assert.equal(construct([80,115,63,92,71],{mode:'angles',constraints:[{vertex:1,angle:90},{vertex:1,angle:100}]}).error,'constraint-limit');
  assert.equal(construct([120,73,91,108],{mode:'angles',constraints:[{vertex:1,angle:1}]}).status,'error');
  assert.equal(construct([1,1,2-1e-14]).status,'error');
});

test('boceto es initial guess, no medida: distintas formas equivalentes, orientación y lados exactos', () => {
  const sides=[100,100,100,100];
  const drawings=[[[0,0],[1,0],[1,1],[0,1]],[[0,0],[1,0],[1.6,0.8],[0.6,0.8]]];
  const results=drawings.map(drawing=>construct(sides,{mode:'guided',drawing}));
  results.forEach(r=>assertShape(r,sides));
  assert.notDeepEqual(results[0].vertices_mm,results[1].vertices_mm);
  const mirrored=construct(sides,{mode:'guided',drawing:drawings[1].map(([x,y])=>[x,-y])});
  assertShape(mirrored,sides); assert.ok(mirrored.vertices_mm[2][1]<0);
  const fixed=construct([120,73,91,108],{mode:'angles',drawing:drawings[0],constraints:[{vertex:1,angle:75}]});
  assertShape(fixed,[120,73,91,108]); near(interiorAngles(fixed.vertices_mm)[1],75,1e-5);
});

test('el resultado siempre pasa política convexa y simplicidad, aun con guesses cóncavos/cruzados', () => {
  for(const drawing of [[[0,0],[2,2],[0,2],[2,0]],[[0,0],[2,0],[0.5,0.5],[0,2]]]) {
    const r=construct([120,73,91,108],{mode:'angles',drawing,constraints:[{vertex:1,angle:100}]});
    assertShape(r,[120,73,91,108]); assert.equal(validateConvexPolygon(r.vertices_mm).isSimple,true);
  }
});
