import { useState, useEffect, useCallback, useId, useRef } from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import { 
  Plus, Trash2, Save, X, PackagePlus, Loader2,
} from "lucide-react";
import "./NuevoPedido.css";
import CustomPieceEditor from './CustomPieceEditor';
import { ConfirmDialog, EmptyState, FeedbackMessage, LoadingState } from "../../shared/components/feedback";
import { createOrder, listOrderMaterials } from './ordersApi';
import { AppShell } from '../../shared/components/AppShell';
import { ActionBar, PageCard, PageHeader } from '../../shared/components/PageLayout';

export default function NuevoPedido({ token, user, toolbar }) {
  const [tiposDisponibles, setTiposDisponibles] = useState([]);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorGlobal, setErrorGlobal] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isCancelDialogOpen, setIsCancelDialogOpen] = useState(false);

  const [piezas, setPiezas] = useState([]);
  const [listaAnimada] = useAutoAnimate();
  const [piezaEnEdicion, setPiezaEnEdicion] = useState(null);
  const nextPieceIdRef = useRef(0);
  const formId = useId();
  const editorDialogRef = useRef(null);
  const editorCloseRef = useRef(null);
  const editorTriggerRef = useRef(null);
  const titleId = useId();
  const editorTitleId = useId();

  useEffect(() => {
    if (piezaEnEdicion === null) return undefined;
    const trigger = editorTriggerRef.current;
    editorCloseRef.current?.focus();
    return () => trigger?.focus?.();
  }, [piezaEnEdicion]);

  useEffect(() => {
    const controller = new AbortController();
    const fetchTiposVidrio = async () => {
      try {
        const data = await listOrderMaterials({ signal: controller.signal, token });
        setTiposDisponibles(data);
      } catch (err) {
        if (err.name === 'AbortError') return;
        console.error(err);
        setErrorGlobal("Error al conectar con la base de datos para cargar los vidrios.");
      } finally {
        if (!controller.signal.aborted) setIsLoadingConfig(false);
      }
    };
    fetchTiposVidrio();
    return () => controller.abort();
  }, [token]);

  // Función para obtener los espesores dinámicos según el vidrio seleccionado en cada pieza
  const obtenerEspesores = (idVidrio) => {
    const tipo = tiposDisponibles.find(t => t.id_tipo_vidrio.toString() === idVidrio?.toString());
    return tipo ? tipo.espesores_mm : [];
  };

  const agregarPieza = () => {
    const id = nextPieceIdRef.current;
    nextPieceIdRef.current += 1;
    setPiezas((current) => {
      const numeroMaximo = current.length > 0
        ? Math.max(...current.map((piece) => parseInt(piece.nombre.split(' ')[1], 10) || 0))
        : 0;

      return [...current, {
        id,
        nombre: `Pieza ${numeroMaximo + 1}`,
        espesor: "",
        cantidad: 1,
        tipo_forma: "RECTANGULO",
        dimensiones: { width_mm: '', height_mm: '' },
      }];
    });
  };
  const eliminarPieza = (id) => {
      // 1. Filtramos para quitar la pieza eliminada
      // 2. Usamos map() para renumerar las que quedan (index + 1)
      const piezasRenumeradas = piezas
        .filter((pieza) => pieza.id !== id)
        .map((pieza, index) => ({
          ...pieza,
          nombre: `Pieza ${index + 1}`
        }));
        
      setPiezas(piezasRenumeradas);
    };

