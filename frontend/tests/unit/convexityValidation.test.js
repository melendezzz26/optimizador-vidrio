import test from 'node:test';
import assert from 'node:assert/strict';
import { validateConvexPolygon } from '../../src/features/orders/convexityValidation.js';

const triangle = [[0, 0], [4, 0], [0, 3]];
const rectangle = [[0, 0], [4, 0], [4, 3], [0, 3]];
const pentagon = [[0, 0], [3, 0], [4, 2], [1.5, 4], [-1, 2]];
const concave = [[0, 0], [4, 0], [2, 1], [4, 4], [0, 4]];
const bowTie = [[0, 0], [2, 2], [0, 2], [2, 0]];

function reason(points, expected) {
  const actual = validateConvexPolygon(points);
  assert.equal(actual.reason, expected);
  assert.equal(actual.isValid, expected === 'VALID');
  assert.equal(typeof actual.message, 'string');
  assert.ok(actual.message.length > 0);
  return actual;
}

for (const [name, points, orientation] of [
  ['triangle CW', triangle, 'CW'],
  ['triangle CCW', [...triangle].reverse(), 'CCW'],
  ['rectangle CW', rectangle, 'CW'],
  ['rectangle CCW', [...rectangle].reverse(), 'CCW'],
  ['pentagon CW', pentagon, 'CW'],
  ['pentagon CCW', [...pentagon].reverse(), 'CCW'],
]) {
  test(`T03-U: accepts ${name} in SVG Y-down coordinates`, () => {
    const actual = reason(points, 'VALID');
    assert.equal(actual.orientation, orientation);
    assert.equal(actual.isSimple, true);
    assert.equal(actual.isConvex, true);
    assert.equal(actual.message, 'Geometría convexa validada.');
  });
}

test('T03-U: rejects a simple concave pentagon in both orientations', () => {
  for (const points of [concave, [...concave].reverse()]) {
    const actual = reason(points, 'NON_CONVEX');
    assert.equal(actual.isSimple, true);
    assert.equal(actual.isConvex, false);
    assert.equal(actual.message, 'La figura resultante no es convexa.');
  }
});

test('T03-U: symmetric bow-tie is SELF_INTERSECTION despite zero signed area', () => {
  const actual = reason(bowTie, 'SELF_INTERSECTION');
  assert.equal(actual.isSimple, false);
  assert.equal(actual.orientation, null);
  assert.equal(actual.message, 'La geometría se intersecta consigo misma.');
});

test('T03-U: asymmetric crossing with nonzero signed area is SELF_INTERSECTION', () => {
  reason([[0, 0], [4, 3], [0, 3], [2, 0]], 'SELF_INTERSECTION');
});

test('T03-U: a star with same-sign turns still fails simplicity', () => {
  const outer = Array.from({ length: 5 }, (_, i) => [Math.cos(2 * Math.PI * i / 5), Math.sin(2 * Math.PI * i / 5)]);
  reason([0, 2, 4, 1, 3].map((i) => outer[i]), 'SELF_INTERSECTION');
});

test('T03-U: all collinear points take DEGENERATE priority over overlap/contact', () => {
  for (const points of [[[0, 0], [1, 0], [2, 0]], [[0, 0], [4, 4], [2, 2], [3, 3]]]) reason(points, 'DEGENERATE');
});

test('T03-U: an intermediate collinear vertex is valid, including at the cyclic seam', () => {
  const points = [[0, 0], [2, 0], [4, 0], [4, 3], [0, 3]];
  for (let i = 0; i < points.length; i++) reason([...points.slice(i), ...points.slice(0, i)], 'VALID');
});

test('T03-U: adjacent collinear backtracking is DEGENERATE', () => {
  reason([[0, 0], [4, 0], [2, 0], [4, 3], [0, 3]], 'DEGENERATE');
});

test('T03-U: backtracking across the closing seam is DEGENERATE', () => {
  reason([[2, 0], [4, 0], [4, 3], [0, 3], [4, 0]], 'DEGENERATE');
});

for (const points of [[], [[0, 0]], [[0, 0], [1, 1]]]) {
  test(`T03-U: ${points.length} vertices are TOO_FEW_VERTICES`, () => reason(points, 'TOO_FEW_VERTICES'));
}

for (const value of [null, undefined]) {
  test(`T03-U: absent input ${value} is INCOMPLETE`, () => {
    const actual = reason(value, 'INCOMPLETE');
    assert.equal(actual.isSimple, null);
    assert.equal(actual.isConvex, null);
    assert.equal(actual.orientation, null);
    assert.equal(actual.message, 'Pendiente de completar dimensiones.');
  });
}

for (const value of [NaN, Infinity, -Infinity, '1', null, undefined]) {
  test(`T03-U: coordinate ${String(value)} (${typeof value}) is INVALID_COORDINATES`, () => {
    reason([[0, 0], [4, value], [0, 3]], 'INVALID_COORDINATES');
    reason([[value, 0], [4, 0], [0, 3]], 'INVALID_COORDINATES');
  });
}

