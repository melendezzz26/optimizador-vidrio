import { orderWorkState } from './workLabels';
import { useCallback, useEffect, useRef, useState } from 'react';
import { getOrder, listOrderMaterials, listOrders } from '../orders/ordersApi';
import { rasterizePiece, startOptimization } from './optimizationApi';

const PAGE_SIZE = 10;
const NOOP = () => {};

export function useOptimization({ token, onSessionExpired = NOOP }) {
  const [scope, setScope] = useState('PENDIENTE');
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [list, setList] = useState({ items: [], totalPages: 0, loading: true, error: '' });
  const [materials, setMaterials] = useState([]);
  const [materialStatus, setMaterialStatus] = useState('loading');
  const [materialWarning, setMaterialWarning] = useState('');
  const [selection, setSelection] = useState(null);
  const [starting, setStarting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [pieceId, setPieceId] = useState('');
  const [resolution, setResolution] = useState('5');
  const [raster, setRaster] = useState(null);
  const [rasterizing, setRasterizing] = useState(false);
  const [rasterError, setRasterError] = useState('');
  const mounted = useRef(false);
  const startBusy = useRef(false);
  const preparationRequest = useRef({ id: 0, controller: null });
  const detailRequest = useRef({ id: 0, controller: null });
  const rasterRequest = useRef({ id: 0, controller: null, busy: false });

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      detailRequest.current.controller?.abort();
      detailRequest.current.id++;
      rasterRequest.current.controller?.abort();
      rasterRequest.current.id++;
      preparationRequest.current.controller?.abort();
      preparationRequest.current.id++;
    };
  }, []);

  const reportSession = useCallback(error => {
    if (mounted.current && error.status === 401) onSessionExpired();
  }, [onSessionExpired]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    listOrders({ page, limit: PAGE_SIZE, estado: scope }, { token, signal: controller.signal })
      .then(data => {
        if (!active) return;
        const totalPages = data.total_pages ?? 0;
        if (page > Math.max(1, totalPages)) { setPage(Math.max(1, totalPages)); return; }
        setList({ items: data.items ?? [], totalPages, loading: false, error: '' });
      })
      .catch(error => {
        if (!active || error.name === 'AbortError') return;
        reportSession(error);
        setList({ items: [], totalPages: 0, loading: false, error: error.message });
      });
    return () => { active = false; controller.abort(); };
  }, [page, scope, version, token, reportSession]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    listOrderMaterials({ token, signal: controller.signal })
      .then(data => { if (active) { setMaterials(data); setMaterialStatus('ready'); } })
      .catch(error => {
        if (!active || error.name === 'AbortError') return;
        reportSession(error);
        setMaterialStatus('error');
        setMaterialWarning('No se pudo consultar el catálogo de vidrios. Intenta actualizar la vista.');
      });
    return () => { active = false; controller.abort(); };
  }, [token, reportSession]);

  const refresh = () => {
    setList(current => ({ ...current, loading: true, error: '' }));
    setVersion(value => value + 1);
  };
  const invalidateRaster = () => {
    rasterRequest.current.controller?.abort();
    rasterRequest.current = { id: rasterRequest.current.id + 1, controller: null, busy: false };
    setRaster(null);
    setRasterError('');
    setRasterizing(false);
  };
  const resetPiece = () => {
    invalidateRaster();
    setPieceId('');
    setResolution('5');
  };

  async function readDetails(item, { reconcile = false, prepared = false } = {}) {
    detailRequest.current.controller?.abort();
    const controller = new AbortController();
    const id = detailRequest.current.id + 1;
    detailRequest.current = { id, controller };
    if (mounted.current) setSelection(current => ({ ...current, item, loading: true, error: '', blocked: true, reconcile, prepared }));
    try {
      const order = await getOrder(item.id_pedido, { token, signal: controller.signal, timeoutMs: 30000 });
      if (!mounted.current || id !== detailRequest.current.id) return;
      if (order.id_pedido !== item.id_pedido || !Array.isArray(order.piezas)) throw new Error('El detalle recibido no es válido. Actualiza los datos.');
      setSelection({ item, order, loading: false, error: '', blocked: false, reconcile: false,
        prepared: prepared && order.estado === 'PENDIENTE' });
      if (reconcile) setFeedback({ variant: 'info', message: order.estado === 'EN_OPTIMIZACION'
        ? 'El pedido está en optimización. Puedes consultar sus piezas sin cambiar su estado.'
        : order.estado === 'PENDIENTE'
          ? 'El pedido sigue pendiente. Puedes volver a preparar su vista previa.'
          : `El pedido está ${orderWorkState(order.estado)}. No se puede continuar con la vista previa.` });
    } catch (error) {
      if (!mounted.current || id !== detailRequest.current.id || error.name === 'AbortError') return;
      reportSession(error);
      if (reconcile) {
        setSelection(current => ({ ...current, order: null, loading: false, blocked: true, error: error.message, reconcile: true }));
        setFeedback({ variant: 'warning', message: 'No se pudo validar la vista previa ni consultar el pedido. Actualiza el detalle antes de volver a prepararla.' });
      } else {
        setSelection(current => ({ ...current, loading: false, blocked: true, error: error.message }));
      }
    }
  }

  function selectOrder(item) {
    if (startBusy.current) return;
    resetPiece();
    setFeedback(null);
    setSelection({ item, order: null, loading: true, error: '', blocked: true });
    void readDetails(item);
  }

  function changeScope(nextScope) {
    if (startBusy.current) return;
    detailRequest.current.controller?.abort();
    detailRequest.current.id++;
    resetPiece();
    setSelection(null);
    setFeedback(null);
    setList({ items: [], totalPages: 0, loading: true, error: '' });
    setPage(1);
    setScope(nextScope);
  }

  const order = selection?.order;
  const ready = Boolean(order && !selection.loading && !selection.blocked && order.piezas.length);
  const canStart = ready && order.estado === 'PENDIENTE' && !selection.prepared && !starting;
  const canChoosePiece = ready && (order.estado === 'EN_OPTIMIZACION'
    || (order.estado === 'PENDIENTE' && selection.prepared)) && !starting;
  const validResolution = resolution.trim() !== '' && Number.isFinite(Number(resolution)) && Number(resolution) > 0;
  const chosenPiece = order?.piezas.find(piece => String(piece.id_pieza) === pieceId);
  const canRasterize = canChoosePiece && Boolean(chosenPiece) && validResolution && !rasterizing;

  async function start() {
    if (!canStart || startBusy.current) return;
    const item = selection.item;
    const controller = new AbortController();
    const id = preparationRequest.current.id + 1;
    preparationRequest.current = { id, controller };
    const current = () => mounted.current && id === preparationRequest.current.id;
    startBusy.current = true;
    setStarting(true);
    setFeedback(null);
    resetPiece();
    try {
      await startOptimization(item.id_pedido, { token, signal: controller.signal });
      if (!current()) return;
      setFeedback({ variant: 'success', message: `Vista previa del pedido #${item.id_pedido} validada. La preparación no cambia el estado del pedido.` });
      await readDetails(item, { prepared: true });
    } catch (error) {
      if (!current() || error.name === 'AbortError') return;
      reportSession(error);
      const uncertain = error.status === 0 || error.status >= 500 || error.status === 200;
      if (mounted.current) {
        setFeedback({ variant: uncertain ? 'warning' : 'error', message: uncertain
          ? 'No se pudo validar la vista previa. Consultando el pedido; puedes volver a prepararla sin cambiar su estado.'
          : error.status === 409 ? 'El pedido ya no está pendiente. Actualiza sus datos antes de continuar.' : error.message });
        if ([403, 404, 409].includes(error.status)) setSelection(current => ({ ...current, blocked: true }));
        if ([404, 409].includes(error.status)) refresh();
      }
      if (uncertain) {
        await readDetails(item, { reconcile: true });
        if (mounted.current) refresh();
      }
    } finally {
      if (current()) {
        startBusy.current = false;
        setStarting(false);
      }
    }
  }

  async function rasterize(event) {
    event.preventDefault();
    if (!canRasterize || rasterRequest.current.busy) return;
    const controller = new AbortController();
    const id = rasterRequest.current.id + 1;
    rasterRequest.current = { id, controller, busy: true };
    setRaster(null);
    setRasterError('');
    setRasterizing(true);
    try {
      const result = await rasterizePiece({ idPedido: order.id_pedido, idPieza: chosenPiece.id_pieza, resolutionMm: Number(resolution) }, { token, signal: controller.signal });
      if (mounted.current && id === rasterRequest.current.id) setRaster(result);
    } catch (error) {
      if (!mounted.current || id !== rasterRequest.current.id || error.name === 'AbortError') return;
      reportSession(error);
      setRasterError(error.message);
      if ([403, 404, 409].includes(error.status)) setSelection(current => ({ ...current, blocked: true }));
    } finally {
      if (mounted.current && id === rasterRequest.current.id) {
        rasterRequest.current.busy = false;
        setRasterizing(false);
      }
    }
  }

  return {
    scope, page, list, materials, materialStatus, materialWarning, selection, starting, feedback, pieceId, resolution,
    raster, rasterizing, rasterError, canStart, canChoosePiece, canRasterize, validResolution,
    refresh, selectOrder, changeScope, start, rasterize,
    goToPage(next) { setList(current => ({ ...current, loading: true, error: '' })); setPage(next); },
    reloadSelection() { resetPiece(); void readDetails(selection.item, { reconcile: selection.reconcile, prepared: selection.prepared }); },
    changePiece(value) { invalidateRaster(); setPieceId(value); },
    changeResolution(value) { invalidateRaster(); setResolution(value); },
  };
}
