import test from "node:test";
import assert from "node:assert/strict";

import {
  getBoundingBox,
  scaleVerticesToDimensions,
} from "../../src/features/orders/geometryScaling.js";

const RECTANGLE_VERTICES = [
  { x: 100, y: 100 },
  { x: 500, y: 100 },
  { x: 500, y: 300 },
  { x: 100, y: 300 },
];

test("calculates the bounding box from graphical vertices", () => {
  assert.deepEqual(getBoundingBox(RECTANGLE_VERTICES), {
    minX: 100,
    maxX: 500,
    minY: 100,
    maxY: 300,
    width: 400,
    height: 200,
  });
});

test("scales graphical vertices to the requested dimensions in millimeters", () => {
  const result = scaleVerticesToDimensions(
    RECTANGLE_VERTICES,
    1000,
    500,
  );

  assert.deepEqual(result, [
    { xMm: 0, yMm: 0 },
    { xMm: 1000, yMm: 0 },
    { xMm: 1000, yMm: 500 },
    { xMm: 0, yMm: 500 },
  ]);
});

test("rejects zero or negative dimensions", () => {
  assert.equal(
    scaleVerticesToDimensions(RECTANGLE_VERTICES, 0, 500),
    null,
  );

  assert.equal(
    scaleVerticesToDimensions(RECTANGLE_VERTICES, 1000, -1),
    null,
  );
});

test("rejects an empty vertex collection", () => {
  assert.equal(
    scaleVerticesToDimensions([], 1000, 500),
    null,
  );
});

test("rejects a drawing with zero graphical width", () => {
  const vertices = [
    { x: 100, y: 100 },
    { x: 100, y: 200 },
    { x: 100, y: 300 },
  ];

  assert.equal(
    scaleVerticesToDimensions(vertices, 1000, 500),
    null,
  );
});

test("rejects a drawing with zero graphical height", () => {
  const vertices = [
    { x: 100, y: 100 },
    { x: 200, y: 100 },
    { x: 300, y: 100 },
  ];

  assert.equal(
    scaleVerticesToDimensions(vertices, 1000, 500),
    null,
  );
});