const actualizarPieza = useCallback((id, campo, valor) => {
    // Usamos prevPiezas para evitar problemas de dependencias en React
    setPiezas(prevPiezas => prevPiezas.map(pieza => {
      if (pieza.id === id) {
        if (campo === 'cantidad') {
          return { ...pieza, cantidad: valor === '' ? '' : Number(valor) };
        }
        if (campo === 'tipo_vidrio_id') {
          return { ...pieza, tipo_vidrio_id: valor, espesor: "" };
        }
        if (campo === 'espesor') {
          return { ...pieza, espesor: valor };
        }
        if (campo === 'tipo_forma') {
          let nuevasDimensiones = {};
          if (valor === 'RECTANGULO') nuevasDimensiones = { width_mm: '', height_mm: '' };
          if (valor === 'CIRCUNFERENCIA') nuevasDimensiones = { radius_mm: '' };
          if (valor === 'POLIGONO_CONVEXO') nuevasDimensiones = { vertices: [] };
          return { ...pieza, tipo_forma: valor, dimensiones: nuevasDimensiones };
        }
        
        if (campo === 'dimensiones') {
          return { ...pieza, dimensiones: valor };
        }

        return { 
          ...pieza, 
          dimensiones: { ...pieza.dimensiones, [campo]: parseFloat(valor) || '' } 
        };
      }
      return pieza;
    }));
  }, []);
  
  const esPedidoValido = () => {
    if (piezas.length === 0) return false;
    
    return piezas.every(p => {
      const cantidad = Number(p.cantidad);
      const espesor = Number(p.espesor);
      const medidaPositiva = (valor) => Number.isFinite(Number(valor)) && Number(valor) > 0;

      // Cada pieza requiere material, espesor y una cantidad entera positiva.
      if (!p.tipo_vidrio_id || !medidaPositiva(espesor)
        || !Number.isInteger(cantidad) || cantidad <= 0) return false;
      
      // Validar medidas finitas y positivas según la forma elegida.
      if (p.tipo_forma === 'RECTANGULO'
        && (!medidaPositiva(p.dimensiones.width_mm) || !medidaPositiva(p.dimensiones.height_mm))) return false;
      if (p.tipo_forma === 'CIRCUNFERENCIA' && !medidaPositiva(p.dimensiones.radius_mm)) return false;
      
      // 3. Validar que el polígono tenga al menos 3 vértices dibujados
      if (p.tipo_forma === 'POLIGONO_CONVEXO' && (!p.dimensiones.vertices || p.dimensiones.vertices.length < 3)) return false;
      
      return true;
    });
  };

  // Limpiar el pedido borra todas las piezas: se confirma con el diálogo compartido.
  const cancelarPedido = () => {
    setIsCancelDialogOpen(true);
  };

  const confirmarCancelacion = () => {
    setPiezas([]);
    setErrorGlobal("");
    setSuccessMessage("");
    setIsCancelDialogOpen(false);
  };

