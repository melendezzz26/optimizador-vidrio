# HU-007 T01/T02 — Pruebas automatizadas frontend

## Contexto y fuentes

| Campo | Valor |
|---|---|
| PBI / tareas | HU-007 / T01 editor gráfico y T02 medidas individuales |
| Fecha de ejecución | 2026-10-07, fecha de la sesión del usuario (Etc/GMT+8) |
| Rama | `feature/HU-007-lienzo-pieza-personalizada` |
| Commit base | `d024dbc30a68a7538d5f775d65c617e74f67156a` |
| Árbol de trabajo | Limpio al comenzar; pruebas, configuración y documentación sin commit al terminar |
| Sistema | Windows 10, build 19045, PowerShell |
| Runtime | Node 24.21.0; npm 11.19.0; React/React DOM 19.3.0; Vite 8.3.1 |
| Navegador ejecutado | Google Chrome 154.0.8037.98, canal `chrome` de Playwright, headless |
| Viewports | Escritorio 1440×900; móvil Chromium emulado 390×844, `isMobile` y `hasTouch` |
| Entrada | `http://127.0.0.1:5173/hu007-t01.html`, servidor Vite local administrado por Playwright |

Fuentes de verdad autorizadas expresamente por el usuario: reglas del prompt,
[SPEC T01](../../../specs/SPEC-HU-007-pieza-personalizada.md),
[SPEC T02](../../../specs/SPEC-HU-007-T02-medidas-reales.md) y evidencia de esta carpeta.
Los documentos externos `Documento_Estrategia_Plan_Pruebas_NewGlass` y
`Documento_Estandares_Ingenieria_Desarrollo_NewGlass_v1_0` no están versionados;
el usuario confirmó que no es necesario acceder físicamente a ellos para esta
ejecución. Se aplicaron las decisiones de testing transcritas en su solicitud.

## Auditoría previa a los cambios

- Inspeccionados `frontend/package.json`, lockfile, Vite, ESLint, README,
  `CustomPieceEditor.jsx/.css`, `segmentGeometry.js`, `geometryScaling.js`,
  `tests/unit/geometryScaling.test.js`, `tests/manual/`, `hu007-t01.html`, ambas
  SPEC, evidencia HU-007, `CONTRIBUTING.md` y convenciones de testing/evidencia.
- No se encontraron instrucciones `AGENTS.md` aplicables.
- Scripts anteriores: `dev`, `build`, `lint`, `preview`; todos conservados.
- Vitest, React Testing Library, user-event y Playwright no estaban instalados.
  No había configuración de componentes o E2E frontend reutilizable.
- Existían **38 unitarias con `node:test`** y una página manual independiente
  que monta el componente real en StrictMode. Las unitarias dieron 38 PASS al
  inicio y se conservaron sin editar; la página se reutilizó sin modificarla.
- Se reutiliza `vite.config.js` mediante `mergeConfig` en Vitest. El componente
  importa el solver y el preview reales: no se sustituyen reglas geométricas.

### Dependencias y archivos

Agregadas únicamente a `devDependencies`, con versiones resueltas en el lockfile:

| Paquete | Versión |
|---|---|
| `vitest` | 5.0.3 |
| `@testing-library/react` | 16.3.3 |
| `@testing-library/dom` | 10.4.2 (peer de Testing Library) |
| `@testing-library/user-event` | 14.6.7 |
| `@testing-library/jest-dom` | 7.0.1 (aserciones DOM/accesibilidad para Vitest) |
| `jsdom` | 30.1.2 (entorno DOM de componentes) |
| `@playwright/test` | 1.63.0 |

Comparación estructural de `packages` del lockfile contra el commit base:
**cero entradas preexistentes modificadas o eliminadas**. Las dependencias de
producción permanecen iguales. `npm audit` informó un aviso alto en
`source-map-js@1.2.1`, ya presente en el lockfile base; no se ejecutó `audit fix`
ni se actualizaron paquetes ajenos a esta tarea.

Archivos nuevos (rutas relativas al repositorio):

