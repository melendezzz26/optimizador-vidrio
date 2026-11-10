# TA-QA-008 - Matriz de pruebas

Base: f46d96db9f5ca6071445bae5f884908aed734ff4. Las expectativas siguientes se fijan antes de ejecutar. Chrome y Edge reales; viewports 1920x1080, 1366x768, 768x1024 y 390x844, estos dos ultimos emulados. No se declara soporte de Firefox ni de un dispositivo fisico. Versiones y resultados se registraran al ejecutar.

| Caso | Navegador | Viewport | Flujo | Resultado esperado | Resultado |
|---|---|---|---|---|---|
| CF-01 | Chrome / Edge | los cuatro | Login | Campos, envio y sesion funcional | PASS en ocho combinaciones |
| CF-02 | Chrome / Edge | los cuatro | Pedidos | Listado, alta e importacion accesibles | PASS en ocho combinaciones |
| CF-03 | Chrome / Edge | los cuatro | Inventario | Listados y formularios de planchas y retazos accesibles | PASS en ocho combinaciones |
| CF-04 | Chrome / Edge | los cuatro | Optimizacion | Seleccionar pedido y ejecutar | PASS en ocho combinaciones |
| CF-05 | Chrome / Edge | los cuatro | Comparacion | Resultados, tabs y controles operativos | PASS en ocho combinaciones |
| CF-06 | Chrome / Edge | los cuatro | Navegacion | Sidebar y rutas principales operativas | PASS en ocho combinaciones |

## Auditoria

React 19 y Vite 8; Playwright usa Chromium desktop 1440x900 y mobile 390x844 en configuracion existente. Breakpoints observados incluyen 1024, 900, 768, 720, 680, 640, 600 y 480 px segun componente. E2E existente usa frontend real y backend con PostgreSQL temporal; no sustituir con HTML simulado. Las tablas pueden tener scroll horizontal utilizable; no contar eso automaticamente como fallo.

## Correccion de referencia

La matriz integrada de TA-QA-001 contenia operadores aritmeticos sustituidos erroneamente durante su migracion. Esta rama restaura * 100 en 19 formulas porcentuales y multiplicacion y comparacion en p50/p95, sin cambiar definiciones ni metas. La correccion requiere revision junto con este PR.

## Resultados locales de la matriz

Fecha: 2026-11-10 UTC. Chrome 157.0.8103.39 y Edge 157.0.4341.42 en Windows; tablet y movil son viewports emulados, no dispositivos fisicos. Backend real en WSL con PostgreSQL 16 temporal y datos sinteticos; frontend Vite local. Se ejecutaron 56 pruebas, 56 PASS, 0 FAIL y 0 omitidas: [resultados por caso y combinacion](resultados.json). Cada navegador se ejecuto en 1920x1080, 1366x768, 768x1024 y 390x844. [Captura desktop](chrome-desktop.png) y [captura movil](chrome-mobile.png); el tablero movil aun mostraba carga al tomar la imagen.

| Combinacion | Pruebas automatizadas | Estado |
|---|---:|---|
| Chrome 1920x1080 | 7 | PASS |
| Chrome 1366x768 | 7 | PASS |
| Chrome 768x1024 | 7 | PASS |
| Chrome 390x844 | 7 | PASS |
| Edge 1920x1080 | 7 | PASS |
| Edge 1366x768 | 7 | PASS |
| Edge 768x1024 | 7 | PASS |
| Edge 390x844 | 7 | PASS |

Los casos cubren login, crear pedido, importar CSV, crear y editar plancha, crear retazo, navegacion y comparacion real con seis resultados completos. Las pruebas verifican accesibilidad de controles seleccionados y ausencia de overflow horizontal de pagina; no verifican automaticamente todo posible solapamiento, clipping, legibilidad o comportamiento de desplazamiento de tablas. La seleccion real de First Fit y la habilitacion de confirmacion pasaron en ocho combinaciones adicionales; ver [seleccion](seleccion-resultados.json). Los controles de siete pantallas por combinacion se inspeccionaron con desplazamiento, visibilidad, prueba de clic y sin overflow horizontal de pagina: [responsive](responsive-resultados.json). Los mensajes de campos obligatorios del login pasaron en ocho combinaciones: [mensajes](login-mensajes-resultados.json).

Comando de la matriz con servidores de pruebas reales ya iniciados: `npx playwright test --config playwright.ta-qa-008.config.js`. No usar produccion. Las capturas y datos de prueba no implican soporte universal ni dispositivos fisicos. La primera pasada de exploracion de comparacion tuvo inventario insuficiente; se creo una plancha sintetica por caso y la corrida indicada arriba verifico los seis resultados completos. Una prueba exploratoria de retazo omitio el codigo obligatorio; se corrigio el fixture antes de la corrida indicada. No se han detectado defectos de interfaz o motor en estos casos; se registra por separado D-01 en documentacion.

