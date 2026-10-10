import { useState, useEffect, useCallback } from "react";
import { 
  Home, ShoppingCart, Archive, BarChart2, Users, Settings,
  Search, Plus, Eye, FileEdit, ChevronLeft, ChevronRight, Loader2, PackageSearch, Trash2
} from "lucide-react";
import fondoVidrio from "../../assets/fondo-vidrio.png";
import "./NuevoPedido.css"; // Reutilizamos estilos generales, luego puedes crear GestionPedidos.css
import FormularioPedido from "./FormularioPedido";

export default function GestionPedidos({ token }) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  // Estados de los datos y paginación
  const [pedidos, setPedidos] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  
  // Estados de la UI
  const [isLoading, setIsLoading] = useState(false);
  const [errorGlobal, setErrorGlobal] = useState("");
  const [pedidoSeleccionado, setPedidoSeleccionado] = useState(null); // Controla el Modal Inteligente
  const [modoCreacion, setModoCreacion] = useState(false);

  // Estados de los filtros
  const [filtroEstado, setFiltroEstado] = useState("");
  const [filtroCliente, setFiltroCliente] = useState("");
  const [filtroFecha, setFiltroFecha] = useState("");

  const cargarPedidos = useCallback(async () => {
    setIsLoading(true);
    setErrorGlobal("");

    try {
      // Construimos los Query Parameters dinámicamente
      const params = new URLSearchParams({
        page: page,
        limit: limit
      });

      if (filtroEstado) params.append("estado", filtroEstado);
      if (filtroCliente) params.append("cliente", filtroCliente);
      if (filtroFecha) params.append("fecha", filtroFecha);

      const response = await fetch(`${baseUrl}/api/orders?${params.toString()}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error("No se pudieron cargar los pedidos.");
      }

      const data = await response.json();
      setPedidos(data.items);
      setTotalItems(data.total);
      setTotalPages(data.total_pages);

    } catch (error) {
      console.error(error);
      setErrorGlobal(error.message);
    } finally {
      setIsLoading(false);
    }
  }, [baseUrl, token, page, limit, filtroEstado, filtroCliente, filtroFecha]);

  // Se ejecuta al cargar el componente o cambiar la página
  useEffect(() => {
    cargarPedidos();
  }, [cargarPedidos, page]);

  // Manejador del botón de búsqueda (para no buscar en cada tecla que presiona el usuario)
  const handleBuscar = (e) => {
    e.preventDefault();
    setPage(1); // Reiniciar a la página 1 al aplicar nuevos filtros
    cargarPedidos();
  };

  const abrirModal = (id_pedido) => {
    setPedidoSeleccionado(id_pedido);
  };

  const cerrarModal = () => {
    setPedidoSeleccionado(null);
    setModoCreacion(false);
    cargarPedidos(); // Refrescar la tabla por si hubo cambios en la edición
  };

  // Helper para pintar el estado con colores
  const renderBadgeEstado = (estado) => {
    const colores = {
      'PENDIENTE': { bg: '#fef3c7', text: '#d97706' },
      'EN_OPTIMIZACION': { bg: '#e0e7ff', text: '#4f46e5' },
      'OPTIMIZADO': { bg: '#dcfce7', text: '#16a34a' },
      'CONFIRMADO': { bg: '#dbeafe', text: '#2563eb' },
      'CANCELADO': { bg: '#fee2e2', text: '#dc2626' }
    };
    const estilo = colores[estado] || { bg: '#f3f4f6', text: '#4b5563' };
    
    return (
      <span style={{ 
        backgroundColor: estilo.bg, color: estilo.text, 
        padding: '4px 10px', borderRadius: '999px', fontSize: '12px', fontWeight: 'bold' 
      }}>
        {estado}
      </span>
    );
  };

  return (
    <div className="app-layout">
      {/* SIDEBAR LATERAL */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">N</div>
          <div>
            <h2>NewGlass</h2>
            <p>Especialistas en vidrio</p>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button className="nav-item"><Home size={20} /> Inicio</button>
          {/* Aquí puedes usar router (Link) para navegar a /nuevo-pedido */}
          <button className="nav-item active"><ShoppingCart size={20} /> Gestión de pedidos</button>
          <button className="nav-item"><Archive size={20} /> Gestión de inventario</button>
          <button className="nav-item"><BarChart2 size={20} /> Consulta de resultados</button>
          <button className="nav-item"><Users size={20} /> Panel de roles</button>
          <button className="nav-item"><Settings size={20} /> Configuración</button>
        </nav>
      </aside>

      {/* ÁREA DE CONTENIDO PRINCIPAL */}
      <main className="pagina-pedido" style={{ backgroundImage: `linear-gradient(rgba(245, 247, 250, 0.85), rgba(245, 247, 250, 0.85)), url(${fondoVidrio})`, backgroundAttachment: 'fixed' }}>
        
        <div className="contenedor-pedido" style={{ maxWidth: '1200px' }}>
          
          <div className="encabezado" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <span className="etiqueta-pagina">
                <PackageSearch size={16} /> Panel de control
              </span>
              <h1>Gestión de Pedidos</h1>
              <p>Busca, filtra y administra los pedidos de tus clientes.</p>
            </div>
            {/* Botón para ir a crear nuevo pedido (Ideal si usas react-router-dom) */}
            <button className="boton-guardar" style={{ padding: '10px 20px' }} onClick={() => setModoCreacion(true)}>
                <Plus size={18} /> Nuevo pedido
            </button>
          </div>

          {errorGlobal && (
            <div className="alerta-error" role="alert">
              {errorGlobal}
            </div>
          )}

          {/* BARRA DE FILTROS */}
          <section className="seccion" style={{ marginBottom: '24px' }}>
            <form onSubmit={handleBuscar} style={{ display: 'flex', gap: '16px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
              <div style={{ flex: '1', minWidth: '200px' }}>
                <label style={{ fontSize: '13px', color: 'var(--text-600)', display: 'block', marginBottom: '6px' }}>Buscar por Cliente</label>
                <input 
                  type="text" 
                  placeholder="Ej: Constructora XYZ" 
                  value={filtroCliente}
                  onChange={(e) => setFiltroCliente(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                />
              </div>

              <div style={{ flex: '1', minWidth: '150px' }}>
                <label style={{ fontSize: '13px', color: 'var(--text-600)', display: 'block', marginBottom: '6px' }}>Estado</label>
                <select 
                  value={filtroEstado}
                  onChange={(e) => setFiltroEstado(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                >
                  <option value="">Todos los estados</option>
                  <option value="PENDIENTE">PENDIENTE</option>
                  <option value="EN_OPTIMIZACION">EN OPTIMIZACION</option>
                  <option value="OPTIMIZADO">OPTIMIZADO</option>
                  <option value="CONFIRMADO">CONFIRMADO</option>
                  <option value="CANCELADO">CANCELADO</option>
                </select>
              </div>

              <div style={{ flex: '1', minWidth: '150px' }}>
                <label style={{ fontSize: '13px', color: 'var(--text-600)', display: 'block', marginBottom: '6px' }}>Fecha de Registro</label>
                <input 
                  type="date" 
                  value={filtroFecha}
                  onChange={(e) => setFiltroFecha(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--border-strong)' }}
                />
              </div>

              <button type="submit" className="boton-guardar" style={{ padding: '9px 16px', height: 'fit-content' }}>
                <Search size={18} /> Buscar
              </button>
            </form>
          </section>

          {/* TABLA DE RESULTADOS */}
          <section className="seccion" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead style={{ backgroundColor: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                  <tr>
                    <th style={{ padding: '16px', fontSize: '14px', color: 'var(--text-600)' }}>ID</th>
                    <th style={{ padding: '16px', fontSize: '14px', color: 'var(--text-600)' }}>Fecha de Registro</th>
                    <th style={{ padding: '16px', fontSize: '14px', color: 'var(--text-600)' }}>Cliente</th>
                    <th style={{ padding: '16px', fontSize: '14px', color: 'var(--text-600)' }}>Estado</th>
                    <th style={{ padding: '16px', fontSize: '14px', color: 'var(--text-600)', textAlign: 'right' }}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan="5" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-500)' }}>
                        <Loader2 className="spin" size={24} style={{ margin: '0 auto 8px' }} />
                        Cargando pedidos...
                      </td>
                    </tr>
                  ) : pedidos.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-500)' }}>
                        No se encontraron pedidos que coincidan con la búsqueda.
                      </td>
                    </tr>
                  ) : (
                    pedidos.map((pedido) => (
                      <tr key={pedido.id_pedido} style={{ borderBottom: '1px solid #e5e7eb', backgroundColor: 'white' }}>
                        <td style={{ padding: '16px', fontWeight: 'bold', color: 'var(--text-900)' }}>#{pedido.id_pedido}</td>
                        <td style={{ padding: '16px', color: 'var(--text-700)' }}>
                          {new Date(pedido.fecha_registro).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute:'2-digit' })}
                        </td>
                        <td style={{ padding: '16px', color: 'var(--text-700)' }}>{pedido.cliente}</td>
                        <td style={{ padding: '16px' }}>{renderBadgeEstado(pedido.estado)}</td>
                        <td style={{ padding: '16px', textAlign: 'right' }}>
                          <button 
                            onClick={() => abrirModal(pedido.id_pedido)}
                            style={{ 
                              padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-strong)', 
                              backgroundColor: 'white', cursor: 'pointer', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '6px' 
                            }}
                          >
                            {pedido.estado === 'PENDIENTE' ? <><FileEdit size={16} /> Editar</> : <><Eye size={16} /> Ver detalle</>}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* CONTROLES DE PAGINACIÓN */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', borderTop: '1px solid #e5e7eb', backgroundColor: '#f9fafb' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-600)' }}>
                Mostrando página {page} de {totalPages || 1} ({totalItems} pedidos)
              </span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  disabled={page === 1} 
                  onClick={() => setPage(page - 1)}
                  style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', backgroundColor: 'white', cursor: page === 1 ? 'not-allowed' : 'pointer', opacity: page === 1 ? 0.5 : 1 }}
                >
                  <ChevronLeft size={18} />
                </button>
                <button 
                  disabled={page === totalPages || totalPages === 0} 
                  onClick={() => setPage(page + 1)}
                  style={{ padding: '6px', borderRadius: '6px', border: '1px solid var(--border-strong)', backgroundColor: 'white', cursor: page === totalPages ? 'not-allowed' : 'pointer', opacity: page === totalPages ? 0.5 : 1 }}
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          </section>
        </div>
      </main>

    {(pedidoSeleccionado !== null || modoCreacion) && (
        <div className="modal-overlay">
          <div className="modal-content">
            
            <div style={{ padding: '16px 24px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, color: 'var(--text-900)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {modoCreacion ? "Crear Nuevo Pedido" : `Pedido #${pedidoSeleccionado}`}
                </h3>
              </div>
              <button onClick={cerrarModal} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px' }}>
                X 
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', backgroundColor: '#f9fafb' }}>
              <FormularioPedido 
                token={token} 
                idPedido={pedidoSeleccionado} // Si modoCreacion es true, esto es null y activa el modo POST
                onCerrar={cerrarModal} 
              />
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
}