- `frontend/vitest.config.js`
- `frontend/playwright.config.js`
- `frontend/tests/component/setup.js`
- `frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx`
- `frontend/tests/e2e/hu007-custom-piece.spec.js`
- `docs/evidence/sprint-01/HU-007/t01-t02-pruebas-frontend.md`

Archivos modificados: `frontend/package.json`, `frontend/package-lock.json`,
`frontend/.gitignore`, `frontend/eslint.config.js`, `frontend/README.md` y
`docs/testing/README.md`. Los directorios de resultados generados se ignoran en
Git y ESLint. No se modificó código funcional, CSS, backend, BD, SPEC ni evidencia
manual existente.

## Niveles y técnicas

| Tarea | Nivel / evidencia | Técnica | Resultado |
|---|---|---|---|
| T01 | Component (unidad de UI; componente montado con React real) | Caja negra; interacciones y salida visible | 7 PASS |
| T01 | E2E frontend | Caja negra; clics reales, cierre, deshacer/reiniciar | Incluido en E01/E04, ambos viewports PASS |
| T01 | Manual | Caja negra / inspección visual | P-01…P-08 históricos PASS, no reejecutados manualmente aquí |
| T02 | Unit | Principalmente caja blanca/límites; funciones e invariantes | 38 PASS |
| T02 | Component | Caja negra; formulario, selección, estados, errores | 13 PASS |
| T02 | E2E frontend | Caja negra; flujo visible del Operario | 12 PASS contando variantes y viewports |
| T02 | Manual | Caja negra / inspección visual | T02-M01…M11 PASS reportados por el usuario; matriz no disponible en el archivo local |
| T01/T02 | Integration backend / API / DB | No aplica al alcance actual | No se crean pruebas ni contratos ficticios |

Caja negra y caja blanca son **técnicas**, no niveles independientes. Las pruebas
de componente ejercitan colaboración real entre UI y geometría local, pero no
se presentan como pruebas de integración backend. T01 no tiene otra suite
unitaria aislada: su comportamiento se prueba al nivel de componente.

## Matriz de componentes

Archivo: [CustomPieceEditor.test.jsx](../../../../frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx).
Los identificadores C/E son nombres nuevos de casos de prueba; los CA referidos
son exclusivamente los que existen en las SPEC. Técnica de todas estas filas:
**caja negra**. Nivel: **Component**. En las filas parametrizadas se indica el
número de ejecuciones.

