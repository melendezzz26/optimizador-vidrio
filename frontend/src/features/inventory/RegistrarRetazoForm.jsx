import { useId, useRef, useState } from 'react';
import { Layers3, LoaderCircle, Plus, Save, Trash2 } from 'lucide-react';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import './RegistrarRetazoForm.css';

const SHAPES = [
  { value: 'RECTANGULO', label: 'Rectángulo' },
  { value: 'CIRCUNFERENCIA', label: 'Circunferencia' },
  { value: 'POLIGONO_CONVEXO', label: 'Polígono convexo' },
];

const MIN_VERTICES = 3;

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
      ? type.espesores_mm.map(positiveNumber).filter((v) => v !== null)
      : [];
    types.set(id, {
      id,
      nombre: type.nombre.trim(),
      espesores: [...new Set(thicknesses)].sort((a, b) => a - b),
    });
  }
  return [...types.values()];
}

function emptyVertex() {
  return { x: '', y: '' };
}

function initialVertices() {
  return [emptyVertex(), emptyVertex(), emptyVertex()];
}

function initialGeometryValues(geometria) {
  if (!geometria) return { forma: '', width_mm: '', height_mm: '', radius_mm: '', vertices: initialVertices() };
  if (geometria.type === 'RECTANGULO') {
    return {
      forma: 'RECTANGULO',
      width_mm: String(geometria.width_mm),
      height_mm: String(geometria.height_mm),
      radius_mm: '',
      vertices: initialVertices(),
    };
  }
  if (geometria.type === 'CIRCUNFERENCIA') {
    return {
      forma: 'CIRCUNFERENCIA',
      width_mm: '',
      height_mm: '',
      radius_mm: String(geometria.radius_mm),
      vertices: initialVertices(),
    };
  }
  if (geometria.type === 'POLIGONO_CONVEXO') {
    return {
      forma: 'POLIGONO_CONVEXO',
      width_mm: '',
      height_mm: '',
      radius_mm: '',
      vertices: geometria.vertices_mm.map(([x, y]) => ({ x: String(x), y: String(y) })),
    };
  }
  return { forma: '', width_mm: '', height_mm: '', radius_mm: '', vertices: initialVertices() };
}

/**
 * SPEC-HU-005-registrar-retazo: T01.
 * Formulario desacoplado de HTTP para registrar un retazo reutilizable.
 * catalogo: tipos con id_tipo_vidrio, nombre, estado y espesores_mm.
 * onSubmit(payload): recibe el payload de creación; puede devolver una promesa.
 * isSubmitting: bloquea el formulario durante el procesamiento externo.
 * onCancel: opcional; sin callback, Cancelar permanece deshabilitado.
 */
