import { useId, useState } from 'react';
import { LoaderCircle, Save, ShieldCheck } from 'lucide-react';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';
import { EMPTY_FORM, validateUserForm } from './userFormRules';

function valuesFor(user) {
  if (!user) return EMPTY_FORM;
  return { nombres: user.nombres, apellidos: user.apellidos, dni: user.dni, password: '', id_rol: String(user.id_rol) };
}

// Formulario de alta y edición. Recibe onSubmit(valores) y muestra sus errores.
export function UserForm({ roles, editingUser, isOwnAccount, onSubmit, onCancel }) {
  const isEditing = Boolean(editingUser);
  const [values, setValues] = useState(() => valuesFor(editingUser));
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const id = useId();

  function setField(name, value) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isSubmitting) return;

    const errors = validateUserForm(values, { isEditing });
    setFieldErrors(errors);
    setFormError('');
    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);
    try {
      await onSubmit(values);
      if (!isEditing) setValues(EMPTY_FORM);
    } catch (error) {
      // 409 al crear: el DNI ya está registrado; el aviso va junto a ese campo.
      if (error.status === 409 && !isEditing) setFieldErrors({ dni: error.message });
      else setFormError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  // Atributos comunes de un control: id, estado de error y textos asociados.
  function controlProps(name, hintId) {
    const errorId = `${id}-${name}-error`;
    const describedBy = [hintId, fieldErrors[name] ? errorId : null].filter(Boolean).join(' ');
    return {
      id: `${id}-${name}`,
      className: 'ng-control',
      'aria-invalid': fieldErrors[name] ? true : undefined,
      'aria-describedby': describedBy || undefined,
    };
  }

  function errorMessage(name) {
    if (!fieldErrors[name]) return null;
    return <p className="users-error" id={`${id}-${name}-error`}>{fieldErrors[name]}</p>;
  }

  const dniHintId = `${id}-dni-hint`;
  const passwordHintId = `${id}-password-hint`;
  const roleHintId = `${id}-rol-hint`;

  return (
    <PageCard as="form" className="users-form" onSubmit={handleSubmit} noValidate
      aria-busy={isSubmitting} aria-labelledby={`${id}-title`}>
      <PageHeader context="Panel de roles" title="Gestión de usuarios" titleId={`${id}-title`}
        icon={ShieldCheck}
        description="Registra usuarios, asígnales un rol y activa o desactiva su acceso.">
        <p className="users-hint">Los campos marcados con * son obligatorios.</p>
      </PageHeader>

      <fieldset className="ng-form-section" disabled={isSubmitting}>
        <legend>{isEditing ? `Editar usuario ${editingUser.usuario}` : 'Nuevo usuario'}</legend>
        <div className="ng-field-grid">
          <div className="ng-field">
            <label htmlFor={`${id}-nombres`}>Nombres *</label>
            <input {...controlProps('nombres')} type="text" maxLength={100} required
              value={values.nombres} onChange={(event) => setField('nombres', event.target.value)} />
            {errorMessage('nombres')}
          </div>

          <div className="ng-field">
            <label htmlFor={`${id}-apellidos`}>Apellidos *</label>
            <input {...controlProps('apellidos')} type="text" maxLength={100} required
              value={values.apellidos} onChange={(event) => setField('apellidos', event.target.value)} />
            {errorMessage('apellidos')}
          </div>

          {isEditing ? (
            <dl className="ng-field users-readonly">
              <div>
                <dt>DNI</dt>
                <dd>{editingUser.dni}</dd>
              </div>
              <div>
                <dt>Usuario de acceso</dt>
                <dd>{editingUser.usuario}</dd>
              </div>
            </dl>
          ) : (
            <div className="ng-field">
              <label htmlFor={`${id}-dni`}>DNI *</label>
              <input {...controlProps('dni', dniHintId)} type="text" inputMode="numeric"
                autoComplete="off" maxLength={8} required
                value={values.dni} onChange={(event) => setField('dni', event.target.value)} />
              <p className="users-hint" id={dniHintId}>
                8 dígitos. El usuario de acceso se genera con la inicial del nombre y el DNI.
              </p>
              {errorMessage('dni')}
            </div>
          )}

          <div className="ng-field">
            <label htmlFor={`${id}-password`}>{isEditing ? 'Nueva contraseña' : 'Contraseña *'}</label>
            <input {...controlProps('password', passwordHintId)} type="password"
              autoComplete="new-password" maxLength={72} required={!isEditing}
              value={values.password} onChange={(event) => setField('password', event.target.value)} />
            <p className="users-hint" id={passwordHintId}>
              {isEditing ? 'Déjala vacía para conservar la actual. Mínimo 8 caracteres.' : 'Mínimo 8 caracteres.'}
            </p>
            {errorMessage('password')}
          </div>

          <div className="ng-field">
            <label htmlFor={`${id}-id_rol`}>Rol *</label>
            <select {...controlProps('id_rol', isOwnAccount ? roleHintId : undefined)} required
              disabled={isOwnAccount} value={values.id_rol}
              onChange={(event) => setField('id_rol', event.target.value)}>
              <option value="">Seleccionar rol</option>
              {roles.map((role) => <option key={role.id_rol} value={role.id_rol}>{role.nombre}</option>)}
            </select>
            {isOwnAccount && <p className="users-hint" id={roleHintId}>No puedes cambiar tu propio rol.</p>}
            {errorMessage('id_rol')}
          </div>
        </div>
      </fieldset>

      {formError && <p className="users-error" role="alert">{formError}</p>}

      <ActionBar>
        {isEditing && (
          <button className="ng-button" type="button" onClick={onCancel} disabled={isSubmitting}>
            Cancelar
          </button>
        )}
        <button className="ng-button ng-button--primary" type="submit"
          aria-busy={isSubmitting} disabled={isSubmitting}>
          {isSubmitting
            ? <LoaderCircle className="ng-loading-icon" size={18} aria-hidden="true" />
            : <Save size={18} aria-hidden="true" />}
          {isSubmitting ? 'Guardando...' : isEditing ? 'Guardar cambios' : 'Registrar usuario'}
        </button>
      </ActionBar>
    </PageCard>
  );
}