| Caso | SPEC / CA | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|
| T01-C01 | T01 CA-01 | Editor visible y etiquetado; cero vértices, controles deshabilitados, sin dimensiones | Estado inicial y nombres/descripción accesibles verificados | PASS |
| T01-C02 | T01 CA-01/02/03 | Clics crean puntos ordenados y polilínea; cierre bloqueado con 1/2 puntos, permitido con 3 | Posiciones/puntos SVG, contador, controles y triángulo cerrado verificados | PASS |
| T01-C03 | T01 CA-06; CA-03 parcial | Cierre conserva contorno y bloquea nuevos puntos; Deshacer/Reiniciar disponibles | Dos clics posteriores no alteraron puntos ni contador; feedback cerrado | PASS |
| T01-C04 | T01 CA-04 | Deshacer abierto elimina el último punto hasta vaciar | Secuencia 3→2→1→0 y foco de vuelta al dibujo | PASS |
| T01-C05 | T01 CA-04/06 | Deshacer cerrado reabre, elimina el último y permite continuar | Secuencia 5→4→5 con recierre operativo | PASS |
| T01-C06, abierto/cerrado (2) | T01 CA-05 | Reiniciar vacía todo y permite comenzar de nuevo | Sin círculos/lados/dimensiones; nuevo primer punto aceptado | 2 PASS |
| T02-C01 | T02 CA-02/03/04/07/08 | S1…S5 con labels en mm y valores vacíos, 0 de 5, sin escala | Cinco entradas vacías; step any, required; sin entradas ancho/alto | PASS |
| T02-C02 | T02 CA-07/09/10 | S1=850 da 1 de 5; pendientes vacíos y estimaciones provisionales | Cuatro campos vacíos y preview provisional, sin estado completo | PASS |
| T02-C03 | T02 CA-05/06/17/20 | Seleccionar S1→S3→S5 sincroniza controles y vistas sin perder S1 | aria-pressed único, foco e indicadores SVG coinciden con Sx; S1=850 conservado | PASS |
| T02-C04 | T02 CA-13/14 | Editar S1=850→900 recalcula preview sin cambiar otros campos ni boceto | Puntos renderizados del preview cambiaron; boceto y S2…S5 iguales | PASS |
| T02-C05 | T02 CA-07/12/21 | Cinco medidas compatibles dan vista completa; Agregar sigue disabled y explica T03 | 5 de 5, vista completa y descripción accesible exacta de T03 | PASS |
| T02-C06 | T02 CA-11/18/21 | 1000/100/100/100/100 no permiten cerrar; sin mensaje de convexidad | Alerta dimensional, preview retirado, Agregar disabled | PASS |
| T02-C07, 0/-1 (2) | T02 CA-03/18/20 | Entradas inválidas producen error visible/asociado; no cuentan como medida | aria-invalid, descripción de error, 0 de 5 y sin preview | 2 PASS |
| T02-C08 | T02 CA-03 | Aceptar decimal 0.001 sin mínimo artificial | Medida conservada, 1 de 5, preview provisional, sin error | PASS |
| T02-C09 | T02 CA-07/08/10/13 | Borrar medida vuelve a provisional; borrar todas elimina escala | 4 de 5 y después 0 de 5; mensaje Sin escala física | PASS |
| T02-C10 | T02 CA-19 | Deshacer invalida medidas, selección y preview; recierre regenera segmentos | Sin campos/selección/preview tras deshacer; S1…S4 vacíos al recerrar | PASS |
| T02-C11 | T02 CA-19 | Reiniciar borra el borrador completo, sin selección/medidas residuales | Estado inicial; nuevo pentágono con cinco campos vacíos y selección S1 | PASS |
| T02-C12 | T02 CA-05/20; sección 7 | Cerrar por teclado enfoca S1; activar S2 enfoca su entrada etiquetada | Tab/Enter y foco comprobados con user-event | PASS |

No se usan `data-testid`. Las consultas priorizan roles/nombres/texto. Para
polilíneas, puntos renderizados y resaltados SVG `aria-hidden`, se inspeccionan
primitivas SVG dentro del lienzo localizado por su nombre accesible; no tienen
roles consultables y no se inspecciona estado privado de React.

## Matriz unitaria conservada

Archivo: [geometryScaling.test.js](../../../../frontend/tests/unit/geometryScaling.test.js).
Nivel **Unit**, técnica principal **caja blanca/límites**. Se agrupan nombres
descriptivos existentes, sin renombrar ni reducir ninguno de los 38 tests.

| Casos existentes (agrupados) | Cantidad | SPEC T02 | Esperado | Obtenido / estado |
|---|---:|---|---|---|
| Longitud euclidiana; IDs/orden/lado final | 2 | CA-02 | Distancias y S1…Sn correctos | 2 PASS |
| Sin medidas; una medida provisional; mediana par/impar | 3 | CA-07/08/09/10 | Escala/estimaciones correctas sin rellenar entradas | 3 PASS |
| Modelo completo; rectángulo conocido; triángulo 3-4-5 | 3 | CA-12/15 | Lados, origen y cierre dentro de tolerancia | 3 PASS |
| Edición de lado; orientación trasladada/rotada; pentágono determinista | 3 | CA-12/13/14/15 | Recalcular cierre conservando orden y otras medidas | 3 PASS |
| Referencia cóncava; seis o más lados; referencia colineal | 3 | CA-12/22 | Reconstrucción local sin validar T03 | 3 PASS |
| Valores inválidos: 0, -1, NaN, ±Infinity, abc, vacío, espacios, null, undefined, true | 11 | CA-03/18 | Rechazar valores, nunca sustituir por estimaciones | 11 PASS |
| Desigualdad estricta; incompatibilidad provisional; badInput nativo | 3 | CA-11/18 | Rechazar igualdad/lado excesivo y errores, sin resultado completo | 3 PASS |
| Decimal menor que 0.01; caso casi degenerado | 2 | CA-03/12 | Aceptar entradas positivas factibles, cierre tolerado | 2 PASS |
| Lados faltantes/vértices coincidentes/no finitos; overflow de escala | 2 | CA-18 | Error explícito sin coordenadas inválidas | 2 PASS |
| Entradas congeladas e inmutabilidad | 1 | CA-14 | Ninguna operación modifica los datos de origen | PASS |
| Preview 200:5000, 5000:200, 1000:500 en tamaños desktop/móvil | 3 | CA-16 | Escala uniforme, centrado y proporciones preservadas | 3 PASS |
| Bounds/tamaños inválidos y extensión de un eje | 1 | CA-16/18 | Rechazo/ajuste correcto según entrada | PASS |
| Borrar medidas completas/parciales | 1 | CA-08/10/13 | Volver a provisional y después sin escala | PASS |
| **Total** | **38** | | | **38 PASS / 0 FAIL** |

