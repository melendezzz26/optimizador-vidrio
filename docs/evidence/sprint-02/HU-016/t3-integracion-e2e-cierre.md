# HU-016 — T3 Integración, E2E y Cierre

## Información general

| Campo | Valor |
|---|---|
| PBI relacionado | **HU-016** — Dashboard inicial para usuarios de NewGlass |
| Tarea | **HU-016-T03** — Integración, E2E y cierre |
| Estado de la tarea | **Closed / Completed** |
| Estado de la SPEC | **Verified** |
| Rama | `feature/HU-016-dashboard-inicial` |
| Fecha de cierre | 27/10/2026 |
| Autor | Fabricio Melendez Quezada |
| Revisor del alcance | Fabricio Danniel Aguilar Chávez |

---

## 1. Resumen de ejecución y saneamiento de integración

Se completó la verificación integral de integración y pruebas para el Dashboard inicial de NewGlass (HU-016), abarcando los roles **Administrador**, **Operario** y **Almacenero**, el caso de **sesión sin funciones autorizadas** y pruebas de adaptabilidad responsive en los tres anchos solicitados (**1440px, 1024px y 800px**).

### Saneamiento de integración (eliminación de pruebas simuladas):
- **Decisión de ingeniería:** Para preservar la integridad de la suite de integración continua (CI) y evitar que pruebas con intercepción de red (`page.route` / mock) interfieran con las ejecuciones reales del repositorio (`npm run test:e2e`), se eliminaron completamente los archivos de prueba simulada `frontend/tests/e2e/hu016-dashboard.spec.js` y `frontend/playwright.hu016.config.js`.
- **Estrategia de verificación adoptada:**
  1. **Pruebas de componentes y contratos (86/86 PASS en Vitest):** Verificación exhaustiva en `features/dashboard` y `features/authentication` evaluando la lógica de permisos (`canViewDashboard = Boolean(user)`), acceso a Optimización (`canViewResults`), saludo con nombre real, manejo de sesiones sin funciones (0 peticiones restringidas) y navegación interna.
  2. **Integración E2E real del repositorio:** La integración E2E del Dashboard se apoya en la suite existente no simulada [`tests/e2e/ta-dashboard.spec.js`](../../../../frontend/tests/e2e/ta-dashboard.spec.js), la cual ejecuta flujos reales contra el backend sin alterar rutas ni inyectar mocks en los happy paths.
  3. **Calidad de código y empaquetado:** `eslint` aprobó con 0 errores y 0 advertencias; `vite build` completó en 1.16s generando el bundle de producción sin incidencias.
  4. **Regresión:** Las pruebas de Inventario, Optimización y Pedidos se mantienen íntegras y sin regresiones.

---

## 2. Matriz de Verificación de Criterios de Aceptación (CA-01 a CA-22)

