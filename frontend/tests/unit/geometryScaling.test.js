import test from 'node:test';
import assert from 'node:assert/strict';
import { fitVerticesToPreview, getBoundingBox } from '../../src/features/orders/geometryScaling.js';
import { buildDimensionalGeometry, createSegments, getDrawingSegmentLength, scaleSketchToLengths, isPositiveLength, resolveSegmentLengths } from '../../src/features/orders/segmentGeometry.js';
import { hasFiniteVertices, edgeLengths, interiorAngles, scaleVertices } from '../../src/features/orders/polygonMeasurements.js';
import { validateConvexPolygon } from '../../src/features/orders/convexityValidation.js';

const rectangle = [[0,0],[400,0],[400,200],[0,200]];
const points = rectangle.map(([x,y]) => ({x,y}));
const near = (a,b) => assert.ok(Math.abs(a-b) < 1e-7, `${a} != ${b}`);

test('equal lengths cannot determine shape: square and rhombus retain distinct vertices and angles', () => {
  const square = [[0,0],[10,0],[10,10],[0,10]];
  const rhombus = [[0,0],[10,0],[16,8],[6,8]];
  edgeLengths(square).forEach((length,i) => near(length, edgeLengths(rhombus)[i]));
  assert.notDeepEqual(interiorAngles(square), interiorAngles(rhombus));
  assert.notDeepEqual(scaleVertices(square,2), scaleVertices(rhombus,2));
  const model = vertices => buildDimensionalGeometry(vertices.map(([x,y]) => ({x,y})),
    createSegments(vertices).map((s,i) => ({...s,lengthMm:edgeLengths(vertices)[i]})));
  assert.deepEqual(model(square).vertices_mm, square);
  assert.deepEqual(model(rhombus).vertices_mm, rhombus);
});

test('scale preserves shape, vertex order and angle sum in either winding', () => {
  near(getDrawingSegmentLength({ x: -8, y: 12 }, { x: -5, y: 16 }), 5);
  near(getDrawingSegmentLength({ x: 0, y: 0 }, { x: 0, y: 0 }), 0);
  for (const polygon of [rectangle, [...rectangle].reverse(), [[0,0],[300,0],[300,400]]]) {
    const scaled = scaleVertices(polygon,2);
    edgeLengths(scaled).forEach((length,i) => near(length, edgeLengths(polygon)[i]*2));
    interiorAngles(scaled).forEach((angle,i) => near(angle, interiorAngles(polygon)[i]));
    near(interiorAngles(scaled).reduce((sum,a)=>sum+a,0), (polygon.length-2)*180);
    const segments = createSegments(polygon).map((segment, i) => ({ ...segment, lengthMm: edgeLengths(scaled)[i] }));
    assert.deepEqual(buildDimensionalGeometry(polygon.map(([x, y]) => ({ x, y })), segments).vertices_mm, scaled);
  }
});

test('concave angles are derived with reflex vertex; validation remains separate', () => {
  const polygon = [[0,0],[4,0],[2,1],[4,4],[0,4]];
  assert.ok(interiorAngles(polygon)[2] > 180);
  near(interiorAngles(polygon).reduce((sum,a)=>sum+a,0),540);
  const scaled = scaleVertices(polygon, 2);
  const segments = createSegments(polygon).map((segment, i) => ({ ...segment, lengthMm: edgeLengths(scaled)[i] }));
  const result = buildDimensionalGeometry(polygon.map(([x, y]) => ({ x, y })), segments);
  assert.deepEqual(result.vertices_mm, scaled);
  assert.equal(validateConvexPolygon(result.vertices_mm).isValid, false);
});

for (const invalid of [[], [[0,0],[1,0]], [[0,0],[1,0],[NaN,1]], [[0,0],[1,0],[Infinity,1]], [[0,0],[1,0],['2',1]], [[0,0],[1,0],[true,1]]]) {
  test(`invalid finite vertices ${JSON.stringify(invalid)}`, () => {
    assert.equal(hasFiniteVertices(invalid),false);
    assert.throws(()=>edgeLengths(invalid));
    assert.throws(()=>interiorAngles(invalid));
  });
}
for (const degenerate of [[[0,0],[0,0],[1,1]], [[0,0],[1,0],[2,0]], [[0,0],[1,0],[2,0],[2,1],[0,1]]]) {
  test(`degenerate geometry ${JSON.stringify(degenerate)} is rejected`,()=>assert.throws(()=>interiorAngles(degenerate),RangeError));
}
for (const invalid of [0,-1,NaN,Infinity,'',null,true]) {
  test(`invalid length ${String(invalid)} cannot yield a polygon`,()=>{
    assert.equal(isPositiveLength(invalid),false);
    assert.equal(scaleSketchToLengths(points,[invalid,200,400,200]).error,'length');
  });
}