## Matriz E2E frontend

Archivo: [hu007-custom-piece.spec.js](../../../../frontend/tests/e2e/hu007-custom-piece.spec.js).
Nivel **E2E frontend**, técnica **caja negra**. Todas las filas se ejecutan en
los dos proyectos de viewport. Son seis escenarios concretos por proyecto,
doce ejecuciones en total, sin retries ni skips.

| Caso | SPEC | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|
| T01-T02-E01 | T01 CA-01/03; T02 CA-02/05/06/07/09/10/13/16/21 | Dibujar/cerrar pentágono, S1…S5, medidas parciales→completas, seleccionar/editar S3 y mantener T03 bloqueado | Clics SVG reales; 0→1→5 de 5, cuatro pendientes vacíos, preview completo; S3=620 conserva otros valores; sin overflow horizontal | 2 PASS |
| T02-E02 | T02 CA-11/18/21 | Desde completo, ingresar 1000/100/100/100/100; retirar preview y mostrar incompatibilidad sin convexidad; poder corregir | Alerta esperada, sin geometría completa ni preview anterior, Agregar disabled; corrección restaura preview | 2 PASS |
| T02-E03: 0 | T02 CA-03/18/20/21 | Error visible/accesible, no contar entrada, retirar preview; corregir | aria-invalid y mensaje asociado; recuperación con 850 | 2 PASS |
| T02-E03: -1 | T02 CA-03/18/20/21 | Mismo comportamiento para negativo | Error y recuperación verificados | 2 PASS |
| T02-E03: 1e | T02 CA-03/18/20/21 | Exponente incompleto nativo no debe tratarse como pendiente válido | Chromium badInput=true; error visible, sin preview; recuperación con 850 | 2 PASS |
| T01-T02-E04 | T01 CA-04/05; T02 CA-19 | Deshacer con medidas reabre/invalida; recierre vacío; reinicio limpia | 5→4 vértices, S1…S4 vacíos; reinicio a cero sin campos, selección ni preview | 2 PASS |

Datos deterministas: pentágono SVG `(200,50), (500,50), (600,250), (350,450),
(100,250)`; longitudes `[850,420,600,510,730]`. Es una traslación del ejemplo
verificable 6 de T02. Playwright lee la transformación real del SVG después del
scroll para localizar cada clic; no inyecta vértices ni invoca el solver.
Los E2E comprueban salidas observables y no el funcionamiento interno del ajuste.

Cada escenario tiene contexto de navegador propio. Un guard de red aborta y
hace fallar solicitudes externas, mutaciones HTTP y fetch/XHR inesperados;
también falla ante errores JS no capturados. No devuelve respuestas ficticias
de API. Los doce escenarios terminaron sin esas incidencias. No se conecta a
Supabase ni modifica datos compartidos.

## Reproducción y resultados de ejecución

Preparación desde `frontend/`, con Google Chrome estable instalado en Windows:

```powershell
npm.cmd ci
```

