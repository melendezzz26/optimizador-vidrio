# HU-015-T3 — Visualización raster y cierre

- **Rama:** `feature/HU-015-interfaz-rasterizacion`
- **Base:** `72bd2d7` — `feat(HU-015): implementar interfaz e integracion de rasterizacion`
- **Estado T3:** escala corregida, validada por las suites frontend y seis E2E reales post-fix. Se generaron e inspeccionaron nueve capturas PNG reales con Playwright/Chromium y backend local conectado a Supabase de pruebas.
- **SPEC / PLAN:** Reviewed / Approved; intactos.
- **Backend productivo:** sin cambios.

## Implementación T3

La página Optimization compara la geometría persistida con la respuesta raster del backend. SVG representa rectángulos, circunferencias y polígonos con medidas/vértices originales. Canvas consume spans_by_row, conserva filas vacías y usa el final derecho exclusivo. Cada celda se dibuja con resolution_mm por píxeles por milímetro, en el mismo marco físico que el SVG; no expande la máscara a matriz booleana ni crea nodos por celda. El canvas limita su backing store al viewport y a DPR 2.

Los previews corresponden al pedido, pieza y resolución vigentes. Al cambiar cualquiera de ellos se invalida la máscara anterior. Ante un 422 se conserva el contorno geométrico, se informa que falta una máscara válida y se permite reintentar. La interfaz conserva etiquetas, descripciones y resumen textual accesibles, y pasa de dos columnas a una en pantallas estrechas.

No se añadieron dependencias. T3 no incorpora FF/BF/WF, stock, placement, aprovechamiento, merma, solución, persistencia de previews ni consumo de inventario.

## E2E real post-fix

El 2026-10-14 se ejecutaron los seis casos existentes de frontend/tests/e2e/hu015-rasterization.spec.js despues de corregir el tamano visual de celda del Canvas. Resultado Playwright: 6 passed en 30.9 s; 0 failed, 0 skipped y 0 flaky. Los tres escenarios se ejecutaron en Chromium desktop y en el proyecto Chromium mobile: 3/3 por proyecto.

El backend normal se inicio con el venv y la configuracion existentes del proyecto, conectado al host Supabase de la instancia de pruebas autorizada. /health/live y /health/ready respondieron 200. Vite se inicio con el script npm del proyecto en http://127.0.0.1:5173/ y uso el API local del puerto 8017. Playwright fue 1.63.0 y Chromium 153.0.8010.12.

Comando: npm.cmd run test:e2e -- --config=./.hu015-t3-supabase.playwright.config.mjs tests/e2e/hu015-rasterization.spec.js. Se uso una configuracion Playwright temporal sin webServer ni globalTeardown para reutilizar los servicios existentes; no se uso PostgreSQL local, no se simularon respuestas y no se uso staging.

| Caso post-fix ejecutado en desktop y mobile | Resultado |
| --- | --- |
| Rectangulo: cantidad 5, raster, 422 con resolucion 0.001, retry a 5, recuperacion, teclado/foco, resoluciones y responsive | 2/2 pasaron |
| Circunferencia: SVG circular y mascara real del backend | 2/2 pasaron |
| Poligono convexo: vertices negativos y raster de mas de 53 columnas | 2/2 pasaron |
| **Total post-fix** | **6 passed, 0 failed, 0 skipped, 0 flaky** |

El flujo post-fix recibio Start 200 y Rasterize 200. La resolucion 0.001 produjo 422; cambiarla a 5 mm/celda permitio retry 200. La pieza con cantidad 5 se mantuvo como un registro con un SVG y un Canvas. A 5 mm/celda, la respuesta reporto 160 columnas, 120 filas y 19 200 celdas ocupadas. Tambien se verificaron 10 mm, un raster acotado de 750 000 celdas y una pieza de 1x10 mm. La recuperacion abrio el pedido EN_OPTIMIZACION sin repetir Start. RECTANGULO, CIRCUNFERENCIA y POLIGONO_CONVEXO se renderizaron desde la geometria persistida; el circulo mantuvo radio 30 y el poligono uso sus vertices negativos originales.

La celda corregida mide resolution_mm por pixeles por milimetro en el mismo marco fisico del SVG. La prueba de componente verifica esta conversion. Las suites frontend post-fix tambien pasaron: 70 focalizadas, 124 unitarias, 296 componentes, lint y build. Los seis E2E post-fix ejercitaron ambos previews en navegador real. Despues se inspeccionaron nueve PNG de Playwright: el SVG y el Canvas del rectangulo conservan la misma extension fisica a 5 mm/celda. El identificador de la cuenta sintetica se reemplazo por «Cuenta de prueba» solo en las imagenes.

