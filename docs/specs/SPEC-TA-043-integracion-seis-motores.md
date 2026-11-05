# SPEC-TA-043 — Integración y validación conjunta de seis motores

## Información general

| Campo | Valor |
|---|---|
| Estado | **Draft — B06 autorizado; resultado pendiente de revisión** |
| PBI / módulo | TA-043 / Sprint 2 / Optimization |
| Responsable | Fabricio Meléndez |
| Reviewer | Por designar; no se atribuye aprobación humana |
| Fecha | 03/11/2026, America/Lima |
| Base oficial | `integration-02` local; referencia remota ausente tras fetch del 04/11/2026 |
| Commit base verificado | `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b` |
| Única rama de trabajo TA-043 | `feature/TA-043-integracion-seis-motores` |
| PLAN | [PLAN-TA-043-integracion-seis-motores.md](PLAN-TA-043-integracion-seis-motores.md) |
| Autorización actual | Exclusivamente B06: persistencia, API v2 y recuperación, pruebas pertinentes, ST-INC-06 y commits locales; detenerse antes de B07 |

La autorización documental inicial fue ampliada para B01 y posteriormente,
por instrucción expresa de Fabricio, exclusivamente para **B02**. Sus alcances
se registran en [evidencia B01](../evidence/sprint-02/TA-043/B01/README.md) y
[evidencia B02](../evidence/sprint-02/TA-043/B02/README.md). Esta ampliación permite
migración y persistencia optativa, probadas solo en PostgreSQL propio; no autoriza
coordinador/endpoints/UI v2 ni otros bloques. El estado general sigue Draft y se
requiere otra parada para revisión antes de cada bloque siguiente. Fabricio
autorizó después exclusivamente **B03**; su adaptación y validación se registran
en [evidencia B03](../evidence/sprint-02/TA-043/B03/README.md). Esta autorización
no habilita B04–B11 ni la ejecución pública de seis motores.
Fabricio autorizó después exclusivamente **B04**, con puerta temprana de
viabilidad y sin aumentar cotas. Su primitiva de procesos, mediciones y límites
se registran en [evidencia B04](../evidence/sprint-02/TA-043/B04/README.md).
Admisión compartida v2 y certificación de parada del supervisor quedan en B05.

## 1. Objetivo, fuentes y base verificada

Integrar FF, BF, WF, HF, BRF y BS-2 como seis ejecuciones identificables de una
comparación sobre la misma entrada congelada. La persona compara sus resultados,
elige una ejecución elegible y confirma exclusivamente esa solución mediante el
ciclo transaccional existente. No se exige superioridad ni igualdad entre motores.

### 1.1 Procedencia de la base

Se inspeccionó Git con árbol limpio y se ejecutó `git fetch origin --prune`.
La primera verificación encontró que `integration-02` no existía. Tras autorización
expresa del responsable, se creó desde el HEAD remoto de `integration/sprint-01`
y se publicó **solo** `refs/heads/integration-02`, sin commits adicionales, merge,
cherry-pick, rebase ni force push. `git ls-remote --heads origin` confirmó ambas
ramas en `d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b`; diferencia entre referencias:
0 commits y 0 archivos. Conforme a la última corrección del responsable, la única
rama activa de TA-043 es `feature/TA-043-integracion-seis-motores`, creada desde
`origin/integration-02`. Se conservaron las referencias documentales anteriores,
creadas antes de esa corrección, y se trasladó la SPEC aún sin commit sin descartar
contenido. No se usarán como ramas de fases ni se crearán ramas adicionales:
SPEC, PLAN, implementación futura, pruebas y evidencias compartirán la rama feature
mediante commits Conventional Commits por bloques validados.

Esta SPEC describe el árbol de **integration-02** en ese SHA. La auditoría anterior
de `integration/sprint-01` es antecedente, no aprobación de TA-043. Cualquier avance
posterior exige revisar diferencias antes de implementar.

### 1.2 Fuentes revisadas y jerarquía

- [CONTRIBUTING](../../CONTRIBUTING.md), [plantilla SPEC](SPEC-TEMPLATE.md),
  [ADR-001](../adr/ADR-001-seleccion-arquitectura.md), diagramas fuente de
  [arquitectura](../architecture/system-architecture.drawio) y
  [datos](../architecture/data-model.drawio): monolito modular, capas y fronteras.
- [Convenciones de pruebas](../testing/README.md), [evidencia](../evidence/README.md),
  [ejecución Linux/WSL2](../development/optimization-wsl2.md) y CI del repositorio.
- SPEC/PLAN de [TA-021](SPEC-TA-021-comparacion-metodos.md),
  [integración visual](SPEC-OPT-MULTIMOTOR-VISUAL.md),
  [HU-017](SPEC-HU-017-proceso-visual-optimizacion.md),
  [TA-037](SPEC-TA-037-control-carga-optimizador.md), SP-002 y TA-016/018/019/020.
- [Contrato comparison-v1](../contracts/optimization/comparison-v1.md) y su
  [fixture compartido](../contracts/optimization/comparison-v1.json), más codecs,
  schemas, supervisor, UoW, modelos, migraciones y consumidores frontend actuales.
