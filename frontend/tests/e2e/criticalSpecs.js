// TA-040: specs E2E que el CI debe ejecutar con éxito en escritorio y en móvil.
// Un spec nuevo se agrega aquí en el mismo PR que lo crea.
export const CRITICAL_E2E_SPECS = Object.freeze([
  'hu007-custom-piece.spec.js',
  'hu007-order-integration.spec.js',
  'hu012-client-order.spec.js',
  'hu014-inventory-writeoff.spec.js',
  'hu015-rasterization.spec.js',
  's1-optimization-ui.spec.js',
  's1-post-review.spec.js',
  'ta-dashboard.spec.js',
  'ta036-retazo-personalizado.spec.js',
  'ta037-load-feedback.spec.js',
]);