test('T03-U: malformed or sparse coordinate arrays are rejected without throwing', () => {
  for (const points of [{}, 'polygon', [null, [1, 0], [0, 1]], [[0], [1, 0], [0, 1]],
    [[0, 0, 0], [1, 0], [0, 1]], Array(3), [Array(2), [1, 0], [0, 1]]]) {
    reason(points, 'INVALID_COORDINATES');
  }
});

test('T03-U: too few vertices take priority over invalid coordinates', () => {
  reason([[NaN, 0]], 'TOO_FEW_VERTICES');
});

test('T03-U: consecutive repeated vertices are DEGENERATE', () => {
  reason([[0, 0], [4, 0], [4, 0], [0, 3]], 'DEGENERATE');
});

test('T03-U: repeated terminal vertex creates a null closing edge', () => {
  reason([...rectangle, rectangle[0]], 'DEGENERATE');
});

test('T03-U: coincident geometry has no scale and is DEGENERATE', () => {
  reason([[2, 2], [2, 2], [2, 2]], 'DEGENERATE');
});

test('T03-U: side and closing-edge equivalence use relative length tolerance', () => {
  reason([[0, 0], [5e-10, 0], [1, 0], [1, 1], [0, 1]], 'DEGENERATE');
  reason([...rectangle, [5e-10, 0]], 'DEGENERATE');
  reason([[0, 0], [2e-9, 0], [1, 0], [1, 1], [0, 1]], 'VALID');
});

test('T03-U: negative coordinates preserve convexity and orientation', () => {
  const actual = reason(rectangle.map(([x, y]) => [x - 8, y - 12]), 'VALID');
  assert.equal(actual.orientation, 'CW');
});

for (const scale of [1e-150, 0.001, 1e150, 1e307]) {
  test(`T03-U: very small/large scale ${scale} preserves classifications`, () => {
    for (const [points, expected] of [[rectangle, 'VALID'], [concave, 'NON_CONVEX'], [bowTie, 'SELF_INTERSECTION']]) {
      reason(points.map(([x, y]) => [x * scale, y * scale]), expected);
    }
  });
}

test('T03-U: finite coordinates whose bounding-box extent overflows still validate', () => {
  reason([[-1e308, -1e308], [1e308, -1e308], [1e308, 1e308], [-1e308, 1e308]], 'VALID');
});

test('T03-U: large translation avoids shoelace cancellation on simple shapes', () => {
  const actual = reason(rectangle.map(([x, y]) => [1e12 + x, -1e12 + y]), 'VALID');
  assert.equal(actual.orientation, 'CW');
});

test('T03-U: vertex touching the interior of a nonadjacent edge is SELF_INTERSECTION', () => {
  reason([[0, 0], [4, 0], [4, 4], [2, 0], [0, 4]], 'SELF_INTERSECTION');
});

test('T03-U: nonadjacent collinear overlapping edges are SELF_INTERSECTION', () => {
  reason([[0, 0], [4, 0], [4, 4], [1, 0], [3, 0], [0, 4]], 'SELF_INTERSECTION');
});

test('T03-U: repeated nonadjacent vertex is an invalid contact', () => {
  reason([[0, 0], [2, 0], [2, 2], [0, 0], [-2, 2], [-2, 0]], 'SELF_INTERSECTION');
});

test('T03-U: contact tolerance distinguishes a near touch from a separated concavity', () => {
  reason([[0, 0], [4, 0], [4, 4], [2, 1e-10], [0, 4]], 'SELF_INTERSECTION');
  reason([[0, 0], [4, 0], [4, 4], [2, 1e-6], [0, 4]], 'NON_CONVEX');
});

test('T03-U: nearly collinear intermediate turns are ignored within tolerance', () => {
  reason([[0, 0], [0.5, 1e-10], [1, 0], [1, 1], [0, 1]], 'VALID');
  reason([[0, 0], [0.5, 1e-6], [1, 0], [1, 1], [0, 1]], 'NON_CONVEX');
});

test('T03-U: simple noncollinear near-zero area is rejected after simplicity', () => {
  const actual = reason([[0, 0], [1, 0], [0.5, 1.5e-9]], 'DEGENERATE');
  assert.equal(actual.isSimple, true);
  reason([[0, 0], [1, 0], [0.5, 3e-9]], 'VALID');
});

test('T03-U: validation never mutates deeply frozen input in any classification', () => {
  for (const original of [rectangle, concave, bowTie, [[0, 0], [1, 0], [2, 0]]]) {
    const points = Object.freeze(original.map((p) => Object.freeze([...p])));
    const snapshot = JSON.stringify(points);
    validateConvexPolygon(points);
    assert.equal(JSON.stringify(points), snapshot);
  }
});

test('T03-U: repeated validation is deterministic and results do not share mutable state', () => {
  for (const points of [rectangle, concave, bowTie]) {
    const initial = validateConvexPolygon(points);
    assert.deepEqual(validateConvexPolygon(points), initial);
    initial.reason = 'changed by consumer';
    assert.notEqual(validateConvexPolygon(points).reason, initial.reason);
  }
});
