# SPEC-T01 — Interfaz Frontend y Formularios Dinámicos (HU-006)

## Información general

| Campo | Valor |
|---|---|
| Estado | Implemented |
| PBI relacionado | HU-006 (Módulo Nuevo Pedido) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Equipo de Desarrollo / Arquitectura |

## 1. Objetivo
Desarrollar la interfaz visual de usuario en React con enrutamiento centralizado y formularios dinámicos para permitir al operario configurar y registrar piezas de vidrio según sus distintas formas geométricas de manera interactiva.

## 2. Alcance
### Incluye
- Creación del componente `NuevoPedido.jsx` y su respectiva hoja de estilos.
- Configuración de `react-router-dom` en `App.jsx` con rutas para el Login y la vista de pedidos.
- Formularios dinámicos condicionales para las formas: Rectángulo/Cuadrado, Círculo y Triángulo.

### Fuera de alcance
- Conexión directa con la base de datos de producción.
- Lógica de optimización de corte.

## 3. Actor y precondiciones
**Actor:** Operario / Administrador autenticado.
**Precondiciones:** Entorno de desarrollo frontend levantado con Vite (`npm run dev`).

## 4. Entradas y datos
| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| tipo_forma | String (Enum) | RECTANGULO, CIRCUNFERENCIA, TRIANGULO |
| cantidad | Entero | Mayor a 0 |
| dimensiones | Objeto JSON | Según la forma geométrica |

## 5. Reglas de negocio
- RN-01: Los campos de dimensiones deben adaptarse dinámicamente según la forma geométrica elegida.

## 6. Flujo principal
1. El usuario accede a la ruta `/pedidos/nuevo`.
2. Selecciona la forma geométrica.
3. Completa dimensiones y cantidad, luego agrega la pieza al pedido.

## 7. Flujos alternativos y errores
- Si faltan campos obligatorios, el formulario bloquea el envío.

## 8. Criterios de aceptación
- CA-01: La interfaz compila sin errores en Vite y la navegación opera mediante `BrowserRouter`.

## 9. Impacto técnico
- **Módulos:** `frontend/src/App.jsx`, `frontend/src/features/orders/NuevoPedido.jsx`

## 10. Pruebas previstas
- Verificación visual de renderizado de componentes y cambio dinámico de inputs.

## 11. Evidencias requeridas
- Captura de pantalla del formulario en ejecución.

## Historial de estado
- Draft -> Reviewed -> Implemented -> Verified