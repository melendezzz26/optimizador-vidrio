# Modelo de calidad de NewGlass — ISO/IEC 25010:2023

| Campo | Valor |
|---|---|
| Tarea | EN-QA-001 |
| SPEC | [SPEC-EN-QA-001](../specs/SPEC-EN-QA-001-modelo-calidad-iso25010.md) |
| Versión | 1.2 (V-19 agregado por TA-QA-006; ver historial) |
| Estado | Pendiente de revisión de Andro Joseph Quispe Cesias |
| Responsable | Fabricio Danniel Aguilar Chavez (`fabrilar1`) |
| Base auditada | `integration-02` en `f46d96d` |
| Fecha | 10/11/2026 |
| Relacionado | [Matriz de métricas TA-QA-001](TA-QA-001-matriz-metricas-iso25023.md) |

## 1. Propósito y cómo leer este documento

Este modelo dice **qué significa calidad para NewGlass**. Para cada una de las nueve
características de la ISO/IEC 25010:2023 indica qué módulos afecta, qué puede salir mal
en este sistema, cómo se evaluará, qué tarea QA del sprint es responsable y qué
evidencia existe hoy en el repositorio.

La matriz de TA-QA-001 dice **cómo se mide** (fórmulas, unidades, protocolos). Este modelo
es su marco: la sección 5 valida qué características quedan cubiertas por esas métricas
y qué vacíos hay.

Tipos de evaluación usados:

- **Prueba**: verificación automatizada (pytest, Vitest, `node --test`, Playwright).
- **Medición**: dato cuantitativo obtenido con un protocolo reproducible.
- **Revisión**: inspección de documentos, código o configuración.

No se declara certificación, conformidad ni acreditación. Las metas y umbrales son
propuestas del proyecto, no requisitos de la norma.

## 2. Nota terminológica

- Las definiciones son **paráfrasis propias**; no se copia texto de la norma.
- Los nombres en español son traducción del equipo; se indica el nombre en inglés entre
  paréntesis para evitar ambigüedad. Antes del informe TA-QA-010 conviene cotejarlos con
  el texto oficial.
- Una subcaracterística marcada **"a confirmar"** es aquella cuya pertenencia o nombre en
  la edición 2023 no se pudo verificar con certeza.
- "Seguridad" se refiere a la protección de la información y del acceso (*security*).
  "Seguridad operacional" se refiere a evitar daños a personas, material o equipos
  (*safety*). Son características distintas.
- Trazabilidad de material no es una característica ISO independiente: se trata como parte
  de la adecuación funcional (completitud) y de la seguridad (rendición de cuentas).

## 3. Matriz resumen

| # | Característica | Subcaracterísticas relevantes para NewGlass | Módulos principales | Evaluación | Tarea QA | Prioridad |
|---|---|---|---|---|---|---|
| 1 | Adecuación funcional | Completitud, corrección, pertinencia | orders, inventory, optimization, results, clients | Prueba + revisión | TA-QA-003 | Crítica |
| 2 | Eficiencia de desempeño | Comportamiento temporal, uso de recursos, capacidad | optimization, results, configuration | Medición | TA-QA-002 | Alta |
| 3 | Compatibilidad | Coexistencia, interoperabilidad | todos (API REST + BD compartida), optimization (contratos) | Prueba + revisión | TA-QA-008 | Media |
| 4 | Capacidad de interacción | Operabilidad, protección contra errores del usuario, inclusividad, asistencia al usuario, autodescriptividad | frontend: orders, inventory, optimization, users, clients, dashboard, authentication | Prueba + medición | TA-QA-005 | Media |
| 5 | Fiabilidad | Ausencia de fallos, disponibilidad, tolerancia a fallos, recuperabilidad | optimization, orders, inventory, results | Prueba + medición | TA-QA-004 | Crítica |
| 6 | Seguridad | Confidencialidad, integridad, autenticidad, rendición de cuentas, no repudio, resistencia | authentication, users, todos los endpoints, inventory, configuration | Prueba + revisión | TA-QA-006 | Crítica |
| 7 | Mantenibilidad | Modularidad, reusabilidad, analizabilidad, modificabilidad, capacidad de prueba | todos, en especial optimization | Prueba + medición + revisión | TA-QA-007 | Media |
| 8 | Flexibilidad | Adaptabilidad, escalabilidad, instalabilidad, reemplazabilidad | configuration, optimization, despliegue, frontend responsive | Prueba + medición + revisión | TA-QA-008 | Media |
| 9 | Seguridad operacional | Restricción operativa, identificación de riesgos, falla segura, advertencia de peligro, integración segura | optimization, inventory, orders, results | Prueba + revisión | TA-QA-009 | Crítica |

Todas las características alimentan el informe consolidado **TA-QA-010** (todo el equipo).
TA-QA-001 (Andro) define las métricas que usan las demás tareas.

## 4. Matriz por característica

### 4.1 Adecuación funcional (*functional suitability*)

