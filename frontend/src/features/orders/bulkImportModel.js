// HU-018: lógica pura de la importación masiva (SPEC-HU-018 §6 y §8).
// Sin React ni llamadas a la API: el backend interpreta las filas y aquí solo se
// decide qué mostrar y cómo pasan las piezas válidas al formulario.

export const SHAPE_LABELS = {
  RECTANGULO: 'Rectángulo',
  CIRCUNFERENCIA: 'Círculo',
  POLIGONO_CONVEXO: 'Polígono convexo',
};

const mm = value => `${Number(value)} mm`;

export function describeMeasures(row) {
  const measures = row?.medidas;
  if (!measures) return '—';
  if (row.tipo_forma === 'RECTANGULO') return `${Number(measures.width_mm)} × ${mm(measures.height_mm)}`;
  if (row.tipo_forma === 'CIRCUNFERENCIA') return `Radio ${mm(measures.radius_mm)}`;
  return `${measures.vertices_mm.length} lados`;
}

export function blockingReason(preview, material) {
  if (!preview?.filas?.length) return 'Carga un archivo con piezas.';
  const observed = preview.filas.filter(row => row.estado !== 'VALIDO').length;
  if (observed) return `Corrige ${observed} ${observed === 1 ? 'fila observada' : 'filas observadas'} para continuar.`;
  if (!material?.tipo_vidrio_id || !material?.espesor) return 'Elige el tipo de vidrio y el espesor.';
  return '';
}

export const canAddToOrder = (preview, material) => blockingReason(preview, material) === '';

export function rowsToPieces(rows) {
  return rows.map(row => ({
    tipo_forma: row.tipo_forma,
    cantidad: row.cantidad,
    dimensiones: row.tipo_forma === 'POLIGONO_CONVEXO'
      ? { vertices: row.medidas.vertices_mm.map(([x, y]) => [x, y]) }
      : { ...row.medidas },
  }));
}

// Todas las filas viajan otra vez, con su número original (SPEC §7.2).
export function revalidationBody(preview, drafts = {}) {
  return {
    archivo: preview.archivo,
    filas: preview.filas.map(row => ({ fila: row.fila, texto: drafts[row.fila] ?? row.texto })),
  };
}

const blankPiece = piece => Object.values(piece.dimensiones ?? {}).every(value =>
  value === '' || value === null || value === undefined || (Array.isArray(value) && !value.length));

// Un grupo sin material ni medidas es el borrador inicial del formulario: no se conserva.
export const isBlankGroup = group => !group.tipo_vidrio_id && !group.espesor && group.piezas.every(blankPiece);

export function addImportedPieces(groups, material, pieces, newGroupId) {
  const sameMaterial = group => String(group.tipo_vidrio_id) === String(material.tipo_vidrio_id)
    && Number(group.espesor) === Number(material.espesor);
  const kept = groups.filter(group => !isBlankGroup(group));
  if (kept.some(sameMaterial)) {
    return kept.map(group => (sameMaterial(group) ? { ...group, piezas: [...group.piezas, ...pieces] } : group));
  }
  return [...kept, {
    id: newGroupId, tipo_vidrio_id: String(material.tipo_vidrio_id), espesor: String(material.espesor), piezas: pieces,
  }];
}