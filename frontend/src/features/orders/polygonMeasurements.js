// Canonical geometry is the ordered vertices_mm array. No inferred directions.
export function hasFiniteVertices(vertices) {
  return Array.isArray(vertices) && vertices.length >= 3 && vertices.every((point) =>
    Array.isArray(point) && point.length === 2 && point.every((value) => typeof value === 'number' && Number.isFinite(value)));
}

export function edgeLengths(vertices) {
  if (!hasFiniteVertices(vertices)) throw new TypeError('Se requieren vértices finitos.');
  const lengths = vertices.map(([x, y], index) => {
    const next = vertices[(index + 1) % vertices.length];
    return Math.hypot(next[0] - x, next[1] - y);
  });
  if (lengths.some((value) => !Number.isFinite(value) || value <= 0)) throw new RangeError('Arista degenerada.');
  return lengths;
}

export function interiorAngles(vertices) {
  const lengths = edgeLengths(vertices);
  // Translate and normalize to avoid cancellation/overflow in area and angles.
  const scale = Math.max(...lengths);
  const points = vertices.map(([x, y]) => [(x - vertices[0][0]) / scale, (y - vertices[0][1]) / scale]);
  const area = points.reduce((sum, [x, y], i) => {
    const next = points[(i + 1) % points.length];
    return sum + x * next[1] - next[0] * y;
  }, 0);
  if (!Number.isFinite(area) || Math.abs(area) <= 1e-12) throw new RangeError('Polígono degenerado.');
  return points.map(([x, y], i) => {
    const previous = points[(i + points.length - 1) % points.length];
    const next = points[(i + 1) % points.length];
    const incoming = [x - previous[0], y - previous[1]];
    const outgoing = [next[0] - x, next[1] - y];
    const cross = incoming[0] * outgoing[1] - incoming[1] * outgoing[0];
    const dot = incoming[0] * outgoing[0] + incoming[1] * outgoing[1];
    const turn = Math.atan2(cross, dot) * Math.sign(area);
    const angle = 180 - turn * 180 / Math.PI;
    if (!Number.isFinite(angle) || Math.abs(cross) <= 1e-12 || angle <= 0 || angle >= 360) {
      throw new RangeError('Vértice degenerado.');
    }
    return angle;
  });
}

export function scaleVertices(vertices, factor) {
  edgeLengths(vertices);
  if (!Number.isFinite(factor) || factor <= 0) throw new RangeError('Escala inválida.');
  const scaled = vertices.map(([x, y]) => [(x - vertices[0][0]) * factor, (y - vertices[0][1]) * factor]);
  edgeLengths(scaled);
  return scaled;
}
