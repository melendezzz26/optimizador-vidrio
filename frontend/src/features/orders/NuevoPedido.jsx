import FormularioPedido from './FormularioPedido';

// Compatibilidad para importadores y pruebas anteriores. La lógica del pedido
// vive en FormularioPedido; este componente solo conserva el modo de creación.
export default function NuevoPedido(props) {
  return <FormularioPedido {...props} mode="create" standalone />;
}
