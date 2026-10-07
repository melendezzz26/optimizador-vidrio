// Relative to the longest bounding-box dimension. Work on a translated,
// uniformly scaled COPY: length tolerance = epsilon * scale; cross/area
// tolerance = epsilon * scale^2. No absolute mm floor, so tiny shapes work too.
const RELATIVE_TOLERANCE = 1e-9;
const TOLERANCE = Object.freeze({
  length: RELATIVE_TOLERANCE,
  cross: RELATIVE_TOLERANCE,
  area: RELATIVE_TOLERANCE,
});

const MESSAGES = Object.freeze({
  INCOMPLETE: "Pendiente de completar dimensiones.",
  TOO_FEW_VERTICES: "La geometría necesita al menos tres vértices.",
  INVALID_COORDINATES: "La geometría contiene coordenadas inválidas. Revisa el dibujo y sus medidas.",
  DEGENERATE: "La geometría tiene lados superpuestos o un área insuficiente. Revisa el dibujo y sus medidas.",
  SELF_INTERSECTION: "La geometría se intersecta consigo misma.",
  NON_CONVEX: "La figura resultante no es convexa.",
  VALID: "Geometría convexa validada.",
});

function result(reason, isSimple = null, orientation = null) {
  return {
    isValid: reason === "VALID",
    // null means not established (early structural rejection / incomplete).
    isSimple,
    isConvex: reason === "VALID" ? true : reason === "INCOMPLETE" ? null : false,
    orientation,
    reason,
    message: MESSAGES[reason],
  };
}

function bounds(points) {
  return points.reduce((box, [x, y]) => ({
    minX: Math.min(box.minX, x), maxX: Math.max(box.maxX, x),
    minY: Math.min(box.minY, y), maxY: Math.max(box.maxY, y),
  }), { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });
}

function normalizedCopy(vertices) {
  let points = vertices;
  let box = bounds(points);
  let scale = Math.max(box.maxX - box.minX, box.maxY - box.minY);
  // Finite opposite-sign coordinates can still overflow their difference.
  // Prescale only in that case, before translating into the unit box.
  if (!Number.isFinite(scale)) {
    const magnitude = Math.max(Math.abs(box.minX), Math.abs(box.maxX), Math.abs(box.minY), Math.abs(box.maxY));
    points = vertices.map(([x, y]) => [x / magnitude, y / magnitude]);
    box = bounds(points);
    scale = Math.max(box.maxX - box.minX, box.maxY - box.minY);
  }
  if (scale === 0) return null;
  return points.map(([x, y]) => [(x - box.minX) / scale, (y - box.minY) / scale]);
}

const distance = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
const cross = (a, b, c) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
const turnSign = (value) => Math.abs(value) <= TOLERANCE.cross ? 0 : Math.sign(value);

function onSegment(a, b, p) {
  return Math.abs(cross(a, b, p)) <= TOLERANCE.cross &&
    p[0] >= Math.min(a[0], b[0]) - TOLERANCE.length && p[0] <= Math.max(a[0], b[0]) + TOLERANCE.length &&
    p[1] >= Math.min(a[1], b[1]) - TOLERANCE.length && p[1] <= Math.max(a[1], b[1]) + TOLERANCE.length;
}

function intersects(a, b, c, d) {
  const abC = turnSign(cross(a, b, c));
  const abD = turnSign(cross(a, b, d));
  const cdA = turnSign(cross(c, d, a));
  const cdB = turnSign(cross(c, d, b));
  return (abC * abD < 0 && cdA * cdB < 0) ||
    (abC === 0 && onSegment(a, b, c)) || (abD === 0 && onSegment(a, b, d)) ||
    (cdA === 0 && onSegment(c, d, a)) || (cdB === 0 && onSegment(c, d, b));
}

/**
 * Validate complete T02 vertices_mm ([x,y] pairs, implicit closing edge).
 * Pass null while T02 is not complete. No sorting, repairs or input mutation.
 * SVG coordinates have Y down: positive signed area is clockwise (CW).
 * Classification priority follows SPEC T03 §7; time O(n²), extra space O(n).
 */
export function validateConvexPolygon(vertices) {
  if (vertices == null) return result("INCOMPLETE");
  if (!Array.isArray(vertices)) return result("INVALID_COORDINATES");
  if (vertices.length < 3) return result("TOO_FEW_VERTICES");
  // Array.from also materializes holes so sparse input cannot bypass validation.
  if (Array.from(vertices).some((point) => !Array.isArray(point) || point.length !== 2 ||
      !Number.isFinite(point[0]) || !Number.isFinite(point[1]))) return result("INVALID_COORDINATES");
  const points = normalizedCopy(vertices);
  if (!points) return result("DEGENERATE");
  const n = points.length;
  const next = (i) => points[(i + 1) % n];
  if (points.some((p, i) => distance(p, next(i)) <= TOLERANCE.length)) return result("DEGENERATE");

  const origin = points[0];
  const farthest = points.reduce((best, p) => distance(origin, p) > distance(origin, best) ? p : best, origin);
  if (points.every((p) => Math.abs(cross(origin, farthest, p)) <= TOLERANCE.cross)) return result("DEGENERATE");

  const turns = points.map((a, i) => turnSign(cross(a, next(i), next(i + 1))));
  for (let i = 0; i < n; i++) {
    const a = points[i], b = next(i), c = next(i + 1);
    const dot = (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]);
    if (turns[i] === 0 && dot < 0) return result("DEGENERATE");
  }

  // Compute area now, but defer its classification until simplicity is known.
  const area = points.reduce((sum, [x, y], i) => sum + x * next(i)[1] - next(i)[0] * y, 0) / 2;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      if (j === i + 1 || (i === 0 && j === n - 1)) continue;
      if (intersects(points[i], next(i), points[j], next(j))) return result("SELF_INTERSECTION", false);
    }
  }
  if (Math.abs(area) <= TOLERANCE.area) return result("DEGENERATE", true);
  const orientation = area > 0 ? "CW" : "CCW";
  const significant = turns.filter((sign) => sign !== 0);
  if (!significant.length) return result("DEGENERATE", true);
  if (significant.some((sign) => sign !== significant[0])) return result("NON_CONVEX", true, orientation);
  return result("VALID", true, orientation);
}