test('inconsistent independent lengths are rejected instead of changing sketch angles',()=>{
  assert.equal(scaleSketchToLengths(points,[800,200,400,200]).error,'shape-mismatch');
  assert.deepEqual(scaleSketchToLengths(points,[800,400,800,400]).vertices_mm,scaleVertices(rectangle,2));
  const segments = createSegments(points).map((segment, i) => ({ ...segment, lengthMm: [800, 200, 400, ''][i] }));
  const result = buildDimensionalGeometry(points, segments);
  assert.equal(result.status, 'error');
  assert.equal(result.error, 'shape-mismatch');
  assert.equal(result.vertices_mm, null);
});

test('partial measurements remain provisional; complete consistent measurements scale vertices',()=>{
  const segments=createSegments(points);
  assert.equal(buildDimensionalGeometry(points,segments).status,'unscaled');
  segments[0].lengthMm=800;
  const provisional = buildDimensionalGeometry(points,segments);
  assert.equal(provisional.status,'provisional');
  assert.equal(provisional.provisionalScale, 2);
  assert.deepEqual(provisional.measured, [true, false, false, false]);
  assert.deepEqual(provisional.lengths, [800, 400, 800, 400]);
  assert.equal(segments[1].lengthMm, '');
  segments.forEach((s,i)=>s.lengthMm=[800,400,800,400][i]);
  const result=buildDimensionalGeometry(points,segments);
  assert.equal(result.status,'complete');
  assert.deepEqual(result.vertices_mm,[[0,0],[800,0],[800,400],[0,400]]);
});

test('frozen coordinates remain unchanged through scaling and responsive previews',()=>{
  const frozen=Object.freeze(rectangle.map(v=>Object.freeze([...v])));
  const snapshot=JSON.stringify(frozen);
  const scaled=scaleVertices(frozen,2);
  const previewPoints = Object.freeze(scaled.map(([x, y]) => Object.freeze({ x, y })));
  for(const [width,height] of [[214,280],[500,300],[1200,300]]) {
    const preview=fitVerticesToPreview(previewPoints,width,height,38);
    near(preview.bounds.width/preview.bounds.height,2);
    near(preview.bounds.x+preview.bounds.width/2,width/2);
    near(preview.bounds.y+preview.bounds.height/2,height/2);
    preview.points.forEach(({x,y})=>assert.ok(x>=37.999&&y>=37.999&&x<=width-37.999&&y<=height-37.999));
  }
  assert.equal(JSON.stringify(frozen),snapshot);
  assert.deepEqual(getBoundingBox(points),{minX:0,maxX:400,minY:0,maxY:200,width:400,height:200});
});

test('invalid scale, numeric overflow and missing edges never emit non-finite coordinates',()=>{
  for(const factor of [0,-1,NaN,Infinity]) assert.throws(()=>scaleVertices(rectangle,factor));
  assert.throws(()=>scaleVertices([[0,0],[1e308,0],[0,1]],2));
  assert.equal(scaleSketchToLengths([],[]).error,'drawing');
  for(const invalid of [[],[{x:0,y:NaN}],[{x:0,y:0}]]) assert.equal(fitVerticesToPreview(invalid),null);
});

const asPoints = vertices => vertices.map(([x, y]) => ({ x, y }));
const measured = vertices => createSegments(vertices).map((segment, i) => ({ ...segment, lengthMm: edgeLengths(vertices)[i] }));

test('preview rejects invalid and non-finite viewport dimensions on either axis', () => {
  for (const [width, height] of [[0, 300], [-1, 300], [300, 0], [300, -1], [NaN, 300], [300, NaN], [Infinity, 300], [300, Infinity]]) {
    assert.equal(fitVerticesToPreview(points, width, height), null);
  }
});

test('preview rejects negative/non-finite padding and a viewport exhausted by padding', () => {
  for (const padding of [-1, NaN, Infinity, 150, 200]) {
    assert.equal(fitVerticesToPreview(points, 300, 300, padding), null);
  }
});