Regresion local: unitarias 217 PASS; componentes 613 PASS; lint PASS; build PASS (advertencia de tamano de chunk). E2E completa: gate TA-040 PASS, 148/148 escenarios, ejecutor por fases en Linux con Chromium y PostgreSQL temporal. Una primera ejecucion directa de la suite produjo fallo de migracion por compartir datos entre pruebas; se interrumpio por no cumplir el aislamiento por fases de CI y no cuenta como resultado de producto.

## Metricas del conjunto evaluado

- MC-01: 8/8 combinaciones navegador x viewport con los flujos definidos exitosos = 100%.
- MC-02: 56/56 observaciones de siete pantallas x ocho combinaciones, sin perdida observada de acceso al control critico seleccionado y sin overflow horizontal de pagina = 100% en este conjunto. No certifica legibilidad, clipping o todos los controles fuera de la muestra; tablas con scroll interno utilizable no se cuentan como fallo.
- MC-03: 48/48 flujos CF-01 a CF-06 x ocho combinaciones exitosos = 100%; CF-04 y CF-05 se ejecutan en una misma prueba y la seleccion se verifica aparte.

Los porcentajes describen solo los escenarios indicados y no establecen soporte general, accesibilidad integral ni resultados en dispositivos fisicos. Firefox no fue probado.

## Defecto D-01 - formulas de TA-QA-001

Ambiente, navegador y viewport: no aplican (documentacion). Ruta: docs/quality/TA-QA-001-matriz-metricas-iso25023.md. Reproduccion: inspeccionar formulas porcentuales y MP-02/MP-03 en f46d96db. Esperado: numerador / denominador * 100, posiciones ceil(0,50 * n) y ceil(0,95 * n) con n >= 100. Obtenido: signo menos en lugar de multiplicacion o comparacion. Severidad: alta para interpretacion de metricas; responsable sugerido: Andro. Causa: normalizacion de caracteres durante migracion anterior. Estado: corregido en esta rama, pendiente de revision. Comprobacion RED contra la base: 19/19 formulas porcentuales incorrectas; GREEN: qa008-quality-matrix.test.js valida las 19 y los dos percentiles. No se cambiaron metas ni resultados medidos.

### Diagnostico de la regresion E2E

Se intento una ejecucion directa completa, que fallo en B02 por mezclar en una misma base datos de comparacion incompatibles con el downgrade. El proyecto exige el ejecutor por fases; esa ejecucion se interrumpio y no certifica la regresion. La primera ejecucion por fases con Python ubicado en la unidad Windows montada fallo en B02 desktop y mobile por timeout de 30 s; el gate quedo 0/148 validado y la fase restante no se ejecuto. El CI post-merge del mismo HEAD habia pasado. La repeticion por fases con Python en el sistema de archivos Linux, sin aumentar limites ni modificar producto, paso B02 (2/2), remaining (146/146) y gate conjunto (148/148).

## Reproduccion de la matriz

1. Preparar dependencias de backend/requirements.txt y binarios locales de PostgreSQL. Desde backend ejecutar `python -m tests.e2e_server` para iniciar su cluster sintetico exclusivo; no proporcionar credenciales ni base de produccion.
2. En otra terminal, desde backend y con el mismo entorno, ejecutar `python -m tests.optimization_e2e_data single` para crear la configuracion vigente sintetica necesaria para las comparaciones. El fixture solo opera sobre la base temporal propiedad del servidor de pruebas.
3. Desde frontend ejecutar `npm ci`, configurar VITE_API_URL como `http://127.0.0.1:8017` e iniciar `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`. Tener Chrome y Edge instalados.
4. Desde frontend ejecutar `npx playwright test --config playwright.ta-qa-008.config.js`. Los datos creados son sinteticos; finalizar el servidor de prueba al terminar. Para repetir solo la seleccion o la inspeccion, agregar `--grep CF-04` o `--grep CF-07` respectivamente.
5. La regresion E2E completa se ejecuta con `node scripts/run-e2e-phases.js` en un checkout limpio y servicios propios; no compartir con la matriz local que ya ocupa los mismos puertos.

Las capturas adicionales corresponden al modal de pedido, pantalla de optimizacion y comparacion real: [pedido movil](chrome-mobile-pedido.png), [optimizacion movil](chrome-mobile-optimizacion.png), [comparacion movil](chrome-mobile-comparacion.png), [pedido desktop](chrome-desktop-pedido.png), [optimizacion desktop](chrome-desktop-optimizacion.png) y [comparacion desktop](chrome-desktop-comparacion.png).
