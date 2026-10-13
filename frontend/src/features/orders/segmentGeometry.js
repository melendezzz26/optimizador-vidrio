import { scaleVertices } from "./polygonMeasurements.js";

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
    return { length: getDrawingSegmentLength(start, end) };
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

/** Scale the actual sketch uniformly; inconsistent lengths cannot redefine its shape. */
export function scaleSketchToLengths(vertices, targetLengths) {
  const edges = getReferenceEdges(vertices);
  if (!edges) return { error: "drawing" };
  if (!Array.isArray(targetLengths) || targetLengths.length !== edges.length || !targetLengths.every(isPositiveLength)) return { error: "length" };
  const scale = Number(targetLengths[0]) / edges[0].length;
  if (!Number.isFinite(scale) || scale <= 0) return { error: "numeric-range" };
  if (edges.some((edge, i) => Math.abs(Number(targetLengths[i]) - edge.length * scale) > Math.max(1, edge.length * scale) * 1e-8)) {
    return { error: "shape-mismatch" };
  }
  try {
    const vertices_mm = scaleVertices(vertices.map(({x,y}) => [x,y]), scale);
    return { vertices_mm, closureErrorMm: 0, toleranceMm: Math.max(...targetLengths.map(Number)) * 1e-9 };
  } catch {
    return { error: "numeric-range" };
  }
}

export function buildDimensionalGeometry(vertices, segments) {
  const resolved = resolveSegmentLengths(vertices, segments);
  if (resolved.error) return { ...resolved, status: "error", vertices_mm: null };
  if (!resolved.lengths) return { ...resolved, status: "unscaled", vertices_mm: null };
  const scaled = scaleSketchToLengths(vertices, resolved.lengths);
  return {
    ...resolved,
    ...scaled,
    vertices_mm: scaled.vertices_mm ?? null,
    status: scaled.error ? "error" : resolved.measured.every(Boolean) ? "complete" : "provisional",
  };
}
