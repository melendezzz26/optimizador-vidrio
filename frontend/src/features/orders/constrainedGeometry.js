import { edgeLengths, interiorAngles } from './polygonMeasurements.js';
import { headingsFromVertices, solveAngularConstraints } from './angularConstraints.js';
import { validateConvexPolygon } from './convexityValidation.js';
import { isPositiveLength } from './segmentGeometry.js';

const error = (reason) => ({ status: 'error', error: reason, vertices_mm: null });
export const GEOMETRY_TOLERANCE = Object.freeze({ relativeLength: 1e-7, angleDegrees: 1e-5 });

// The chosen cyclic constraint supplies shape information that sides alone lack.
// Work in units of the longest side to avoid overflow/underflow of squared lengths.
function cyclicPolygon(sides) {
  const longest = sides.indexOf(Math.max(...sides));
  const angles = radius => sides.map(side => 2 * Math.asin(Math.min(1, side / (2 * radius))));
  const sum = values => values.reduce((total, value) => total + value, 0);
  const minor = sum(angles(0.5)) >= 2 * Math.PI;
  const residual = radius => {
    const values = angles(radius);
    return minor ? sum(values) - 2 * Math.PI : sum(values.filter((_, i) => i !== longest)) - values[longest];
  };
  let low = 0.5;
  let high = 1;
  for (let i = 0; i < 100 && (minor ? residual(high) > 0 : residual(high) < 0); i++) high *= 2;
  for (let i = 0; i < 100; i++) {
    const middle = (low + high) / 2;
    if (minor ? residual(middle) > 0 : residual(middle) < 0) low = middle;
    else high = middle;
  }
  const radius = (low + high) / 2;
  const turns = angles(radius);
  if (!minor) turns[longest] = 2 * Math.PI - turns[longest];
  let angle = 0;
  const points = turns.map(turn => {
    const point = [radius * (Math.cos(angle) - 1), radius * Math.sin(angle)];
    angle += turn;
    return point;
  });
  const [dx, dy] = points[1];
  const length = Math.hypot(dx, dy);
  return points.map(([x, y]) => [(x * dx + y * dy) / length, (y * dx - x * dy) / length]);
}

// V2 is the interior angle between S1 and S2. Circle intersection closes S3/S4.
function quadrilateral(sides, angle) {
  const [a, b, c, d] = sides;
  const radians = angle * Math.PI / 180;
  const opposite = [a - b * Math.cos(radians), b * Math.sin(radians)];
  const diagonal = Math.hypot(...opposite);
  if (diagonal >= c + d || diagonal <= Math.abs(c - d)) return null;
  const along = (d * d - c * c + diagonal * diagonal) / (2 * diagonal);
  const height = Math.sqrt(Math.max(0, d * d - along * along));
  const [ux, uy] = opposite.map(value => value / diagonal);
  for (const sign of [1, -1]) {
    const points = [[0, 0], [a, 0], opposite, [along * ux - sign * height * uy, along * uy + sign * height * ux]];
    if (validateConvexPolygon(points).isValid) return points;
  }
  return null;
}