- [Decisión SP-004](../reviews/SP-004-heuristica-m4-review.md),
  [SPEC TA-042](SPEC-TA-042-hole-filling.md),
  [revisión TA-042](../reviews/TA-042-hole-filling-review.md) y evidencia vigente.
- [Evidencia TA-052](../evidence/sprint-02/TA-052/README.md),
  [SPEC M6](SPEC-TA-053-T01-M6-Beam-Search.md),
  [evidencia TA-053 T02](../evidence/sprint-02/TA-053-T02/README.md) y
  [auditoría FF/BF/WF](../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/FINAL-AUDIT-2026-11-01/README.md).

Los documentos antiguos conservan su alcance histórico. Para estado integrado,
prevalece el código del SHA verificado; las mediciones citadas siguen siendo
antecedentes de sus autores, no ejecuciones realizadas en esta sesión.

### 1.3 Catálogo y brechas reales

Rutas relativas a `backend/app/modules/optimization/domain/`:

| Motor oficial | `method` estable adoptado | Implementación productiva existente | Brecha para TA-043 |
|---|---|---|---|
| FF — First Fit | `FF` | `first_fit.py:FirstFitOptimizer` | Ya público en v1 |
| BF — Best Fit | `BF` | `best_fit.py:BestFitOptimizer` | Ya público en v1 |
| WF — Worst Fit | `WF` | `worst_fit.py:WorstFitOptimizer` | Ya público en v1 |
| HF — Hole Filling, M4 | `HF` | `hole_filling.py:HoleFillingOptimizer` | Falta registro público, codec y persistencia |
| BRF — Best Residual Fit, M5 | `M5` | `best_residual_fit.py:BestResidualFitOptimizer` | Solo comparador interno opcional `EXTENDED_METHODS` |
| BS-2 — Beam Search acotada, M6 | `M6-BS` | `beam_search.py:BeamSearchOptimizer`, ancho 2 | Falta adaptador visual y preservar `BeamSearchOutcome` |

Los nombres visibles son **FF, BF, WF, HF, BRF, BS-2**. Los códigos adoptan las
identidades reales devueltas por dominio; no se renombra M5 ni M6 al persistir,
no se infiere el motor por posición y no se admiten aliases ambiguos. `M6-BS`
queda ligado a la configuración BS-2 en este perfil; otro ancho requeriría una
decisión versionada, no cambiar silenciosamente su significado.

Se verificaron las seis clases en la nueva base. Los últimos cambios productivos
relevantes son `018c9d5` (HF acotado/protección), `393a224` (BRF) y `5fcc988`
(agotamiento temporal en preparación M6). Las ramas remotas TA-042, TA-052 y
TA-053 T02 no contienen commits pendientes respecto de esta base. Ningún motor
falta. Esto no significa que los seis estén integrados en el flujo público:
`METHODS`, `ENGINES`, `RESULT_TYPES`, schemas, SQL y UI siguen limitados a tres.

