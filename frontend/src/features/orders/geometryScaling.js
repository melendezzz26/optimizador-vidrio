export function getBoundingBox(vertices) {
  if (!Array.isArray(vertices) || !vertices.length ||
      vertices.some((point) => !point || !Number.isFinite(point.x) || !Number.isFinite(point.y))) return null;
  const bounds = vertices.reduce((box, { x, y }) => ({
    minX: Math.min(box.minX, x), maxX: Math.max(box.maxX, x),
    minY: Math.min(box.minY, y), maxY: Math.max(box.maxY, y),
  }), { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });
  const width = bounds.maxX - bounds.minX;
  const height = bounds.maxY - bounds.minY;
  return Number.isFinite(width) && Number.isFinite(height) ? { ...bounds, width, height } : null;
}

// Pure display transform. Graphic or millimetric input stays untouched.
export function fitVerticesToPreview(vertices, previewWidth = 560, previewHeight = 300, padding = 40) {
  const box = getBoundingBox(vertices);
  if (!box || ![previewWidth, previewHeight, padding].every(Number.isFinite) || padding < 0) return null;
  const availableWidth = previewWidth - padding * 2;
  const availableHeight = previewHeight - padding * 2;
  if (availableWidth <= 0 || availableHeight <= 0 || (box.width === 0 && box.height === 0)) return null;
  const scale = Math.min(box.width > 0 ? availableWidth / box.width : Infinity,
    box.height > 0 ? availableHeight / box.height : Infinity);
  if (!Number.isFinite(scale) || scale <= 0) return null;
  const width = box.width * scale;
  const height = box.height * scale;
  const x = (previewWidth - width) / 2;
  const y = (previewHeight - height) / 2;
  return {
    points: vertices.map((point) => ({ x: x + (point.x - box.minX) * scale, y: y + (point.y - box.minY) * scale })),
    bounds: { x, y, width, height },
    scale,
  };
}