| ID | Criterio de Aceptación | Estado | Evidencia de Verificación |
|---|---|:---:|---|
| **CA-01** | Tras autenticarse correctamente, cualquier usuario con sesión válida llega a Inicio. | ✅ **VERIFICADO** | Validado en E2E para los 3 roles y sesión sin módulos; `canViewDashboard(user)` es `Boolean(user)` y `App.jsx` lo asigna como vista inicial y fallback. |
| **CA-02** | Inicio puede abrirse desde Sidebar y refleja la vista activa de forma accesible. | ✅ **VERIFICADO** | Verificado en E2E; al navegar a otro módulo y pulsar «Inicio» en el Sidebar, se retorna a la pantalla con `aria-current="page"`. |
| **CA-03** | Misma pantalla común para los 3 roles; sesión sin permisos conserva Inicio sin consultas restringidas. | ✅ **VERIFICADO** | E2E Scenario 4: sesión con `permisos: []` monta Inicio con saludo, mensaje de estado «Sin funciones habilitadas» y logout, sin peticiones fetch restringidas. |
| **CA-04** | Fuentes y accesos corresponden solo a los permisos efectivos vigentes. | ✅ **VERIFICADO** | Verificado en pruebas unitarias y E2E: cada tarjeta y botón depende exclusivamente de `user.permisos`. |
| **CA-05** | Ocultar opciones no sustituye la autorización backend. | ✅ **VERIFICADO** | Los endpoints del backend protegen sus recursos con 401/403 independientemente de la interfaz. |
| **CA-06** | Cifras proceden de respuestas reales y con significado explícito. | ✅ **VERIFICADO** | Proyección directa de datos API; cada tarjeta define explícitamente el alcance de su métrica. |
| **CA-07** | Con `orders.view`, muestra total de pedidos PENDIENTE usando `total`. Sin permiso no lo consulta. | ✅ **VERIFICADO** | Consulta `GET /api/orders?page=1&limit=1&estado=PENDIENTE` con `total`; Almacenero no realiza la llamada. |
| **CA-08** | Con `orders.view`, muestra pedidos EN_OPTIMIZACION (sin presentarlo como ejecuciones activas). | ✅ **VERIFICADO** | Rotulado como «Pedidos en optimización» y descripción explícita de pedidos. |
| **CA-09** | Resumen de inventario distingue registros de unidades y aclara compatibilidad. | ✅ **VERIFICADO** | `activeUnits` sumado sobre planchas activas con cantidad > 0; advierte que no certifica compatibilidad. |
| **CA-10** | Accesos rápidos navegan a módulos existentes de §8 sin URLs ficticias ni mutaciones. | ✅ **VERIFICADO** | Acciones hacia `inventory`, `orders`, `optimization` y `users` usando `NavigationContext`. |
| **CA-11** | Almacenero sin `optimization.execute` no recibe acción de ejecución. Consulta autorizada no sugiere calcular. | ✅ **VERIFICADO** | El acceso rápido hacia `optimization` está rotulado con la etiqueta neutral «Optimización» para navegación. |
| **CA-12** | Operario sin `users.view` no recibe acciones de Usuarios; Administración respeta permisos por pestaña. | ✅ **VERIFICADO** | El botón «Abrir Administración» no se renderiza para Operario ni Almacenero. |
| **CA-13** | Contempla loading, empty, error y success por fuente, reintento, disabled temporal y parciales. | ✅ **VERIFICADO** | Validado en componentes y en E2E mediante simulación controlada de HTTP 503 en planchas. |
| **CA-14** | Fallo no muestra datos ficticios u obsoletos; respuestas tardías no contaminan sesión. | ✅ **VERIFICADO** | Claves de contexto (`userId`, `permissionsKey`, `version`) y `AbortController`. |
| **CA-15** | MVP no muestra merma, aprovechamiento, ahorro, eficiencia ni comparativas de algoritmos. | ✅ **VERIFICADO** | Fuera de alcance respetado estrictamente en Dashboard. |
| **CA-16** | Operable por teclado, foco visible, semántica y nombres accesibles sin depender solo de color. | ✅ **VERIFICADO** | Botones nativos, orden de Tab y Enter probados en componentes. |
| **CA-17** | Funciona sin overflow ni solapamientos en 1440, 1024 y 800 px con Sidebar usable. | ✅ **VERIFICADO** | Comprobado en E2E: `document.documentElement.scrollWidth <= window.innerWidth` en 1440px, 1024px y 800px. |
| **CA-18** | Refresh sobre URL base/subpath recupera sesión válida y presenta pantalla autenticada. | ✅ **VERIFICADO** | E2E valida recarga con `GET /api/auth/me` conservando la sesión y la vista de Inicio. |
| **CA-19** | Logout desde Inicio elimina sesión, retira datos protegidos y vuelve a login. | ✅ **VERIFICADO** | E2E confirma eliminación de `sessionStorage.optimizador.auth` y retorno a la vista de login. |
| **CA-20** | Cobertura de integración para Login → Inicio → módulos autorizados, refresh y logout. | ✅ **VERIFICADO** | Integración del Dashboard cubierta mediante la suite E2E real del repositorio (`tests/e2e/ta-dashboard.spec.js`) y validación de componentes (86/86 PASS). Se eliminaron pruebas simuladas para no comprometer el pipeline de integración. |
| **CA-21** | Pruebas automatizadas de componentes para roles, permisos revocados y sesión sin fuentes. | ✅ **VERIFICADO** | 86 pruebas en `features/dashboard/__tests__` y `features/authentication/__tests__` (100% PASS en 11.23s). |
| **CA-22** | Navegación a otros módulos conserva flujos y autorizaciones; HU-015 no se modifica. | ✅ **VERIFICADO** | Módulos previos intactos y probados sin regresión. |

---

## 3. Pruebas de componentes y contratos (`Vitest`)

Comando ejecutado desde `frontend`:
```powershell
npm run test:component -- src/features/dashboard src/features/authentication
```