| Campo | Contenido |
|---|---|
| Definición | Grado en que el sistema ofrece las funciones que los usuarios necesitan y las ejecuta con resultados correctos, sin pasos de más. |
| Subcaracterísticas | **Completitud** (*functional completeness*): las HU del backlog están cubiertas. **Corrección** (*functional correctness*): patrones de corte válidos y stock correcto. **Pertinencia** (*functional appropriateness*): el flujo pedido → optimización → confirmación no exige pasos innecesarios. |
| Módulos | orders, inventory, optimization, results, clients, configuration; dashboard (frontend). |
| Riesgos | Un motor coloca una pieza fuera de la plancha o encima de otra. Un motor no cumple su política (por ejemplo, Worst Fit abría una plancha por pieza, defecto corregido en S2-WF-CARGA). Una pieza imposible se informa como colocada. La importación masiva (HU-018) acepta una fila inválida. Confirmar descuenta un stock distinto al patrón aprobado. |
| Evaluación | **Prueba**: escenarios controlados por motor con oráculo independiente (AF-01 a AF-12). **Revisión**: cotejo de HU implementadas contra Notion para la completitud. |
| Tarea QA | TA-QA-003 (Andro / Melendez). Métricas MF-01, MF-02 y MF-03; trazabilidad MT-01 y MT-02 (HU-MAT-001). |
| Evidencia existente | [SPEC-TA-QA-003](../specs/SPEC-TA-QA-003-adecuacion-funcional.md) y [evidencia con JUnit](../evidence/sprint-02/TA-QA-003/README.md). [SPEC-ACADEMIC-800](../specs/SPEC-ACADEMIC-800-metodos-independientes.md). [Evidencia HU-018](../evidence/sprint-02/HU-018/README.md). [S2-WF-CARGA](../evidence/sprint-02/S2-WF-CARGA/README.md). Pruebas: `backend/tests/unit/optimization/test_ta_qa_003_common.py`, `test_first_fit.py`, `test_best_fit.py`, `test_worst_fit.py`, `test_hole_filling.py`, `test_best_residual_fit.py`, `test_beam_search*.py`, `test_confirmation.py`; `backend/tests/integration/optimization/test_*_slice.py`; E2E `frontend/tests/e2e/optimization-policy-audit.spec.js`, `hu018-bulk-import.spec.js`. Trazabilidad: [HU-014](../evidence/sprint-01/HU-014/README.md), `frontend/src/features/optimization/__tests__/MaterialTrace.test.jsx`, `frontend/src/features/inventory/__tests__/RemnantOrigin.test.jsx`. |
| Vacíos | MF-01 a MF-03 sin medir. Sin evidencia de completitud frente al backlog de Notion. |

### 4.2 Eficiencia de desempeño (*performance efficiency*)

| Campo | Contenido |
|---|---|
| Definición | Grado en que el sistema responde en tiempos aceptables y usa CPU, memoria y almacenamiento de forma proporcionada a la carga que recibe. |
| Subcaracterísticas | **Comportamiento temporal** (*time behaviour*): tiempo por motor y de la comparación completa. **Uso de recursos** (*resource utilization*): RSS del servidor y de los trabajadores. **Capacidad** (*capacity*): mayor cantidad de piezas que cada motor resuelve dentro de los límites. |
| Módulos | optimization (seis motores, rasterización, supervisor de comparación), results (eventos visuales), configuration (límites L-xx y plazos). |
| Riesgos | La comparación de seis motores no termina dentro del plazo global de 900 s. El RSS supera la memoria del contenedor de Heroku y el proceso se reinicia. La rasterización falla con muchas piezas (`RasterPreparationError`, visto con 200 piezas en WF v1). M6 agota su presupuesto de estado o tiempo con planchas grandes. El cuello en `SheetLayout.first_position` reaparece con círculos y polígonos. |
| Evaluación | **Medición**: latencia, p50/p95, pico de RSS, ejecuciones completas y capacidad observada por escala, con protocolo P de TA-QA-001 en Linux aislado. **Prueba**: límites de admisión y presupuestos (`test_load_budget.py`, `test_run_load_limits*.py`). |
| Tarea QA | TA-QA-002 (Luis / Melendez). Métricas MP-01 a MP-04 y MP-06. |
| Evidencia existente | [comparison-performance.md](../comparison-performance.md). [resource-profile-800.md](../resource-profile-800.md). [S2-WF-CARGA](../evidence/sprint-02/S2-WF-CARGA/README.md). [ACADEMIC-800](../evidence/sprint-02/ACADEMIC-800/README.md). [TA-037](../evidence/sprint-02/TA-037/README.md). [SPEC-TA-037](../specs/SPEC-TA-037-control-carga-optimizador.md). Scripts: `backend/scripts/benchmark_load_engines.py`, `benchmark_academic_800.py`, `profile_comparison_http.py`. Workflow `.github/workflows/resource-profile.yml`. Pruebas: `backend/tests/unit/optimization/test_resource_profile.py`, `test_load_budget.py`, `test_beam_memory*.py`; `backend/tests/api/optimization/test_run_load_stress.py`, `test_resource_profile_api.py`. |
| Vacíos y desfases | Mediciones de una sola corrida, sin p95 con 100 repeticiones (MP-03), tomadas en Linux/WSL y no en Heroku. **S2-WF-CARGA y SPEC-TA-053 describen el respaldo First Fit de M6 que el PR #108 eliminó** (M6 vuelve a ser nativo): su actualización corresponde a TA-QA-002 / TA-QA-003. SPEC-TA-037 v1.4 fijaba L-03 = 300 unidades, mientras ACADEMIC-800 admite 800: **corregido en este PR** (SPEC-TA-037 v1.5, V-17). |

