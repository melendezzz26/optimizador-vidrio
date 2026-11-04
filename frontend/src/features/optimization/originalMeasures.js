// TA-046 T02: medidas originales de una pieza, tal como se ingresaron en el pedido (SPEC-TA-046 RN-08).
// Función pura: lee la geometría guardada y la describe en mm, sin depender de React.
import { decimalKey } from './runContract.js';

export const SHAPE_NAMES = {
  RECTANGULO: 'Rectángulo',
  CIRCUNFERENCIA: 'Círculo',
  POLIGONO_CONVEXO: 'Polígono convexo',
};

// Redondeo a 0,1 mm; sin ceros innecesarios (138.56 -> "138.6", 300 -> "300").
export const formatMm = value => String(Math.round(Number(value) * 10) / 10);

// Las medidas originales conservan todos sus decimales; solo se eliminan ceros redundantes.
export const formatOriginalMm = value => decimalKey(value);

export function polygonSides(vertices) {
  return vertices.map(([x, y], index) => {
    const [nextX, nextY] = vertices[(index + 1) % vertices.length];
    return Math.hypot(nextX - x, nextY - y);
  });
}

export function describeOriginalMeasures(piece) {
  const geometry = piece?.geometria ?? {};
  const shape = piece?.tipo_forma ?? geometry.type;
  if (shape === 'RECTANGULO') return `${formatOriginalMm(geometry.width_mm)} × ${formatOriginalMm(geometry.height_mm)} mm`;
  if (shape === 'CIRCUNFERENCIA') return `Radio ${formatOriginalMm(geometry.radius_mm)} mm`;
  if (shape === 'POLIGONO_CONVEXO' && Array.isArray(geometry.vertices_mm) && geometry.vertices_mm.length >= 3) {
    const sides = polygonSides(geometry.vertices_mm).map(formatMm);
    return `${sides.length} lados: ${sides.join(' · ')} mm`;
  }
  return 'Medidas no disponibles';
}