test('one-axis preview extents remain finite and centered without modifying canonical input', () => {
  for (const vertices_mm of [[[-10, -10], [-10, 10]], [[-10, -10], [10, -10]]]) {
    const original = structuredClone(vertices_mm);
    const preview = fitVerticesToPreview(asPoints(vertices_mm), 300, 300, 40);
    assert.ok(preview);
    preview.points.forEach(point => assert.ok(Number.isFinite(point.x) && Number.isFinite(point.y)));
    near(preview.bounds.x + preview.bounds.width / 2, 150);
    near(preview.bounds.y + preview.bounds.height / 2, 150);
    assert.equal(preview.bounds.width === 0, vertices_mm[0][0] === vertices_mm[1][0]);
    assert.equal(preview.bounds.height === 0, vertices_mm[0][1] === vertices_mm[1][1]);
    assert.deepEqual(vertices_mm, original);
    // A line may be displayed, but cannot become a valid polygon for saving.
    assert.throws(() => interiorAngles(vertices_mm));
  }
});

for (const [width, height] of [[200, 5000], [5000, 200]]) {
  test(`canonical ${width}:${height} polygon preserves angles in tall/wide responsive previews`, () => {
    const vertices_mm = [[-20, 30], [width - 20, 30], [width - 20, height + 30], [-20, height + 30]];
    const snapshot = structuredClone(vertices_mm);
    for (const [viewportWidth, viewportHeight] of [[214, 280], [500, 300], [1200, 300]]) {
      const preview = fitVerticesToPreview(asPoints(vertices_mm), viewportWidth, viewportHeight, 38);
      assert.ok(preview);
      near(preview.bounds.width / preview.bounds.height, width / height);
      near(preview.bounds.x + preview.bounds.width / 2, viewportWidth / 2);
      near(preview.bounds.y + preview.bounds.height / 2, viewportHeight / 2);
      const displayed = preview.points.map(({ x, y }) => [x, y]);
      interiorAngles(displayed).forEach((angle, i) => near(angle, interiorAngles(vertices_mm)[i]));
      preview.points.forEach(({ x, y }) => assert.ok(x >= 37.999 && y >= 37.999 && x <= viewportWidth - 37.999 && y <= viewportHeight - 37.999));
    }
    assert.deepEqual(vertices_mm, snapshot);
  });
}

test('positive physical lengths below 0.01 scale vertices without changing shape', () => {
  for (const length of [0.005, 0.001, 0.000001]) {
    assert.equal(isPositiveLength(String(length)), true);
    const vertices_mm = scaleVertices(rectangle, length / 400);
    const result = buildDimensionalGeometry(points, measured(vertices_mm));
    assert.equal(result.status, 'complete');
    assert.deepEqual(result.vertices_mm, vertices_mm);
    edgeLengths(result.vertices_mm).forEach((value, i) => near(value, edgeLengths(rectangle)[i] * length / 400));
    interiorAngles(result.vertices_mm).forEach(angle => near(angle, 90));
  }
});

test('remaining non-finite and malformed length inputs are rejected rather than estimated', () => {
  for (const value of [-Infinity, undefined, 'abc', ' ']) {
    assert.equal(isPositiveLength(value), false);
    assert.equal(scaleSketchToLengths(points, [value, 200, 400, 200]).error, 'length');
  }
});

test('segment IDs and indices include the closing edge and reject corrupted ordering', () => {
  const segments = createSegments(points);
  assert.deepEqual(segments.map(({ id, index }) => [id, index]), [['S1', 0], ['S2', 1], ['S3', 2], ['S4', 3]]);
  for (const invalid of [segments.slice(1), [...segments].reverse(), segments.map((segment, i) => i ? segment : { ...segment, id: 'S9' })]) {
    assert.equal(resolveSegmentLengths(points, invalid).error, 'segments');
  }
});

test('native badInput is an error even when its displayed value is empty or previously valid', () => {
  for (const lengthMm of ['', '400']) {
    const segments = measured(rectangle);
    segments[0] = { ...segments[0], lengthMm, badInput: true };
    const result = buildDimensionalGeometry(points, segments);
    assert.equal(result.error, 'length');
    assert.equal(result.vertices_mm, null);
  }
});

