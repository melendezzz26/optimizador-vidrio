import { LoaderCircle } from 'lucide-react';
import { useEffect, useId, useRef } from 'react';
import '../ui.css';
import './feedback.css';

export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel = 'Cancelar',
  onConfirm,
  onCancel,
  isConfirming = false,
}) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef(null);
  const cancelRef = useRef(null);

  // Al abrir, el foco va a Cancelar; al cerrar, vuelve al botón que abrió el diálogo.
  useEffect(() => {
    if (!open) return undefined;
    const previousFocus = document.activeElement;
    cancelRef.current?.focus();
    return () => previousFocus?.focus?.();
  }, [open]);

  if (!open) return null;

  function handleKeyDown(event) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      if (!isConfirming) onCancel();
      return;
    }
    if (event.key !== 'Tab') return;
    // Mantiene el foco dentro del diálogo mientras está abierto.
    const buttons = [...dialogRef.current.querySelectorAll('button:not([disabled])')];
    if (buttons.length === 0) {
      event.preventDefault();
      return;
    }
    const first = buttons[0];
    const last = buttons[buttons.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="ng-dialog-backdrop">
      <div
        ref={dialogRef}
        className="ng-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        onKeyDown={handleKeyDown}
      >
        <h2 id={titleId} className="ng-dialog__title">{title}</h2>
        <div id={descriptionId} className="ng-dialog__description">{children}</div>
        <div className="ng-dialog__actions">
          <button ref={cancelRef} type="button" className="ng-button" onClick={onCancel} disabled={isConfirming}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className="ng-button ng-button--danger"
            onClick={onConfirm}
            disabled={isConfirming}
            aria-busy={isConfirming || undefined}
          >
            {isConfirming && <LoaderCircle className="ng-loading-icon" size={18} aria-hidden="true" />}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}