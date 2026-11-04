# PLAN-TA-043 — Integración y validación conjunta de seis motores

## Información general

| Campo | Valor |
|---|---|
| Estado | **Draft — B02 autorizado; resultado pendiente de revisión** |
| SPEC | [SPEC-TA-043-integracion-seis-motores.md](SPEC-TA-043-integracion-seis-motores.md) |
| Responsable | Fabricio Meléndez |
| Reviewer | Por designar; revisión humana pendiente |
| Fecha | 03/11/2026, America/Lima |
| Base oficial | `origin/integration-02`, `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b` |
| Única rama de trabajo | `feature/TA-043-integracion-seis-motores` |
| Autorización actual | Exclusivamente B02, T-02/regresiones pertinentes, ST-INC-02 y commits locales; detenerse antes de B03 |

## 1. Resultado esperado y reglas de ejecución futura

Entregar seis ejecuciones de FF, BF, WF, HF, BRF y BS-2 sobre una entrada común,
con consulta, progreso, métricas, visualización, selección humana y confirmación
transaccional. Conservar v1 de tres motores y `/runs`. El diseño normativo está
en la SPEC; este PLAN lo convierte en bloques con pruebas y evidencia previstas.

La nueva `integration-02` se creó y publicó, por autorización excepcional, desde
el HEAD remoto de `integration/sprint-01`. Ambas se verificaron en el SHA de la
tabla, sin diferencia de commits/árbol. Se confirmaron las seis implementaciones
productivas y los cambios HF `018c9d5`, BRF `393a224` y M6 `5fcc988`.
Las ramas TA-042/TA-052/TA-053 T02 no tienen commits pendientes sobre esa base.
HU-018 sí permanece fuera: PR #96 abierto, HEAD consultado `192c7e7`, 13 commits
propios. No se hará merge ni cherry-pick de ese trabajo en TA-043.

**Flujo obligatorio:** toda TA-043 permanece en la misma rama feature, incluidos
SPEC/PLAN, implementación futura, pruebas, smoke y evidencias. Separar actividades
con commits locales Conventional Commits por bloques validados, nunca mediante
ramas docs/test u otras ramas de fases. Las referencias previas se conservan sin
usarlas para desarrollar. No publicar la feature, fusionar, migrar entornos
compartidos ni desplegar sin autorización. La entrega documental inicial terminó
en Draft; Fabricio autorizó posteriormente solo B01 y su validación. El resultado
se registra en [evidencia B01](../evidence/sprint-02/TA-043/B01/README.md).
Fabricio autorizó posteriormente B02 de forma expresa; su alcance y validaciones
se registran en [evidencia B02](../evidence/sprint-02/TA-043/B02/README.md).
La autorización no se extiende a B03–B11; se detiene al presentar B02.

### 1.1 Agrupaciones de gestión T01, T02 y T03

| Agrupación | Bloques técnicos relacionados |
|---|---|
| T01 — Backend y persistencia multimétodo | B01, B02, B03, B04, B05, B06 y parte backend de B08 |
| T02 — Interfaz de seis motores | B07 y parte frontend de B08 |
| T03 — Regresión y validación conjunta | B09, B10 y B11: validación cruzada de los seis motores sobre las mismas condiciones de entrada, regresión, E2E y smoke integral |

T01–T03 son agrupaciones de gestión; no sustituyen los bloques **B01–B11 como
unidades reales de desarrollo** ni crean tareas de implementación masivas. Se
trabaja bloque por bloque, con implementación, pruebas, smoke cuando corresponda,
evidencias y commits locales. El orden técnico y las dependencias de §3 y §6
tienen prioridad: no es necesario terminar una agrupación completa para iniciar
un bloque cuyas dependencias estén satisfechas. B08 sigue siendo un solo bloque
coordinado, aunque sus partes se relacionen con T01 y T02. Estos identificadores
de gestión no se confunden con las pruebas previstas `T-01`, `T-02` y `T-03` de §2.

## 2. Inventario de módulos y pruebas previstas

