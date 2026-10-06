import test from "node:test";
import assert from "node:assert/strict";
import { fitVerticesToPreview, getBoundingBox } from "../../src/features/orders/geometryScaling.js";
import {
  buildDimensionalGeometry, createSegments, getDrawingSegmentLength, isPositiveLength,
  reconstructPolygonFromSegmentLengths, resolveSegmentLengths,
} from "../../src/features/orders/segmentGeometry.js";

const rectangle = [{ x: 100, y: 100 }, { x: 500, y: 100 }, { x: 500, y: 300 }, { x: 100, y: 300 }];
const pentagon = [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 400, y: 200 }, { x: 150, y: 400 }, { x: -100, y: 200 }];
const triangle = [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 300, y: 400 }];
const withLengths = (vertices, lengths) => createSegments(vertices).map((segment, index) => ({ ...segment, lengthMm: lengths[index] ?? "" }));
const asPoints = (vertices_mm) => vertices_mm.map(([x, y]) => ({ x, y }));
function near(actual, expected, tolerance = 1e-6) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} differs from ${expected} by more than ${tolerance}`);
}
function assertReconstructed(result, lengths) {
  assert.equal(result.error, undefined);
  assert.equal(result.vertices_mm.length, lengths.length);
  assert.deepEqual(result.vertices_mm[0], [0, 0]);
  assert.ok(result.closureErrorMm <= result.toleranceMm);
  const points = asPoints(result.vertices_mm);
  for (let index = 0; index < points.length; index += 1) {
    near(getDrawingSegmentLength(points[index], points[(index + 1) % points.length]), Number(lengths[index]), result.toleranceMm * 2);
  }
}

 test("graphical segment length uses Euclidean distance, independent of translation", () => {
  near(getDrawingSegmentLength({ x: -8, y: 12 }, { x: -5, y: 16 }), 5);
  near(getDrawingSegmentLength({ x: 0, y: 0 }, { x: 0, y: 0 }), 0);
});

test("segment IDs and indices preserve drawing order, including the closing side", () => {
  assert.deepEqual(createSegments(triangle), [
    { id: "S1", index: 0, lengthMm: "" }, { id: "S2", index: 1, lengthMm: "" }, { id: "S3", index: 2, lengthMm: "" },
  ]);
  const resolved = resolveSegmentLengths(triangle, withLengths(triangle, [600, "", ""]));
  assert.deepEqual(resolved.lengths, [600, 800, 1000]);
});

test("no real measure means no physical scale and no vertices_mm", () => {
  const result = buildDimensionalGeometry(rectangle, createSegments(rectangle));
  assert.equal(result.status, "unscaled");
  assert.equal(result.provisionalScale, null);
  assert.equal(result.vertices_mm, null);
  assert.equal(result.measuredCount, 0);
});

test("a single measurement supplies the provisional scale without filling blank inputs", () => {
  const segments = withLengths(rectangle, [800, "", "", ""]);
  const result = resolveSegmentLengths(rectangle, segments);
  assert.equal(result.provisionalScale, 2);
  assert.deepEqual(result.lengths, [800, 400, 800, 400]);
  assert.deepEqual(result.measured, [true, false, false, false]);
  assert.equal(segments[1].lengthMm, "");
  assert.equal(buildDimensionalGeometry(rectangle, segments).status, "provisional");
});

test("odd median is robust to an outlier and even median averages central scales", () => {
  const odd = resolveSegmentLengths(rectangle, withLengths(rectangle, [800, 800, 40000, ""]));
  assert.equal(odd.provisionalScale, 4);
  assert.equal(odd.lengths[3], 800);
  const even = resolveSegmentLengths(rectangle, withLengths(rectangle, [800, 800, "", ""]));
  assert.equal(even.provisionalScale, 3);
  assert.deepEqual(even.lengths, [800, 800, 1200, 600]);
});

test("complete model uses only entered lengths", () => {
  const lengths = [850, 420, 600, 510, 730];
  const result = buildDimensionalGeometry(pentagon, withLengths(pentagon, lengths));
  assert.equal(result.status, "complete");
  assert.equal(result.measuredCount, 5);
  assert.deepEqual(result.lengths, lengths);
  assertReconstructed(result, lengths);
});

test("known rectangle preserves reference directions and has origin at its first vertex", () => {
  const result = reconstructPolygonFromSegmentLengths(rectangle, [1000, 500, 1000, 500]);
  assertReconstructed(result, [1000, 500, 1000, 500]);
  const expected = [[0, 0], [1000, 0], [1000, 500], [0, 500]];
  result.vertices_mm.forEach((point, i) => point.forEach((value, axis) => near(value, expected[i][axis])));
});

test("three sides reconstruct a known 3-4-5 triangle", () => {
  const result = reconstructPolygonFromSegmentLengths(triangle, [300, 400, 500]);
  assertReconstructed(result, [300, 400, 500]);
  result.vertices_mm.forEach((point, index) => point.forEach((value, axis) => near(value, [[0, 0], [300, 0], [300, 400]][index][axis])));
});

test("editing one side changes geometry, closes the chain and keeps all other lengths", () => {
  const segments = withLengths(rectangle, [1000, 500, 1000, 500]);
  const before = buildDimensionalGeometry(rectangle, segments);
  const edited = segments.map((segment, index) => index === 0 ? { ...segment, lengthMm: "1200" } : segment);
  const after = buildDimensionalGeometry(rectangle, edited);
  assert.notDeepEqual(after.vertices_mm, before.vertices_mm);
  assertReconstructed(after, [1200, 500, 1000, 500]);
  // Keeping all original directions here would leave a 200 mm gap.
  near(after.vertices_mm[2][0], 1100);
  assert.deepEqual(edited.slice(1), segments.slice(1));
});

test("reference orientation and vertex order survive a rotated, translated sketch", () => {
  const rotated = rectangle.map(({ x, y }) => ({ x: 42 - y, y: -71 + x }));
  const result = reconstructPolygonFromSegmentLengths(rotated, [1000, 500, 1000, 500]);
  assertReconstructed(result, [1000, 500, 1000, 500]);
  near(result.vertices_mm[1][0], 0);
  near(result.vertices_mm[1][1], 1000);
  near(result.vertices_mm[2][0], -500);
});

test("five different real lengths reconstruct deterministically", () => {
  const lengths = [850, 420, 600, 510, 730];
  const result = reconstructPolygonFromSegmentLengths(pentagon, lengths);
  assertReconstructed(result, lengths);
  assert.deepEqual(reconstructPolygonFromSegmentLengths(pentagon, lengths), result);
});

test("concave sketches are dimensioned without T03 validation", () => {
  const vertices = [{ x: 0, y: 0 }, { x: 300, y: 0 }, { x: 200, y: 100 }, { x: 300, y: 300 }, { x: 0, y: 300 }];
  const lengths = vertices.map((point, index) => getDrawingSegmentLength(point, vertices[(index + 1) % vertices.length]) * 2);
  const result = reconstructPolygonFromSegmentLengths(vertices, lengths);
  assertReconstructed(result, lengths);
  near(result.vertices_mm[2][0], 400);
  near(result.vertices_mm[2][1], 200);
});

test("six or more segments satisfy each target length", () => {
  for (const count of [6, 8, 12]) {
    const vertices = Array.from({ length: count }, (_, i) => ({ x: 100 * Math.cos(i * 2 * Math.PI / count), y: 100 * Math.sin(i * 2 * Math.PI / count) }));
    const lengths = vertices.map((_, i) => 200 + i * 23);
    assertReconstructed(reconstructPolygonFromSegmentLengths(vertices, lengths), lengths);
  }
});

test("a collinear reference can escape the rank-deficient initial directions", () => {
  const vertices = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 200, y: 0 }];
  assertReconstructed(reconstructPolygonFromSegmentLengths(vertices, [300, 400, 500]), [300, 400, 500]);
});

for (const value of [0, -1, NaN, Infinity, -Infinity, "abc", "", " ", null, undefined, true]) {
  test(`invalid length ${String(value)} is rejected, never replaced by an estimate`, () => {
    assert.equal(isPositiveLength(value), false);
    assert.equal(reconstructPolygonFromSegmentLengths(rectangle, [value, 500, 1000, 500]).error, "length");
  });
}

test("strict polygon inequality rejects equality and a side longer than all others", () => {
  for (const lengths of [[2000, 500, 1000, 500], [2001, 500, 1000, 500]]) {
    const result = buildDimensionalGeometry(rectangle, withLengths(rectangle, lengths));
    assert.equal(result.error, "inequality");
    assert.equal(result.status, "error");
    assert.equal(result.vertices_mm, null);
  }
});

test("inconsistent provisional lengths cannot claim a complete preview", () => {
  const result = buildDimensionalGeometry(rectangle, withLengths(rectangle, [10000, 200, 400, ""]));
  assert.equal(result.error, "inequality");
  assert.equal(result.measuredCount, 3);
  assert.equal(result.vertices_mm, null);
});

test("incomplete native numeric input is an error, not an unmeasured estimate", () => {
  const segments = withLengths(rectangle, [1000, "", "", ""]);
  segments[1].badInput = true;
  assert.equal(buildDimensionalGeometry(rectangle, segments).error, "length");
});

test("positive decimals below 0.01 are accepted", () => {
  const lengths = [0.005, 0.003, 0.005, 0.003];
  assertReconstructed(reconstructPolygonFromSegmentLengths(rectangle, lengths), lengths);
});

test("near-degenerate feasible lengths can still close", () => {
  assertReconstructed(reconstructPolygonFromSegmentLengths(triangle, [1000, 1000, 1999.999]), [1000, 1000, 1999.999]);
});

test("missing edges, repeated adjacent vertices and non-finite drawings fail explicitly", () => {
  for (const points of [[], rectangle.slice(0, 2), [...rectangle, rectangle[0]], [{ x: NaN, y: 0 }, ...rectangle], [{ x: Infinity, y: 0 }, ...rectangle]]) {
    assert.equal(reconstructPolygonFromSegmentLengths(points, [1, 1, 1, 1]).error, "drawing");
  }
  assert.equal(reconstructPolygonFromSegmentLengths(rectangle, [1, 1, 1]).error, "length");
  const reversed = createSegments(rectangle).reverse();
  assert.equal(resolveSegmentLengths(rectangle, reversed).error, "segments");
});

test("overflowing provisional scale fails without emitting invalid vertices", () => {
  const points = [{ x: 0, y: 0 }, { x: 1e-300, y: 0 }, { x: 1e-300, y: 1e-300 }];
  const result = buildDimensionalGeometry(points, withLengths(points, [1e300, "", ""]));
  assert.equal(result.error, "numeric-range");
  assert.equal(result.vertices_mm, null);
});

test("all geometry operations leave frozen inputs unchanged", () => {
  const points = Object.freeze(rectangle.map((point) => Object.freeze({ ...point })));
  const segments = Object.freeze(withLengths(points, [1200, 500, 1000, ""]).map(Object.freeze));
  const snapshot = JSON.stringify({ points, segments });
  const result = buildDimensionalGeometry(points, segments);
  assert.equal(result.status, "provisional");
  const previewPoints = Object.freeze(asPoints(result.vertices_mm).map(Object.freeze));
  assert.ok(fitVerticesToPreview(previewPoints, 320, 280));
  assert.deepEqual(getBoundingBox(points), { minX: 100, maxX: 500, minY: 100, maxY: 300, width: 400, height: 200 });
  assert.equal(JSON.stringify({ points, segments }), snapshot);
});

for (const [horizontal, vertical] of [[200, 5000], [5000, 200], [1000, 500]]) {
  test(`preview preserves ${horizontal}:${vertical} at desktop and mobile sizes`, () => {
    const lengths = [horizontal, vertical, horizontal, vertical];
    const result = reconstructPolygonFromSegmentLengths(rectangle, lengths);
    assertReconstructed(result, lengths);
    const points = asPoints(result.vertices_mm);
    const snapshot = JSON.stringify(points);
    for (const [width, height] of [[214, 280], [500, 300], [1200, 300]]) {
      const preview = fitVerticesToPreview(points, width, height, 38);
      near(preview.bounds.width / preview.bounds.height, horizontal / vertical);
      near(preview.bounds.x + preview.bounds.width / 2, width / 2);
      near(preview.bounds.y + preview.bounds.height / 2, height / 2);
      preview.points.forEach(({ x, y }) => assert.ok(x >= 37.999 && y >= 37.999 && x <= width - 37.999 && y <= height - 37.999));
    }
    assert.equal(JSON.stringify(points), snapshot);
  });
}

test("preview rejects invalid bounds and handles non-origin and one-axis extents", () => {
  for (const points of [[], [{ x: 0, y: NaN }], [{ x: 0, y: 0 }]]) assert.equal(fitVerticesToPreview(points), null);
  for (const size of [[0, 100], [100, NaN], [Infinity, 300]]) assert.equal(fitVerticesToPreview(rectangle, ...size), null);
  assert.equal(fitVerticesToPreview(rectangle, 500, 300, -1), null);
  const line = fitVerticesToPreview([{ x: -10, y: -10 }, { x: -10, y: 10 }], 300, 300);
  near(line.bounds.width, 0);
  near(line.bounds.x, 150);
});

test("clearing a completed length returns to provisional; clearing all removes physical scale", () => {
  const segments = withLengths(rectangle, [1000, 500, 1000, 500]);
  assert.equal(buildDimensionalGeometry(rectangle, segments).status, "complete");
  segments[2].lengthMm = "";
  const provisional = buildDimensionalGeometry(rectangle, segments);
  assert.equal(provisional.status, "provisional");
  assert.equal(provisional.measuredCount, 3);
  assert.equal(buildDimensionalGeometry(rectangle, createSegments(rectangle)).status, "unscaled");
});
