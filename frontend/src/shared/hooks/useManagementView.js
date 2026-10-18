import { useCallback, useState } from 'react';

const LIST_VIEW = { mode: 'list', item: null };

// Patrón "listado primero, formulario bajo acción" (TA-034 T02).
// El módulo empieza en el listado; Nuevo y Editar abren el formulario;
// Guardar o Cancelar vuelven al listado. El mensaje de resultado se conserva
// en el listado hasta la siguiente acción.
export function useManagementView() {
  const [view, setView] = useState(LIST_VIEW);
  const [feedback, setFeedback] = useState(null);

  const openCreate = useCallback(() => {
    setFeedback(null);
    setView({ mode: 'create', item: null });
  }, []);

  const openEdit = useCallback((item) => {
    setFeedback(null);
    setView({ mode: 'edit', item });
  }, []);

  // nextFeedback: { variant, message } al guardar; sin argumento al cancelar.
  const backToList = useCallback((nextFeedback = null) => {
    setFeedback(nextFeedback);
    setView(LIST_VIEW);
  }, []);

  return {
    mode: view.mode,
    editingItem: view.item,
    isListVisible: view.mode === 'list',
    isFormOpen: view.mode !== 'list',
    feedback,
    setFeedback,
    openCreate,
    openEdit,
    backToList,
  };
}