### 4.3 Compatibilidad (*compatibility*)

| Campo | Contenido |
|---|---|
| Definición | Grado en que el sistema intercambia información con otros componentes y funciona compartiendo entorno con ellos sin perjudicarlos. |
| Subcaracterísticas | **Coexistencia** (*co-existence*): el backend convive con otras ramas y entornos sobre la BD compartida y los recursos del contenedor. **Interoperabilidad** (*interoperability*): frontend (GitHub Pages) y backend (Heroku) se entienden mediante los contratos REST/JSON versionados. |
| Módulos | Todos los módulos a través de la API; optimization (contratos de comparación v1/v2); authentication (JWT entre frontend y backend); BD compartida en Supabase. |
| Riesgos | El frontend publicado usa un contrato distinto al backend desplegado, porque el despliegue del backend es manual. Una migración de otra rama altera la BD compartida. Un navegador distinto de Chromium no muestra el lienzo o la vista 3D. |
| Evaluación | **Prueba**: pruebas de contrato v1/v2 y E2E en navegadores acordados. **Revisión**: versión de contrato publicada frente a la desplegada y procedimiento de BD compartida. |
| Tarea QA | TA-QA-008 (Andro: compatibilidad). Métrica MC-01. |
| Evidencia existente | Contratos [comparison-v1](../contracts/optimization/comparison-v1.md) y [comparison-v2](../contracts/optimization/comparison-v2.md). Pruebas: `backend/tests/unit/optimization/test_comparison_contract.py`, `test_comparison_v2_contract.py`; `frontend/src/features/optimization/__tests__/ComparisonV2Contract.test.jsx`, `ComparisonContract.test.jsx`, `VisualContract.test.jsx`. BD compartida: [refactor-shared-database.md](../database/refactor-shared-database.md), [EN-001](../evidence/sprint-01/EN-001/shared-database-validation.md). Staging: `backend/tests/integration/test_staging_bootstrap.py`, `frontend/tests/unit/staging.test.js`. |
| Vacíos | Playwright solo ejecuta **Chromium** (`frontend/playwright.config.js`: escritorio 1440 px y móvil 390 px); sin Edge, Firefox ni Safari. Interoperabilidad sin métrica en TA-QA-001. |

### 4.4 Capacidad de interacción (*interaction capability*)

En la edición 2011 esta característica se llamaba *usabilidad*.

| Campo | Contenido |
|---|---|
| Definición | Grado en que usuarios concretos (administrador, almacenero, operario) pueden usar el sistema para cumplir sus tareas de forma eficaz, con comprensión, sin cometer errores evitables y sin barreras de acceso. |
| Subcaracterísticas | **Operabilidad** (*operability*): registrar pedido, importar piezas, optimizar y confirmar con teclado y ratón. **Protección contra errores del usuario** (*user error protection*): validaciones de formulario y confirmaciones. **Inclusividad** (*inclusivity*) y **asistencia al usuario** (*user assistance*): en 2011 se agrupaban como accesibilidad (labels, foco visible, contraste, 390 px). **Autodescriptividad** (*self-descriptiveness*): la interfaz explica por sí sola el estado de una corrida (parcial, sin solución, límite). También existen reconocimiento de adecuación, aprendizaje y compromiso del usuario (*user engagement*); no se priorizan en este sprint. |
| Módulos | Frontend: orders (registro, polígonos, importación masiva), inventory, optimization (comparación y resultados), users, clients, dashboard, authentication (login). |
| Riesgos | El operario no puede crear un polígono sin ratón (corregido en TA-046). El panel de importación no indica qué archivo se cargó ni avisa si falta cliente (pendiente de HU-018). Desbordamiento horizontal a 390 px. El usuario no distingue un resultado parcial de M6 de uno completo. Mensajes de error técnicos o en inglés. |
| Evaluación | **Prueba**: E2E con teclado, pruebas de foco y componentes de feedback. **Medición**: tareas completadas, tiempo por tarea y tasa de errores con participantes (protocolo U). **Revisión**: auditoría de accesibilidad con herramienta automática y checklist WCAG. |
| Tarea QA | TA-QA-005 (Luis). Métricas MU-01 a MU-05. |
| Evidencia existente | [TA-046](../evidence/sprint-02/TA-046/README.md) (K-01 a K-06). [SPEC-EN-006](../specs/SPEC-EN-006-ui-componentes-compartidos.md) y [feedback-compartido.md](../ui-ux/feedback-compartido.md). Capturas por viewport de [HU-016](../evidence/sprint-02/HU-016/t3-integracion-e2e-cierre.md) en `docs/evidence/sprint-02/HU-016/t3/`. Pruebas: `frontend/src/features/orders/__tests__/KeyboardFocus.test.jsx`, `NuevoPedidoFeedback.test.jsx`; `frontend/src/shared/components/__tests__/`; `frontend/src/features/optimization/__tests__/LoadControlFeedback.test.jsx`, `AdmissionDiagnostic.test.jsx`; E2E `ta046-keyboard.spec.js`, `ta037-load-feedback.spec.js`. |
| Vacíos | Sin auditoría automática **axe / WCAG**. Sin prueba con usuarios (MU-01 a MU-03 sin medir). |

