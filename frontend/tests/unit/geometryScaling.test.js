import test from 'node:test';
import assert from 'node:assert/strict';
import { fitVerticesToPreview, getBoundingBox } from '../../src/features/orders/geometryScaling.js';
import { buildDimensionalGeometry, createSegments, scaleSketchToLengths, isPositiveLength } from '../../src/features/orders/segmentGeometry.js';
import { hasFiniteVertices, edgeLengths, interiorAngles, scaleVertices } from '../../src/features/orders/polygonMeasurements.js';

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
  for (const polygon of [rectangle, [...rectangle].reverse(), [[0,0],[300,0],[300,400]]]) {
    const scaled = scaleVertices(polygon,2);
    edgeLengths(scaled).forEach((length,i) => near(length, edgeLengths(polygon)[i]*2));
    interiorAngles(scaled).forEach((angle,i) => near(angle, interiorAngles(polygon)[i]));
    near(interiorAngles(scaled).reduce((sum,a)=>sum+a,0), (polygon.length-2)*180);
  }
});

test('concave angles are derived with reflex vertex; validation remains separate', () => {
  const polygon = [[0,0],[4,0],[2,1],[4,4],[0,4]];
  assert.ok(interiorAngles(polygon)[2] > 180);
  near(interiorAngles(polygon).reduce((sum,a)=>sum+a,0),540);
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
});

test('partial measurements remain provisional; complete consistent measurements scale vertices',()=>{
  const segments=createSegments(points);
  assert.equal(buildDimensionalGeometry(points,segments).status,'unscaled');
  segments[0].lengthMm=800;
  assert.equal(buildDimensionalGeometry(points,segments).status,'provisional');
  segments.forEach((s,i)=>s.lengthMm=[800,400,800,400][i]);
  const result=buildDimensionalGeometry(points,segments);
  assert.equal(result.status,'complete');
  assert.deepEqual(result.vertices_mm,[[0,0],[800,0],[800,400],[0,400]]);
});

test('frozen coordinates remain unchanged through scaling and responsive previews',()=>{
  const frozen=Object.freeze(rectangle.map(v=>Object.freeze([...v])));
  const snapshot=JSON.stringify(frozen);
  const scaled=scaleVertices(frozen,2);
  for(const [width,height] of [[214,280],[500,300],[1200,300]]) {
    const preview=fitVerticesToPreview(scaled.map(([x,y])=>({x,y})),width,height,38);
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
