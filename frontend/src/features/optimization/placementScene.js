import { getGeometryBounds } from './visualizationGeometry.js';
import { containerKey, placementKey } from './optimizationModel.js';

export const DEFAULT_YAW = -24;
export const clampYaw = value => Math.max(-90, Math.min(90, Number.isFinite(value) ? value : DEFAULT_YAW));
const radians = degrees => degrees * Math.PI / 180;
const COLORS = [
  ['#a8c9f8', '#285da8'], ['#9bd9cf', '#176f66'], ['#c8bbef', '#665099'],
  ['#f2cf8e', '#91651d'], ['#e9b5ca', '#91466a'], ['#99d4e7', '#296e86'],
];
export function placementColors(snapshot, placement) {
  const index = Math.max(0, snapshot.groups.flatMap(g => g.units ?? []).findIndex(unit => placementKey(unit) === placementKey(placement)));
  return COLORS[index % COLORS.length];
}

// The same normalized local pivot used by the precise 2D SVG. Circle tessellation
// is display-only; canonical geometry and the backend raster are never changed.
export function placedOutline(geometry, placement = { x_mm: 0, y_mm: 0, rotation_deg: 0 }) {
  const bounds = getGeometryBounds(geometry);
  if (!bounds || ![placement.x_mm, placement.y_mm, placement.rotation_deg].every(Number.isFinite)) return [];
  let points;
  if (geometry.type === 'RECTANGULO') points = [[0, 0], [bounds.width, 0], [bounds.width, bounds.height], [0, bounds.height]];
  else if (geometry.type === 'CIRCUNFERENCIA') points = Array.from({ length: 96 }, (_, i) => {
    const angle = i * Math.PI * 2 / 96;
    return [Math.cos(angle) * geometry.radius_mm, Math.sin(angle) * geometry.radius_mm];
  });
  else points = geometry.vertices_mm;
  const cosine = Math.cos(radians(placement.rotation_deg)), sine = Math.sin(radians(placement.rotation_deg));
  return points.map(([x, y]) => {
    const localX = x - bounds.minX, localY = y - bounds.minY;
    return [placement.x_mm + localX * cosine - localY * sine, placement.y_mm + localX * sine + localY * cosine];
  });
}

export function createPlacementScene(snapshot, container, placements) {
  const width = container.material_width_mm, height = container.material_height_mm;
  if (![width, height].every(n => Number.isFinite(n) && n > 0)) return null;
  const outline = placedOutline(container.geometry);
  if (!outline.length) return null;
  const pieces = placements.filter(p => containerKey(p) === containerKey(container)).flatMap(placement => {
    const piece = snapshot.orders.find(o => o.id_pedido === placement.id_pedido)?.piezas.find(p => p.id_pieza === placement.id_pieza);
    const points = placedOutline(piece?.geometria, placement);
    if (!points.length) return [];
    const key = placementKey(placement);
    const [color, edge] = placementColors(snapshot, placement);
    return [{ key, placement, points, color, edge, label: `#${placement.id_pieza} · ${placement.unit_index + 1}` }];
  });
  const target = Math.max(width, height) / 12;
  const power = 10 ** Math.floor(Math.log10(target));
  const gridStep = [1, 2, 5, 10].find(n => n * power >= target) * power;
  const scene = { width, height, outline, pieces, gridStep };
  return { ...scene, viewBox: sceneViewBox(scene) };
}

// Ground plane X/Z derives from x_mm/y_mm. Y is illustrative elevation only.
// Camera pitch/distance are fixed; yaw is the sole user-controlled rotation.
export function projectPoint([xMm, yMm], elevation, scene, yaw) {
  const scale = 1000 / Math.max(scene.width, scene.height);
  const x = (xMm - scene.width / 2) * scale, z = (yMm - scene.height / 2) * scale;
  const angle = radians(clampYaw(yaw));
  const worldX = x * Math.cos(angle) + z * Math.sin(angle);
  const worldZ = -x * Math.sin(angle) + z * Math.cos(angle);
  const pitch = radians(48);
  const depth = worldZ * Math.cos(pitch) + elevation * Math.sin(pitch);
  const perspective = 2400 / (2400 - depth);
  return { x: worldX * perspective, y: (worldZ * Math.sin(pitch) - elevation * Math.cos(pitch)) * perspective, depth };
}

export function projectedPath(points, elevation, scene, yaw) {
  return points.map((point, i) => {
    const p = projectPoint(point, elevation, scene, yaw);
    return `${i ? 'L' : 'M'}${p.x.toFixed(3)},${p.y.toFixed(3)}`;
  }).join(' ') + ' Z';
}

// A stable frame across all allowed camera angles prevents zooming during drag.
// Include dimension guides, elevations and generous label/shadow padding.
export function sceneViewBox(scene) {
  const margin = scene.gridStep / 2;
  const corners = [[-margin, -margin], [scene.width + margin, -margin],
    [scene.width + margin, scene.height + margin], [-margin, scene.height + margin]];
  let halfWidth = 820, halfHeight = 620;
  for (let yaw = -90; yaw <= 90; yaw += 5) for (const corner of corners) for (const elevation of [-22, 25]) {
    const point = projectPoint(corner, elevation, scene, yaw);
    halfWidth = Math.max(halfWidth, Math.abs(point.x) + 50);
    halfHeight = Math.max(halfHeight, Math.abs(point.y) + 50);
  }
  return [-halfWidth, -halfHeight, halfWidth * 2, halfHeight * 2];
}

export function extrudedSides(points, bottom, top, scene, yaw) {
  return points.map((point, index) => {
    const next = points[(index + 1) % points.length];
    const corners = [projectPoint(point, top, scene, yaw), projectPoint(next, top, scene, yaw),
      projectPoint(next, bottom, scene, yaw), projectPoint(point, bottom, scene, yaw)];
    return { key: index, depth: corners.reduce((n, p) => n + p.depth, 0) / 4,
      path: corners.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(3)},${p.y.toFixed(3)}`).join(' ') + ' Z' };
  }).sort((a, b) => a.depth - b.depth);
}
