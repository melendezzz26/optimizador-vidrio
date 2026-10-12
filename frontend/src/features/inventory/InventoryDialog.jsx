import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

export function InventoryDialog({ title, onClose, children, busy = false, className = '' }) {
  const titleId = useId();
  const dialogRef = useRef(null);

  useEffect(() => {
    const previousFocus = document.activeElement;
    const initialFocus = dialogRef.current?.querySelector('[data-initial-focus]')
      ?? dialogRef.current?.querySelector('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])');
    initialFocus?.focus();

    return () => previousFocus?.focus?.();
  }, []);

  useEffect(() => {
    if (!busy) return;
    const activeElement = document.activeElement;
    if (!dialogRef.current?.contains(activeElement) || activeElement.matches?.(':disabled')) {
      dialogRef.current?.focus();
    }
  }, [busy]);

  function handleKeyDown(event) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      if (!busy) onClose();
      return;
    }
    if (event.key !== 'Tab') return;

    const focusable = [...dialogRef.current.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )].filter((element) => !element.hidden && element.getAttribute('aria-hidden') !== 'true');
    if (!focusable.length) {
      event.preventDefault();
      return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div
      className="ng-dialog-backdrop inventory-dialog-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !busy) onClose();
      }}
    >
      <section
        ref={dialogRef}
        className={`ng-dialog inventory-dialog ${className}`.trim()}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-busy={busy || undefined}
        tabIndex="-1"
        onKeyDown={handleKeyDown}
      >
        <header className="inventory-dialog__header">
          <h2 id={titleId} className="ng-dialog__title">{title}</h2>
          <button
            className="ng-button inventory-dialog__close"
            type="button"
            aria-label="Cerrar diálogo"
            onClick={() => { if (!busy) onClose(); }}
            disabled={busy}
          >
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