export default function RegistrarRetazoForm({
  catalogo = [],
  mode = 'create',
  initialValues = null,
  onSubmit,
  isSubmitting = false,
  onCancel,
}) {
  const id = useId();
  const isEdit = mode === 'edit';
  const sending = useRef(false);
  const [pending, setPending] = useState(false);
  const [attempted, setAttempted] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const initialGeometry = initialGeometryValues(initialValues?.geometria);
  const [values, setValues] = useState(() => ({
    codigo: isEdit && initialValues ? String(initialValues.codigo ?? '') : '',
    id_tipo_vidrio: isEdit && initialValues ? String(initialValues.id_tipo_vidrio ?? '') : '',
    espesor_mm: isEdit && initialValues ? String(initialValues.espesor_mm ?? '') : '',
    forma: initialGeometry.forma,
    width_mm: initialGeometry.width_mm,
    height_mm: initialGeometry.height_mm,
    radius_mm: initialGeometry.radius_mm,
  }));
  const [vertices, setVertices] = useState(() => initialGeometry.vertices);

  const types = activeCatalog(catalogo);
  const selectedType = types.find((t) => t.id === Number(values.id_tipo_vidrio));
  const thicknesses = selectedType?.espesores ?? [];
  const thicknessHelpId = !selectedType || thicknesses.length === 0
    ? `${id}-espesor_mm-help` : undefined;
  const busy = isSubmitting || pending;
  const initialPair = isEdit && initialValues
    ? { id: Number(initialValues.id_tipo_vidrio), espesor: Number(initialValues.espesor_mm) }
    : null;
  const initialCombinationAvailable = !initialPair || types.some((type) => (
    type.id === initialPair.id && type.espesores.includes(initialPair.espesor)
  ));
  const currentCombinationValid = Boolean(selectedType)
    && thicknesses.includes(Number(values.espesor_mm));
  const showHistoricalCombinationWarning = isEdit
    && !initialCombinationAvailable
    && !currentCombinationValid;

  // --- Validación ---
  const errors = {};

  if (!values.codigo.trim()) errors.codigo = 'Ingresa un código de retazo.';
  else if (values.codigo.trim().length > 40) errors.codigo = 'El código no puede exceder 40 caracteres.';

  if (!values.id_tipo_vidrio) errors.id_tipo_vidrio = 'Selecciona un tipo de vidrio.';
  else if (!selectedType) errors.id_tipo_vidrio = 'Selecciona un tipo de vidrio activo disponible.';

  if (!values.espesor_mm) errors.espesor_mm = 'Selecciona un espesor.';
  else if (!thicknesses.includes(Number(values.espesor_mm))) {
    errors.espesor_mm = 'El espesor no es compatible con el tipo seleccionado.';
  }

  if (!values.forma) errors.forma = 'Selecciona un tipo de forma.';

  if (values.forma === 'RECTANGULO') {
    if (!values.width_mm.toString().trim()) errors.width_mm = 'Completa el ancho.';
    else if (positiveNumber(values.width_mm) === null) errors.width_mm = 'Ingresa un número mayor que cero.';

    if (!values.height_mm.toString().trim()) errors.height_mm = 'Completa el alto.';
    else if (positiveNumber(values.height_mm) === null) errors.height_mm = 'Ingresa un número mayor que cero.';
  }

  if (values.forma === 'CIRCUNFERENCIA') {
    if (!values.radius_mm.toString().trim()) errors.radius_mm = 'Completa el radio.';
    else if (positiveNumber(values.radius_mm) === null) errors.radius_mm = 'Ingresa un número mayor que cero.';
  }

  if (values.forma === 'POLIGONO_CONVEXO') {
    if (vertices.length < MIN_VERTICES) {
      errors.vertices = `Se requieren al menos ${MIN_VERTICES} vértices.`;
    } else {
      for (let i = 0; i < vertices.length; i++) {
        const v = vertices[i];
        const xVal = v.x.toString().trim();
        const yVal = v.y.toString().trim();
        if (!xVal || !Number.isFinite(Number(xVal))) {
          errors[`vertex_${i}_x`] = 'Coordenada X inválida.';
        }
        if (!yVal || !Number.isFinite(Number(yVal))) {
          errors[`vertex_${i}_y`] = 'Coordenada Y inválida.';
        }
      }
    }
  }

  // --- Payload ---
  function buildPayload() {
    const payload = {
      codigo: values.codigo.trim(),
      espesor_mm: Number(values.espesor_mm),
      id_tipo_vidrio: Number(values.id_tipo_vidrio),
    };

    if (values.forma === 'RECTANGULO') {
      payload.geometria = {
        type: 'RECTANGULO',
        width_mm: Number(values.width_mm),
        height_mm: Number(values.height_mm),
      };
    } else if (values.forma === 'CIRCUNFERENCIA') {
      payload.geometria = {
        type: 'CIRCUNFERENCIA',
        radius_mm: Number(values.radius_mm),
      };
    } else if (values.forma === 'POLIGONO_CONVEXO') {
      payload.geometria = {
        type: 'POLIGONO_CONVEXO',
        vertices_mm: vertices.map((v) => [Number(v.x), Number(v.y)]),
      };
    }

    return payload;
  }

  // --- Handlers ---
  function change(field, value) {
    setValues((prev) => {
      const next = { ...prev, [field]: value };
      if (field === 'id_tipo_vidrio') next.espesor_mm = '';
      if (field === 'forma') {
        next.width_mm = '';
        next.height_mm = '';
        next.radius_mm = '';
      }
      return next;
    });
    if (field === 'forma') {
      setVertices(initialVertices());
    }
    setSubmitError('');
  }

  function changeVertex(index, axis, value) {
    setVertices((prev) => prev.map((v, i) => i === index ? { ...v, [axis]: value } : v));
    setSubmitError('');
  }

  function addVertex() {
    setVertices((prev) => [...prev, emptyVertex()]);
  }

  function removeVertex(index) {
    setVertices((prev) => prev.length > MIN_VERTICES ? prev.filter((_, i) => i !== index) : prev);
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
      <p className="retazo-form__error" id={`${id}-${field}-error`}>
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
      await onSubmit(buildPayload());
    } catch {
      setSubmitError('No se pudo completar el registro. Revisa los datos e inténtalo nuevamente.');
    } finally {
      sending.current = false;
      setPending(false);
    }
  }

  return (
    <PageCard as="form" className="retazo-form" onSubmit={submit} noValidate aria-busy={busy}
      aria-labelledby={`${id}-title`}>
      <PageHeader context="Gestión de inventario" title={isEdit ? 'Editar retazo' : 'Registrar retazo'}
        titleId={`${id}-title`} icon={Layers3}
        description={isEdit
          ? 'Actualiza el código, material, espesor y geometría del retazo.'
          : 'Ingresa el código, material, espesor y geometría del retazo que deseas incorporar al stock.'}>
        <p className="retazo-form__required">Todos los campos son obligatorios (*).</p>
      </PageHeader>

      {types.length === 0 && (
        <p className="retazo-form__notice" role="status">
          No hay tipos de vidrio activos disponibles. El registro estará disponible cuando haya catálogo.
        </p>
      )}

      {showHistoricalCombinationWarning && (
        <p className="retazo-form__notice" role="status">
          La combinación actual de tipo de vidrio y espesor ya no está disponible en el catálogo activo.
          Selecciona una combinación activa para guardar cambios o cancela la edición.
        </p>
      )}

      <fieldset className="ng-form-section" disabled={busy}>
        <legend>Datos del retazo</legend>
        <div className="ng-field-grid">
          {/* Código */}
          <div className="ng-field">
            <label htmlFor={`${id}-codigo`}>Código *</label>
            <input className="ng-control" {...fieldProps('codigo')} type="text" maxLength={40}
              value={values.codigo} onChange={(e) => change('codigo', e.target.value)} />
            {errorMessage('codigo')}
          </div>

          {/* Tipo de vidrio */}
          <div className="ng-field">
            <label htmlFor={`${id}-id_tipo_vidrio`}>Tipo de vidrio *</label>
            <select className="ng-control" {...fieldProps('id_tipo_vidrio')}
              value={values.id_tipo_vidrio}
              onChange={(e) => change('id_tipo_vidrio', e.target.value)} disabled={types.length === 0}>
              <option value="">Seleccionar tipo</option>
              {isEdit && values.id_tipo_vidrio && !selectedType && (
                <option value={values.id_tipo_vidrio} disabled>
                  Tipo de vidrio no disponible ({values.id_tipo_vidrio})
                </option>
              )}
              {types.map((t) => <option key={t.id} value={t.id}>{t.nombre}</option>)}
            </select>
            {errorMessage('id_tipo_vidrio')}
          </div>

          {/* Espesor */}
          <div className="ng-field">
            <label htmlFor={`${id}-espesor_mm`}>Espesor (mm) *</label>
            <select className="ng-control" {...fieldProps('espesor_mm', thicknessHelpId)}
              value={thicknesses.includes(Number(values.espesor_mm))
                ? String(Number(values.espesor_mm)) : values.espesor_mm}
              onChange={(e) => change('espesor_mm', e.target.value)}
              disabled={!selectedType || thicknesses.length === 0}>
              <option value="">Seleccionar espesor</option>
              {isEdit && values.espesor_mm && !thicknesses.includes(Number(values.espesor_mm)) && (
                <option value={values.espesor_mm} disabled>
                  Espesor no disponible ({values.espesor_mm} mm)
                </option>
              )}
              {thicknesses.map((v) => <option key={v} value={v}>{v} mm</option>)}
            </select>
            {!selectedType && (
              <p className="retazo-form__hint" id={thicknessHelpId}>Selecciona primero un tipo de vidrio.</p>
            )}
            {selectedType && thicknesses.length === 0 && (
              <p className="retazo-form__hint" id={thicknessHelpId}>
                Este tipo no tiene espesores disponibles. Selecciona otro tipo.
              </p>
            )}
            {errorMessage('espesor_mm')}
          </div>

          {/* Tipo de forma */}
          <div className="ng-field">
            <label htmlFor={`${id}-forma`}>Tipo de forma *</label>
            <select className="ng-control" {...fieldProps('forma')}
              value={values.forma} onChange={(e) => change('forma', e.target.value)}>
              <option value="">Seleccionar forma</option>
              {SHAPES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            {errorMessage('forma')}
          </div>
        </div>
      </fieldset>

      {/* Campos de geometría dinámicos */}
      {values.forma && (
        <fieldset className="ng-form-section" disabled={busy}>
          <legend>Geometría</legend>

          {values.forma === 'RECTANGULO' && (
            <div className="ng-field-grid">
              <div className="ng-field">
                <label htmlFor={`${id}-width_mm`}>Ancho (mm) *</label>
                <input className="ng-control" {...fieldProps('width_mm')} type="number" step="any" min="0"
                  inputMode="decimal" value={values.width_mm}
                  onChange={(e) => change('width_mm', e.target.value)} />
                {errorMessage('width_mm')}
              </div>
              <div className="ng-field">
                <label htmlFor={`${id}-height_mm`}>Alto (mm) *</label>
                <input className="ng-control" {...fieldProps('height_mm')} type="number" step="any" min="0"
                  inputMode="decimal" value={values.height_mm}
                  onChange={(e) => change('height_mm', e.target.value)} />
                {errorMessage('height_mm')}
              </div>
            </div>
          )}

          {values.forma === 'CIRCUNFERENCIA' && (
            <div className="ng-field-grid">
              <div className="ng-field">
                <label htmlFor={`${id}-radius_mm`}>Radio (mm) *</label>
                <input className="ng-control" {...fieldProps('radius_mm')} type="number" step="any" min="0"
                  inputMode="decimal" value={values.radius_mm}
                  onChange={(e) => change('radius_mm', e.target.value)} />
                {errorMessage('radius_mm')}
              </div>
            </div>
          )}

          {values.forma === 'POLIGONO_CONVEXO' && (
            <div>
              <p className="retazo-form__hint">
                Ingresa al menos {MIN_VERTICES} vértices como pares de coordenadas (X, Y) en milímetros.
                No es necesario repetir el primer vértice al final.
              </p>
              {errorMessage('vertices')}
              <ol className="retazo-form__vertices-list">
                {vertices.map((v, i) => (
                  <li key={i} className="retazo-form__vertex-row">
                    <div className="ng-field">
                      <label htmlFor={`${id}-vertex_${i}_x`} className="retazo-form__vertex-label">V{i + 1} X *</label>
                      <input className="ng-control" type="number" step="any" inputMode="decimal"
                        id={`${id}-vertex_${i}_x`} name={`vertex_${i}_x`} required
                        aria-label={`Vértice ${i + 1} coordenada X`}
                        aria-invalid={attempted && Boolean(errors[`vertex_${i}_x`])}
                        aria-describedby={attempted && errors[`vertex_${i}_x`] ? `${id}-vertex_${i}_x-error` : undefined}
                        value={v.x} onChange={(e) => changeVertex(i, 'x', e.target.value)} />
                      {errorMessage(`vertex_${i}_x`)}
                    </div>
                    <div className="ng-field">
                      <label htmlFor={`${id}-vertex_${i}_y`} className="retazo-form__vertex-label">V{i + 1} Y *</label>
                      <input className="ng-control" type="number" step="any" inputMode="decimal"
                        id={`${id}-vertex_${i}_y`} name={`vertex_${i}_y`} required
                        aria-label={`Vértice ${i + 1} coordenada Y`}
                        aria-invalid={attempted && Boolean(errors[`vertex_${i}_y`])}
                        aria-describedby={attempted && errors[`vertex_${i}_y`] ? `${id}-vertex_${i}_y-error` : undefined}
                        value={v.y} onChange={(e) => changeVertex(i, 'y', e.target.value)} />
                      {errorMessage(`vertex_${i}_y`)}
                    </div>
                    <button type="button" className="retazo-form__vertex-remove"
                      aria-label={`Eliminar vértice ${i + 1}`}
                      disabled={vertices.length <= MIN_VERTICES}
                      onClick={() => removeVertex(i)}>
                      <Trash2 size={16} aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ol>
              <button type="button" className="retazo-form__add-vertex" onClick={addVertex} disabled={busy}>
                <Plus size={16} aria-hidden="true" />
                Agregar vértice
              </button>
            </div>
          )}
        </fieldset>
      )}

      {attempted && Object.keys(errors).length > 0 && (
        <p className="retazo-form__error" role="alert">
          Revisa los campos indicados antes de {isEdit ? 'guardar' : 'registrar'}.
        </p>
      )}
      {submitError && <p className="retazo-form__error" role="alert">{submitError}</p>}
      {!onCancel && (
        <p className="retazo-form__hint retazo-form__cancel-hint" id={`${id}-cancel-help`}>
          Cancelar no está disponible en esta vista.
        </p>
      )}
      <ActionBar>
        <button className="ng-button" type="button" onClick={onCancel}
          disabled={busy || !onCancel} aria-describedby={!onCancel ? `${id}-cancel-help` : undefined}>
          Cancelar
        </button>
        <button className="ng-button ng-button--primary" type="submit"
          aria-busy={busy} disabled={busy || types.length === 0 || (isEdit && !currentCombinationValid)}>
          {busy ? <LoaderCircle className="ng-loading-icon" size={18} aria-hidden="true" />
            : <Save size={18} aria-hidden="true" />}
          {busy ? (isEdit ? 'Guardando...' : 'Registrando...')
            : (isEdit ? 'Guardar cambios' : 'Registrar retazo')}
        </button>
      </ActionBar>
    </PageCard>
  );
}
