import { renderNumber } from './runContract.js';
import { getGeometryBounds } from './visualizationGeometry.js';
import { containerKey, placementKey } from './optimizationModel.js';

export const DEFAULT_YAW = -24;
export const clampYaw = value => Math.max(-180, Math.min(180, Number.isFinite(value) ? value : DEFAULT_YAW));
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
  if (!bounds) return [];
  let x, y;
  try { x = renderNumber(placement.x_mm); y = renderNumber(placement.y_mm); renderNumber(placement.rotation_deg); } catch { return []; }
  let points;
  if (geometry.type === 'RECTANGULO') points = [[0, 0], [bounds.width, 0], [bounds.width, bounds.height], [0, bounds.height]];
  else if (geometry.type === 'CIRCUNFERENCIA') points = Array.from({ length: 96 }, (_, i) => {
    const angle = i * Math.PI * 2 / 96;
    return [Math.cos(angle) * geometry.radius_mm, Math.sin(angle) * geometry.radius_mm];
  });
  else points = geometry.vertices_mm;
  return points.map(([px, py]) => [x + px - bounds.minX, y + py - bounds.minY]);
}

export function createPlacementScene(snapshot, container, placements) {
  const width = container.material_width_mm, height = container.material_height_mm;
  if (![width, height].every(n => Number.isFinite(n) && n > 0)) return null;
  const outline = placedOutline(container.geometry);
  if (!outline.length) return null;
  const pieces = placements.filter(p => containerKey(p) === containerKey(container)).flatMap(placement => {
    const points = placedOutline(placement.geometria, placement);
    if (!points.length) return [];
    const key = placementKey(placement);
    const [color, edge] = placementColors(snapshot, placement);
    return [{ key, placement, points, color, edge, label: `#${placement.id_pieza} · ${placement.unit_index}` }];
  });
  const target = Math.max(width, height) / 12;
  const power = 10 ** Math.floor(Math.log10(target));
  const gridStep = [1, 2, 5, 10].find(n => n * power >= target) * power;
  const scene = { width, height, outline, pieces, gridStep };
  return { ...scene, viewBox: sceneViewBox(scene) };
}

// Physical glass uses XY. Z is display thickness only; the orbit camera
// has azimuth, elevation (camera Z), perspective distance and screen pan.
export function projectPoint([xMm, yMm], elevation, scene, yaw, camera = {}) {
  const scale = 1000 / Math.max(scene.width, scene.height);
  const x = (xMm - scene.width / 2) * scale, y = (yMm - scene.height / 2) * scale;
  const angle = radians(clampYaw(yaw));
  const worldX = x * Math.cos(angle) + y * Math.sin(angle);
  const worldY = -x * Math.sin(angle) + y * Math.cos(angle);
  const pitch = radians(camera.elevation ?? 48);
  const depth = worldY * Math.cos(pitch) + elevation * Math.sin(pitch);
  const perspective = 2400 / Math.max(600, 2400 - depth);
  return { x: worldX * perspective + (camera.panX ?? 0), y: (worldY * Math.sin(pitch) - elevation * Math.cos(pitch)) * perspective + (camera.panY ?? 0), depth };
}

export function projectedPath(points, elevation, scene, yaw, camera = {}) {
  return points.map((point, i) => {
    const p = projectPoint(point, elevation, scene, yaw, camera);
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
  for (let yaw = -180; yaw <= 180; yaw += 10) for (const corner of corners) for (const elevation of [-22, 25]) for (const pitch of [5, 48, 90]) {
    const point = projectPoint(corner, elevation, scene, yaw, { elevation: pitch });
    halfWidth = Math.max(halfWidth, Math.abs(point.x) + 50);
    halfHeight = Math.max(halfHeight, Math.abs(point.y) + 50);
  }
  return [-halfWidth, -halfHeight, halfWidth * 2, halfHeight * 2];
}

export function extrudedSides(points, bottom, top, scene, yaw, camera = {}) {
  return points.map((point, index) => {
    const next = points[(index + 1) % points.length];
    const corners = [projectPoint(point, top, scene, yaw, camera), projectPoint(next, top, scene, yaw, camera),
      projectPoint(next, bottom, scene, yaw, camera), projectPoint(point, bottom, scene, yaw, camera)];
    return { key: index, depth: corners.reduce((n, p) => n + p.depth, 0) / 4,
      path: corners.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(3)},${p.y.toFixed(3)}`).join(' ') + ' Z' };
  }).sort((a, b) => a.depth - b.depth);
}
