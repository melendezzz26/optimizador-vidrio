import { useId, useRef, useState } from 'react';
import { Layers3, LoaderCircle, Save } from 'lucide-react';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import './RegistrarPlanchaForm.css';

function positiveNumber(value) {
  if (typeof value !== 'number' && typeof value !== 'string') return null;
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function activeCatalog(catalogo) {
  const types = new Map();
  for (const type of Array.isArray(catalogo) ? catalogo : []) {
    const id = positiveNumber(type?.id_tipo_vidrio);
    if (!Number.isSafeInteger(id) || type?.estado !== true
      || typeof type.nombre !== 'string' || !type.nombre.trim() || types.has(id)) continue;

    const thicknesses = Array.isArray(type.espesores_mm)
      ? type.espesores_mm.map(positiveNumber).filter((value) => value !== null)
      : [];
    types.set(id, {
      id,
      nombre: type.nombre.trim(),
      espesores: [...new Set(thicknesses)].sort((a, b) => a - b),
    });
  }
  return [...types.values()];
}

/**
 * SPEC-HU-004-registrar-plancha: T01 y T03 (CA-01 a CA-03, CA-07 a CA-11).
 * UI: Documento_Diseno_UI_UX_Accesibilidad_NewGlass_v1_0.
 * catalogo: tipos con id_tipo_vidrio, nombre, estado y espesores_mm.
 * onSubmit(payload): recibe cinco campos numéricos; puede devolver una promesa.
 * El consumidor controla el registro y la confirmación de éxito.
 * isSubmitting: bloquea el formulario durante el procesamiento externo.
 * onCancel: opcional; sin callback, Cancelar permanece deshabilitado.
 * Evidencia visual, teclado y Lighthouse pendientes de la pantalla integrada.
 */
export default function RegistrarPlanchaForm({ catalogo = [], onSubmit, isSubmitting = false, onCancel }) {
  const id = useId();
  const sending = useRef(false);
  const [pending, setPending] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [values, setValues] = useState({
    id_tipo_vidrio: '', espesor_mm: '', ancho_mm: '', alto_mm: '', cantidad: '',
  });

  const types = activeCatalog(catalogo);
  const selectedType = types.find((type) => type.id === Number(values.id_tipo_vidrio));
  const thicknesses = selectedType?.espesores ?? [];
  const thicknessHelpId = !selectedType || thicknesses.length === 0
    ? `${id}-espesor_mm-help` : undefined;
  const busy = isSubmitting || pending;
  const payload = Object.fromEntries(
    Object.entries(values).map(([field, value]) => [field, Number(value)]),
  );
  const errors = {};

  if (!values.id_tipo_vidrio) errors.id_tipo_vidrio = 'Selecciona un tipo de vidrio.';
  else if (!selectedType) errors.id_tipo_vidrio = 'Selecciona un tipo de vidrio activo disponible.';

  if (!values.espesor_mm) errors.espesor_mm = 'Selecciona un espesor.';
  else if (!thicknesses.includes(payload.espesor_mm)) {
    errors.espesor_mm = 'El espesor no es compatible con el tipo seleccionado.';
  }

  for (const [field, label] of [['ancho_mm', 'el ancho'], ['alto_mm', 'el alto'], ['cantidad', 'la cantidad']]) {
    if (!values[field].trim()) errors[field] = `Completa ${label}.`;
    else if (positiveNumber(values[field]) === null) errors[field] = 'Ingresa un número mayor que cero.';
  }
  if (!errors.cantidad && !Number.isSafeInteger(payload.cantidad)) {
    errors.cantidad = 'Ingresa una cantidad entera mayor que cero.';
  }

  function change(field, value) {
    setValues((previous) => ({
      ...previous,
      [field]: value,
      ...(field === 'id_tipo_vidrio' ? { espesor_mm: '' } : {}),
    }));
    setSubmitError('');
  }

  function fieldProps(field, helperId) {
    return {
      id: `${id}-${field}`,
      name: field,
      required: true,
      'aria-invalid': attempted && Boolean(errors[field]),
      'aria-describedby': [
        helperId,
        attempted && errors[field] ? `${id}-${field}-error` : undefined,
      ].filter(Boolean).join(' ') || undefined,
    };
  }

  function errorMessage(field) {
    return attempted && errors[field] ? (
      <p className="plancha-form__error" id={`${id}-${field}-error`}>
        {errors[field]}
      </p>
    ) : null;
  }

  async function submit(event) {
    event.preventDefault();
    if (busy || sending.current) return;
    setAttempted(true);
    setSubmitError('');
    if (Object.keys(errors).length > 0) {
      // Un selector puede estar deshabilitado si el catálogo no está disponible.
      const firstField = Object.keys(errors).find((field) => {
        const control = event.currentTarget.elements.namedItem(field);
        return control && !control.disabled;
      });
      if (firstField) event.currentTarget.elements.namedItem(firstField).focus();
      return;
    }

    sending.current = true;
    setPending(true);
    try {
      await onSubmit(payload);
    } catch {
      setSubmitError('No se pudo completar el registro. Revisa los datos e inténtalo nuevamente.');
    } finally {
      sending.current = false;
      setPending(false);
    }
  }

  return (
    <PageCard as="form" className="plancha-form" onSubmit={submit} noValidate aria-busy={busy}
      aria-labelledby={`${id}-title`}>
      <PageHeader context="Gestión de inventario" title="Registrar plancha comercial"
        titleId={`${id}-title`} icon={Layers3}
        description="Ingresa el material, las dimensiones y la cantidad de planchas que deseas registrar.">
        <p className="plancha-form__required">Todos los campos son obligatorios (*).</p>
      </PageHeader>

      {types.length === 0 && (
        <p className="plancha-form__notice" role="status">
          No hay tipos de vidrio activos disponibles. El registro estará disponible cuando haya catálogo.
        </p>
      )}

      <fieldset className="ng-form-section" disabled={busy}>
        <legend>Datos de la plancha</legend>
        <div className="ng-field-grid">
          <div className="ng-field">
            <label htmlFor={`${id}-id_tipo_vidrio`}>Tipo de vidrio *</label>
            <select className="ng-control" {...fieldProps('id_tipo_vidrio')} value={selectedType ? values.id_tipo_vidrio : ''}
              onChange={(event) => change('id_tipo_vidrio', event.target.value)} disabled={types.length === 0}>
              <option value="">Seleccionar tipo</option>
              {types.map((type) => <option key={type.id} value={type.id}>{type.nombre}</option>)}
            </select>
            {errorMessage('id_tipo_vidrio')}
          </div>

          <div className="ng-field">
            <label htmlFor={`${id}-espesor_mm`}>Espesor (mm) *</label>
            <select className="ng-control" {...fieldProps('espesor_mm', thicknessHelpId)}
              value={thicknesses.includes(payload.espesor_mm) ? values.espesor_mm : ''}
              onChange={(event) => change('espesor_mm', event.target.value)}
              disabled={!selectedType || thicknesses.length === 0}>
              <option value="">Seleccionar espesor</option>
              {thicknesses.map((value) => <option key={value} value={value}>{value} mm</option>)}
            </select>
            {!selectedType && (
              <p className="plancha-form__hint" id={thicknessHelpId}>Selecciona primero un tipo de vidrio.</p>
            )}
            {selectedType && thicknesses.length === 0 && (
              <p className="plancha-form__hint" id={thicknessHelpId}>
                Este tipo no tiene espesores disponibles. Selecciona otro tipo.
              </p>
            )}
            {errorMessage('espesor_mm')}
          </div>

          {[
            ['ancho_mm', 'Ancho (mm)', 'any'],
            ['alto_mm', 'Alto (mm)', 'any'],
            ['cantidad', 'Cantidad', '1'],
          ].map(([field, label, step]) => (
            <div className="ng-field" key={field}>
              <label htmlFor={`${id}-${field}`}>{label} *</label>
              <input className="ng-control" {...fieldProps(field)} type="number" step={step}
                min={field === 'cantidad' ? '1' : '0'}
                inputMode={field === 'cantidad' ? 'numeric' : 'decimal'}
                value={values[field]} onChange={(event) => change(field, event.target.value)} />
              {errorMessage(field)}
            </div>
          ))}
        </div>
      </fieldset>

      {attempted && Object.keys(errors).length > 0 && (
        <p className="plancha-form__error" role="alert">Revisa los campos indicados antes de registrar.</p>
      )}
      {submitError && <p className="plancha-form__error" role="alert">{submitError}</p>}
      {!onCancel && (
        <p className="plancha-form__hint plancha-form__cancel-hint" id={`${id}-cancel-help`}>
          Cancelar no está disponible en esta vista.
        </p>
      )}
      <ActionBar>
        <button className="ng-button" type="button" onClick={onCancel}
          disabled={busy || !onCancel} aria-describedby={!onCancel ? `${id}-cancel-help` : undefined}>
          Cancelar
        </button>
        <button className="ng-button ng-button--primary" type="submit"
          aria-busy={busy} disabled={busy || types.length === 0}>
          {busy ? <LoaderCircle className="ng-loading-icon" size={18} aria-hidden="true" />
            : <Save size={18} aria-hidden="true" />}
          {busy ? 'Registrando...' : 'Registrar plancha'}
        </button>
      </ActionBar>
    </PageCard>
  );
}