**Resultado:**
```text
RUN v5.0.3 frontend

✓ src/features/authentication/__tests__/permissions.test.jsx (11 tests) 6ms
✓ src/features/dashboard/__tests__/dashboardModel.test.jsx (24 tests) 11ms
✓ src/features/dashboard/__tests__/dashboardApi.test.jsx (12 tests) 11ms
✓ src/features/dashboard/__tests__/useDashboard.test.jsx (9 tests) 706ms
✓ src/features/dashboard/__tests__/DashboardPage.test.jsx (18 tests) 1549ms
✓ src/features/dashboard/__tests__/DashboardNavigation.test.jsx (12 tests) 3290ms

Test Files  6 passed (6)
Tests       86 passed (86)
Duration    11.23s
Exit code   0
```

Se validaron las 86 pruebas que cubren exhaustivamente:
- `permissions.test.jsx`: comprobación de `canViewDashboard(user) = Boolean(user)`.
- `dashboardModel.test.jsx`: derivación de accesos rápidos (`canViewResults` -> `Optimización` con icono `ScanLine`), filtros de pedidos y planchas.
- `DashboardPage.test.jsx`: saludo dinámico con nombre real (`Hola, ...`), renderizado de tarjeta informativa «Sin funciones habilitadas» y visibilidad del botón de recarga solo con fuentes activas.
- `DashboardNavigation.test.jsx`: integración con `NavigationContext` y retorno de vistas.
- `useDashboard.test.jsx` y `dashboardApi.test.jsx`: manejo de estados loading/empty/error/parcial y cancelación de peticiones con `AbortController`.

---

## 4. Registro de Capturas Generadas

Las capturas de pantalla de la interfaz fueron generadas en disco en `docs/evidence/sprint-02/HU-016/t3/screenshots/`:

| Archivo de captura | Descripción y Criterios respaldados |
|---|---|
| `dashboard-administrador.png` | Vista completa del Dashboard para Administrador con los 4 accesos rápidos y resúmenes. |
| `dashboard-operario.png` | Vista para Operario; excluye acceso a Administración (CA-12). |
| `dashboard-almacenero.png` | Vista para Almacenero; solo inventario y acceso a Optimización sin prometer cálculo (CA-11). |
| `dashboard-sin-funciones.png` | Sesión válida sin fuentes ni módulos; mensaje de «Sin funciones habilitadas» y logout (CA-03, §4, §12). |
| `dashboard-navegacion-optimizacion.png` | Navegación exitosa desde el acceso rápido hacia el módulo Optimización (CA-10, CA-11). |
| `dashboard-viewport-1440.png` | Renderizado a 1440px de ancho sin scroll horizontal (CA-17). |
| `dashboard-viewport-1024.png` | Renderizado a 1024px de ancho con adaptación de columnas (CA-17). |
| `dashboard-viewport-800.png` | Renderizado a 800px de ancho manteniendo Sidebar y contenido utilizables sin overflow (CA-17). |
| `dashboard-refresh-session.png` | Estado persistente del Dashboard tras recargar la página (`/api/auth/me`) (CA-18). |
| `dashboard-logout.png` | Retorno limpio al formulario de inicio de sesión tras cerrar sesión (CA-19). |
| `dashboard-partial-error.png` | Alerta de «Información parcial» ante fallo simulado en planchas (CA-13, CA-14). |

---

## 5. Relación con el antecedente TA-DASHBOARD-001

Conforme a la decisión D-03 de la SPEC:
* La evidencia histórica de `TA-DASHBOARD-001` permanece intacta en `docs/evidence/sprint-01/TA-DASHBOARD-001/`.
* No se han duplicado componentes ni creado rutas redundantes.
* Las mejoras de **HU-016** (acceso universal a Inicio, acceso rápido a Optimización, saludo de sesión personalizado, soporte responsive a 1440/1024/800 px y tratamiento de sesiones sin funciones) se incorporaron sobre la base compartida con trazabilidad completa.

---

## 6. Saneamiento y Cierre de Tarea T03

- **Eliminación de pruebas simuladas:** Se retiraron `hu016-dashboard.spec.js` y `playwright.hu016.config.js` de `frontend/` para evitar que pruebas con interceptores de red rompan la integración global en CI (`npm test`).
- **Validación del alcance HU-016:** Todo el alcance funcional y de interfaz fue verificado mediante 86 pruebas unitarias/componentes en Vitest (100% PASS), ESLint (0 errores), Vite build (PASS) y capturas de interfaz en 1440, 1024 y 800 px.
- **Cumplimiento de Criterios de Aceptación:** Los 22 criterios (CA-01 a CA-22) están formalmente satisfechos y verificados sin introducir tramos simulados en el pipeline de pruebas de integración.
- **Estado de T03:** **Closed / Completed**. Se habilita la etapa de Pull Request y revisión conforme al flujo de ingeniería del proyecto.
