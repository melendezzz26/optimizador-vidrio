// T02 dimensional consistency only. No convexity or intersection validation.
export function isPositiveLength(value) {
  return (typeof value === "number" || typeof value === "string") &&
    String(value).trim() !== "" && Number.isFinite(Number(value)) && Number(value) > 0;
}

export function getDrawingSegmentLength(start, end) {
  return Math.hypot(end.x - start.x, end.y - start.y);
}

export function createSegments(vertices) {
  return vertices.map((_, index) => ({ id: `S${index + 1}`, index, lengthMm: "" }));
}

function getReferenceEdges(vertices) {
  if (!Array.isArray(vertices) || vertices.length < 3 ||
      vertices.some((point) => !point || !Number.isFinite(point.x) || !Number.isFinite(point.y))) return null;
  const edges = vertices.map((start, index) => {
    const end = vertices[(index + 1) % vertices.length];
    return { length: getDrawingSegmentLength(start, end), angle: Math.atan2(end.y - start.y, end.x - start.x) };
  });
  return edges.every(({ length }) => Number.isFinite(length) && length > 0) ? edges : null;
}

export function resolveSegmentLengths(vertices, segments) {
  const edges = getReferenceEdges(vertices);
  if (!edges) return { error: "drawing" };
  if (!Array.isArray(segments) || segments.length !== edges.length ||
      segments.some((segment, index) => segment.index !== index || segment.id !== `S${index + 1}`)) {
    return { error: "segments" };
  }
  const measured = segments.map(({ lengthMm }) => isPositiveLength(lengthMm));
  const measuredCount = measured.filter(Boolean).length;
  if (segments.some(({ lengthMm, badInput }) => badInput ||
      (String(lengthMm).trim() !== "" && !isPositiveLength(lengthMm)))) {
    return { error: "length", measuredCount };
  }
  if (!measuredCount) return { lengths: null, measured, measuredCount, provisionalScale: null };
  const scales = segments.flatMap(({ lengthMm }, index) => measured[index]
    ? [Number(lengthMm) / edges[index].length] : []).sort((a, b) => a - b);
  const middle = Math.floor(scales.length / 2);
  const provisionalScale = scales.length % 2 ? scales[middle] : scales[middle - 1] / 2 + scales[middle] / 2;
  const lengths = segments.map(({ lengthMm }, index) => measured[index]
    ? Number(lengthMm) : edges[index].length * provisionalScale);
  if (!Number.isFinite(provisionalScale) || provisionalScale <= 0 || !lengths.every(isPositiveLength)) {
    return { error: "numeric-range", measuredCount };
  }
  return { lengths, measured, measuredCount, provisionalScale };
}

const MAX_ITERATIONS = 160;
const NORMALIZED_TOLERANCE = 1e-11;
const REGULARIZATION = 1e-12;

function closure(lengths, angles) {
  return lengths.reduce((sum, length, index) => ({
    x: sum.x + length * Math.cos(angles[index]),
    y: sum.y + length * Math.sin(angles[index]),
  }), { x: 0, y: 0 });
}

function closeDirections(lengths, initialAngles) {
  let angles = [...initialAngles];
  for (let iteration = 0; iteration < MAX_ITERATIONS; iteration += 1) {
    const residual = closure(lengths, angles);
    const error = Math.hypot(residual.x, residual.y);
    if (error <= NORMALIZED_TOLERANCE) return angles;
    const jx = lengths.map((length, index) => -length * Math.sin(angles[index]));
    const jy = lengths.map((length, index) => length * Math.cos(angles[index]));
    let a = REGULARIZATION;
    let b = 0;
    let d = REGULARIZATION;
    for (let i = 0; i < lengths.length; i += 1) {
      a += jx[i] * jx[i];
      b += jx[i] * jy[i];
      d += jy[i] * jy[i];
    }
    const determinant = a * d - b * b;
    if (!Number.isFinite(determinant) || determinant <= 0) return null;
    const ux = (d * residual.x - b * residual.y) / determinant;
    const uy = (a * residual.y - b * residual.x) / determinant;
    const delta = jx.map((value, index) => -(value * ux + jy[index] * uy));
    const largestDelta = delta.reduce((largest, value) => Math.max(largest, Math.abs(value)), 0);
    // Limit angular jumps, then backtrack until closure improves.
    let damping = Math.min(1, 0.35 / largestDelta);
    let improved = false;
    for (let trial = 0; trial < 16; trial += 1) {
      const candidate = angles.map((angle, index) => angle + damping * delta[index]);
      const next = closure(lengths, candidate);
      if (Math.hypot(next.x, next.y) < error) {
        angles = candidate;
        improved = true;
        break;
      }
      damping *= 0.5;
    }
    if (!improved) return null;
  }
  return null;
}