### 4.5 Fiabilidad (*reliability*)

| Campo | Contenido |
|---|---|
| Definición | Grado en que el sistema cumple sus funciones sin fallar durante el uso normal y, cuando algo falla, se mantiene operativo o vuelve a un estado coherente sin pérdida de datos. |
| Subcaracterísticas | **Ausencia de fallos** (*faultlessness*, antes *maturity*). **Disponibilidad** (*availability*): backend en Heroku y endpoints de salud. **Tolerancia a fallos** (*fault tolerance*): un motor que falla no derriba la comparación. **Recuperabilidad** (*recoverability*): pedidos y corridas vuelven a un estado coherente tras un timeout, una desconexión o un reinicio. |
| Módulos | optimization (supervisor, trabajadores, admisión, recuperación), orders (estados del pedido), inventory (confirmación transaccional), results. |
| Riesgos | Un pedido queda retenido en optimización tras la caída del proceso. Dos confirmaciones concurrentes descuentan stock dos veces. Un reinicio del contenedor a mitad de una comparación deja la corrida sin cerrar. Un fallo de persistencia guarda `SIN_SOLUCION` en lugar de `FALLIDA`. Tras un merge no se redespliega y la demo muestra una versión anterior. |
| Evaluación | **Prueba**: recuperación, rollback, concurrencia y reinicio HTTP con PostgreSQL de pruebas (corren en el CI). **Medición**: ejecuciones completas sobre iniciadas (MP-05) y disponibilidad del endpoint de salud en una ventana fijada. **Revisión**: procedimiento de recuperación manual (`recover_stopped_run`, `reconcile_stuck_orders`). |
| Tarea QA | TA-QA-004 (Aguilar). Métrica existente: MP-05 (asignada a TA-QA-002). |
| Evidencia existente | TA-049: [S2-TA049-recuperacion-pedidos.md](../reviews/S2-TA049-recuperacion-pedidos.md). TA-037: [admission-lifecycle.md](../evidence/sprint-02/TA-037/admission-lifecycle.md). Scripts: `backend/scripts/recover_stopped_run.py`, `reconcile_stuck_orders.py`. Pruebas: `backend/tests/api/optimization/test_run_recovery.py`, `test_comparison_recovery.py`, `test_comparison_connection_lifecycle.py`; `backend/tests/integration/optimization/test_run_recovery.py`, `test_comparison_v2_http_restart.py`, `test_confirmation_rollback.py`, `test_confirmation_concurrency.py`, `test_start_concurrency.py`, `test_comparison_supervision_v2.py`, `test_stuck_order_reconciliation_pg.py`, `test_run_states.py`; `backend/tests/unit/optimization/test_supervision_contracts.py`, `test_stuck_order_reconciliation_unit.py`; salud: `backend/tests/api/test_health_api.py`, `backend/tests/integration/test_health_database.py`. |
| Vacíos y desfases | **La SPEC-TA-049 no está en `integration-02`**; solo está su review. Se recuperará en TA-QA-004. Una sola métrica de fiabilidad (MP-05). Sin métricas de disponibilidad, tolerancia a fallos ni recuperabilidad. Varias pruebas solo corren en Linux o con PostgreSQL y en Windows se omiten. |

### 4.6 Seguridad (*security*)

