# SPEC-T01 — Interfaz Frontend y Formularios Dinámicos (HU-006)

## Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| PBI relacionado | HU-006 (Módulo Nuevo Pedido) |
| Responsable | Luis Anthony Ibañez Herrera |
| Reviewer | Equipo de Desarrollo / Arquitectura |

## 1. Objetivo
Desarrollar la interfaz visual de usuario en React con navegación centralizada en App y formularios dinámicos para permitir al operario configurar y registrar piezas de vidrio según sus distintas formas geométricas de manera interactiva.

## 2. Alcance
### Incluye
- Creación del componente `NuevoPedido.jsx` y su respectiva hoja de estilos.
- Conservación de la navegación funcional de `App.jsx` y permisos actuales. BrowserRouter no es requisito vigente; no introducir una librería por la TASK antigua.
- Formularios dinámicos condicionales para las formas: Rectángulo/Cuadrado, Circunferencia y Polígono convexo mediante CustomPieceEditor HU-007.

### Fuera de alcance
- Conexión directa con la base de datos de producción.
- Lógica de optimización de corte.

## 3. Actor y precondiciones
**Actor:** Operario / Administrador autenticado.
**Precondiciones:** Entorno de desarrollo frontend levantado con Vite (`npm run dev`).

## 4. Entradas y datos
| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| tipo_forma | String (Enum) | RECTANGULO, CIRCUNFERENCIA, POLIGONO_CONVEXO |
| cantidad | Entero | Mayor a 0 |
| dimensiones | Objeto JSON | Según la forma geométrica |

## 5. Reglas de negocio
- RN-01: Los campos de dimensiones deben adaptarse dinámicamente según la forma geométrica elegida.

## 6. Flujo principal
1. El usuario accede a Registro de pedidos desde la navegación autorizada de App.
2. Selecciona material, espesor, cantidad y forma de la pieza.
3. Completa dimensiones y cantidad, luego agrega la pieza al pedido.

## 7. Flujos alternativos y errores
- Si faltan campos obligatorios o cantidad/medidas válidas, se bloquea agregar.
- Hasta migrar HTTP/BD, un pedido con más de una pareja no genera POST: se informa la restricción y se conserva el borrador.
- Se conservan catálogo real, VITE_API_URL, doble envío protegido y feedback 401/403/422 HU-007.

## 8. Criterios de aceptación
- CA-01: La interfaz compila sin errores en Vite y la navegación de App mantiene permisos y acceso a Auth, Users e Inventory. La lista admite las tres formas con material/espesor/cantidad por pieza.

## 9. Impacto técnico
- **Módulos:** `frontend/src/App.jsx`, `frontend/src/features/orders/NuevoPedido.jsx`

## 10. Pruebas previstas
- Verificación visual de renderizado de componentes y cambio dinámico de inputs.

## 11. Evidencias requeridas
- Captura de pantalla del formulario en ejecución.

## Historial de estado
- Estado anterior: Implemented, correspondiente al aporte previo a la convergencia.
- Estado actual: Reviewed; contrato multimaterial definido, implementación completa y verificación pendientes.
- La cobertura previa HU-007 acredita la versión histórica, no el contrato nuevo.