En los bloques, **O/** significa `backend/app/modules/optimization/`, **F/**
`frontend/src/features/optimization/`. Son abreviaturas documentales, no carpetas
nuevas. Los archivos marcados «nuevo» son propuestas para la implementación futura.

| Prueba prevista | Nivel / alcance | Ubicación prevista |
|---|---|---|
| T-01 | Catálogo, perfil HTTP y codecs: seis identidades, round-trip histórico y rechazo de incoherencias | `backend/tests/unit/optimization/`, `backend/tests/api/optimization/`; fixtures compartidos en `docs/contracts/optimization/` |
| T-02 | Migración PostgreSQL vacía/con historia, unicidad/FK y downgrade protegido | `backend/tests/integration/optimization/test_comparison_migration.py`, `test_comparison_persistence.py` |
| T-03 | Adaptadores, paridad directa, callbacks, diagnósticos HF/BRF/BS-2 y frontera provisional | `backend/tests/unit/optimization/`, `backend/tests/optimization/` |
| T-04 | Procesos reales, límites por motor/global, cola, RSS/espacio virtual, IPC y retención | `backend/tests/unit/optimization/test_comparison_runner.py`, pruebas de integración focalizadas |
| T-05 | Supervisor: fallos independientes, spawn/DB/IPC/observador, shutdown/reinicio y orden parada/admisión | `backend/tests/integration/optimization/test_comparison_calculation.py`, pruebas de runtime/runner |
| T-06 | API real, aceptación/consulta por clave, permisos, recuperación, selección y cruces de perfil | `backend/tests/api/optimization/`, `backend/tests/integration/optimization/test_comparison_slice.py` |
| T-07 | Componentes/contratos frontend, pestañas, teclado, estados parciales/fallidos, 2D/3D y provisional | `F/__tests__/Comparison*.test.jsx`, `Visual*.test.jsx`, `RunVisualization.test.jsx` |
| T-08 | Confirmación PostgreSQL, selección/versiones, stock concurrente, idempotencia y rollback | `backend/tests/integration/optimization/test_comparison_confirmation.py`, API correspondiente |
| T-09 | E2E real seis motores e historia/legacy, escritorio/móvil, recarga y confirmación | `frontend/tests/e2e/optimization-comparison.spec.js` y spec TA-043 nuevo si conviene |
| T-10 | Regresión FF/BF/WF/HF/BRF/BS-2, reglas SP-002, geometría/rotación/métricas y suites backend/frontend | Directorios actuales de pruebas y gate E2E TA-040 |
| T-11 | Perfil de recursos/latencia/serialización/callbacks y preparación operativa | Harness futuro junto a herramientas de validación; salidas seleccionadas en evidencia TA-043 |
| T-12 | HU-018 condicionado: CSV/XLSX → pedido mixto persistido → seis motores a 5° | Pruebas API/integración orders y E2E tras integración independiente de HU-018 |
| T-13 | Smoke incremental ST-INC sobre servicios reales tras cada bloque funcional ejecutable | Actividad §4; ST-INC-01 implementado y ejecutado; demás entregas pendientes |
| T-14 | Smoke integral ST-INT obligatorio con PostgreSQL aislado y navegador real | Actividad §4; gate de cierre, sin ejecución en esta sesión |

No duplicar casos geométricos entre niveles ni confundir pruebas de fixture con
ejecución real. Las rutas existentes se extienden cuando su alcance corresponda;
no crear una suite paralela que solo replique aserciones internas.

## 3. Bloques incrementales

### B01 — Catálogo y contratos de seis motores

- **Estado del bloque:** alcance técnico y validación en [evidencia B01](../evidence/sprint-02/TA-043/B01/README.md);
  resultado pendiente de revisión de Fabricio. No se habilitan consumidores B02/B03.
- **Objetivo:** fijar identidad y fronteras de v2 sin alterar v1/legacy.
- **Requisitos / CA:** RF-02, RF-11, RF-12, RF-14; CA-02, CA-11, CA-12, CA-14.
- **Archivos/módulos previstos:** `O/application/comparison_contracts.py`, catálogo
  nuevo si procede, `O/presentation/comparison_schemas.py`, schemas v2 nuevos,
  `O/infrastructure/comparison_snapshot.py`, `docs/contracts/optimization/comparison-v2.md`
  y fixture JSON nuevo; `F/comparisonApi.js`, `runContract.js`, `visualContract.js`.
- **Dependencias:** SPEC revisada/autorizada y contratos v1 actuales. Acordar
  payload entre backend/frontend antes de desarrollar consumidores.
- **Pasos concretos:** 1) registrar códigos `FF/BF/WF/HF/M5/M6-BS` y nombres visibles
  FF/BF/WF/HF/BRF/BS-2; 2) separar catálogo por perfil; 3) definir seis ejecuciones,
  despacho, completitud, razón/origen de terminación y capacidades visuales;
  4) especificar `/comparisons-v2`, acceso cruzado y claves idempotentes entre
  perfiles; 5) definir agregado snapshot 2 y resultado snapshot 3 con lectores
  históricos; 6) inventariar todos los hardcodes de tres en runner/UoW/runtime/UI.
- **Pruebas:** T-01 y contratos frontend T-07; fixture v1 intacto, código desconocido,
  duplicado o identidad contradictoria falla. ST-INC-01 si hay entrega ejecutable.
- **Aceptación:** CA-02/11/12/14 cubiertos en contrato; fixture v2 no se presenta
  como prueba de concurrencia y ningún cliente v1 recibe seis por defecto.
- **Puerta de revisión contractual:** al finalizar B01, detenerse para revisión
  de Fabricio antes de implementar consumidores dependientes. Revisar los seis
  nombres oficiales y su correspondencia con códigos de §1.3 de la SPEC,
  comparison-v2, preservación de comparison-v1 y `/runs`, schemas/codecs, estados
  y diagnósticos, semántica de eventos/resultados M6 y compatibilidad prevista
  backend/frontend. Presentar las pruebas contractuales T-01 y las pertinentes
  de T-07, sus resultados/evidencias y cualquier pendiente; registrar la decisión
  del responsable. Sin su aprobación no se avanza a consumidores dependientes.
- **Riesgos:** confundir versiones de perfil/snapshot/configuración/optimismo;
  renombrar BRF/M6 al serializar o codificar seis en todos los consumidores.
- **Evidencias:** catálogo, diff contractual, fixtures con procedencia y resultados
  reales de pruebas futuras, almacenados bajo TA-043.
- **Orden / coordinación:** primero; backend, frontend y responsable de datos
  acuerdan el contrato. Tras aprobar la puerta de revisión, B02, B03 y prototipos
  de B07 pueden desarrollarse independientemente en la misma rama, mediante commits
  coordinados.

### B02 — Compatibilidad histórica y evolución del esquema de datos

- **Objetivo:** permitir historia de tres/seis motores sin reinterpretar filas.
- **Requisitos / CA:** RF-11, RF-13, RF-14; CA-11, CA-13, CA-14.
- **Archivos/módulos previstos:** `backend/app/models.py`, nueva revisión en
  `backend/alembic/versions/`, `O/infrastructure/comparison_snapshot.py`,
  `comparison_uow.py`; pruebas T-02 y documentación de migración futura.
- **Dependencias:** B01; confirmar head Alembic real antes de crear revisión y
  coordinar cualquier cambio concurrente del esquema con su responsable.
- **Pasos concretos:** 1) capturar historia FF snapshot 1 y comparación v1 snapshot
  2 en PostgreSQL aislado antes de migrar; 2) ampliar CHECK de método a seis sin
  tocar migraciones antiguas; 3) conservar FK/unicidad por agregado/método;
  4) persistir perfil/lista/diagnósticos en sobres versionados; 5) leer v1 con su
  cardinalidad y v2 con su catálogo congelado; 6) proteger downgrade antes de DDL
  y documentar rollback operativo deshabilitando creación v2, conservando lectores.
- **Pruebas:** T-01/T-02, upgrade vacío/con historia, round-trip de entrada/resultado,
  métodos ajenos/duplicados, lectura antes/después, downgrade vacío y rechazo con v2;
  ST-INC-02 tras entrega ejecutable.
- **Aceptación:** CA-11/13/14; cero backfill ficticio de motores y datos históricos
  conservados, incluida consulta original y recibos.
- **Riesgos:** lector antiguo sobre filas nuevas, pérdida de diagnóstico parcial,
  varios heads Alembic y bloqueos del CHECK en tablas con historia.
- **Evidencias:** revisión padre/hija real, esquema/constraints, hashes de snapshots
  antes/después y logs de upgrade/rechazo de downgrade en BD propia.
- **Orden / coordinación:** después de B01, independiente de B03/B04; coordinar con
  datos y mantenimiento de lectores. No aplicar migraciones remotas como validación.

### B03 — Adaptadores de ejecución y diagnósticos

- **Objetivo:** conectar los seis motores sin alterar sus decisiones.
- **Requisitos / CA:** RF-04, RF-14–RF-18, RNF-05; CA-04, CA-14–CA-18, CA-N05.
- **Archivos/módulos previstos:** adaptador de motores nuevo en `O/application/`
  o infrastructure según su dependencia; `O/infrastructure/comparison_runner.py`,
  `comparison_transport.py`, `comparison_snapshot.py`; contratos de observación;
  `domain/beam_search.py` únicamente si requiere un puerto neutral de observación.
- **Dependencias:** B01 y código productivo de los seis motores. Acordar con
  Andro la política HF vigente y con Luis Anthony el score/parámetros BRF.
- **Pasos concretos:** 1) factory nueva por ejecución; 2) conectar callbacks
  existentes FF/BF/WF/HF/BRF; 3) adaptar M6 a `run()` para conservar outcome,
  estadísticas y cuatro razones de recursos; 4) propagar checkpoint aun sin UI;
  5) representar progreso de búsqueda sin falsos placements finales; si se exponen
  estados provisionales, reemplazo por estado/revisión; 6) construir presentación
  final desde frontera ganadora sin repetir búsqueda; 7) preservar límites internos
  y eventos de HF solo de su solución elegida.
- **Pruebas:** T-03/T-10, paridad con ejecución directa sin corte temporal, callbacks
  activos/inactivos, cada razón M6, parcial vacío y no-fit, HF fallback/guard y BRF
  residual/desempates; ST-INC-03 mediante servicios cuando el adaptador sea accesible.
- **Aceptación:** CA-04/14–18/N05; no TypeError por `on_visual`, no pérdida de causa,
  mismas decisiones productivas y ningún import de experimentos en aplicación.
- **Riesgos:** telemetría que altera costo/resultado, excepción del observador,
  `optimize()` que elimina diagnóstico y ramas BS sumadas como hechos definitivos.
- **Evidencias:** entradas/hashes, trazas y comparación directa/integrada por motor,
  ejemplos de terminación y timeline provisional/final.
- **Orden / coordinación:** después de B01; puede avanzar independiente de B02.
  Acordar semántica de eventos con frontend antes de B07; no reabrir SP-004 ni DJD.

### B04 — Política de recursos y concurrencia

- **Objetivo:** ejecutar seis métodos bajo capacidad real controlada.
- **Requisitos / CA:** RF-03, RF-04, RNF-01–RNF-03; CA-03/04/N01/N02/N03.
- **Archivos/módulos previstos:** `O/application/comparison_limits.py`,
  `resource_policy.py`, `load_budget.py`, `admission.py`,
  `O/infrastructure/comparison_runner.py`, `in_process_admission.py`,
  `process_lifecycle.py`; diagnóstico `backend/scripts/check_comparison_environment.py`.
- **Dependencias:** B01/B03 para identificar recursos/outcomes. Presupuestos
  existentes son cotas de partida, no nuevas garantías de rendimiento.
- **Pasos concretos:** 1) v2 con un worker activo y cola estable de seis; mantener
  v1 con su comportamiento contractual; 2) admisión compartida FF/v1/v2 en una
  instancia web; 3) startup por proceso, cálculo por motor y deadline global que
  incluye cola; 4) verificar límites internos/exteriores y causa que actuó primero;
  5) sumar supervisor/hijos/reserva/IPC/retención, sin multiplicar presupuestos;
  6) al vencer global terminar activas y marcar pendientes nunca iniciadas;
  7) rechazar plataforma/capacidad insuficiente y registrar recursos realmente medidos.
- **Viabilidad temprana:** cuando se autorice B04, medir en entorno aislado los
  seis motores productivos, sus tiempos y recursos por motor y del conjunto,
  incluido el costo de callbacks. Un worker activo y 180 s globales son una
  política conservadora pendiente de validación, no garantía de completar los
  seis motores. Presentar esta medición antes de cerrar B04; si resulta inviable,
  documentar alternativas y solicitar la decisión de Fabricio antes de continuar.
  No aumentar presupuestos o concurrencia automáticamente ni modificar heurísticas
  para superar las pruebas. B10 conserva la medición final del producto integrado.
- **Pruebas:** T-04/T-05 reales en Linux/WSL2; cola máxima, deadline antes del sexto,
  RSS, espacio virtual, paquetes sobredimensionados, consumidores lentos, retención
  de seis sesiones y exclusión FF/v1/v2; ST-INC-04.
- **Aceptación:** CA-03/04/N01/N02/N03; nunca seis simultáneos por defecto, memoria/
  tiempo no se amplían para conseguir verde y cada pendiente tiene causa explícita.
- **Riesgos:** seis corridas seriales superan 180 s, HF costoso, RSS doble cuenta
  páginas, M6 cota estimada distinta de RSS y preflight Heroku insuficiente.
- **Evidencias:** reporte por método/PID, máximo de procesos activos, cotas
  aplicadas y picos/intervalos de muestreo; rechazos/finales reales.
- **Orden / coordinación:** antes de B05; medición inicial puede ser independiente
  de persistencia/frontend. Coordinar con infraestructura; cualquier aumento de
  concurrencia o presupuesto vuelve a revisión, no se presupone autorizado.

### B05 — Supervisor y coordinador multimétodo

- **Objetivo:** capturar una vez, ejecutar/persistir independientemente y cerrar
  solo después de detener todos los componentes del cálculo.
- **Requisitos / CA:** RF-01, RF-03/04/14, RNF-01–RNF-03;
  CA-01/03/04/14/N01/N02/N03.
- **Archivos/módulos previstos:** `O/application/comparisons.py`,
  `comparison_calculation.py`, `comparison_contracts.py`,
  `O/infrastructure/comparison_runner.py`, `comparison_uow.py`,
  `O/presentation/comparison_runtime.py`, lifecycle/shutdown de la aplicación.
- **Dependencias:** B02–B04; entrada DTO y contrato acordados.
- **Pasos concretos:** 1) captura común bajo snapshot consistente PostgreSQL
  (transacción corta con aislamiento apropiado, p. ej. REPEATABLE READ), resolución
  de conflictos conservando idempotencia y seis ejecuciones en aceptación;
  2) enviar/verificar hash en cada worker sin conexiones DB; 3) sustituir bucles,
  barreras, mapas, contextos y contadores de tres por conjunto del perfil;
  4) guardar resultado/diagnóstico por ejecución y emitir después de commit;
  5) continuar ante fallo local y cerrar pendientes por fallo global;
  6) cerrar/join hijos, lectores y monitor incluso con fallo DB/IPC/observer;
  7) un dueño externo espera el fin del supervisor y persiste prueba de cierre
  antes de liberar lease/habilitar selección; 8) aplicar igual protocolo a shutdown
  y reconciliación; no declarar parada mediante TTL o desde el hilo aún vivo.
- **Pruebas:** T-04/T-05/T-06, arranque fallido, worker muerto, error de DB,
  observador roto y stream desconectado; timeline real supervisor-fin → admisión;
  ST-INC-05 inicia/consulta v2 sin exigir todavía UI v2 completa.
- **Aceptación:** CA-01/03/04/14/N01–N03; seis registros contabilizados, hash común,
  resultados independientes y ninguna admisión libre mientras el supervisor vive.
- **Riesgos:** deadlock al intentar self-join, liberar desde `work()` demasiado
  pronto, doble cierre o aceptar comparación nueva con procesos anteriores vivos.
- **Evidencias:** secuencia de transiciones/commits y PID con tiempo de inicio,
  joins, shutdown/reinicio y ausencia de huérfanos.
- **Orden / coordinación:** integra B02–B04; Fabricio coordina runtime/API/datos.
  No paralelizar modificaciones incompatibles al mismo protocolo de cierre.

### B06 — Persistencia, API y recuperación

- **Objetivo:** exponer v2 y recuperar historia/resultados sin recálculo.
- **Requisitos / CA:** RF-04/09/11–RF-14/19;
  CA-04/09/11/12/13/14/19.
- **Archivos/módulos previstos:** `O/presentation/comparison_routes.py`, rutas v2
  nuevas, schemas/serialización/runtime, router/dependencies;
  `O/infrastructure/comparison_uow.py`, `comparison_snapshot.py`, transporte;
  auth y UoW actuales sin mezclar responsabilidades.
- **Dependencias:** B01/B02/B05 y acuerdo de códigos HTTP/permisos con frontend.
- **Pasos concretos:** 1) conservar `/comparisons` y `/runs`; 2) añadir subrecursos
  de `/comparisons-v2`; 3) aceptación por clave con conflicto entre perfiles/lotes;
  4) lecturas por perfil persistido y resultado por dueño; 5) diagnóstico durable
  independiente de retención; 6) validar identidades en NDJSON/manifiestos/máscaras;
  7) recuperar cursores/retención/reinicio con snapshots sin recalcular;
  8) reconciliar solo al demostrar parada; selección/confirmación se completan en B08.
- **Pruebas:** T-01/T-02/T-06; HTTP real 401/403/404/409/422/503 según causa,
  acceso cruzado, claves concurrentes, v1 histórico, `/runs`, pérdida de respuesta,
  reinicio y máscara ajena; ST-INC-06.
- **Aceptación:** CA-04/09/11–14/19; perfiles explícitos, historia accesible y
  ningún reintento/reinicio vuelve a ejecutar heurísticas terminadas.
- **Riesgos:** endpoint sin versión que filtra v2 a clientes antiguos, datos
  visuales efímeros tratados como durables y claves reutilizadas entre perfiles.
- **Evidencias:** requests/responses sanitizados, snapshots/recibos antes/después
  y verificación de ausencia de nuevas ejecuciones durante recuperación.
- **Orden / coordinación:** después de B05; contrato permite trabajo frontend
  previo, pero cerrar este bloque requiere API/BD reales, no solo mocks.

### B07 — Frontend, visualización y progreso

- **Objetivo:** mostrar seis ejecuciones y comparación con navegación accesible.
- **Requisitos / CA:** RF-05/06/11/12/18/19, RNF-04;
  CA-05/06/11/12/18/19/N04.
- **Archivos/módulos previstos:** `F/comparisonApi.js`, `comparisonController.js`,
  `ComparisonWorkspace.jsx/.css`, `OptimizationPage.jsx`, `visualContract.js`,
  `visualState.js`, `runContract.js`, `RunVisualization.jsx`, `PlacementCanvas.jsx`,
  `PlacementScene3D.jsx`; pruebas de componentes y E2E.
- **Dependencias:** B01 para estructura; B03 para semántica BS/HF; B06 para conexión
  real. Coordinar interfaces antes de alterar parsers compartidos con legacy.
- **Pasos concretos:** 1) generalizar la vista FF/BF/WF existente con parsers v1/v2
  y acceso histórico, sin ventanas nuevas por motor ni componentes duplicados;
  2) pestañas/tabla desde catálogo del recurso, sin `METHODS` global único ni
  conteos de tres;
  3) espera/arranque/cálculo/terminal y errores independientes; 4) métricas comunes,
  null, cobertura, piezas no colocadas, tiempos de cálculo, planchas y retazos,
  sin ranking automático; 5) reutilizar visores y resolver
  máscaras por dueño; 6) provisional BS reemplazable o solo progreso de búsqueda,
  final desde snapshot; 7) teclado/ARIA/foco/Home/End/reducir movimiento;
  8) conservar selección y recuperación al recargar. Confirmación depende de B08.
- **Pruebas:** T-07/T-09/T-10; escritorio/móvil, cuatro estados visuales,
  seis pestañas más comparación, perfil antiguo, stream vencido y provisional
  distinto al final; ST-INC-07 sobre API real.
- **Aceptación:** CA-05/06/11/12/18/19/N04; seis layouts identificados, métricas
  correctas y misma solución en API, 2D y 3D, sin rotación doble.
- **Riesgos:** asociar pestaña por índice, mock que oculta errores de contrato,
  foco perdido al actualizar estados y animación presentada como cálculo en vivo.
- **Evidencias:** capturas/trazas por ejecución, navegación teclado, viewport,
  network real y comparación de geometrías con snapshots.
- **Orden / coordinación:** componentes pueden avanzar tras B01/B03; integración
  real tras B06. Responsable frontend por acordar, sin cambiar de rama de TA-043.

### B08 — Selección y confirmación transaccional

- **Objetivo:** permitir elección humana y consumir solo su solución de forma segura.
- **Requisitos / CA:** RF-07–RF-10/13/19; CA-07/08/09/10/13/19.
- **Archivos/módulos previstos:** `O/application/comparison_confirmation.py`,
  `O/infrastructure/comparison_confirmation.py`, `comparison_stock.py`,
  `comparison_uow.py`, adaptadores de confirmación, rutas/serialización;
  `F/ComparisonWorkspace.jsx`, controlador y API.
- **Dependencias:** B02/B05/B06; integrar UI de B07. Coordinar bloqueos con
  inventario/pedidos y conservar el orden de bloqueo existente.
- **Pasos concretos:** 1) validar pertenencia, completo/persistido y cierre seguro;
  2) selección inicial nula y control optimista; 3) confirmar snapshot elegido del
  servidor con clave estable; 4) bloquear comparación/ejecuciones/pedidos/fuentes
  en orden estable, revalidar estado/cantidades; 5) transacción única para consumo,
  movimientos, remanentes, pedidos y recibo; 6) rechazo/rollback en conflicto,
  conservando la selección previa y los cambios externos legítimos de stock;
  7) recuperación de confirmación ambigua y repetición idempotente sin doble consumo;
  8) preservar consulta de los otros cinco y liberación sin confirmar.
- **Pruebas:** T-06/T-08/T-09, ejecución ajena/parcial/fallida, selección obsoleta,
  cambio de stock y doble confirmación concurrente; fallo inducido tras primera
  escritura real en transacción aislada; ST-INC-08.
- **Aceptación:** CA-07/08/09/10/13/19; deltas exactos de selección confirmada y
  cero consumo por simular/seleccionar, rollback integral y recibo único.
- **Riesgos:** filtro implícito FF, consumo de unión de seis layouts, petición con
  layout arbitrario y selección revalidada antes del bloqueo pero no dentro de él.
- **Evidencias:** snapshots/deltas completos de tablas, SQL/estados sanitizados,
  recibos y resultados de reintentos/conflictos.
- **Orden / coordinación:** tras B06 y cierre seguro B05; API puede prepararse
  mientras B07 avanza. Integrar conjuntamente con inventario/pedidos/frontend.

### B09 — Pruebas integrales backend/frontend/E2E

- **Objetivo:** demostrar cumplimiento completo y compatibilidad entre componentes.
- **Requisitos / CA:** RF-01–RF-20, RNF-01–RNF-06, SM-01–SM-10;
  todos los CA de la matriz §5; RF-20/CA-20 es condicionado.
- **Archivos/módulos previstos:** pruebas de §2, fixtures compartidos v1/v2,
  `frontend/tests/e2e/criticalSpecs.js`, reporter/gate TA-040 y CI si el alcance
  exige incorporar un spec nuevo, conservando controles actuales.
- **Dependencias:** B01–B08; entorno aislado y datos versionados; no esperar a B09
  para ejecutar las pruebas y smoke incrementales de bloques ya ejecutables.
- **Pasos concretos:** 1) ejecutar catálogo/codec/migración/historia; 2) paridad y
  recursos reales; 3) API/recuperación y confirmación; 4) componentes y E2E desktop/
  mobile sin red simulada; 5) integrar nuevos specs al gate TA-040 para que faltante,
  skip o ejecución ausente no parezca PASS; 6) suites de regresión existentes;
  7) ST-INC-09 y ST-INT obligatorios sobre build/commit candidato;
  8) si HU-018 está integrado aparte, ejecutar T-12; de lo contrario registrar
  condicionado y su responsable, sin declarar ese escenario aprobado.
- **Pruebas:** T-01–T-14 según matriz; backend completo separa runner en proceso
  pytest limpio como CI. Unitarias/componentes no sustituyen E2E/smoke real.
- **Aceptación:** todos los CA incondicionales con evidencia; ST-INT PASS y
  ausencia de saltos obligatorios. No sumar conteos de suites solapadas.
- **Riesgos:** suite total infla RSS del supervisor, E2E no ejecutado en uno de los
  proyectos, pruebas geométricas duplicadas y evidencia previa presentada como nueva.
- **Evidencias:** comandos/directorios, commit exacto, versiones, conteos por
  selección, reportes backend/frontend/E2E/smoke y resultados negativos conservados.
- **Orden / coordinación:** después de B08 para integral; QA/reviewer independiente
  por acordar. Fallos vuelven al bloque propietario en la misma rama.

### B10 — Medición de recursos y preparación para despliegue

- **Objetivo:** determinar capacidad operativa verificable antes de proponer despliegue.
- **Requisitos / CA:** RF-03/04/05/17, RNF-02/03/05/06;
  CA-03/04/05/17/N02/N03/N05/N06.
- **Archivos/módulos previstos:** harness de medición futuro y reporte en evidencia
  TA-043; `docs/development/optimization-wsl2.md`, documentación de infraestructura
  si debe reflejar v2, configuración de presupuestos solo tras decisión revisada.
- **Dependencias:** B04/B09; plataforma y recursos del destino conocidos mediante
  revisión/diagnóstico autorizado, sin ejecutar pruebas destructivas en Heroku.
- **Pasos concretos:** 1) medir caso smoke y SMALL/MEDIUM/COMPLEX/mixtos pertinentes;
  2) cubrir formas, grupos, cantidades y límites TA-037 con datos controlados;
  3) registrar latencia por motor, cola/global, RSS/espacio virtual, serialización,
  callbacks, retención y tiempo de shutdown; 4) comprobar que un worker es viable;
  5) cualquier concurrencia mayor se ensaya aislada bajo los mismos presupuestos
  y se revisa antes de habilitar; 6) si no cabe, registrar rechazo/limitación y
  decisión pendiente, sin subir límites ni cambiar heurísticas; 7) preparar
  procedimiento de migración, activación v2 y rollback que conserva lectores;
  8) ST-INC-10 y repetir ST-INT si cambia comportamiento/configuración del candidato.
- **Pruebas:** T-04/T-05/T-10/T-11/T-13/T-14; no extrapolar ratios HF ni resultados
  locales como capacidad de Heroku. Pruebas de carga distintas del smoke mínimo.
- **Aceptación:** cotas y capacidad efectiva documentadas; ninguna afirmación de
  seis simultáneos ni despliegue seguro sin medición; CA-N02/N03/N06 satisfechos.
- **Riesgos:** muestras sin picos, warmed cache ocultando costo, plazos seriales
  mayores al global y destino que no supera siquiera el preflight de 1 GiB.
- **Evidencias:** entradas/semillas, muestras crudas seleccionadas, medianas/picos,
  reloj/contexto y propuesta de límites diferenciada de valores aprobados.
- **Orden / coordinación:** medición exploratoria puede empezar en B04; validación
  final tras B09 con infraestructura/reviewer. Preparar no autoriza deploy.

### B11 — Evidencias y cierre de TA-043

- **Objetivo:** permitir revisión y cierre sustentados, sin confundir documentos con producto.
- **Requisitos / CA:** RNF-06, SM-01–SM-10; CA-N06, CA-S01–CA-S10 y todos los
  CA incondicionales por comprobación de la matriz; CA-20 según condición externa.
- **Archivos/módulos previstos:** `docs/evidence/sprint-02/TA-043/README.md` e
  índice de evidencias futuros, SPEC/PLAN, revisión técnica futura y commits.
- **Dependencias:** B01–B10 y revisión humana real; todos los incidentes críticos
  resueltos y smoke integral del candidato válido.
- **Pasos concretos:** 1) enlazar requisito → CA → actividad → prueba → evidencia;
  2) comprobar qué commit se ensayó y correspondencia del diff final; 3) registrar
  ST-INC-11 de entrega ejecutable y ST-INT final/repetición si cambia producto;
  4) comprobar limpieza de datos/procesos y regresión histórica; 5) registrar
  revisión humana sin atribuir aprobaciones previas inexistentes; 6) acordar
  tratamiento explícito de pendientes operativos y de HU-018; 7) actualizar
  estados solo conforme a hechos; 8) preparar commits/PR para autorización posterior.
- **Pruebas:** T-10/T-13/T-14 y auditoría de trazabilidad; ninguna fila obligatoria
  sin prueba real/evidencia puede declararse PASS ni cerrarse por inspección estática.
- **Aceptación:** CA-N06 y diez CA smoke aprobados, revisión y limitaciones
  documentadas; si hay bloqueo de recursos o smoke FAIL, TA-043 permanece abierta.
- **Riesgos:** declarar Closed con smoke pendiente, confundir CI antiguo con el
  candidato final o borrar evidencia negativa al resumir.
- **Evidencias:** índice final con comandos, resultados y enlaces; historial de
  revisión y decisión de cierre, sin secretos ni datos compartidos mutados.
- **Orden / coordinación:** último; Fabricio y reviewer humano por designar.
  B11 no forma parte de la autorización actual limitada a B01.

## 4. Actividad identificable: TA-043 — Smoke Tests

**ID de actividad:** ST; niveles **ST-INC** (T-13) y **ST-INT** (T-14).
**Estado actual:** ST-INC-01 ejecutado con alcance v1/legacy; resultado y limpieza
en [evidencia B01](../evidence/sprint-02/TA-043/B01/README.md). Los demás smoke,
incluido ST-INT, siguen **PLANIFICADOS / NO EJECUTADOS**. Sus harness y servicios
se prepararán solo cuando se autorice el bloque correspondiente, en esta rama.

### 4.1 Contrato común obligatorio E0 / D0 / P0 / L0

Las dos fichas y cada fila incremental de §4.2 heredan explícitamente los campos
de este protocolo. Así cada ejecución tiene precondiciones, entorno, datos, pasos,
resultado, PASS/FAIL, evidencia y limpieza, sin depender de un entorno compartido.

**E0 — Precondiciones, entorno y servicios.** Commit/build candidato identificado,
dependencias fijadas del repo, Python 3.11 Linux/WSL2 con procfs/RLIMIT/prctl,
PostgreSQL local temporal propio, Node 22 y navegador Chromium/Chrome real según
configuración Playwright. Un FastAPI con un proceso web, frontend Vite/build
servido por HTTP y destinos loopback explícitos. Preflight satisfactorio y puertos
libres; configuración vigente controlada de 5°. Autenticación real con usuario de
prueba y permisos mínimos de vista/ejecución/confirmación. Desactivar carga de
`.env` mediante `PYTHON_DOTENV_DISABLED=1`, exigir PostgreSQL de prueba mediante
`NEWGLASS_REQUIRE_POSTGRES=1` y verificar privadamente destino de conexión.

Reutilizar la creación de clúster propio de
`backend/tests/integration/postgres_support.py`, el servidor HTTP real
`backend/tests/e2e_server.py` y los datos de `backend/tests/optimization_e2e_data.py`;
adaptar su ciclo de vida, no apuntarlo a Supabase. PostgreSQL
se inicializa/migra **solo en ese clúster** en la futura ejecución autorizada.
No usar SQLite, repositorios en memoria, motores simulados, `route.fulfill`, mocks
de red, inspección estática o solo unitarias para declarar smoke aprobado.

**D0 — Datos de prueba controlados.** Versionar fixture/manifiesto con geometrías,
IDs creados, cantidades, ranking de fuentes, configuración y resultados esperados;
registrar su hash. No usar IDs existentes de desarrollo. Preparar conjuntos separados:

| Conjunto | Datos y propósito |
|---|---|
| D1 — Éxito mínimo | Pedido pequeño de rectángulo, círculo y polígono convexo válidos, fuentes compatibles holgadas y configuración real 5°; seis resultados completos bajo cotas existentes. Seleccionar dimensiones pequeñas tras comprobar el caso, sin alterar heurísticas/límites. |
| D2 — Historia | FF legacy y comparación real v1 con tres ejecuciones, snapshots/solicitud/recibo según caso, persistidos **antes** de migración v2; no construir seis ni recalcular para presentarlos como historia. |
| D3 — Selección distinguible | Caso de fuentes alternativas basado en los contraejemplos de políticas existentes, más stock testigo no utilizado; al menos un motor usa una fuente distinta. Elegir resultado elegible y calcular delta esperado desde su snapshot, no desde la unión de motores. |
| D4 — Fallo independiente | Copia de caso pequeño cuyo worker propio se puede detener después de `engine_started`, conservando los otros cinco; fallo externo de proceso real, no motor fake. Sincronizar desde el harness mediante checkpoint/barrera exclusiva de prueba para evitar una carrera con un cálculo diminuto; el motor sigue siendo productivo. Usar otra comparación, nunca la que ya se confirmó. |
| D5 — Parcial/recuperación | Stock insuficiente controlado, referencias a resultados parciales y escenario de expiración/reinicio; completo/parcial/fallido visibles sin habilitar selección indebida. |
| D6 — HU-018 condicionado | Tras integración separada: CSV/XLSX mixto persistido por flujo real de Orders; cantidad expandida ≤150, dentro de los demás límites TA-037 y paso 5°. No usar importación en el smoke base mientras falte HU-018. |

D1 debe conservar seis éxitos; D3 distingue consumo del seleccionado y testigos;
D4 comprueba fallo aislado. No exigir que las seis distribuciones sean diferentes
ni usar un fixture enorme como smoke. Los casos de límites/estrés son T-04/T-11.

**P0 — Pasos comunes de ejecución y evidencia.**

1. Registrar commit, árbol, versiones y manifiesto; iniciar clúster aislado, aplicar
   esquema y seed controlado; si se prueba migración, crear D2 con esquema anterior
   y capturar historia antes del upgrade. Registrar destino sin contraseña.
2. Capturar inventario completo de planchas/retazos/movimientos y PID/identidad de
   servicios. Levantar backend/frontend reales, comprobar health/readiness,
   `openapi.json`, login y solicitud UI→API; no basta `OPTIONS` ni build.
3. Ejecutar las operaciones de la ficha con HTTP/navegador reales y claves nuevas
   por intención. Conservar request/response, ID de comparación y seis ejecuciones,
   eventos/consultas hasta terminal y capturas por motor cuando corresponda.
4. Comparar snapshots/deltas de BD en cada punto requerido y conservar recibos;
   verificar identidades/fuentes y que reintento no duplica efectos.
5. Registrar terminación de todos los procesos propios, orden de supervisor/admisión
   y posibilidad de admitir otro trabajo solo después de su parada.
6. Ejecutar L0 en éxito **y** fallo. Publicar reporte PASS/FAIL con CA comprobados,
   comandos exactos, directorio, datos/hashes y limitaciones, sin tokens/credenciales.

**Resultado esperado / PASS/FAIL común.** Servicios sanos, operaciones y estados
coherentes con el bloque, datos reales consultables, ningún consumo fuera de
confirmación seleccionada y ningún proceso propio huérfano. PASS solo si todas las
aserciones obligatorias de esa ficha se ejecutaron y pasaron y L0 completó. Fallo
de arranque, requisito omitido, servicio ausente, timeout sin causa registrada,
skip o limpieza incompleta es FAIL/bloqueo documentado; no se cuenta como PASS.
Una ficha incremental temprana no acredita capacidades todavía no integradas.

**L0 — Limpieza de datos y procesos.** Guardar evidencia antes de limpiar.
Solicitar cancelación/shutdown por ciclo soportado; esperar supervisor y joins de
workers/lectores/monitor; comprobar PID **y tiempo de inicio** contra el inventario
del harness. Si falla, detener solo descendientes propios comprobados y registrar
FAIL; nunca matar por nombre o barrer procesos de otras sesiones. Cerrar navegador,
frontend y backend propios; detener PostgreSQL con su directorio/identidad y
destruir exclusivamente el clúster/base temporal propios, tras verificar ruta y
destino. Si se reutiliza un clúster propio, eliminar solo la BD/schema creado por
esa ejecución, respetando FK. No editar stock para ocultar un fallo; destruir la
BD efímera de confirmación. Verificar puertos/procesos sin remanentes y registrar
resultado de limpieza. No tocar Supabase, Heroku ni servicios compartidos.

### 4.2 ST-INC — Smoke incremental (T-13)

- **Objetivo y escenario:** tras cada bloque funcional ejecutable, comprobar que
  el producto integrado levanta y que v1/legacy más la nueva capacidad accesible
  siguen operativos; avanzar progresivamente hasta seis motores/confirmación.
- **Precondiciones:** E0 y bloque candidato integrado en la misma rama; B01/B02
  puramente documentales o sin capacidad ejecutable no reciben PASS funcional.
  No se retrasa el smoke de un bloque ejecutable hasta B09.
- **Entorno/servicios y datos:** E0, P0, L0 obligatorios para **cada** fila; D1/D2
  como base y conjuntos adicionales indicados. Backend/frontend siempre levantados.
- **Pasos:** P0 y los pasos adicionales de la fila; cada fila se ejecuta contra
  un estado limpio/controlado. Si una capacidad aún no existe, comprobar el camino
  vigente real y registrar pendiente, sin sustituirla por mock ni declarar seis motores.

| Smoke / bloque | Datos y pasos adicionales | Resultado esperado / PASS específico | Evidencia reproducible y limpieza |
|---|---|---|---|
| ST-INC-01 / B01 | D1/D2; levantar servicios y abrir comparación v1/legacy; consultar perfiles expuestos cuando B01 tenga entrega ejecutable | v1 conserva tres y legacy responde; catálogo/contrato nuevo no rompe arranque. Seis motores siguen pendientes hasta estar conectados | P0 + HTTP/UI y contrato del commit; L0 |
| ST-INC-02 / B02 | D2 creado antes del upgrade; migrar solo BD propia, consultar por API/UI su historia después | Mismos IDs, métodos, geometría y datos v1/legacy; ninguna ejecución ficticia | P0 + esquema/hashes antes/después; L0 |
| ST-INC-03 / B03 | D1; usar capacidad de ejecución ya conectada al servicio; comprobar resultados/diagnóstico de adaptadores accesibles y consulta v1 | Motor real responde con identidad y callbacks coherentes; adaptador sin ruta integrada queda pendiente de smoke, no se reemplaza por ejecución unitaria | P0 + eventos/resultados y capacidad realmente disponible; L0 |
| ST-INC-04 / B04 | D1; iniciar trabajo y observar despacho/capacidad; intentar otra admisión incompatible; consultar UI real | Concurrencia v2 inicial uno, espera visible cuando disponible y rechazo seguro; v1 sigue operativo | P0 + reporte de procesos/tiempos y respuesta de admisión; L0 |
| ST-INC-05 / B05 | D1/D4; iniciar v2 y consultar seis ejecuciones; detener un worker propio con PID verificado | Seis identidades llegan a terminal, cinco consultables si uno falla; cierre/admisión en orden seguro | P0 + NDJSON/GET, fallo y timeline de joins; L0 |
| ST-INC-06 / B06 | D1/D2; POST v2, GET ID/clave, recarga, perfil cruzado e historia v1 por HTTP; UI servida sana | Aceptación única y consulta durable; error de perfil explícito y lectura histórica intacta | P0 + HTTP real, snapshots y ausencia de recálculo; L0 |
| ST-INC-07 / B07 | D1/D2/D5; abrir seis pestañas, tabla/2D/3D, teclado, recarga y parcial | Seis resultados reales accesibles; historial de tres intacto y parcial/espera no confirmables | P0 + traza navegador y capturas por motor/viewport; L0 |
| ST-INC-08 / B08 | D3; capturar stock, simular, seleccionar, confirmar y repetir misma clave | Cero consumo en simular/seleccionar y delta exacto solo del seleccionado al confirmar; recibo único | P0 + dumps/deltas y recibos sanitizados; L0 |
| ST-INC-09 / B09 | D1–D5; ejecutar flujo mínimo completo más fallo/historia antes de ST-INT | Todos los componentes integrados siguen operativos y fallos se aíslan | P0 + reporte T-13 y enlace a ST-INT separado; L0 |
| ST-INC-10 / B10 | D1/D3/D4 con configuración candidata medida; repetir si cambia concurrencia/presupuesto autorizado | Capacidad aplicada coincide con lo medido, sin huérfanos ni regresión del flujo mínimo | P0 + configuración/picos/timeline; L0 |
| ST-INC-11 / B11 | D1–D5 en candidato final si cambió producto desde último smoke; verificar evidencias/limpieza | Entrega ejecutable sana y evidencia del mismo candidato; cambios solo documentales no inventan una nueva ejecución | P0 + commit/hashes y reporte final o enlace justificado al vigente; L0 |

**FAIL específico:** cualquier expectativa de la fila incumplida. Registrar CA
verificados y pendientes; ST-INC no sustituye ST-INT ni aprueba por anticipado los
diez requisitos smoke. Cada entrega ejecutable conserva su evidencia de smoke.

### 4.3 ST-INT — Smoke integral obligatorio (T-14)

- **Objetivo y escenario:** demostrar el flujo mínimo completo de seis motores,
  selección/confirmación exclusiva, compatibilidad histórica y fallo independiente
  antes de declarar terminada TA-043.
- **Precondiciones:** B01–B08 integrados, pruebas de B09 disponibles, E0 superado,
  política de recursos aplicada y candidato identificado; D1 capaz de completar
  los seis dentro de cotas existentes. Debe ejecutarse después de completar la
  integración y repetirse si un cambio funcional invalida su evidencia.
- **Entorno y servicios necesarios:** todos los de E0, sin sustitutos; PostgreSQL
  aislado con historia D2, backend de un proceso web, frontend y navegador reales.
- **Datos:** D1–D5; D6 solo si HU-018 ya fue integrado por su flujo independiente.
  Guardar manifiestos y snapshots de referencia antes de cada subescenario.
- **Pasos de ejecución y resultados esperados:**

| Paso | Operación real | Aserción / criterio |
|---|---|---|
| 1 | P0.1–2: iniciar PostgreSQL/backend/frontend, readiness y login | Servicios levantados y UI llama a API real: CA-S01 |
| 2 | D1: iniciar comparación v2 con clave y consultar por ID/clave hasta terminal | Una comparación, seis ejecuciones distintas y perfil v2: CA-S02 |
| 3 | Registrar transición espera/arranque/cálculo/terminal de FF/BF/WF/HF/BRF/BS-2 | Identidades estables, ningún motor omitido o sustituido: CA-S03 |
| 4 | GET de los seis resultados; abrir pestañas, tabla y visores 2D/3D con teclado | Seis resultados completos y layouts del snapshot correcto, no ramas falsas: CA-S04 |
| 5 | D3: capturar BD antes de simular, tras simular y tras selección de un completo; recargar UI | Selección inicial nula, luego selección persistida elegible; cero consumo/movimientos: CA-S05/CA-S07 |
| 6 | Confirmar el seleccionado con versión/clave y repetir exactamente la operación | Solo delta previsto por ese snapshot; fuentes testigo/ajenas intactas, recibo único: CA-S06 |
| 7 | D2: consultar comparación v1 preexistente por API y UI; comprobar `/runs` legacy | Tres resultados históricos sin conversión, geometría/IDs conservados: CA-S08 y CA-11 |
| 8 | D4: iniciar otra comparación y detener un worker propio iniciado, usando PID+inicio del harness | Fallo explícito de ese motor; otros cinco resultados consultables/visibles y completos en ese caso: CA-S09 |
| 9 | D5: abrir parcial y comprobar acción de selección/confirmación bloqueada; recuperar tras pérdida de visual/reinicio controlado | Estado parcial y motivo correctos, resultados durables accesibles sin recalcular: CA-04/07/19 |
| 10 | Al finalizar, verificar workers/lectores/monitor y supervisor detenidos antes de nueva admisión; ejecutar L0 | Sin procesos propios huérfanos ni liberación prematura, limpieza registrada: CA-S10 |

- **Criterio PASS/FAIL:** PASS exige **CA-S01–CA-S10** observados y aprobados en
  servicios reales, y limpieza L0 completa. Un requisito omitido, mock, skip,
  timeout no diagnosticado, delta incorrecto o proceso remanente da FAIL; impide
  cerrar TA-043. El fallo inducido de D4 es PASS solo si se observa el aislamiento
  esperado; no se considera exitoso un fallo accidental del entorno.
- **Evidencia reproducible:** `docs/evidence/sprint-02/TA-043/smoke/integral/`
  propuesto, con commit/build, comandos exactos/directorios, versiones, manifiestos,
  HTTP/NDJSON, seis IDs/métodos, capturas por ejecución, snapshots/deltas/recibo,
  PID+inicio, orden de parada/admisión y reporte de limpieza. Registrar resultado
  real y limitaciones; ningún PASS se hereda de la auditoría anterior.
- **Procedimiento de limpieza:** L0 obligatorio tras cada subescenario y al final;
  conservar reportes de fallos. Nunca ejecutar confirmaciones/destrucción en
  Supabase, Heroku ni otro entorno compartido sin autorización específica.

## 5. Matriz de trazabilidad SPEC → PLAN → pruebas

«Prevista» significa pendiente de implementación y ejecución. Esta matriz cubre
todos los requisitos y todos los CA de la SPEC; los smoke son parte del cierre.

| Requisito SPEC | CA SPEC | Actividad PLAN | Prueba prevista | Evidencia futura principal |
|---|---|---|---|---|
| RF-01 | CA-01 | B05, B06 | T-03, T-05, T-06 | Hash/DTO y captura común de seis workers |
| RF-02 | CA-02 | B01, B03 | T-01, T-03 | Catálogo/identidades y rechazos |
| RF-03 | CA-03 | B04, B05 | T-04, T-05 | Seis estados y aborto global con pendientes |
| RF-04 | CA-04 | B03–B06 | T-01, T-03, T-05, T-06 | Round-trip de parciales/fallos y razones M6 |
| RF-05 | CA-05 | B07, B10 | T-03, T-07, T-11 | Métricas directas/HTTP/UI y reloj |
| RF-06 | CA-06 | B07 | T-07, T-09 | Seis distribuciones 2D/3D |
| RF-07 | CA-07 | B08, B09 | T-06, T-08, T-09 | Selección elegible y rechazos |
| RF-08 | CA-08 | B08, ST-INT | T-08, T-09, T-14 | Delta exclusivo del seleccionado |
| RF-09 | CA-09 | B06, B08 | T-06, T-08 | Aceptación/recibo únicos y conflictos |
| RF-10 | CA-10 | B08 | T-08 | Stock cambiado y rollback integral |
| RF-11 | CA-11 | B01, B02, B06, B07 | T-01, T-02, T-06, T-09 | Historia v1/FF antes/después |
| RF-12 | CA-12 | B01, B06, B07 | T-01, T-06, T-07 | Perfiles y acceso cruzado |
| RF-13 | CA-13 | B02, B06, B08 | T-02, T-08 | Migración/FK/unicidad/downgrade protegido |
| RF-14 | CA-14 | B01–B03, B05, B06 | T-01, T-02, T-03, T-05 | Registro/codecs/UoW sin cardinalidad tres en v2 |
| RF-15 | CA-15 | B03, B09 | T-03, T-10 | Regresión HF actual y guard/fallback |
| RF-16 | CA-16 | B03, B09 | T-03, T-10 | Paridad BRF/score/desempates |
| RF-17 | CA-17 | B03, B09, B10 | T-03, T-10, T-11 | Paridad BS-2/traza/límites |
| RF-18 | CA-18 | B03, B07 | T-03, T-07, T-09 | Callbacks y provisional/final BS |
| RF-19 | CA-19 | B06–B08 | T-06, T-07, T-08, T-09 | Recuperación/permisos/trazabilidad sin recálculo |
| RF-20 | CA-20 | B09, escenario D6 | T-12 | HU-018 condicionado, 5° y ≤150 unidades |
| RNF-01 | CA-N01 | B04, B05 | T-03, T-04, T-05, T-06 | Aislamiento y máscaras ajenas rechazadas |
| RNF-02 | CA-N02 | B04, B05, B10 | T-04, T-11 | Recursos reales y cotas compartidas |
| RNF-03 | CA-N03 | B04, B05, B10 | T-04, T-05, T-14 | Fin supervisor/joins antes de admisión |
| RNF-04 | CA-N04 | B07 | T-07, T-09 | Teclado/ARIA/móvil/movimiento reducido |
| RNF-05 | CA-N05 | B03, B09, B10 | T-03, T-10, T-11 | Regresión/determinismo equivalente |
| RNF-06 | CA-N06 | B09–B11, ST | T-10, T-13, T-14 | Matriz completa, revisión y smoke PASS |
| SM-01 | CA-S01 | ST-INC, ST-INT pasos 1 | T-13, T-14 | Servicios/readiness/login reales |
| SM-02 | CA-S02 | B05, B06, ST-INT paso 2 | T-13, T-14 | POST/GET v2 real, seis IDs |
| SM-03 | CA-S03 | B05, B07, ST-INT paso 3 | T-13, T-14 | Estados/métodos por ejecución |
| SM-04 | CA-S04 | B07, ST-INT paso 4 | T-13, T-14 | Seis resultados y capturas UI |
| SM-05 | CA-S05 | B08, ST-INT paso 5 | T-13, T-14 | Selección manual y recarga |
| SM-06 | CA-S06 | B08, ST-INT paso 6 | T-13, T-14 | Delta/recibo exclusivo e idempotencia |
| SM-07 | CA-S07 | B08, ST-INT paso 5 | T-13, T-14 | Inventario/movimientos intactos antes de confirmar |
| SM-08 | CA-S08 | B02, B06, B07, ST-INT paso 7 | T-13, T-14 | Historia de tres por HTTP/UI |
| SM-09 | CA-S09 | B05, ST-INT paso 8 | T-13, T-14 | Worker muerto y otros cinco consultables |
| SM-10 | CA-S10 | B05, B10, ST-INT paso 10 | T-13, T-14 | Identidades/PID y limpieza sin huérfanos |

## 6. Secuencia, coordinación y decisiones pendientes

Orden recomendado: **B01 → B02/B03 → B04 → B05 → B06 → B07/B08 → B09 → B10 → B11**.
B04 puede iniciar mediciones tras disponer de adaptadores; B07 puede preparar
componentes tras fijar contratos, pero su validación real espera API/runner.
B08 backend puede avanzar junto a B07. Ninguna independencia permite saltar smoke
de una entrega ejecutable o abrir ramas de fases: coordinar commits en la misma
feature y revisar contratos antes de integrar consumidores.

| Coordinación / dependencia | Acuerdo o salida necesaria |
|---|---|
| Fabricio / reviewer humano por designar | Revisar SPEC/PLAN y autorizar implementación; el cierre requiere revisión real |
| Andro / HF TA-042 | Conservar búsqueda acotada y protección actual; confirmar contrato de callbacks/diagnósticos, sin atribuir aprobación académica pendiente |
| Luis Anthony Ibáñez Herrera / BRF TA-052 | Conservar score/parámetros y confirmar adaptación de identidad `M5` al nombre visible BRF |
| Frontend/API/datos, responsables por acordar | Esquemas v2, estados, codecs, migración, UI de recuperación y límites de compartidos |
| Inventario/pedidos | Orden de bloqueo y efectos exactos de confirmación/rollback |
| Infraestructura/QA | Linux/WSL2, PostgreSQL propio, capacidad objetivo, procesos y gate de pruebas reales |
| HU-018 / PR #96 | Integración ajena a TA-043; D6/T-12 después, sin importar sus 13 commits ni correcciones |

Decisiones de diseño adoptadas en Draft: nuevo perfil/rutas v2; identidades de
dominio conservadas con nombres oficiales; un worker v2 inicial; presupuestos
actuales sin multiplicar; codecs versionados y lectura histórica; cierre por dueño
externo que espera supervisor; progreso BS sin ramas presentadas como finales.

Pendientes de medición/revisión antes de habilitar producto: concurrencia mayor
a uno, viabilidad de seis dentro del deadline global, memoria/RSS/espacio virtual,
serialización/IPC/retención de seis, costo HF/callbacks y capacidad real Heroku.
No hay nuevos tiempos/memorias aprobados. Si no se cumplen cotas existentes,
registrar limitación y decisión explícita; nunca adaptar las heurísticas para
igualar resultados o presentar un fallo de recursos como ausencia geométrica.

## 7. Validación documental actual y puertas de aprobación

La revisión documental inicial comprobó organización de plantilla/PLAN, enlaces locales, cobertura
de los 20 RF, 6 RNF y 10 SM mediante sus 36 CA, correspondencia de cada fila con
actividad/prueba prevista, compatibilidad histórica, límites con fuente, aislamiento
HU-018, rama única y `git diff --check`. Estas comprobaciones documentales no son
ejecución de T-01–T-14 ni smoke y no habilitan implementación.

Resultado de la revisión documental inicial del 03/11/2026: 36 requisitos y 36 CA con
36 filas de trazabilidad concordantes, once bloques con los diez campos pedidos,
once entradas smoke incrementales, enlaces locales válidos y UTF-8 sin BOM.
`git diff --cached --check` y `git diff --check` sin incidencias; el diff contiene
exclusivamente esta SPEC y este PLAN. Esta constatación no acredita servicios,
pruebas de producto ni aprobación humana.

La fase documental produjo los commits locales `9ef0001` y `1d20a70` en esta
misma rama y se detuvo para revisión. La autorización posterior permite B01,
sus pruebas/smoke y commits separados por cambios lógicos; su resultado exige
otra parada para revisión antes de consumidores dependientes. No publicar la
feature ni cambiar el estado general a Implemented/Verified.

Antes de implementar otro bloque: superar la puerta B01 y obtener autorización
expresa de su alcance; asignar reviewer y coordinar interfaces; refrescar
base/diferencias sin merge automático; preparar entorno aislado. Antes de cerrar:
matriz completa con evidencia real, regresión,
ST-INC de entregas ejecutables y **ST-INT PASS obligatorio**, medición operativa y
revisión humana. D6 pendiente por HU-018 se registra por separado y no se presenta
como prueba aprobada; cualquier exclusión futura requiere decisión visible.

La instrucción posterior de Fabricio habilita exclusivamente B02 sobre los commits
B01 `5dcc316`, `8ab8eaa` y `f65292f`. T-02 se concreta en
`test_comparison_v2_migration.py` y `test_comparison_v2_persistence.py`, conservando
las suites históricas; ST-INC-02 comprueba historia real creada antes del upgrade.
Esta evidencia no acredita ejecución pública de seis motores, prueba de parada
del supervisor v2, selección/confirmación v2 ni ST-INT. No iniciar B03 sin revisión.

## Historial de estado

- 03/11/2026 — **Draft**: autorización limitada a B02 y sus validaciones;
  migración/persistencia y ST-INC-02 documentados en evidencia B02. Se conservan
  los once bloques, dependencias, 36 requisitos/CA y matriz; parada antes de B03.

- 03/11/2026 — **Draft**: PLAN redactado después de la SPEC, con once bloques y
  actividad obligatoria TA-043 — Smoke Tests; documentación para revisión.
  Implementación, migraciones, scripts, pruebas y smoke no ejecutados en esta sesión.
- 03/11/2026 — **Draft**: revisión final; agrupaciones de gestión T01–T03, puerta
  contractual de B01, viabilidad temprana de B04 y precisión de reutilización en
  B07. Se conservan requisitos, CA, matriz, dependencias y smoke; no se inicia B01.
- 03/11/2026 — **Draft**: autorización posterior limitada a B01. Se registran sus
  contratos, validación y ST-INC-01; puerta de revisión de Fabricio pendiente.
  No se ejecutan B02/B03 ni se aprueba el cierre integral de TA-043.