| Campo | Contenido |
|---|---|
| Definición | Grado en que el sistema protege la información y las funciones para que cada persona o componente acceda solo a lo que le corresponde según su rol, y en que deja constancia de quién hizo qué. |
| Subcaracterísticas | **Confidencialidad** (*confidentiality*): contraseñas y secretos no se exponen. **Integridad** (*integrity*): solo roles autorizados modifican stock, pedidos y configuración. **Autenticidad** (*authenticity*): JWT firmado, con expiración y claims válidos. **Rendición de cuentas** (*accountability*): movimientos de inventario atribuibles a un usuario. **No repudio** (*non-repudiation*): una confirmación de corte no puede negarse. **Resistencia** (*resistance*, nueva en 2023): el sistema sigue protegido ante intentos de ataque. |
| Módulos | authentication, users (roles y permisos configurables), todos los endpoints (autorización en el backend), inventory (movimientos), configuration (solo administrador), `backend/app/shared/security`. |
| Riesgos | Un operario confirma un corte o cambia la configuración sin permiso. El seed devuelve permisos a un rol vaciado (corregido en TA-039). Un 422 repite la contraseña enviada (corregido en TA-041). El backend arranca sin `SECRET_KEY`. Los source maps publican el código del frontend. Intentos repetidos de login sin límite. La matriz documentada de permisos no coincide con el RBAC configurado. |
| Evaluación | **Prueba**: permisos por endpoint y rol, tokens, contraseñas, sanitización de errores. **Revisión**: matriz de permisos frente al catálogo y el seed, secretos en el repositorio y artefactos publicados, registro de autoría de movimientos. |
| Tarea QA | TA-QA-006 (Aguilar). Sin métricas en TA-QA-001. |
| Evidencia existente | [matriz_permisos.md](../seguridad/matriz_permisos.md). [SPEC-S1-RBAC](../specs/SPEC-S1-RBAC-roles-permisos-configurables.md). [TA-039](../evidence/sprint-02/TA-039/README.md). [TA-041](../evidence/sprint-02/TA-041/README.md). [Source maps TA-DEPLOY-001](../evidence/sprint-01/TA-DEPLOY-001/test-results/security-source-map-js.md). Pruebas: `backend/tests/api/authorization/test_endpoint_permissions.py`, `test_permissions_from_database.py`, `test_roles_api.py`; `backend/tests/api/test_require_permission.py`, `test_auth_api.py`, `test_validation_errors_sanitized.py`; `backend/tests/unit/shared/test_tokens.py`, `test_passwords.py`; `backend/tests/unit/authentication/test_permission_seed.py`, `test_permission_catalog.py`; `frontend/src/features/authentication/__tests__/permissions.test.jsx`, `frontend/src/features/users/__tests__/RolePermissions.test.jsx`. |
| Vacíos | Sin métricas de seguridad en TA-QA-001. `matriz_permisos.md` es una tabla fija Sí/No: a verificar frente al RBAC configurable. Sin pruebas de intentos repetidos de login (resistencia). Rendición de cuentas y no repudio de la confirmación: a verificar. |

### 4.7 Mantenibilidad (*maintainability*)

| Campo | Contenido |
|---|---|
| Definición | Grado en que el equipo puede entender, corregir, cambiar y probar el sistema sin introducir defectos y con un esfuerzo razonable. |
| Subcaracterísticas | **Modularidad** (*modularity*): capas Presentation → Application → Domain por módulo. **Reusabilidad** (*reusability*): componentes de feedback compartidos, reglas comunes de los motores. **Analizabilidad** (*analysability*): diagnosticar un fallo con logs y resúmenes sanitizados. **Modificabilidad** (*modifiability*): cambiar un motor sin romper los demás. **Capacidad de prueba** (*testability*): pruebas por capa y CI reproducible. |
| Módulos | Todos; en especial optimization (el más grande, seis motores y supervisor). |
| Riesgos | El dominio importa FastAPI o SQLAlchemy y rompe la arquitectura. Un cambio en un motor altera otro sin que una prueba lo detecte. Las pruebas exclusivas de Linux no corren en Windows y los defectos aparecen recién en el CI. Las SPEC quedan desactualizadas respecto del código (por ejemplo, el desfase de M6). |
| Evaluación | **Prueba**: dependencias entre capas por módulo y contrato del CI. **Medición**: cobertura, duplicación, complejidad y tasa de éxito del CI (protocolo M). **Revisión**: ADR y SPEC al día. |
| Tarea QA | TA-QA-007 (Melendez). Métricas MM-01 a MM-04. |
| Evidencia existente | [ADR-001](../adr/ADR-001-seleccion-arquitectura.md), [ADR-002](../adr/ADR-002-operacion-pre-raster.md). [Convenciones de pruebas](../testing/README.md). Pruebas: `backend/tests/unit/authentication/test_layer_dependencies.py`, `backend/tests/unit/users/test_layer_dependencies.py`, `backend/tests/unit/clients/test_layer_dependencies.py`, `backend/tests/unit/modules/orders/test_layer_dependencies.py`; `backend/tests/unit/test_ci_contract.py`, `test_backend_failure_summary.py`. Workflow `.github/workflows/ci.yml` (backend, frontend con lint y build, E2E con gate TA-040). |
| Vacíos | Sin prueba de capas en **inventory, optimization, configuration ni results**. Sin **herramienta de cobertura**, duplicación ni complejidad (MM-01 a MM-03 sin herramienta). Una búsqueda en `backend/tests` no encontró pruebas que importen directamente `app.modules.results` ni `app.modules.configuration`: a verificar. |

### 4.8 Flexibilidad (*flexibility*)

En la edición 2011 buena parte de esta característica se llamaba *portabilidad*.