export function buildConstrainedGeometry(segments, { mode = 'cyclic', angle = 90, constraints = [], drawing = [] } = {}) {
  if (!Array.isArray(segments) || segments.length < 3) return error('drawing');
  if (segments.some(s => s.badInput || (s.lengthMm !== '' && !isPositiveLength(s.lengthMm)))) return error('length');
  const measured = segments.map(s => isPositiveLength(s.lengthMm));
  const measuredCount = measured.filter(Boolean).length;
  if (measuredCount !== segments.length) return { status: measuredCount ? 'provisional' : 'unscaled', measured, measuredCount, vertices_mm: null };
  const lengths = segments.map(s => Number(s.lengthMm));
  const fixed = mode === 'angle' ? [{ vertex: 1, angle }] : constraints;
  if (!Array.isArray(fixed) || fixed.length > lengths.length - 3 ||
      new Set(fixed.map(item => item.vertex)).size !== fixed.length) return error('constraint-limit');
  if (fixed.some(item => !Number.isInteger(item.vertex) || item.vertex < 0 || item.vertex >= lengths.length ||
      !isPositiveLength(item.angle) || Number(item.angle) >= 180)) return error('angle');
  const scale = Math.max(...lengths);
  const normalized = lengths.map(length => length / scale);
  const rest = normalized.reduce((sum, side) => sum + side, 0) - 1;
  if (rest <= 1) return error('inequality');
  if (rest - 1 < 1e-12 || normalized.some(side => side < 1e-12)) return error('numeric-range');
  let points;
  if (mode === 'angle') {
    if (lengths.length !== 4 || !isPositiveLength(angle) || Number(angle) >= 180) return error('angle');
    points = quadrilateral(normalized, Number(angle));
    if (!points) return error('angle-configuration');
  } else if (['cyclic', 'guided', 'angles'].includes(mode)) {
    const cyclic = cyclicPolygon(normalized);
    if (!fixed.length && mode === 'cyclic') points = cyclic;
    else {
      const seeds = [headingsFromVertices(cyclic)];
      if (drawing.length === lengths.length && validateConvexPolygon(drawing).isValid) {
        const orientation = drawing.reduce((sum, p, i) => sum + p[0] * drawing[(i + 1) % drawing.length][1] - drawing[(i + 1) % drawing.length][0] * p[1], 0);
        seeds.unshift(headingsFromVertices(drawing.map(([x, y]) => [x, orientation < 0 ? -y : y])));
      }
      // Deterministic alternate guesses; never accept a non-convex closure.
      const base = seeds.at(-1);
      for (const shift of [-0.25, 0.25, -0.5, 0.5]) seeds.push(base.map((h, i) => h + shift * Math.sin((i + 1) * Math.PI / lengths.length)));
      for (const seed of seeds) {
        const candidate = solveAngularConstraints(normalized, fixed, seed);
        if (candidate && validateConvexPolygon(candidate).isValid) { points = candidate; break; }
      }
      if (!points) return error('angle-configuration');
    }
  }
  else return error('configuration');
  // Keep the sketch's orientation/handedness, without treating it as exact measurement.
  const heading = drawing.length > 1 ? Math.atan2(drawing[1][1] - drawing[0][1], drawing[1][0] - drawing[0][0]) : 0;
  const signed = drawing.reduce((sum, p, i) => sum + p[0] * drawing[(i + 1) % drawing.length][1] - drawing[(i + 1) % drawing.length][0] * p[1], 0);
  const vertices_mm = points.map(([x, y]) => {
    if (signed < 0) y = -y;
    return [(x * Math.cos(heading) - y * Math.sin(heading)) * scale, (x * Math.sin(heading) + y * Math.cos(heading)) * scale];
  });
  // Validate both closure lengths and the actual output, never claim success on a solver guess.
  try {
    const actual = edgeLengths(vertices_mm);
    if (actual.some((side, i) => Math.abs(side - lengths[i]) > lengths[i] * GEOMETRY_TOLERANCE.relativeLength)) return error('numeric-range');
    if (!validateConvexPolygon(vertices_mm).isValid) return error('numeric-range');
    const angles = interiorAngles(vertices_mm);
    if (fixed.some(({ vertex, angle }) => Math.abs(angles[vertex] - Number(angle)) > GEOMETRY_TOLERANCE.angleDegrees) ||
        Math.abs(angles.reduce((sum, a) => sum + a, 0) - (lengths.length - 2) * 180) > lengths.length * GEOMETRY_TOLERANCE.angleDegrees) return error('angle-configuration');
  } catch { return error('numeric-range'); }
  return { status: 'complete', lengths, measured, measuredCount, vertices_mm };
}
