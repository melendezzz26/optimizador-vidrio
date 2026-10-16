// Preview only. Backend remains authoritative for feasibility and final grouping.
export function materialKey(piece) {
  const thickness = Number(piece.espesor_mm);
  return piece.id_tipo_vidrio != null && Number.isFinite(thickness) && thickness > 0
    ? `${piece.id_tipo_vidrio}:${thickness}` : null;
}

export function detectMaterialGroups(orders, resolveMaterial = () => null) {
  const groups = new Map();
  const unresolved = [];
  for (const order of orders) {
    if (!order.piezas?.length) unresolved.push(order.id_pedido);
    for (const piece of order.piezas ?? []) {
      const id = materialKey(piece);
      if (!id || !Number.isInteger(piece.cantidad) || piece.cantidad <= 0) { unresolved.push(order.id_pedido); continue; }
      if (!groups.has(id)) {
        const material = resolveMaterial(id);
        groups.set(id, { id, materialId: piece.id_tipo_vidrio,
          name: material?.name ?? piece.material_name ?? `Material #${piece.id_tipo_vidrio}`,
          thickness: Number(piece.espesor_mm), orders: [], units: [], containers: material?.containers ?? [] });
      }
      const group = groups.get(id);
      if (!group.orders.includes(order.id_pedido)) group.orders.push(order.id_pedido);
      for (let unit_index = 0; unit_index < piece.cantidad; unit_index++) group.units.push({ id_pedido: order.id_pedido, id_pieza: piece.id_pieza, unit_index });
    }
  }
  return { groups: [...groups.values()], unresolved: [...new Set(unresolved)] };
}

export function placementMatchesGroup(snapshot, placement) {
  const group = snapshot.groups.find(g => g.id === placement.group_id);
  const piece = snapshot.orders.find(o => o.id_pedido === placement.id_pedido)?.piezas?.find(p => p.id_pieza === placement.id_pieza);
  const container = group?.containers.find(c => c.material_source === placement.material_source && c.material_id === placement.material_id);
  return Boolean(piece && group && container && materialKey(piece) === group.id
    && Number(container.espesor_mm) === Number(piece.espesor_mm)
    && (container.id_tipo_vidrio == null || String(container.id_tipo_vidrio) === String(piece.id_tipo_vidrio))
    && !snapshot.groups.some(g => g.id !== group.id && g.containers.some(c => c.material_source === container.material_source && c.material_id === container.material_id))
    && group.units.some(u => u.id_pedido === placement.id_pedido && u.id_pieza === placement.id_pieza && u.unit_index === placement.unit_index));
}