| Campo | Contenido |
|---|---|
| Definición | Grado en que el sistema se adapta a cambios de entorno, de carga o de requisitos, y en que puede instalarse o sustituir partes sin rehacerlo. |
| Subcaracterísticas | **Adaptabilidad** (*adaptability*): funciona en escritorio y en móvil de 390 px, y con distintos límites de contenedor. **Escalabilidad** (*scalability*, nueva en 2023): admite más piezas (de 150 a 300 y luego a 800 unidades) sin cambiar el diseño. **Instalabilidad** (*installability*): levantar el entorno local, staging y Heroku de forma reproducible. **Reemplazabilidad** (*replaceability*): agregar o quitar motores desde el catálogo. |
| Módulos | configuration (configuración publicable, pasos angulares, límites), optimization (catálogo de motores, detección de cgroup), `backend/app/shared/config`, despliegue (Heroku, GitHub Pages), frontend responsive. |
| Riesgos | Cambiar un límite exige tocar código y redesplegar. El comparador no corre en Windows nativo y exige WSL2. Un despliegue nuevo falla porque falta un paso manual. Agregar un séptimo motor (idea M7) obliga a tocar el supervisor y la interfaz. |
| Evaluación | **Prueba**: publicación de configuración y E2E por viewport. **Medición**: pantallas y flujos sin pérdida por viewport (MC-02, MC-03); escala admitida. **Revisión**: instalación limpia siguiendo la documentación. |
| Tarea QA | TA-QA-008 (Andro: adaptabilidad; Aguilar: despliegue reproducible y contratos). Escalabilidad junto con TA-QA-002. Métricas MC-02 y MC-03. |
| Evidencia existente | [S2-angular-configuration](../reviews/S2-angular-configuration.md). [SPEC-TA-043](../specs/SPEC-TA-043-integracion-seis-motores.md) y `backend/app/modules/optimization/application/comparison_catalog.py`. [resource-profile-800.md](../resource-profile-800.md). [SPEC-ACADEMIC-800](../specs/SPEC-ACADEMIC-800-metodos-independientes.md). [staging.md](../infrastructure/staging.md), [SPEC-TA-DEPLOY-001](../specs/SPEC-TA-DEPLOY-001-staging.md), [optimization-wsl2.md](../development/optimization-wsl2.md). Pruebas: `backend/tests/integration/optimization/test_configuration_publication.py`, `test_configuration_seed.py`; `backend/scripts/publish_configuration.py`; E2E en el proyecto `chromium-mobile` (390 px). |
| Vacíos | Sin prueba de instalación limpia reproducible. Adaptabilidad medida solo con dos viewports. Escalabilidad, instalabilidad y reemplazabilidad sin métrica en TA-QA-001. |

### 4.9 Seguridad operacional (*safety*)

Característica nueva en la edición 2023.

| Campo | Contenido |
|---|---|
| Definición | Grado en que el sistema, dentro de su contexto de uso, evita llevar a situaciones que dañen a personas, material o equipos, y avisa cuando existe ese riesgo. En NewGlass: que un plan de corte no lleve a cortar vidrio de forma imposible, peligrosa o con pérdida de material. |
| Subcaracterísticas | **Restricción operativa** (*operational constraint*): márgenes, separación, límites de plancha y rotaciones permitidas. **Identificación de riesgos** (*risk identification*): validaciones previas a la optimización. **Falla segura** (*fail safe*): ante un error no se descuenta stock ni se confirma un resultado parcial. **Advertencia de peligro** (*hazard warning*): avisos antes de una acción irreversible. **Integración segura** (*safe integration*): a confirmar cómo aplica a NewGlass; probablemente la coherencia entre el patrón mostrado al operario y el confirmado. |
| Módulos | optimization (geometría, rasterización, preflight, separación), inventory (confirmación que descuenta stock), orders (validación de piezas y polígonos), results (patrón mostrado al operario). |
| Riesgos | Un patrón con separación o margen insuficiente produce un corte que rompe la plancha. La pieza cortada no coincide con la medida pedida por redondeo (TA-046 muestra ahora las medidas originales). Se confirma un resultado parcial de M6. La simulación modifica inventario. Se aceptan polígonos no convexos o fuera de rango. |
| Evaluación | **Prueba**: rechazo de casos inválidos, ausencia de falsas aceptaciones, margen y separación, no elegibilidad de parciales, confirmación transaccional. **Revisión**: avisos y confirmaciones en la interfaz antes de descontar stock. |
| Tarea QA | TA-QA-009 (Melendez / Luis). Métricas MS-01 a MS-03. |
| Evidencia existente | [SPEC-TA-007](../specs/SPEC-TA-007-validacion-geometrica.md), [SPEC-TA-045](../specs/SPEC-TA-045-separacion-corte.md), [SPEC-TA-036](../specs/SPEC-TA-036-saneamiento-funcional.md), [SPEC-HU-007-T03](../specs/SPEC-HU-007-T03-validar-poligono-convexo.md), [SPEC-ACADEMIC-800](../specs/SPEC-ACADEMIC-800-metodos-independientes.md) (parcial de M6 no confirmable). Pruebas: `backend/tests/unit/optimization/test_geometric_preflight.py`, `test_run_geometry.py`, `test_ta045_separation.py`, `test_commercial_raster.py`, `test_confirmation.py`; `backend/tests/optimization/test_placement.py`; `backend/tests/api/optimization/test_commercial_cut.py`, `test_comparison_v2_preflight.py`, `test_run_geometry_api.py`; `backend/tests/integration/optimization/test_confirmation_rollback.py`; `frontend/tests/unit/convexityValidation.test.js`; `frontend/src/shared/components/__tests__/ConfirmDialog.test.jsx`. |
| Vacíos | MS-01 a MS-03 sin medir. Sin evidencia de advertencias de peligro específicas (por ejemplo, aviso antes de confirmar un corte). Integración segura a confirmar. |

