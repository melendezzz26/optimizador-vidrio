export function getBoundingBox(vertices) {
  if (!Array.isArray(vertices) || vertices.length === 0) {
    return null;
  }

  const xs = vertices.map((vertex) => vertex.x);
  const ys = vertices.map((vertex) => vertex.y);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  return {
    minX,
    maxX,
    minY,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

export function scaleVerticesToDimensions(vertices, widthMm, heightMm) {
  const numericWidth = Number(widthMm);
  const numericHeight = Number(heightMm);

  if (
    !Number.isFinite(numericWidth) ||
    !Number.isFinite(numericHeight) ||
    numericWidth <= 0 ||
    numericHeight <= 0
  ) {
    return null;
  }

  const boundingBox = getBoundingBox(vertices);

  if (
    !boundingBox ||
    boundingBox.width <= 0 ||
    boundingBox.height <= 0
  ) {
    return null;
  }

  return vertices.map((vertex) => ({
    xMm:
      ((vertex.x - boundingBox.minX) / boundingBox.width) *
      numericWidth,
    yMm:
      ((vertex.y - boundingBox.minY) / boundingBox.height) *
      numericHeight,
  }));
}