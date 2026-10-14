import { listClients } from '../clients';
import { getPlanchas, getRetazos, getTiposVidrio } from '../inventory';
import { getOrder, listOrders } from '../orders';

function itemsFrom(response) {
  return Array.isArray(response?.items) ? response.items : [];
}

function asDashboardOrder(order, detail, typesById) {
  const pieces = Array.isArray(detail?.piezas) ? detail.piezas : [];
  const glassTypes = [...new Set(pieces.map((piece) => {
    const material = typesById.get(Number(piece.id_tipo_vidrio)) ?? 'Vidrio';
    const thickness = piece.espesor_mm ? ` ${Number(piece.espesor_mm)} mm` : '';
    return `${material}${thickness}`;
  }))];

  return {
    id: order.id_pedido,
    client: order.cliente || 'Consumidor final',
    date: order.fecha_registro,
    status: order.estado,
    pieceCount: pieces.length
      ? pieces.reduce((total, piece) => total + (Number(piece.cantidad) || 0), 0)
      : null,
    glassSummary: glassTypes.length
      ? `${glassTypes.slice(0, 2).join(' · ')}${glassTypes.length > 2 ? ` +${glassTypes.length - 2}` : ''}`
      : null,
  };
}

function fulfilledValue(result) {
  return result.status === 'fulfilled' ? result.value : null;
}

export async function loadDashboardData({ token, canAccessOrders = false, canAccessInventory = false } = {}) {
  const requests = await Promise.allSettled([
    canAccessOrders ? listOrders({ page: 1, limit: 6 }, { token }) : Promise.resolve(null),
    canAccessOrders
      ? listOrders({ page: 1, limit: 100, estado: 'PENDIENTE' }, { token })
      : Promise.resolve(null),
    canAccessInventory ? getPlanchas() : Promise.resolve(null),
    canAccessInventory ? getRetazos() : Promise.resolve(null),
    canAccessInventory ? getTiposVidrio() : Promise.resolve(null),
    canAccessOrders ? listClients({ token }) : Promise.resolve(null),
  ]);
  const [recentResult, pendingResult, sheetsResult, offcutsResult, materialsResult, clientsResult] = requests;
  let unauthorized = requests.some((result) => result.status === 'rejected' && result.reason?.status === 401);
  const inventory = canAccessInventory ? {
    sheets: fulfilledValue(sheetsResult),
    offcuts: fulfilledValue(offcutsResult),
    materials: fulfilledValue(materialsResult),
    sheetError: sheetsResult.status === 'rejected' ? sheetsResult.reason : null,
    offcutError: offcutsResult.status === 'rejected' ? offcutsResult.reason : null,
    materialsError: materialsResult.status === 'rejected' ? materialsResult.reason : null,
  } : null;

  const typesById = new Map((inventory?.materials ?? []).map((material) => (
    [Number(material.id_tipo_vidrio), material.nombre]
  )));
  const orderItems = fulfilledValue(recentResult) ? itemsFrom(recentResult.value) : [];
  const detailResults = await Promise.allSettled(
    canAccessOrders ? orderItems.map((order) => getOrder(order.id_pedido, { token })) : [],
  );
  unauthorized ||= detailResults.some((result) => result.status === 'rejected' && result.reason?.status === 401);

  const recentOrders = orderItems.map((order, index) => {
    const detailResult = detailResults[index];
    return asDashboardOrder(
      order,
      detailResult?.status === 'fulfilled' ? detailResult.value : null,
      typesById,
    );
  });
  const pendingOrders = fulfilledValue(pendingResult) ? itemsFrom(pendingResult.value) : [];
  const clientItems = fulfilledValue(clientsResult);

  return {
    recentOrders,
    totalOrders: fulfilledValue(recentResult)
      ? Number(recentResult.value?.total ?? orderItems.length)
      : null,
    pendingOrders,
    pendingCount: fulfilledValue(pendingResult)
      ? Number(pendingResult.value?.total ?? pendingOrders.length)
      : null,
    inventory,
    clientsCount: Array.isArray(clientItems) ? clientItems.length : null,
    recentError: recentResult.status === 'rejected' ? recentResult.reason : null,
    pendingError: pendingResult.status === 'rejected' ? pendingResult.reason : null,
    clientsError: clientsResult.status === 'rejected' ? clientsResult.reason : null,
    unauthorized,
    recentDetailsPartial: detailResults.some((result) => result.status === 'rejected'),
  };
}