## 5. Validación de TA-QA-001

Revisión de la [matriz de TA-QA-001](TA-QA-001-matriz-metricas-iso25023.md) contra este
modelo, sobre la base auditada. **No se modifica la matriz**: los vacíos se asignan a la
tarea QA que debe cubrirlos.

### 5.1 Cobertura por característica

| Característica | Métricas TA-QA-001 | Cobertura | Observación |
|---|---|---|---|
| Adecuación funcional | MF-01, MF-02, MF-03 (+ MT-01, MT-02) | Buena para corrección | Completitud y pertinencia sin métrica. |
| Eficiencia de desempeño | MP-01 a MP-04, MP-06 | Buena | Cubre tiempo, recursos y capacidad. |
| Compatibilidad | MC-01 | Parcial | MC-01 mide navegadores, pero lo clasifica como coexistencia. En este modelo eso se acerca más a interoperabilidad o adaptabilidad. Revisarlo con Andro. |
| Capacidad de interacción | MU-01 a MU-05 | Buena para operabilidad y foco | MU-04 y MU-05 usan "Accesibilidad", nombre de la edición 2011. En 2023 corresponde a inclusividad y asistencia al usuario. |
| Fiabilidad | MP-05 | **Insuficiente** | Una sola métrica, asignada a TA-QA-002. |
| Seguridad | — | **Sin cobertura** | La matriz declara que no evalúa seguridad. |
| Mantenibilidad | MM-01 a MM-04 | Buena en definición | MM-01 a MM-03 sin herramienta elegida. |
| Flexibilidad | MC-02, MC-03 | Parcial | Solo adaptabilidad. |
| Seguridad operacional | MS-01 a MS-03 | Buena para restricción operativa | Falla segura y advertencia sin métrica. |

### 5.2 Vacíos y tarea que debe cubrirlos