HU-018, [PR #96](https://github.com/melendezzz26/optimizador-vidrio/pull/96), se
verificó abierto y no integrado; su HEAD consultado es `192c7e7`, con 13 commits
propios respecto de esta base. No se incorporan esas correcciones. Las aprobaciones
humanas pendientes en evidencias previas tampoco se presumen concedidas.

## 2. Alcance

### Incluye

- Captura común, seis ejecuciones aisladas, estados completos/parciales/fallidos,
  diagnósticos, métricas y distribuciones reales por motor.
- Evolución versionada de contratos, persistencia PostgreSQL, API, recuperación,
  supervisión y recursos; conservación de comparaciones de tres motores y `/runs`.
- Frontend dinámico, accesible, visores 2D/3D reutilizados, selección manual y
  confirmación transaccional de una ejecución.
- Pruebas previstas de compatibilidad, integración, transacciones, recursos,
  frontend/E2E, regresión y smoke incremental/integral sobre servicios reales.

### Fuera de alcance

- Implementación y pruebas de B05–B11 en esta entrega B04; no se habilita el
  coordinador público de seis motores ni se ejecuta el smoke integral.
- Cambiar heurísticas, geometría, scores, desempates, prioridades o fórmulas para
  igualar resultados; reintroducir DJD-1/3, Filler o Pair-Block como M4.
- Ganador automático, nuevas ponderaciones de métricas, soporte Windows nativo
  del supervisor, múltiples procesos web/réplicas o infraestructura distribuida.
- Importación HU-018, sus correcciones, estrés de importación y tareas TA-044
  y siguientes. Su interoperabilidad se trata solo como escenario condicionado.
- Push de `feature/TA-043-integracion-seis-motores`, merge, deploy o cambios en
  Supabase/Heroku.

## 3. Actor y precondiciones

**Actor:** persona autorizada con `optimization.execute`, `optimization.view` y,
para confirmar, `optimization.confirm`, según cada operación.

- Pedidos persistidos válidos y en estado admitido; configuración vigente válida,
  stock compatible y umbrales de retazo disponibles al aceptar.
- Linux/WSL2 con procfs, `spawn`, límites de proceso y control de descendientes;
  preflight real satisfactorio. Una única instancia web y admisión compartida con
  FF legacy y v1. No se asume que seis workers caben en un dyno Heroku.
- Para pruebas mutantes: PostgreSQL propio y aislado, servicios loopback, usuarios
  y datos sintéticos controlados. Sin uso implícito de la BD de `.env`.
- La autorización vigente cubre exclusivamente B01. Sus consumidores requieren
  superar la puerta de revisión y autorización expresa del responsable. Estado
  Draft no equivale a aprobación de TA-043 completa.

## 4. Entradas y datos

| Dato | Representación / regla |
|---|---|
| Pedidos y unidades | `order_ids`; `order_id`, `piece_id`, `unit_index`, cantidades expandidas y solicitud original persistida |
| Formas y material | Geometrías canónicas RECTANGULO, CIRCUNFERENCIA, POLIGONO_CONVEXO; tipo de vidrio y espesor exactos |
| Fuentes | `source`, `material_id`, `physical_unit_index`, geometría y ranking capturados una vez; retazo unitario |
| Configuración común | Resolución, margen, separación, paso angular real 5°, ID/versión de configuración y mínimos de retazo; no se releen por motor |
| Entrada congelada | DTO canónico desconectado y SHA256 del problema; mínimos métricos y solicitud original también congelados en el agregado |
| Identidad | `comparison_id`, `execution_id`, `method`; conjunto y orden de métodos guardados explícitamente por perfil |
| Ejecución | Estado de ciclo, despacho, `complete`, resultado opcional, métricas opcionales, tiempo de cálculo y diagnóstico de terminación separado |
| Concurrencia optimista | `expected_version`, clave idempotente del actor, ejecución seleccionada y recibo durable |

Simular puede registrar comparación, ejecuciones y estado de pedidos del ciclo
existente; **no** reserva ni consume stock, ni genera movimientos o retazos.
Los workers reciben el mismo DTO sin ORM, sesiones DB, layouts ni cachés mutables
compartidos. El hash del problema no sustituye la captura de mínimos métricos.

## 5. Reglas de negocio y requisitos

### 5.1 Requisitos funcionales

| ID | Requisito |
|---|---|
| RF-01 | Capturar una sola vez pedidos, piezas/unidades, stock, configuración y mínimos métricos; mantener esa entrada para los seis motores. |
| RF-02 | Usar exclusivamente el catálogo de §1.3 con identidad estable y sin duplicados, aliases o sustituciones silenciosas. |
| RF-03 | Crear exactamente una ejecución por método en v2 y contabilizar las seis hasta un estado terminal, incluidas las no iniciadas por aborto global. |
| RF-04 | Distinguir resultado completo, parcial válido y fallo técnico; conservar motivos de terminación y no convertir agotamiento en `NO_FIT`. |
| RF-05 | Comparar las métricas comunes con las fórmulas/unidades actuales y el mismo contexto; mostrar ausencia como tal y completitud junto a las métricas. |
| RF-06 | Consultar y visualizar cada ejecución con navegación dinámica, sus distribuciones 2D/3D, progreso y errores propios. |
| RF-07 | Permitir selección manual solo de ejecución completa, persistida, perteneciente al agregado y elegible tras parada segura del cálculo. |
| RF-08 | Confirmar exclusivamente la ejecución seleccionada, usando su snapshot del servidor; simular y seleccionar no consumen inventario. |
| RF-09 | Mantener aceptación y confirmación idempotentes, recuperación por clave y control de versión sin duplicar ejecuciones ni consumos. |
| RF-10 | Revalidar y bloquear pedidos/stock al confirmar; revertir todos los efectos ante conflicto o fallo transaccional. |
| RF-11 | Preservar comparison-v1, sus tres métodos, su historia y el endpoint legacy `/api/optimization/runs`, sin conversiones ficticias. |
| RF-12 | Publicar seis motores mediante comparison-v2 explícito, validar perfil/versión y rechazar cruces de perfil sin degradación silenciosa. |
| RF-13 | Persistir perfil, métodos, entrada, resultados/diagnósticos y elección/recibo con migración aditiva PostgreSQL y protección de historia. |
| RF-14 | Adaptar registros, factories, contratos y codecs al perfil; eliminar cardinalidades de tres en el camino v2 y validar identidades en cada frontera. |
| RF-15 | Conservar HF productivo aprobado por la línea integrada: búsqueda local acotada, filtro, fallback y protección de cobertura/planchas de TA-042. |
| RF-16 | Conservar BRF: maximizar rectángulo residual, minimizar fragmentación y mantener desempates canónicos y parámetros actuales. |
| RF-17 | Conservar BS-2: ancho 2, generación, score, poda, desempates y límites internos existentes, sin invocar otro motor como reemplazo. |
| RF-18 | Adaptar callbacks/checkpoints y diagnóstico de M6; diferenciar estados provisionales de Beam Search de placements finales persistidos. |
| RF-19 | Recuperar por ID/clave tras recarga, pérdida de eventos o reinicio sin recalcular; conservar permisos y trazabilidad de pedido/pieza/unidad/fuente. |
| RF-20 | Tras integración independiente de HU-018, verificar pedidos importados de las tres formas con seis motores, 5° y límite operativo vigente, sin incorporar sus correcciones en TA-043. |

### 5.2 Requisitos no funcionales

| ID | Requisito |
|---|---|
| RNF-01 | Aislar estado, procesos, cachés y referencias visuales por ejecución; un fallo local no elimina resultados ajenos ni altera el problema común. |
| RNF-02 | Aplicar presupuestos globales y por motor, IPC/retención acotados, admisión exclusiva y concurrencia limitada; medir antes de ampliar cualquier presupuesto. |
| RNF-03 | Demostrar parada de workers, lectores/monitor y supervisor antes de liberar admisión; no dejar huérfanos ni usar TTL como prueba de muerte. |
| RNF-04 | Mantener teclado, foco, semántica de pestañas, estados legibles, movimiento reducido y diseño usable en escritorio/móvil. |
| RNF-05 | Preservar determinismo del cálculo bajo entradas/límites equivalentes y regresión de reglas comunes; diferencias por límites temporales se diagnostican. |
| RNF-06 | Cerrar TA-043 solo con trazabilidad completa, revisión humana, evidencias reproducibles y smoke real incremental/integral aprobado. |

### 5.3 Requisitos smoke obligatorios

| ID | Requisito sobre servicios reales en entorno aislado |
|---|---|
| SM-01 | Backend y frontend levantan correctamente y se comunican. |
| SM-02 | La API inicia y consulta una comparación v2 de seis motores. |
| SM-03 | FF, BF, WF, HF, BRF y BS-2 exponen seis estados/identidades inequívocos. |
| SM-04 | Los seis resultados del caso completo se consultan por API y se visualizan en frontend. |
| SM-05 | Se selecciona manualmente una ejecución completa y elegible. |
| SM-06 | Confirmar afecta únicamente los materiales de esa ejecución y conserva trazabilidad. |
| SM-07 | Simular y seleccionar dejan intactos inventario y movimientos. |
| SM-08 | Una comparación histórica v1 de tres motores sigue consultable en API y frontend. |
| SM-09 | Un motor fallido no impide consultar/visualizar los resultados de los demás. |
| SM-10 | Al terminar no quedan procesos de optimización huérfanos y la admisión se libera solo después de la parada del supervisor. |

## 6. Flujo principal

1. La UI solicita explícitamente el perfil v2 con lote y clave idempotente.
2. Preflight/admisión compartida; una transacción corta valida pedidos y captura
   entrada/configuración/stock bajo un snapshot consistente PostgreSQL, y crea las
   seis ejecuciones. Resolver conflictos de concurrencia conservando idempotencia.
3. El supervisor despacha procesos aislados según la política de §9.2. La UI
   distingue espera y cálculo; no afirma que seis motores corren simultáneamente.
4. Cada resultado/diagnóstico se valida y persiste independientemente. El anuncio
   `result_persisted` ocurre después de su commit. Un observador no gobierna cálculo.
5. Se detienen y verifican descendientes y supervisor; el cierre seguro habilita
   selección de resultados completos persistidos y libera admisión en ese orden.
6. La persona compara cobertura, aprovechamiento, merma, recuperable, fuentes y
   tiempo de cálculo, consulta distribuciones y selecciona una ejecución elegible.
7. Confirma con ejecución, versión y clave. El servidor revalida, aplica solo esa
   solución en una transacción y entrega recibo durable recuperable por reintento.

## 7. Flujos alternativos y errores

- Resultado parcial: se conserva y visualiza con cobertura/razón; no es elegible.
  Un motor fallido sin resultado tiene métricas `null`, nunca ceros ficticios.
- Agotamiento M6: conservar `EXPANSION_LIMIT`, `GEOMETRY_PROBE_LIMIT`,
  `STATE_MEMORY_LIMIT`, `TIME_LIMIT` y última frontera completa si pudo entregarse.
  No prometer rescatar un parcial después de un kill duro sin paquete válido.
- Fallo independiente: terminar solo esa ejecución, conservar las demás y continuar
  la cola dentro del presupuesto global. Ante fallo global, marcar explícitamente
  cada ejecución pendiente, incluidas las nunca despachadas, con causa global.
- Desconexión, pausa visual, cambio de pestaña o error del observador no cancelan
  cálculo. Cursor vencido/retención agotada exige snapshot; no fabricar replay.
- Conflicto de selección, versión o stock: rechazar y recuperar estado; sin efectos
  parciales ni aceptar layouts enviados por el navegador.
- Plataforma insuficiente/ocupada: rechazo explícito antes de aceptar cuando se
  detecta en preflight; no simular éxito ni bajar precisión automáticamente.
- Recuperación ambigua: comprobar PID y tiempo de inicio de supervisor/workers;
  conservar admisión y bloqueo operativo si no se puede demostrar parada.
- Cliente antiguo ante recurso v2: error explícito de perfil incompatible; nunca
  entregar seis ejecuciones con etiqueta v1 ni esconder tres resultados.

## 8. Criterios de aceptación verificables

Cada fila es una obligación independiente; el PLAN enlaza todas con actividad y
prueba. El cumplimiento integral de los criterios permanece pendiente; las
verificaciones parciales de B01 se delimitan en su evidencia, sin aprobar TA-043
por redactar o probar solo contratos.

| CA | Requisito | Comprobación de aceptación |
|---|---|---|
| CA-01 | RF-01 | Los seis procesos verifican el mismo hash/DTO, mínimos y versión de configuración; cambios posteriores de stock/configuración no cambian sus entradas. |
| CA-02 | RF-02 | Exactamente los seis códigos de §1.3, nombres correctos y seis IDs distintos; método desconocido/duplicado se rechaza antes de ejecutar. |
| CA-03 | RF-03 | Agregado v2 conserva seis ejecuciones en éxito, arranque fallido y aborto global, sin pendientes indefinidas ni séptimo método. |
| CA-04 | RF-04 | Completo, parcial, no-fit y fallo se distinguen en API/BD/UI; las cuatro razones M6 sobreviven round-trip y un kill sin parcial no se inventa. |
| CA-05 | RF-05 | Métricas coinciden con cálculo común directo; unidades/cobertura son visibles, fallos usan null y tiempo de cola no se etiqueta cálculo. |
| CA-06 | RF-06 | Se abren seis ejecuciones y comparación con pestañas generadas desde datos; visores 2D/3D corresponden a sus snapshots sin doble rotación. |
| CA-07 | RF-07 | Solo un completo persistido es seleccionable tras cierre seguro; parcial, fallido, ajeno o versión obsoleta se rechazan sin elegir ganador. |
| CA-08 | RF-08 | El delta de materiales/movimientos/remanentes coincide exclusivamente con la selección del servidor; los otros cinco resultados no consumen stock. |
| CA-09 | RF-09 | Reintentos/concurrencia con igual clave recuperan una aceptación/recibo; distinto lote o perfil produce conflicto, sin duplicación. |
| CA-10 | RF-10 | Stock cambiado y fallo inducido a mitad de confirmación dejan el estado previo a ese intento: sin consumos, movimientos, remanentes ni recibo nuevos; se conservan la selección previa y los cambios externos legítimos de stock. |
| CA-11 | RF-11 | Fixture e historia real persistida v1 se leen antes/después de migrar; tres ejecuciones y respuestas legacy permanecen compatibles sin recálculo. |
| CA-12 | RF-12 | Rutas v1 reciben tres y v2 seis; todos los sobres/eventos/máscaras declaran perfil correcto; un acceso cruzado falla explícitamente. |
| CA-13 | RF-13 | Upgrade desde base vacía y con historia preserva datos/FK/unicidad; codecs históricos siguen válidos y downgrade con historia v2 se bloquea antes de DDL. |
| CA-14 | RF-14 | Registro/factory/codec/schema/UoW/visual/UI concuerdan por perfil; v2 no depende de cardinalidad tres ni de fallback FF. |
| CA-15 | RF-15 | HF integrado reproduce los casos vigentes de pocket/fallback/cobertura/planchas, límites y eventos de solución elegida sin cambiar su política. |
| CA-16 | RF-16 | BRF integrado conserva fuentes, placements y score/desempates frente al motor productivo directo bajo la misma entrada. |
| CA-17 | RF-17 | BS-2 integrado conserva ancho, traza, placements y métricas respecto de M6 directo/SP-006 en fixtures equivalentes sin corte temporal. |
| CA-18 | RF-18 | Callbacks no producen TypeError ni alteran resultado; rama provisional no se acumula como placement definitivo; al persistir, API/2D/3D coinciden con la frontera ganadora. |
| CA-19 | RF-19 | Recarga, expiración visual y reinicio recuperan resultados/elección/recibo sin optimizar otra vez; permisos e identidades impiden cruces de ejecuciones. |
| CA-20 | RF-20 | Si HU-018 se integra, pedido importado mixto ejecuta seis motores a 5° dentro de 150 unidades; geometría/cantidades se conservan. Antes se registra condicionado, sin falso PASS. |
| CA-N01 | RNF-01 | Fallo/mutación del estado privado de un worker no altera entrada ni resultados ajenos; referencias de máscaras cruzadas se rechazan. |
| CA-N02 | RNF-02 | Solo se inicia la concurrencia configurada y medida; límites por motor/global/IPC/retención se verifican realmente sin ampliarlos para pasar pruebas. |
| CA-N03 | RNF-03 | Evidencia temporal demuestra join de hijos/lectores/monitor y fin del supervisor antes de admisión libre; muerte, timeout y fallo DB no dejan procesos propios vivos. |
| CA-N04 | RNF-04 | Teclado recorre todas las pestañas y controles con foco/ARIA coherentes; escritorio/móvil y movimiento reducido conservan datos/acciones. |
| CA-N05 | RNF-05 | Regresiones comunes y de seis motores pasan; ejecuciones repetidas/directas equivalentes conservan identidades, fuentes y geometría sin exigir que todos obtengan lo mismo. |
| CA-N06 | RNF-06 | Cada CA tiene actividad/prueba/evidencia, revisión humana registrada y smoke incremental/integral PASS real; una omisión obligatoria impide cierre. |
| CA-S01 | SM-01 | Arranque real, health/readiness y carga UI/API autenticada satisfactorios con PostgreSQL aislado; sin mocks de red ni motores. |
| CA-S02 | SM-02 | POST v2 retorna aceptación y seis IDs; GET por ID/clave recupera el mismo trabajo y llega a terminal. |
| CA-S03 | SM-03 | Registro API/UI identifica FF, BF, WF, HF, BRF y BS-2 desde espera hasta su estado terminal. |
| CA-S04 | SM-04 | Caso pequeño completo permite consultar seis resultados persistidos y abrir sus distribuciones reales en frontend. |
| CA-S05 | SM-05 | Selección de completo elegible persiste al recargar y coincide con la UI; selección inicial es nula. |
| CA-S06 | SM-06 | Confirmación y repetición idempotente generan exactamente el delta previsto para el seleccionado, con recibo y fuentes trazables. |
| CA-S07 | SM-07 | Comparación exacta de planchas, retazos y movimientos antes/después de simular y seleccionar demuestra cero consumo. |
| CA-S08 | SM-08 | Comparación v1 preexistente conserva tres resultados y se consulta por HTTP y UI tras migración/arranque de v2. |
| CA-S09 | SM-09 | Muerte controlada de un worker propio en otro caso mantiene accesibles los otros cinco resultados y el diagnóstico del fallido. |
| CA-S10 | SM-10 | Inventario de PID/identidad antes y después acredita cero procesos propios huérfanos, supervisor detenido y nueva admisión segura. |

## 9. Impacto técnico y decisiones propuestas

### 9.1 D-01 — Nuevo perfil comparison-v2 y compatibilidad explícita

Se adopta **nueva versión**, porque v1 exige exactamente FF/BF/WF en documentación,
`comparison_schemas.py`, `comparisonApi.js`, UoW y codecs; añadir tres valores no
es una evolución compatible para sus consumidores estrictos.

Propuesta de API: `/api/optimization/comparisons-v2` para el nuevo perfil
`comparison-v2`, `schema_version: 2`; conserva los subrecursos actuales de inicio,
consulta por clave/ID, ejecuciones, eventos, visual/máscaras, selección,
confirmación y liberación. `/comparisons` conserva v1, creación de tres motores y
su política histórica; `/runs` conserva FF y `visual-v2`. No cambia el default
de clientes antiguos. Es una decisión de esta SPEC pendiente de revisión.

Cada ruta exige el perfil persistido; acceso cruzado devuelve conflicto explícito
de perfil (código propuesto `COMPARISON_PROFILE_MISMATCH`) sin ejecutar ni mutar.
La UI despacha parsers por perfil, conserva enlaces v1/legacy y, al buscar por ID,
resuelve el perfil mediante respuesta/diagnóstico explícito; nunca prueba una
mutación como mecanismo de detección. Las claves siguen siendo únicas por actor:
reutilizarlas entre perfiles/lotes incompatibles produce conflicto.

### 9.2 D-02 — Supervisión con concurrencia acotada

V2 propone **un worker activo inicialmente**, seis procesos independientes a lo
largo del trabajo, en orden estable del catálogo. No se comparte una instancia
de motor ni se conserva memoria de un worker para el siguiente. Cualquier mayor
concurrencia requiere medición y revisión de presupuesto; no se dispara seis
workers simultáneos ni se extrapola capacidad del entorno local a Heroku.

Se mantienen como cotas iniciales los valores existentes de
`application/comparison_limits.py`: 1 GiB RSS agregado muestreado, 240 MiB RSS de
supervisor, 256 MiB de espacio virtual duro por worker, reserva auxiliar 16 MiB;
arranque 30 s, cálculo por motor 120 s y global 180 s; paquetes 12 MiB/visual 4 MiB,
un paquete en cola por worker, retención visual total 32 MiB y eventos 8 MiB.
Las cotas se comparten entre seis, no se multiplican. RSS y espacio virtual son
medidas distintas. Se conservan además las cotas geométricas/cache y las de
observadores/eventos/ventanas vigentes. No se inventan límites nuevos de memoria
o tiempo ni se promete que estos presupuestos permitan completar toda entrada.

El reloj global incluye espera/despacho/arranques; el de cálculo por motor inicia
al calcular y no incluye cola. Startup se controla por proceso despachado. Si el
global vence antes del sexto, las pendientes terminan con motivo global explícito.
La UI muestra espera y causa, no falta de solución. Los límites internos M6
(30 s, 32 MiB estimados de estado, 60.000 expansiones, 1.000.000 sondeos, ancho 2,
12 hijos y 2 posiciones) siguen vigentes; la primera cota alcanzada se conserva.

Un dueño externo al hilo de cálculo debe esperar su fin real antes de liberar
la lease: el supervisor no puede certificar su propio join. El orden obligatorio
es detener/join workers y lectores/monitor, finalizar supervisor, verificar
identidades y persistir cierre seguro, luego liberar admisión/habilitar selección.
El runtime actual libera desde `work()` antes de salir del hilo; esa brecha debe
resolverse en la implementación, sin cambiarla en esta sesión. Shutdown/reinicio
usa el mismo protocolo y conserva admisión si la parada es incierta.

### 9.3 D-03 — Adaptadores y semántica visual fiel

Registro por perfil con factory/identidad/tipo de resultado/capacidades de
observación. Los tres primeros y HF/BRF aceptan `checkpoint` y `on_visual`;
M6 acepta `checkpoint`/`on_event`, pero no `on_visual`, y `optimize()` descarta
el diagnóstico de `run()`. El adaptador M6 debe conservar `BeamSearchOutcome`
y traducir observación sin cambiar búsqueda, score, poda o desempates.

Los eventos durante Beam Search describen exploración: no son una secuencia
irreversible de colocaciones. La primera entrega puede mostrar progreso de
búsqueda sin dibujar ramas. Si muestra una frontera provisional, debe identificar
estado/revisión y **reemplazar** su dibujo, no sumar placements incompatibles.
Solo la frontera ganadora validada y persistida alimenta el layout definitivo;
su replay se etiqueta como presentación posterior. No se recalcula para animar.
HF conserva replay exclusivo de la solución elegida; sus exploraciones internas
no se presentan como colocaciones finales. Los checkpoints siguen activos aun
sin observadores y la telemetría acotada no cambia decisiones del algoritmo.

### 9.4 D-04 — Persistencia y migración

Reutilizar `optimizaciones`, `ejecuciones_optimizacion`, materiales, métricas y
relaciones existentes; no crear tablas por heurística. Ampliar mediante nueva
migración el CHECK `ck_ejecuciones_metodo` de FF/BF/WF a los seis códigos; mantener
unicidad `(id_optimizacion, metodo)`, FK y elección del dueño correcto. Determinar
la revisión Alembic padre desde el head vigente al implementar, no editar
migraciones históricas ni ejecutar contra una BD compartida en esta sesión.

Propuesta durable: agregado `comparison_snapshot_version: 2` para v2, con perfil,
lista de métodos, configuración de motores/presupuestos y marcas de despacho/
parada; resultado `snapshot_version: 3` para identidad, resultado y diagnóstico
(`termination_reason`, origen motor/supervisor y estadísticas permitidas).
No confundir estas versiones con `comparison_version` (optimista), perfil HTTP
o versión de configuración. Los lectores mantienen agregado v1 y resultados
snapshot 1 (FF) y 2 (FF/BF/WF), sin reescribirlos, rellenar motores ni recalcular.
Razón de parada no se reduce a `failure_code`: un parcial puede tener resultado
válido y diagnóstico de recurso. Estado de despacho en v2 distingue espera/
arranque/cálculo/terminal sin modificar el significado histórico de estados SQL.

Upgrade aditivo sobre BD vacía y con historia real controlada; cambios de JSON
solo en nuevos registros. Downgrade debe fallar antes de DDL si perdería historia
v2 o métodos nuevos. Rollback operativo preferido: deshabilitar creación v2 y
mantener lectores compatibles; no desplegar lectores antiguos sobre historia v2.

### 9.5 Módulos, API y frontend previstos

Backend conserva `Presentation -> Application -> Domain`; infrastructure
implementa puertos. La aplicación no importa experimentos. El alcance previsto
incluye `comparison_contracts`, `comparisons`, `comparison_calculation`,
`comparison_runner`, `comparison_snapshot`, `comparison_uow`, `comparison_transport`,
`comparison_runtime`, schemas/serialización/rutas y confirmación. Dominio solo
recibe adaptación de contratos/observación si es necesaria, sin cambios de política.

Frontend generaliza la estructura visual FF/BF/WF existente mediante
`comparisonApi`, `comparisonController`, `ComparisonWorkspace`,
`visualContract`, `visualState` y `runContract`; reutiliza `RunVisualization`,
`PlacementCanvas` y `PlacementScene3D`, sin ventanas nuevas por motor ni componentes
duplicados. Conserva métricas, cobertura, piezas no colocadas, tiempos de cálculo,
planchas y retazos por ejecución. Pestañas y tabla usan ejecuciones del
perfil, con una columna/fila por motor y metadatos de nombre/capacidad. Mantener
roles ARIA, flechas/Home/End, foco, teclado en diálogos, móvil y movimiento reducido.
Fallos muestran diagnóstico y métricas ausentes; parciales muestran cobertura y
distribución disponible sin habilitar confirmación.

## 10. Pruebas previstas

El PLAN define T-01–T-14 y ST-INC/ST-INT, con trazabilidad por CA. Se prevén
contratos/round-trip, paridad de seis motores, fallo independiente, recursos reales,
historia v1/legacy, migración PostgreSQL, aceptación/recuperación, selección,
confirmación/rollback, componentes, E2E escritorio/móvil y regresión.

Los smoke son **ejecuciones reales**: FastAPI, frontend servido, navegador y
PostgreSQL aislado con motores productivos y procesos `spawn`. Mocks, inspección
estática, lint/build o unitarias solas no satisfacen SM-01–SM-10. Habrá smoke
incremental después de cada bloque funcional ejecutable y smoke integral
obligatorio de seis motores antes de cierre. El PLAN especifica entorno, datos,
pasos, PASS/FAIL, evidencia y limpieza. ST-INC-01 se registra por separado en la
evidencia B01; el smoke integral y las capacidades futuras siguen pendientes.

## 11. Riesgos, dependencias, mediciones y evidencias

| Riesgo / dependencia | Tratamiento y decisión pendiente |
|---|---|
| Presupuesto global 180 s frente a cola de seis y HF costoso | Medir latencia/cobertura/espera real; no subir timeout ni prometer seis completos para cualquier entrada. HF tiene antecedente puntual 24,76× FF, no cota universal. |
| Memoria M6/rasters, IPC y seis sesiones visuales | Medir RSS agregado, espacio virtual, retención, colas y descarte; mantener cotas totales. |
| Heroku sin capacidad preflight suficiente | Plataforma/presupuesto concreto pendientes de verificación; preparación de despliegue no autoriza deploy ni seis workers. |
| Salida M6 sin diagnóstico o ramas visuales mezcladas | Adaptador de outcome y pruebas de frontera/provisional/final obligatorios. |
| Liberación temprana o proceso huérfano | Dueño externo espera supervisor, prueba de muerte con identidad, reconciliación conservadora. |
| Historia ilegible / cliente v1 estricto | Perfil/rutas separados, lectores múltiples y pruebas de upgrade con historia. |
| Consumo ajeno o doble confirmación | Bloqueos, versión, idempotencia y transacción única sobre selección del servidor. |
| Coordinación de interfaces | Fabricio integra; coordinar con Andro para HF/revisión y con Luis Anthony Ibáñez Herrera para BRF; responsables de frontend/API/BD/QA se acuerdan, no se inventan asignaciones. |
| HU-018 / PR #96 | Dependencia externa condicionada; probar después de su integración separada, sin bloquear el núcleo si sigue ausente. |

Quedan por medir: concurrencia admisible superior a uno, picos/contabilidad real,
duración de seis motores con callbacks, costo de serialización/replay, retención
compartida y capacidad de la plataforma objetivo. Mantener 20 pedidos, **150
unidades expandidas**, 128 vértices y 50 unidades físicas de stock por material,
según TA-037; son límites de admisión, no garantía de tiempo/memoria. Ninguna
medición pendiente recibe un PASS ni un nuevo número sin evidencia/revisión.

Evidencia por bloque en `docs/evidence/sprint-02/TA-043/`: commit probado, entorno,
comandos exactos/directorio, fixtures/hashes, configuración 5°, HTTP/NDJSON,
capturas accesibles, snapshots/deltas PostgreSQL, recibos, reporte PID/joins,
recursos y limpieza. Separar resultados históricos, condicionados y actuales;
no almacenar secretos. El cierre exige CA-N06 y CA-S01–CA-S10, smoke incremental
e integral reales, regresión y revisión humana; documentar una prueba no la ejecuta.

## Historial de estado

- 04/11/2026 — **Draft**: Fabricio autoriza exclusivamente B06 sobre B05
  `70084ce`, `42e98bd`, `18c36bc`. API explícita v2, lectura por propietario,
  transporte y recuperación sin recálculo; selección/confirmación pendientes B08
  y seis pestañas pendientes B07. Fetch detecta eliminación externa de
  `origin/integration-02`; se conserva la base local `integration-02` en
  `d85a8d3`, sin recrear/publicar referencias ni incorporar otra integración.
  [Evidencia B06](../evidence/sprint-02/TA-043/B06/README.md). Se conservan los
  36 requisitos/CA y las decisiones de algoritmos, contratos y cierre seguro.

- 03/11/2026 — **Draft**: autorización exclusiva B05 y ampliación interna de
  `runtime` aprobada por Fabricio para propiedad versionada, token del supervisor
  y PID/start_ticks de dueño/workers; lector B02 anterior conservado. Sin cambios
  SQL/Alembic, codecs B01 o cotas B04. Coordinación v2 validable en aplicación/BD/
  procesos; comprobación pública v2 pendiente de B06. Evidencia en
  [B05](../evidence/sprint-02/TA-043/B05/README.md); parada obligatoria antes de B06.

- 03/11/2026 — **Draft**: autorización exclusiva B04; puerta temprana y primitiva
  secuencial de recursos documentadas. Smoke de servicios disponibles separado
  de las pruebas reales de procesos; despacho/admisión v2 por HTTP pendientes de
  B05/B06. Detenerse antes de B05; sin cambios de presupuestos o heurísticas.

- 03/11/2026 — **Draft**: autorización limitada a B03. Adaptadores optativos,
  observación neutral M6 y validación directa/durable registradas en evidencia.
  ST-INC-03 valida v1/legacy; los adaptadores desde HTTP siguen pendientes de
  integración B05/B06. Parada antes de B04; no se aprueba el cierre de TA-043.

- 03/11/2026 — **Draft**: autorización limitada a B02; migración aditiva,
  persistencia v2 optativa, lectores históricos y ST-INC-02 registrados en su
  evidencia. B03 y posteriores, así como el cierre integral, siguen pendientes.

- 03/11/2026 — **Draft**: verificación de base y revisión documental; SPEC y PLAN
  preparados para revisión de Fabricio. Implementación, pruebas y smoke pendientes
  de autorización. No marcar Reviewed, Implemented, Verified ni TA-043 Closed.
- 03/11/2026 — **Draft**: revisión final; se precisa la reutilización de la vista
  FF/BF/WF y de sus datos por ejecución en §9.5, sin cambiar requisitos, CA ni
  decisiones arquitectónicas. Implementación no autorizada.
- 03/11/2026 — **Draft**: autorización posterior expresa de Fabricio limitada a
  B01; catálogo/contratos, pruebas y ST-INC-01 registrados en evidencia B01.
  Revisión de su resultado pendiente; B02/B03 y demás consumidores no autorizados.