useEffect(() => {
  const recibirDatosDelEditor = (evento) => {
      if (evento.key === 'verticesPoligono_completados') {
        const index = localStorage.getItem('piezaEnEdicion_index');
        
        if (index !== null) {
          const vertices = JSON.parse(evento.newValue);
          actualizarPieza(parseInt(index), 'dimensiones', { vertices });
          
          localStorage.removeItem('verticesPoligono_completados');
          localStorage.removeItem('piezaEnEdicion_index');
        }
      }
    };

    window.addEventListener('storage', recibirDatosDelEditor);
    return () => window.removeEventListener('storage', recibirDatosDelEditor);
  }, [actualizarPieza]);

  const abrirEditor = (id) => {
    editorTriggerRef.current = document.activeElement;
    setPiezaEnEdicion(id);
  };

  const manejarTecladoEditor = (event) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      setPiezaEnEdicion(null);
      return;
    }
    if (event.key !== 'Tab') return;
    const controls = [...editorDialogRef.current.querySelectorAll(
      'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )];
    if (controls.length === 0) {
      event.preventDefault();
      return;
    }
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (!editorDialogRef.current.contains(document.activeElement)) {
      event.preventDefault();
      first.focus();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const guardarPedido = async () => {
    setIsSubmitting(true);
    setErrorGlobal("");
    setSuccessMessage("");
    
    const payload = {
      // Ya no enviamos id_tipo_vidrio ni espesor_mm aquí afuera
      piezas: piezas.map(p => {
        // 1. Extraemos rawState y vertices originales para no enviarlos tal cual
        // eslint-disable-next-line no-unused-vars
        const { rawState, vertices, ...medidasLimpias } = p.dimensiones;

        // 2. Armamos la pieza metiendo el material y espesor ADENTRO, como exige FastAPI
        const piezaFormateada = {
          tipo_forma: p.tipo_forma, 
          id_tipo_vidrio: parseInt(p.tipo_vidrio_id), // Movido adentro de la pieza
          espesor_mm: parseFloat(p.espesor),         // Movido adentro de la pieza
          cantidad: parseInt(p.cantidad),
          ...medidasLimpias // Inyecta width_mm, height_mm, o radius_mm
        };

        // 3. Si es polígono, le cambiamos el nombre de "vertices" a "vertices_mm"
        if (p.tipo_forma === 'POLIGONO_CONVEXO') {
          piezaFormateada.vertices_mm = vertices;
        }

        return piezaFormateada;
      })
    };

    try {
      await createOrder(payload, { token });
      setSuccessMessage("Pedido registrado correctamente.");
      setPiezas([]);
      
    } catch (error) {
      console.error(error);
      // Muestra el mensaje de error preparado arriba (nunca el detalle técnico del servidor)
      setErrorGlobal(error.message); 
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell activeItem="orders" user={user}>
      {toolbar}
      <PageHeader
        context="Registro de pedido"
        title="Nuevo pedido"
        description="Configura el material, espesor y medidas de cada pieza requerida por el cliente."
        titleId={titleId}
        icon={PackagePlus}
      />
      <PageCard as="section" className="orders-page-card" aria-labelledby={titleId}>
        <div className="ng-ui">
            {isLoadingConfig && <LoadingState>Cargando materiales…</LoadingState>}
            {errorGlobal && (
              <FeedbackMessage variant="error" title="No se pudo completar la operación">{errorGlobal}</FeedbackMessage>
            )}
            {successMessage && <FeedbackMessage variant="success">{successMessage}</FeedbackMessage>}
          </div>

          <section className="seccion">
            <div className="encabezado-piezas">
              <div>
                <h2>Piezas del pedido</h2>
                <p className="texto-secundario">Agrega todas las piezas que forman parte del pedido.</p>
              </div>
              <button type="button" className="boton-agregar" onClick={agregarPieza} disabled={isLoadingConfig || isSubmitting}>
                <Plus size={18} /> Agregar pieza
              </button>
            </div>

            <div ref={listaAnimada}>
              {piezas.length === 0 ? (
                <div className="ng-ui">
                  <EmptyState
                    title="No hay piezas agregadas"
                    description="Haz clic en «Agregar pieza» para comenzar a armar el pedido."
                  />
                </div>
              ) : (

              <div className="lista-piezas">
                {piezas.map((pieza, index) => {
                  const fieldIds = Object.fromEntries(
                    ['material', 'espesor', 'forma', 'cantidad', 'ancho', 'alto', 'radio']
                      .map((field) => [field, `${formId}-pieza-${pieza.id}-${field}`]),
                  );
                  return (
                  <div className="pieza" key={pieza.id} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    
                    {/* Fila 1: Título y Eliminar */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div className="pieza-info">
                        <div className="numero-pieza">{index + 1}</div>
                        <div className="datos-pieza">
                          <strong>{pieza.nombre}</strong>
                          <span>Configura material y medidas</span>
                        </div>
                      </div>
                      <button type="button" className="boton-eliminar" onClick={() => eliminarPieza(pieza.id)} title="Eliminar pieza">
                        <Trash2 size={18} />
                      </button>
                    </div>

                    {/* Fila 2: Material, Espesor, Forma y Cantidad */}
                    <div style={{ display: 'flex', gap: '24px', paddingLeft: '48px', flexWrap: 'wrap', alignItems: 'center' }}>
                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label htmlFor={fieldIds.material} style={{ fontSize: '13px', color: 'var(--text-600)' }}>Material</label>
                        <select 
                          id={fieldIds.material}
                          value={pieza.tipo_vidrio_id} 
                          onChange={(e) => actualizarPieza(pieza.id, 'tipo_vidrio_id', e.target.value)}
                          style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', fontSize: '13px', width: '140px' }}
                        >
                          <option value="">Seleccionar...</option>
                          {tiposDisponibles.map(t => <option key={t.id_tipo_vidrio} value={t.id_tipo_vidrio}>{t.nombre}</option>)}
                        </select>
                      </div>

                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label htmlFor={fieldIds.espesor} style={{ fontSize: '13px', color: 'var(--text-600)' }}>Espesor</label>
                        <select 
                          id={fieldIds.espesor}
                          value={pieza.espesor} 
                          onChange={(e) => actualizarPieza(pieza.id, 'espesor', e.target.value)}
                          disabled={!pieza.tipo_vidrio_id}
                          style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', fontSize: '13px', width: '100px' }}
                        >
                          <option value="">Espesor...</option>
                          {obtenerEspesores(pieza.tipo_vidrio_id).map(e => <option key={e} value={e}>{e} mm</option>)}
                        </select>
                      </div>

                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label htmlFor={fieldIds.forma} style={{ fontSize: '13px', color: 'var(--text-600)' }}>Forma</label>
                        <select 
                          id={fieldIds.forma}
                          value={pieza.tipo_forma} 
                          onChange={(e) => {
                            const nuevaForma = e.target.value;
                            actualizarPieza(pieza.id, 'tipo_forma', nuevaForma);
                            // Abre el editor de inmediato si es polígono convexo
                            if (nuevaForma === 'POLIGONO_CONVEXO') {
                              abrirEditor(pieza.id);
                            }
                          }}
                          style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', fontSize: '13px', width: '190px' }} 
                        >
                          <option value="RECTANGULO">Rectángulo / Cuadrado</option>
                          <option value="CIRCUNFERENCIA">Círculo</option>
                          <option value="POLIGONO_CONVEXO">Polígono Convexo</option>
                        </select>
                      </div>

                      <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <label htmlFor={fieldIds.cantidad} style={{ fontSize: '13px', color: 'var(--text-600)' }}>Cant.</label>
                        <input 
                          id={fieldIds.cantidad}
                          type="number" min="1" 
                          value={pieza.cantidad} 
                          onChange={(e) => actualizarPieza(pieza.id, 'cantidad', e.target.value)}
                          style={{ width: '60px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                        />
                      </div>
                    </div>

                    {/* Fila 3: Medidas dinámicas según el tipo de forma */}
                    <div style={{ display: 'flex', gap: '24px', paddingLeft: '48px', alignItems: 'center' }}>
                      {pieza.tipo_forma === 'RECTANGULO' && (
                        <>
                          <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label htmlFor={fieldIds.ancho} style={{ fontSize: '13px', color: 'var(--text-600)' }}>Ancho (mm)</label>
                            <input 
                              id={fieldIds.ancho}
                              type="number" min="1" placeholder="Ej: 1000"
                              value={pieza.dimensiones.width_mm} 
                              onChange={(e) => actualizarPieza(pieza.id, 'width_mm', e.target.value)}
                              style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                            />
                          </div>
                          <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <label htmlFor={fieldIds.alto} style={{ fontSize: '13px', color: 'var(--text-600)' }}>Alto (mm)</label>
                            <input 
                              id={fieldIds.alto}
                              type="number" min="1" placeholder="Ej: 500"
                              value={pieza.dimensiones.height_mm} 
                              onChange={(e) => actualizarPieza(pieza.id, 'height_mm', e.target.value)}
                              style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                            />
                          </div>
                        </>
                      )}

                      {pieza.tipo_forma === 'CIRCUNFERENCIA' && (
                        <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <label htmlFor={fieldIds.radio} style={{ fontSize: '13px', color: 'var(--text-600)' }}>Radio (mm)</label>
                          <input 
                            id={fieldIds.radio}
                            type="number" min="1" placeholder="Ej: 250"
                            value={pieza.dimensiones.radius_mm} 
                            onChange={(e) => actualizarPieza(pieza.id, 'radius_mm', e.target.value)}
                            style={{ width: '90px', padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                          />
                        </div>
                      )}

                      {pieza.tipo_forma === 'POLIGONO_CONVEXO' && (
                        <div className="campo-mini" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          {pieza.dimensiones?.vertices?.length > 0 ? (
                            <span style={{ color: 'green', fontSize: '13px', fontWeight: 'bold' }}>✓ Vértices cargados</span>
                          ) : (
                            <span style={{ color: '#d97706', fontSize: '13px', fontWeight: 'bold' }}>⚠️ Falta dibujar</span>
                          )}
                          <button
                            type="button"
                            onClick={() => abrirEditor(pieza.id)}
                            style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-strong)', backgroundColor: 'white', cursor: 'pointer', fontSize: '13px' }}
                          >
                            Editar dibujo
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  );
                })}
              </div>  
              )}
            </div>
          </section>

          <ActionBar>
            <button type="button" className="ng-button" onClick={cancelarPedido} disabled={isSubmitting}>
              <X size={18} /> Cancelar
            </button>

            <button 
              type="button" 
              className="ng-button ng-button--primary"
              onClick={guardarPedido} 
              disabled={!esPedidoValido() || isSubmitting}
            >
              {isSubmitting ? <Loader2 size={18} className="spin" /> : <Save size={18} />}
              {isSubmitting ? "Guardando..." : "Guardar pedido"}
            </button>
          </ActionBar>
        <div className="ng-ui">
          <ConfirmDialog
            open={isCancelDialogOpen}
            title="¿Limpiar el pedido?"
            confirmLabel="Limpiar piezas"
            onConfirm={confirmarCancelacion}
            onCancel={() => setIsCancelDialogOpen(false)}
          >
            <p>Se quitarán todas las piezas agregadas. Esta acción no se puede deshacer.</p>
          </ConfirmDialog>
        </div>
      </PageCard>
      
      {piezaEnEdicion !== null && (
        <div className="orders-editor-backdrop">
          <div
            ref={editorDialogRef}
            className="orders-editor-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={editorTitleId}
            tabIndex={-1}
            onKeyDown={manejarTecladoEditor}
          >
            <div className="orders-editor-dialog__header">
              <h3 id={editorTitleId}>Dibujar Polígono Convexo</h3>
              <button ref={editorCloseRef} type="button" aria-label="Cerrar editor de polígono" onClick={() => setPiezaEnEdicion(null)}>
                <X size={24} aria-hidden="true" />
              </button>
            </div>
            <div className="orders-editor-dialog__content">
              <CustomPieceEditor
                // Buscamos la pieza que estamos editando y le pasamos su rawState
                initialState={piezas.find(p => p.id === piezaEnEdicion)?.dimensiones?.rawState}
                onGuardarVertices={(datos) => {
                  // datos ahora trae { vertices, rawState }
                  actualizarPieza(piezaEnEdicion, 'dimensiones', datos);
                  setPiezaEnEdicion(null); 
                }}
              />
            </div>
            
          </div>
        </div>
      )}
    </AppShell>
  );
}