Estos seis casos no incluyen el conflicto Start 409. Este conserva la cobertura previa de T1/T2 y no se atribuye a los E2E T3.

## Datos y limpieza

La corrida E2E post-fix creo el usuario sintetico ID 13, cliente 41, material 7, pedidos 49-54 y ocho piezas. Se eliminaron esos registros y una consulta posterior confirmo que no quedaban.

La captura final uso Supabase de pruebas, backend local en 127.0.0.1:8017 y Vite en http://127.0.0.1:5173/. Creo usuario sintetico ID 17, cliente 8 y material 15, mas los pedidos 58-60 y tres piezas 84-86. Tras capturar se eliminaron las tres piezas, los pedidos y las entidades sinteticas; la verificacion confirmo ausencia de esos IDs. Los reintentos intermedios limpiaron sus entidades temporales (usuarios IDs 14-16): los dos primeros no llegaron a crear pedidos o piezas y el siguiente creo tres pedidos y tres piezas, todos eliminados. No se cambiaron registros ajenos ni se conservaron credenciales.

## Evidencia visual

Se guardaron solo PNG en `NewGlass-Notion/Fabricio-Melendez-Inventario/Semana-7-Sprint-Review-Retrospective/HU-015-T3-visualizacion-e2e/`:

- `HU015-T3-01-modulo-pendiente-piezas.png` — pedido PENDIENTE, geometria, una fila con cantidad 5 y material/espesor.
- `HU015-T3-02-comparacion-rectangulo.png` — Start 200 y raster 200 a 5 mm/celda; una pieza, un SVG y un Canvas.
- `HU015-T3-03-resolucion-alternativa-10mm.png` — misma geometria con raster actualizado a 10 mm/celda.
- `HU015-T3-04-error-422.png` — 422 real a 0.001; geometria conservada y mascara vigente ausente.
- `HU015-T3-05-retry-200.png` — retry real a 5 mm/celda y resultado restaurado.
- `HU015-T3-06-recuperacion-proceso.png` — EN_OPTIMIZACION recuperado al volver al modulo sin repetir Start.
- `HU015-T3-07-responsive-800.png` — previews apilados a 800 px, sin overflow horizontal.
- `HU015-T3-08-comparacion-circunferencia.png` — SVG circular y raster real.
- `HU015-T3-09-comparacion-poligono.png` — poligono convexo persistido con vertices negativos.

Las nueve imagenes fueron inspeccionadas. La carpeta destino contiene exclusivamente PNG. No se guardaron capturas, videos, traces ni reportes en el repositorio.
## Otras validaciones

| Comando | Resultado |
| --- | --- |
| `npm.cmd run test:component -- src/features/optimization/__tests__` | 70/70 pasaron en 3 archivos. |
| `npm.cmd run test:unit` | 124 pasaron; 0 fallos. |
| `npm.cmd run test:component` | 296 pasaron en 26 archivos; 0 fallos. |
| `npm.cmd run lint` | PASS. |
| `npm.cmd run build` | PASS. |
| E2E HU-015 T3 post-fix | 6 pasaron en 30.9 s; 0 fallos, skips o flaky contra backend real y Supabase de pruebas, despues de corregir la escala. |

No se afirma certificación WCAG ni auditoría Lighthouse/Axe.

## Matriz CA-01 a CA-23

Los estados separan implementación, pruebas automatizadas previas (T1/T2/unit/component) y evidencia de navegador de esta ejecución. «E2E verificado» se limita a los escenarios realmente ejecutados.