test('malformed/repeated/non-finite sketch vertices cannot yield physical geometry', () => {
  for (const invalid of [points.slice(0, 2), [...points, points[0]], [{ x: NaN, y: 0 }, ...points], [{ x: Infinity, y: 0 }, ...points]]) {
    assert.equal(scaleSketchToLengths(invalid, [400, 200, 400, 200]).error, 'drawing');
  }
  assert.equal(scaleSketchToLengths(points, [400, 200, 400]).error, 'length');
});

test('overflow of provisional scale fails before emitting non-finite vertices', () => {
  const sketch = [{ x: 0, y: 0 }, { x: 1e-300, y: 0 }, { x: 1e-300, y: 1e-300 }];
  const segments = createSegments(sketch);
  segments[0].lengthMm = 1e300;
  const result = buildDimensionalGeometry(sketch, segments);
  assert.equal(result.error, 'numeric-range');
  assert.equal(result.vertices_mm, null);
});

test('rotated/translated canonical sketch retains orientation and ordered vertices after scaling', () => {
  const rotated = rectangle.map(([x, y]) => [42 - y, -71 + x]);
  const result = buildDimensionalGeometry(asPoints(rotated), measured(scaleVertices(rotated, 2)));
  assert.deepEqual(result.vertices_mm, [[0, 0], [0, 800], [-400, 800], [-400, 0]]);
  interiorAngles(result.vertices_mm).forEach((angle, i) => near(angle, interiorAngles(rotated)[i]));
});

test('six or more vertices retain their canonical shape rather than solving independent side lengths', () => {
  for (const count of [6, 8, 12]) {
    const vertices_mm = Array.from({ length: count }, (_, i) => [100 * Math.cos(i * 2 * Math.PI / count), 100 * Math.sin(i * 2 * Math.PI / count)]);
    const result = buildDimensionalGeometry(asPoints(vertices_mm), measured(scaleVertices(vertices_mm, 2)));
    assert.equal(result.status, 'complete');
    result.vertices_mm.forEach((point, i) => point.forEach((value, axis) => near(value, scaleVertices(vertices_mm, 2)[i][axis])));
    near(interiorAngles(result.vertices_mm).reduce((sum, angle) => sum + angle, 0), (count - 2) * 180);
  }
});

test('dimensional pipeline leaves frozen sketch and segment inputs unchanged', () => {
  const sketch = Object.freeze(points.map(point => Object.freeze({ ...point })));
  const segments = Object.freeze(measured(scaleVertices(rectangle, 2)).map(Object.freeze));
  const snapshot = JSON.stringify({ sketch, segments });
  assert.equal(buildDimensionalGeometry(sketch, segments).status, 'complete');
  assert.equal(JSON.stringify({ sketch, segments }), snapshot);
});

test('clearing all measurements removes physical scale and previously derived vertices', () => {
  const segments = measured(rectangle);
  assert.equal(buildDimensionalGeometry(points, segments).status, 'complete');
  segments[0].lengthMm = '';
  assert.equal(buildDimensionalGeometry(points, segments).status, 'provisional');
  segments.forEach(segment => { segment.lengthMm = ''; });
  const result = buildDimensionalGeometry(points, segments);
  assert.equal(result.status, 'unscaled');
  assert.equal(result.vertices_mm, null);
});

test('odd and even subsets of canonical measurements resolve the same uniform scale', () => {
  for (const measuredIndices of [[0, 1, 2], [0, 1]]) {
    const segments = measured(scaleVertices(rectangle, 2)).map((segment, i) => ({
      ...segment, lengthMm: measuredIndices.includes(i) ? segment.lengthMm : '',
    }));
    const result = resolveSegmentLengths(points, segments);
    assert.equal(result.provisionalScale, 2);
    assert.deepEqual(result.lengths, [800, 400, 800, 400]);
  }
});

test('thin non-degenerate canonical triangle survives scaling while a collinear polygon stays invalid', () => {
  const vertices_mm = [[0, 0], [1000, 0], [2000, 0.1]];
  const scaled = scaleVertices(vertices_mm, 0.5);
  const result = buildDimensionalGeometry(asPoints(vertices_mm), measured(scaled));
  assert.equal(result.status, 'complete');
  assert.deepEqual(result.vertices_mm, scaled);
  assert.equal(validateConvexPolygon(result.vertices_mm).isValid, true);
  interiorAngles(scaled).forEach((angle, i) => near(angle, interiorAngles(vertices_mm)[i]));
  const collinear = [[0, 0], [1000, 0], [2000, 0]];
  assert.equal(validateConvexPolygon(scaleVertices(collinear, 0.5)).isValid, false);
});