/**
 * Adjust directions using damped minimum-norm closure corrections.
 * Lengths alone do not uniquely determine a polygon: the sketch selects a local
 * solution, not a guaranteed global minimum or a geometry approved for cutting.
 * vertices_mm excludes the repeated terminal point; closureErrorMm bounds the
 * discrepancy of that final implicit edge. Inputs are never changed.
 */
export function reconstructPolygonFromSegmentLengths(vertices, targetLengths) {
  const edges = getReferenceEdges(vertices);
  if (!edges) return { error: "drawing" };
  if (!Array.isArray(targetLengths) || targetLengths.length !== edges.length ||
      !targetLengths.every(isPositiveLength)) return { error: "length" };
  const lengthsMm = targetLengths.map(Number);
  const maxLength = lengthsMm.reduce((largest, length) => Math.max(largest, length), 0);
  const lengths = lengthsMm.map((length) => length / maxLength);
  const longestIndex = lengths.indexOf(1);
  const others = lengths.reduce((sum, length, index) => sum + (index === longestIndex ? 0 : length), 0);
  if (others <= 1) return { error: "inequality" };
  if (lengths.some((length) => length === 0)) return { error: "numeric-range" };
  const reference = edges.map(({ angle }) => angle);
  let best = null;
  let bestCost = Infinity;
  // Deterministic small perturbations escape a collinear/rank-deficient start.
  // Choose the successful branch with the least angular departure from the sketch.
  for (const perturbation of [0, 0.025, -0.025]) {
    const initial = reference.map((angle, index) => angle + perturbation * Math.sin(index + 1));
    const candidate = closeDirections(lengths, initial);
    if (!candidate) continue;
    const cost = candidate.reduce((sum, angle, index) => {
      const difference = Math.atan2(Math.sin(angle - reference[index]), Math.cos(angle - reference[index]));
      return sum + difference * difference;
    }, 0);
    if (cost < bestCost) { best = candidate; bestCost = cost; }
    if (cost < 1e-20) break;
  }
  if (!best) return { error: "convergence" };
  let x = 0;
  let y = 0;
  const vertices_mm = lengthsMm.map((length, index) => {
    const point = [x, y];
    x += length * Math.cos(best[index]);
    y += length * Math.sin(best[index]);
    return point;
  });
  const closureErrorMm = Math.hypot(x, y);
  const toleranceMm = maxLength * 1e-9;
  if (!vertices_mm.every((point) => point.every(Number.isFinite)) || !Number.isFinite(closureErrorMm)) {
    return { error: "numeric-range" };
  }
  if (closureErrorMm > toleranceMm) return { error: "convergence" };
  return { vertices_mm, closureErrorMm, toleranceMm };
}

export function buildDimensionalGeometry(vertices, segments) {
  const resolved = resolveSegmentLengths(vertices, segments);
  if (resolved.error) return { ...resolved, status: "error", vertices_mm: null };
  if (!resolved.lengths) return { ...resolved, status: "unscaled", vertices_mm: null };
  const reconstruction = reconstructPolygonFromSegmentLengths(vertices, resolved.lengths);
  return {
    ...resolved,
    ...reconstruction,
    vertices_mm: reconstruction.vertices_mm ?? null,
    status: reconstruction.error ? "error" : resolved.measured.every(Boolean) ? "complete" : "provisional",
  };
}
