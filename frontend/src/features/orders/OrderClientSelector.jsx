import { useEffect, useRef, useState } from 'react';
import { Check, Search, UserPlus } from 'lucide-react';
import { createClient, searchClients } from '../clients/clientsApi';
import { EmptyState, FeedbackMessage, LoadingState } from '../../shared/components/feedback';
import '../../shared/components/ui.css';
import './OrderClientSelector.css';

const emptyDraft = { nombre_razon_social: '', tipo_documento: '', numero_documento: '', telefono: '' };
const documentLabel = (client) => [client.tipo_documento, client.numero_documento].filter(Boolean).join(' — ') || 'Sin documento';

export default function OrderClientSelector({ value, onChange, disabled, token }) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('query');
  const [results, setResults] = useState(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState(emptyDraft);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const controller = useRef(null);
  const searchInput = useRef(null);
  const selected = useRef(null);
  const nameInput = useRef(null);

  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => {
    if (value) selected.current?.focus();
    else if (creating) nameInput.current?.focus();
  }, [value, creating]);

  const choose = (client, message = '') => {
    onChange(client);
    setCreating(false);
    setResults(null);
    setError('');
    setNotice(message);
  };

  const search = async (event) => {
    event.preventDefault();
    if (busy || disabled || !query.trim()) return;
    controller.current?.abort();
    controller.current = new AbortController();
    setBusy(true);
    setResults(null);
    setError('');
    setNotice('');
    try {
      setResults(await searchClients(query, mode, { token, signal: controller.current.signal }));
    } catch (failure) {
      if (failure.name !== 'AbortError') setError(failure.message);
    } finally { setBusy(false); }
  };

  const register = async (event) => {
    event.preventDefault();
    if (busy || disabled || !draft.nombre_razon_social.trim()) return;
    setBusy(true);
    setError('');
    controller.current = new AbortController();
    try {
      const body = Object.fromEntries(Object.entries(draft).map(([key, text]) => [key, text.trim() || null]));
      const client = await createClient(body, { token, signal: controller.current.signal });
      choose(client, 'Cliente registrado y seleccionado para este pedido.');
      setDraft(emptyDraft);
    } catch (failure) {
      if (failure.name !== 'AbortError') setError(failure.message);
    } finally { setBusy(false); }
  };

  return (
    <section className="orders-section order-client ng-ui" aria-labelledby="order-client-title">
      <h2 id="order-client-title">Cliente</h2>
      <p className="orders-section__description" id="order-client-help">Selecciona un cliente o registra uno nuevo para guardar el pedido.</p>
      {error && <FeedbackMessage variant="error" title="No se pudo completar la operación de clientes">{error}</FeedbackMessage>}
      {notice && <FeedbackMessage variant="success">{notice}</FeedbackMessage>}
      {value ? (
        <div className="order-client__selected" ref={selected} tabIndex={-1} aria-label="Cliente seleccionado">
          <div>
            <p><Check size={18} aria-hidden="true" /> Cliente seleccionado</p>
            <strong>{value.nombre_razon_social}</strong>
            <p>{documentLabel(value)} · {value.estado ? 'Activo' : 'Inactivo'}</p>
          </div>
          <button type="button" className="ng-button" disabled={disabled || busy} onClick={() => {
            choose(null);
            requestAnimationFrame(() => searchInput.current?.focus());
          }}>Cambiar cliente</button>
        </div>
      ) : creating ? (
        <form onSubmit={register} aria-label="Registrar nuevo cliente">
          <h3>Registrar nuevo cliente</h3>
          <div className="ng-field-grid">
            {Object.entries({ nombre_razon_social: 'Nombre o razón social', tipo_documento: 'Tipo de documento (opcional)',
              numero_documento: 'Número de documento (opcional)', telefono: 'Teléfono (opcional)' }).map(([key, label]) => (
              <div className="ng-field" key={key}>
                <label htmlFor={`client-${key}`}>{label}</label>
                <input id={`client-${key}`} className="ng-control" value={draft[key]}
                  ref={key === 'nombre_razon_social' ? nameInput : undefined}
                  type={key === 'telefono' ? 'tel' : 'text'} required={key === 'nombre_razon_social'}
                  disabled={disabled || busy}
                  onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} />
              </div>
            ))}
          </div>
          <div className="ng-action-bar">
            <button type="button" className="ng-button" disabled={disabled || busy} onClick={() => {
              setCreating(false); setError(''); requestAnimationFrame(() => searchInput.current?.focus());
            }}>Volver a buscar</button>
            <button className="ng-button ng-button--primary" disabled={disabled || busy || !draft.nombre_razon_social.trim()} aria-busy={busy}>
              {busy ? 'Registrando cliente…' : 'Registrar y seleccionar'}
            </button>
          </div>
        </form>
      ) : (
        <>
          <form className="order-client__search" onSubmit={search} aria-label="Buscar cliente">
            <div className="ng-field">
              <label htmlFor="client-mode">Buscar por</label>
              <select id="client-mode" className="ng-control" value={mode} disabled={disabled || busy}
                onChange={(event) => { setMode(event.target.value); setResults(null); }}>
                <option value="query">Nombre o razón social</option>
                <option value="document">Documento exacto</option>
              </select>
            </div>
            <div className="ng-field">
              <label htmlFor="client-search">{mode === 'document' ? 'Documento del cliente' : 'Nombre del cliente'}</label>
              <input id="client-search" className="ng-control" ref={searchInput} value={query} disabled={disabled || busy}
                onChange={(event) => { setQuery(event.target.value); setResults(null); }} />
            </div>
            <button className="ng-button ng-button--primary" disabled={disabled || busy || !query.trim()} aria-busy={busy}>
              <Search size={18} aria-hidden="true" /> Buscar
            </button>
          </form>
          {busy && <LoadingState>Buscando clientes…</LoadingState>}
          {results?.length === 0 && <EmptyState title="No se encontraron clientes" description="Prueba otro nombre o documento, o registra un cliente nuevo." />}
          {results?.length > 0 && <>
            <p role="status">Resultados: {results.length}</p>
            <ul className="order-client__results" aria-label="Resultados de clientes">
              {results.map((client) => <li key={client.id_cliente}>
                <div><strong>{client.nombre_razon_social}</strong><p>{documentLabel(client)} · {client.estado ? 'Activo' : 'Inactivo'}</p></div>
                <button type="button" className="ng-button" disabled={disabled || busy} aria-label={`Seleccionar ${client.nombre_razon_social}`}
                  onClick={() => choose(client)}>Seleccionar</button>
              </li>)}
            </ul>
          </>}
          <button type="button" className="ng-button order-client__register" disabled={disabled || busy} onClick={() => {
            setCreating(true); setError(''); setNotice('');
          }}><UserPlus size={18} aria-hidden="true" /> Registrar nuevo cliente</button>
        </>
      )}
    </section>
  );
}