En esta máquina, la instalación inicial de dependencias se realizó con
`npm.cmd install --save-dev vitest @testing-library/react @testing-library/dom @testing-library/user-event @testing-library/jest-dom jsdom @playwright/test`.
`npm ci` es el procedimiento de reproducción desde el lockfile, no una ejecución
adicional atribuida a esta sesión.

### Corrección de infraestructura E2E — 2026-10-07

Incidencia de entorno previa: "Descarga de Chromium de Playwright fallida por timeout; ejecución local realizada posteriormente con Google Chrome instalado."

El usuario reportó que la descarga agotó repetidamente los 30 segundos y que
`npm.cmd run test:e2e` falló al lanzar el navegador por ausencia de
`chromium_headless_shell`. Esos errores de arranque impidieron ejecutar el flujo
funcional; no demuestran fallos funcionales de NewGlass. Los PASS anteriores de
este documento correspondían a Chrome seleccionado explícitamente mediante
`PLAYWRIGHT_CHANNEL=chrome`, no al comando sin esa variable.

Se cambió únicamente la selección predeterminada en `frontend/playwright.config.js`:
`channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome'`. Utiliza el
[canal oficial de Chrome estable](https://playwright.dev/docs/browsers#google-chrome--microsoft-edge)
sin rutas absolutas. Ambos proyectos heredan esa opción y conservan sus nombres
`chromium-desktop`/`chromium-mobile`, viewports, los doce casos, webServer Vite,
trazas, capturas de fallo y reportes. No se modificaron tests ni dependencias.

Esta corrección solo modifica cuatro archivos: la configuración Playwright,
`frontend/README.md`, `docs/testing/README.md` y este documento. Los demás cambios
sin commit listados por Git ya existían al comenzar esta corrección.

Nueva ejecución con `PLAYWRIGHT_CHANNEL` ausente: **Google Chrome 154.0.8037.98**,
headless; versión comprobada mediante `chromium.launch({ channel: 'chrome' })`
y `browser.version()`. `npm.cmd run test:e2e` ejecutó los doce casos en 14.2 s:
seis desktop y seis mobile, todos aprobados, sin skips ni reintentos.

Comandos de revalidación realmente ejecutados, primero E2E y después las demás
comprobaciones:

```powershell
# Desde frontend/, con el puerto 5173 libre
# PLAYWRIGHT_CHANNEL ausente: Chrome se selecciona por defecto
npm.cmd run test:e2e
npm.cmd run test:unit
npm.cmd run test:component
npm.cmd run lint
npm.cmd run build

# Desde la raíz del repositorio
git diff --check
git status --short
git diff --stat
```

`npm test` ejecuta en orden estos comandos reproducibles por separado:

```powershell
npm.cmd run test:unit       # node --test tests/unit/geometryScaling.test.js
npm.cmd run test:component  # vitest run
npm.cmd run test:e2e        # playwright test
```

| Verificación | Resultado observado | Estado |
|---|---|---|
| Unitarias | 38 tests, 38 pass, 0 fail, 0 skipped | PASS |
| Componentes | 1 archivo, 20 tests passed | PASS |
| E2E desktop | Chrome 154.0.8037.98; 6 PASS, 0 FAIL | PASS |
| E2E mobile emulado | Chrome 154.0.8037.98; 6 PASS, 0 FAIL | PASS |
| E2E total | 12 PASS, 0 FAIL; sin skips ni reintentos | PASS |
| ESLint | Código de salida 0, sin errores | PASS |
| Build Vite | Compilación completada, código de salida 0 | PASS |
| `git diff --check` | Sin errores de whitespace | PASS |

Total de las tres suites: **70 PASS / 0 FAIL** (38 unitarias + 20 componentes +
12 E2E realmente ejecutados).

### Portabilidad a futura CI

En Windows local basta Chrome estable instalado y `npm.cmd run test:e2e`.
Una futura CI puede instalar los navegadores oficiales de Playwright mediante
`npx playwright install --with-deps chromium` y seleccionar
`PLAYWRIGHT_CHANNEL=chromium`, conservando ambos proyectos. Esta alternativa
requiere descarga y dependencias del sistema; no se ejecutó ni se declara
validada en esta revisión local. Si CI conserva el canal predeterminado,
necesitará Chrome instalado. No se modificaron workflows CI.

Playwright genera un reporte HTML local en `frontend/playwright-report/` y
artefactos de fallos en `frontend/test-results/`, ambos ignorados. Abrir el
reporte con `npx.cmd playwright show-report` desde frontend. No se agregan
capturas manuales como sustituto de las aserciones automatizadas.

## Evidencia manual preservada y limitaciones

- [T01 validación funcional](t01-validacion-funcional.md) registra P-01…P-08
  PASS y conserva las dos capturas desktop/móvil. Es evidencia histórica de T01,
  no una nueva ejecución manual ni una validación de las medidas añadidas en T02.
- [T02 validación](t02-validacion.md) local termina dentro del bloque de comandos
  de validación técnica. No contiene la matriz T02-M01…M11. El usuario reportó
  esos once casos PASS; se conserva ese antecedente con atribución, sin inventar
  pasos ni resultados individuales y sin reemplazar el archivo existente.
- El E2E prueba el editor real desde su entrada aislada, no Login, NuevoPedido
  integrado, Orders/API/BD ni registro definitivo del pedido. El E2E completo
  del Operario se incorporará cuando esa integración esté estabilizada.
- jsdom no representa layout ni transforms SVG: solo se sustituyen
  `ResizeObserver`, `DOMPoint`, `getScreenCTM` y `scrollIntoView` en el setup de
  componente. Playwright cubre el comportamiento de navegador real. La entrada
  nativa incompleta `1e` se verifica en Playwright, sin falsificar `badInput` en jsdom.
- Solo se ejecutó Chromium mediante Chrome instalado. No se afirma cobertura
  Firefox/WebKit ni dispositivo móvil físico; el navegador administrado por
  Playwright no se pudo descargar en esta ejecución.
- Las comprobaciones de selección y overflow no equivalen a una auditoría visual
  o de accesibilidad completa. Dibujar íntegramente por teclado sigue siendo
  una limitación heredada documentada en la SPEC.
- T01 CA-03 describe Cerrar deshabilitado tras el cierre; la implementación base
  ya lo sustituye por «Contorno cerrado». Se documenta esta divergencia heredada:
  se prueba el bloqueo efectivo y la sustitución existente, sin declarar
  cumplimiento literal de esa frase ni cambiar la UI. T01 CA-07 pertenece al
  alcance gráfico original; las medidas actuales están definidas por la SPEC T02.
- Las filas relacionan cobertura concreta con CA; no constituyen una afirmación
  de cobertura exhaustiva de todos los criterios ni de todas las ramas del solver.

## Pruebas no aplicables

| Nivel / área | Estado | Justificación |
|---|---|---|
| API / contrato HTTP | No aplica al alcance actual | T01/T02 no consumen ni crean API |
| Integración backend | No aplica al alcance actual | Flujo frontend y geometría local |
| PostgreSQL / Supabase / BD | No aplica al alcance actual | No hay lectura/escritura de datos en este editor |
| Repositorios | No aplica al alcance actual | No existe adaptador de persistencia en T01/T02 |
| Migraciones Alembic | No aplica al alcance actual | No hay cambios de esquema |
| Persistencia | No aplica al alcance actual | Borrador exclusivamente en memoria |
| Smoke post-deploy | No aplica al alcance actual | No se despliega una release en este trabajo |
| Benchmark | No aplica al alcance actual | No se incorpora optimización ni requisito de rendimiento reproducible |

Son exclusiones justificadas por alcance, no pruebas faltantes. La ejecución de
Vite local tampoco se presenta como smoke post-deploy.

## Defectos, regresión y cambios funcionales

No se detectó ni corrigió un defecto funcional nuevo. No hay test de regresión
asociado a una corrección nueva ni ciclo rojo/verde que atribuir. Las suites
añadidas protegen el comportamiento existente. **Ningún cambio funcional** fue
necesario para hacer testeable el editor; T03, convexidad, registro, persistencia,
backend, base de datos y migraciones permanecen fuera del trabajo.

Sin commit ni push.