| CA | Implementación | Evidencia | Estado |
| --- | --- | --- |
| CA-01 | Filtro PENDIENTE y seleccion del pedido. | Orders filtra por PENDIENTE; el flujo real seleccionó pedidos sintéticos pendientes. | E2E post-fix; acceso/permisos cubiertos por T2. |
| CA-02 | Detalle persistido y filas PIEZA. | GET de detalle y dos piezas persistidas; cantidad 5 quedó en una fila. | E2E post-fix. |
| CA-03 | SVG de RECTANGULO, CIRCUNFERENCIA y POLIGONO_CONVEXO. | Geometría persistida del backend para RECTANGULO, CIRCUNFERENCIA y POLIGONO_CONVEXO se mostró en SVG. | E2E post-fix. |
| CA-04 | Cantidad como atributo, sin duplicar previews. | Cantidad 5 se mantuvo como atributo de una pieza; un SVG y un Canvas. | E2E post-fix. |
| CA-05 | resolution_mm positiva, default 5. | Resolución 5 inicial, 10 y 0.8 positivas, y 0.001 rechazada por el backend; validaciones de UI cubiertas por T1/T2. | E2E post-fix; UI/backend probado por T1/T2. |
| CA-06 | Cambio de resolucion invalida raster y permite retry. | Resolución demasiado fina produjo 422; cambiarla a 5 permitió retry 200. | E2E post-fix. |
| CA-07 | Start explicito y recuperacion sin reenviar Start. | Start fue explícito; raster no inició otro proceso; recuperación no volvió a enviar Start. | E2E post-fix; loading/doble submit cubiertos por T1/T2. |
| CA-08 | Canvas comparte escala fisica: resolution_mm por pixeles/mm. | Prueba de componente y seis E2E reales post-fix; PNG del rectangulo inspeccionado visualmente con extension fisica coincidente. | E2E post-fix verificado. |
| CA-09 | Resumen tecnico usa el resultado backend. | A 5 mm/celda se verificó 160×120 y 19 200 celdas; se probó además pieza de 1×10 mm. | E2E post-fix. |
| CA-10 | Canvas consume spans_by_row con final exclusivo. | Canvas consumió los spans reales; pruebas unitarias/componentes comprueban extremos exclusivos y filas vacías; el E2E valida polígono ancho. | Probado T1/T3; geometrías principales E2E previa a correccion de escala. |
| CA-11 | Invalidacion por seleccion y recuperacion del pedido. | Invalidación y descarte de respuestas tardías cubiertos por hook/tests T2; E2E post-fix y captura recuperaron EN_OPTIMIZACION sin reenviar Start. | E2E post-fix verificado. |
| CA-12 | Errores API con feedback seguro y recuperable. | Transporte y errores seguros de T1/T2; mensaje 422 y retry comprobados con backend real. | 422 E2E post-fix; otros contratos probados T1/T2. |
| CA-13 | Estados vacios y pedido sin piezas. | Pedido vacío/sin piezas y estado vacío cubiertos por Orders/Optimization T1/T2. | Probado T1/T2; no incluido en estos seis E2E. |
| CA-14 | T3 no agrega seleccion ni consumo de stock. | Raster se ejecutó para material de prueba sin crear stock; no hubo planchas ni retazos del fixture. | E2E post-fix; inventario no consumido. |
| CA-15 | Start confirma PENDIENTE a EN_OPTIMIZACION. | Start 200 real en los tres escenarios; concurrencia y 409 tienen evidencia de T1/T2. | Start E2E post-fix; 409 probado T1/T2. |
| CA-16 | Acceso por rol y navegacion Optimization. | E2E autenticó como Operario; autorización y navegación por roles cubiertas por T1/T2. | Operario E2E post-fix; Admin/403 probados T1/T2. |
| CA-17 | Backend valida existencia y pertenencia pieza/pedido. | Pieza inexistente/ajena y asociación pedido-pieza cubiertas por contratos y pruebas T1/T2. | Probado T1/T2; no incluido en estos seis E2E. |
| CA-18 | Teclado, foco visible y layout responsive. | Navegación por teclado, foco visible, comparación sin overflow a 1440/1024/800 px. | E2E post-fix; no equivale a certificación WCAG. |
| CA-19 | Spans conservan filas vacias e indices. | T1 verifica spans; unit/component T3 cubre vacíos/índices y E2E mostró Canvas del backend real. | Probado T1/T3; Canvas E2E post-fix. |
| CA-20 | Sin persistir resultado ni modificar inventario. | No se persistió optimización/ejecución ni se consumió inventario; cleanup confirmó cero optimizaciones para fixtures. | Probado T1 y confirmado durante E2E/cleanup. |
| CA-21 | Backend trata id_pieza inexistente. | ID de pieza inexistente devuelve 404 según pruebas/backend T1. | Probado T1; no incluido en estos seis E2E. |
| CA-22 | Backend valida pertenencia pieza/pedido. | Pieza ajena al pedido devuelve 404 según pruebas/backend T1. | Probado T1; no incluido en estos seis E2E. |
| CA-23 | Backend rechaza geometria invalida de forma segura. | Geometría corrupta/no compatible produce 422 seguro según pruebas/backend T1. | Probado T1; no incluido en estos seis E2E. |

## Archivos y alcance

**Producción frontend:** `OptimizationPage.jsx`, `OptimizationPage.css`, `GeometryPreview.jsx`, `RasterComparison.jsx`, `RasterPreview.jsx`, `rasterCanvas.js`, `visualizationGeometry.js`.

**Pruebas:** `OptimizationPage.test.jsx`, `OptimizationVisualizations.test.jsx`, `tests/e2e/hu015-rasterization.spec.js`.

Backend productivo, dependencias, SPEC y PLAN permanecen intactos. Las nueve capturas PNG están fuera del repositorio; no se guardaron traces, videos ni reportes persistentes. No hubo stage, commit, push, PR o merge. HU-015 no se marca como Verified y queda pendiente de la revision documental final aprobada.