| ID | Vacío | Tarea QA |
|---|---|---|
| V-01 | Sin métricas de seguridad: permisos por rol y endpoint, tokens, secretos, sanitización, resistencia. | TA-QA-006 |
| V-02 | Una sola métrica de fiabilidad (MP-05, asignada a TA-QA-002); faltan disponibilidad, tolerancia a fallos y recuperabilidad. | TA-QA-004 (MP-05 se mantiene en TA-QA-002) |
| V-03 | MF-01 a MF-03 en estado DEFINIDA, sin medir. | TA-QA-003 |
| V-04 | MP-01 a MP-06 en estado DEFINIDA, sin medir. | TA-QA-002 |
| V-05 | MC-01 a MC-03 en estado DEFINIDA, sin medir. | TA-QA-008 |
| V-06 | MU-01 a MU-05 en estado DEFINIDA, sin medir. | TA-QA-005 |
| V-07 | MM-01 a MM-04 en estado DEFINIDA, sin medir. | TA-QA-007 |
| V-08 | MS-01 a MS-03 en estado DEFINIDA, sin medir. | TA-QA-009 |
| V-09 | E2E solo en Chromium; MC-01 no puede medir Edge u otros navegadores sin ampliar Playwright o hacer pruebas manuales. | TA-QA-008 |
| V-10 | Sin auditoría automática axe / WCAG. | TA-QA-005 |
| V-11 | Sin prueba de dependencias entre capas en inventory, optimization, configuration y results. | TA-QA-007 |
| V-12 | Sin herramienta de cobertura de código (y tampoco de duplicación ni complejidad). | TA-QA-007 |
| V-13 | Interoperabilidad (contratos v1/v2 publicados frente a desplegados) sin métrica. | TA-QA-008 |
| V-14 | Escalabilidad, instalabilidad y reemplazabilidad sin métrica. | TA-QA-008 (instalación reproducible) y TA-QA-002 (escalabilidad) |
| V-15 | Completitud funcional frente al backlog de Notion sin métrica. | TA-QA-003 |
| V-16 | Falla segura y advertencia de peligro sin métrica. | TA-QA-009 |
| V-17 | Desfase de L-03: SPEC-TA-037 decía 300 unidades frente a 800 en ACADEMIC-800 (PR #108). **Corregido en este PR** ([SPEC-TA-037](../specs/SPEC-TA-037-control-carga-optimizador.md) v1.5). | EN-QA-001 |
| V-18 | Desfases de evidencia pendientes: SPEC-TA-049 ausente en `integration-02`; respaldo de M6 descrito en S2-WF-CARGA y SPEC-TA-053. | TA-QA-004 (TA-049); TA-QA-002 / TA-QA-003 (M6) |
| V-19 | Resistencia sin control: `POST /api/auth/login` no limita los intentos fallidos por cuenta ni por origen (hallazgo H-01 de TA-QA-006). Mitigaciones actuales: mensaje único, bcrypt y validación de formato. Falta decidir la regla (umbral, ventana y bloqueo temporal) y su métrica. | Por asignar (nueva tarea del backlog; fuera de TA-QA-006) |

Todas las métricas siguen en estado **DEFINIDA**; el informe TA-QA-010 debe distinguir
lo definido de lo medido.

## 6. Prioridades para NewGlass

| Prioridad | Característica | Por qué |
|---|---|---|
| Crítica | Adecuación funcional | Es el propósito del sistema: un plan de corte incorrecto o que no respeta la política del motor invalida la comparación de heurísticas, que es el núcleo académico del proyecto. |
| Crítica | Seguridad operacional | El plan se traduce en cortes reales de vidrio. Un margen o una separación mal aplicados, o un parcial confirmado, provocan pérdida de material y manipulación de vidrio roto. |
| Crítica | Fiabilidad | La confirmación descuenta stock. Un fallo a mitad de una corrida no puede dejar pedidos retenidos ni descontar dos veces; además, el despliegue es manual y en un solo proceso web. |
| Crítica | Seguridad | Tres roles con permisos distintos sobre stock y configuración. La autorización vive en el backend y hubo defectos reales (TA-039, TA-041). |
| Alta | Eficiencia de desempeño | Fue la observación principal del profesor (revisión del 04/11/2026): seis motores, 900 s globales, 120 s por motor y hasta 800 unidades en un contenedor con memoria limitada. |
| Media | Capacidad de interacción | El operario trabaja con formas complejas y necesita poder hacerlo con teclado y en pantallas pequeñas; ya hay base con TA-046 y EN-006. |
| Media | Mantenibilidad | Cuatro integrantes trabajando en paralelo sobre un monolito modular; la arquitectura por capas ya está definida, pero no se verifica en todos los módulos. |
| Media | Flexibilidad | Los límites y motores cambian con frecuencia (150 → 300 → 800 unidades; seis motores, posible M7), aunque el entorno de despliegue es fijo. |
| Media | Compatibilidad | Una sola API propia y una BD compartida; el riesgo principal es el desfase entre frontend y backend desplegados. |

## 7. Nota sobre ISO/IEC 25023:2016 y ISO/IEC 25010:2023

La ISO/IEC 25023:2016, que define medidas de calidad de producto, está alineada con el
modelo de la **ISO/IEC 25010:2011**, no con el de 2023. Por eso las métricas de TA-QA-001
basadas en 25023 deben **adaptarse** cuando la característica o subcaracterística es nueva
o cambió de nombre:

| 25010:2011 | 25010:2023 | Efecto en las métricas |
|---|---|---|
| Usabilidad | Capacidad de interacción | Reasignar MU-01 a MU-05 con el nombre nuevo. |
| Accesibilidad (subcaracterística) | Inclusividad + asistencia al usuario | MU-04 y MU-05 deben indicar a cuál de las dos corresponden. |
| Estética de la interfaz | Compromiso del usuario | Sin métrica en este sprint. |
| — | Autodescriptividad (nueva) | 25023:2016 no trae medida; definirla en el proyecto si se evalúa. |
| Madurez | Ausencia de fallos | Adaptar el nombre en métricas de fiabilidad. |
| — | Resistencia (seguridad, nueva) | Sin medida en 25023:2016; definirla en TA-QA-006. |
| Portabilidad | Flexibilidad | MC-02 y MC-03 quedan bajo flexibilidad (adaptabilidad). |
| — | Escalabilidad (nueva) | Sin medida en 25023:2016; puede apoyarse en MP-06 (capacidad observada). |
| — | Seguridad operacional (nueva) | Sin medidas en 25023:2016; MS-01 a MS-03 son propuestas del proyecto. |

Las medidas propias del proyecto deben declararse como tales y no atribuirse a la norma.

## 8. Referencias internas

- [SPEC-EN-QA-001](../specs/SPEC-EN-QA-001-modelo-calidad-iso25010.md)
- [Matriz TA-QA-001](TA-QA-001-matriz-metricas-iso25023.md) · [SPEC-TA-QA-001](../specs/SPEC-TA-QA-001-metricas-calidad-iso25023.md)
- [SPEC-TA-QA-003](../specs/SPEC-TA-QA-003-adecuacion-funcional.md)
- [Convenciones de pruebas](../testing/README.md)
- [Convenciones de evidencia](../evidence/README.md)

## 9. Historial

| Fecha | Versión | Origen | Cambio |
|---|---|---|---|
| 10/11/2026 | 1.0 | EN-QA-001 | Creación del modelo: nueve características, validación de TA-QA-001 (V-01 a V-18), prioridades y nota 25023/25010. |
| 10/11/2026 | 1.1 | EN-QA-001 | V-17 corregido en SPEC-TA-037 (L-03 = 800 unidades). |
| 10/11/2026 | 1.2 | TA-QA-006 | Nuevo vacío V-19 (login sin límite de intentos, resistencia), desde el hallazgo H-01 de [SPEC-TA-QA-006](../specs/SPEC-TA-QA-006-seguridad-permisos.md). Ningún otro cambio en el modelo. |
