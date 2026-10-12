import { useId, useState } from 'react';
import { FeedbackMessage } from '../../shared/components/feedback';
import { InventoryDialog } from './InventoryDialog';

const WRITE_OFF_EVENTS = [
  { value: 'BAJA_ROTURA', label: 'Rotura' },
  { value: 'BAJA_MERMA', label: 'Merma' },
  { value: 'BAJA_ERROR_REGISTRO', label: 'Error de registro' },
  { value: 'BAJA_RETIRO', label: 'Retiro' },
];

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number)
    ? new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 }).format(number)
    : '—';
}

function geometryDescription(geometry) {
  if (geometry?.type === 'RECTANGULO') {
    return `Rectángulo · ${formatNumber(geometry.width_mm)} × ${formatNumber(geometry.height_mm)} mm`;
  }
  if (geometry?.type === 'CIRCUNFERENCIA') {
    return `Circunferencia · radio ${formatNumber(geometry.radius_mm)} mm`;
  }
  if (geometry?.type === 'POLIGONO_CONVEXO') {
    return `Polígono convexo · ${geometry.vertices_mm?.length ?? 0} vértices`;
  }
  return 'Geometría no disponible';
}

function resourceDescription(resource, kind, typesById) {
  const typeName = typesById.get(Number(resource.id_tipo_vidrio)) ?? `Tipo de vidrio #${resource.id_tipo_vidrio}`;
  if (kind === 'plancha') {
    return `${typeName} · ${formatNumber(resource.espesor_mm)} mm · ${formatNumber(resource.ancho_mm)} × ${formatNumber(resource.alto_mm)} mm · cantidad ${formatNumber(resource.cantidad)}`;
  }
  return `${resource.codigo} · ${typeName} · ${formatNumber(resource.espesor_mm)} mm · ${geometryDescription(resource.geometria)}`;
}

export function WriteoffDialog({
  resource, kind, typesById, error, isSubmitting, onClose, onSubmit,
}) {
  const fieldId = useId();
  const [step, setStep] = useState('form');
  const [eventType, setEventType] = useState(WRITE_OFF_EVENTS[0].value);
  const [reason, setReason] = useState('');
  const [observation, setObservation] = useState('');
  const [validationError, setValidationError] = useState('');
  const resourceId = kind === 'plancha' ? resource.id_plancha : resource.id_retazo;
  const resourceKind = kind === 'plancha' ? 'plancha' : 'retazo';
  const selectedEvent = WRITE_OFF_EVENTS.find((item) => item.value === eventType);

  function continueToConfirmation(event) {
    event.preventDefault();
    if (!reason.trim()) {
      setValidationError('El motivo es obligatorio.');
      return;
    }
    setValidationError('');
    setStep('confirm');
  }

  function confirmWriteoff() {
    onSubmit({
      tipo_evento: eventType,
      motivo: reason.trim(),
      observacion: observation.trim() || null,
    });
  }

  return (
    <InventoryDialog
      title={step === 'form' ? `Dar de baja ${resourceKind}` : 'Confirmar baja manual'}
      onClose={onClose}
      busy={isSubmitting}
      className="inventory-dialog--writeoff"
    >
      {step === 'form' ? (
        <form className="inventory-dialog__body" onSubmit={continueToConfirmation}>
          <p className="inventory-dialog__resource">{resourceDescription(resource, kind, typesById)}</p>
          <div className="ng-field">
            <label htmlFor={`${fieldId}-event`}>Tipo de baja</label>
            <select
              id={`${fieldId}-event`}
              className="ng-control"
              value={eventType}
              onChange={(event) => setEventType(event.target.value)}
              disabled={isSubmitting}
              data-initial-focus
            >
              {WRITE_OFF_EVENTS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
          <div className="ng-field">
            <label htmlFor={`${fieldId}-reason`}>Motivo <span aria-hidden="true">*</span></label>
            <textarea
              id={`${fieldId}-reason`}
              className="ng-control inventory-dialog__textarea"
              value={reason}
              onChange={(event) => {
                setReason(event.target.value);
                if (validationError) setValidationError('');
              }}
              required
              aria-invalid={Boolean(validationError) || undefined}
              aria-describedby={validationError ? `${fieldId}-validation` : undefined}
              disabled={isSubmitting}
            />
            {validationError && (
              <p className="inventory-dialog__field-error" id={`${fieldId}-validation`} role="alert">
                {validationError}
              </p>
            )}
          </div>
          <div className="ng-field">
            <label htmlFor={`${fieldId}-observation`}>Observación (opcional)</label>
            <textarea
              id={`${fieldId}-observation`}
              className="ng-control inventory-dialog__textarea"
              value={observation}
              onChange={(event) => setObservation(event.target.value)}
              disabled={isSubmitting}
            />
          </div>
          {error && <FeedbackMessage variant="error" title="No se pudo registrar la baja">{error}</FeedbackMessage>}
          <div className="ng-action-bar">
            <button className="ng-button" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancelar
            </button>
            <button className="ng-button ng-button--primary" type="submit" disabled={isSubmitting}>
              Revisar baja
            </button>
          </div>
        </form>
      ) : (
        <div className="inventory-dialog__body">
          <p>Revisa los datos antes de guardar el movimiento.</p>
          <dl className="inventory-writeoff-summary">
            <div><dt>Material</dt><dd>{resourceDescription(resource, kind, typesById)}</dd></div>
            <div><dt>Identificador</dt><dd>#{resourceId}</dd></div>
            <div><dt>Tipo de baja</dt><dd>{selectedEvent?.label}</dd></div>
            <div><dt>Motivo</dt><dd>{reason.trim()}</dd></div>
            {observation.trim() && <div><dt>Observación</dt><dd>{observation.trim()}</dd></div>}
            <div><dt>Efecto</dt><dd>Se registrará en el historial y el material quedará inactivo. No se eliminará.</dd></div>
          </dl>
          {error && <FeedbackMessage variant="error" title="No se pudo registrar la baja">{error}</FeedbackMessage>}
          <div className="ng-action-bar">
            <button
              className="ng-button"
              type="button"
              onClick={() => setStep('form')}
              disabled={isSubmitting}
            >
              Volver
            </button>
            <button className="ng-button" type="button" onClick={onClose} disabled={isSubmitting}>
              Cancelar
            </button>
            <button
              className="ng-button ng-button--danger"
              type="button"
              onClick={confirmWriteoff}
              disabled={isSubmitting}
              aria-busy={isSubmitting || undefined}
            >
              {isSubmitting ? 'Registrando…' : 'Confirmar baja'}
            </button>
          </div>
        </div>
      )}
    </InventoryDialog>
  );
}
