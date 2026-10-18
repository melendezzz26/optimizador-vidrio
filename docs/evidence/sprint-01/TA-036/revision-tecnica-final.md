# TA-036 — Revisión técnica final

Fecha: 13/10/2026 (America/Lima). Revisión técnica asistida, **no revisión
humana formal**. Rama `feature/TA-036-saneamiento-funcional`, inicio limpio en
`8520ac7639713090d77cbd3a74e13379424f940f`. Se comprobaron los seis commits
solicitados desde `f6ed987` hasta `8520ac7`. Integración permanece en `b7a0175`.

Se leyeron íntegramente la SPEC y las cinco evidencias indicadas en el índice,
y se contrastaron con código, tests y refs paralelas locales. Este documento
añade el análisis literal de CA-09, el conflicto documental de HU-008 y una
nueva ejecución completa; no reemplaza los resultados históricos de T06.
No cambia producción, migraciones, criterios ni estado formal de la SPEC:
**Draft / Reviewer pendiente**. Reviewed, Implemented y Verified requieren
el flujo formal posterior; el reviewer humano debe ser distinto del autor.

## CA-09: texto, alcance y resultado

Texto exacto vigente:

> La compatibilidad de stock útil queda invocable desde Optimization sin dependencia innecesaria de los esquemas HTTP/ORM de Orders.

**Resultado: PARTIAL.** “Queda invocable” exige disponibilidad técnica de una
capacidad reutilizable. No significa necesariamente que un flujo de
Optimization ya la invoque en producción (la lectura A sería más fuerte que
el texto), pero tampoco basta una intención documental de integración futura
(la lectura B, por sí sola, es más débil que el criterio). No se acredita esa
capacidad en el árbol TA-036: no contiene `get_compatible_stock`,
StockCompatibilityValidator ni un consumidor de Optimization, cuyo módulo
solo conserva el esqueleto. El POST sí permanece desacoplado y probado.

| Fuente | Exigencia o hecho | Consecuencia |
| --- | --- | --- |
| CA-09 | Disponibilidad “invocable desde Optimization”, sin acoplamiento HTTP/ORM de Orders | Requiere algo más que no llamar stock desde POST. |
| Alcance §4 | Mantener registro independiente y reservar consulta para Optimization | Delimita saneamiento y destino del contrato. |
| Decisión §6.2 | Consulta en etapa posterior; preservar implementación útil cuando se inicie esa etapa | Define un momento posterior, sin autorizar duplicación ahora. |
| Impacto §7 y coordinación §8 | Reutilizar después; consulta paralela de Luis/Andro; TA-036 no integra/copia ramas | Separa el consumo futuro de la implementación actual. |
| Fuera de alcance §5 | No implementar algoritmos de Optimization ni integrar ramas paralelas | No excluye por sí solo todo adaptador, pero impide resolver el faltante absorbiendo HU-008. La exclusión T02–T06 aplica al primer bloque documental, no a las etapas posteriores ya autorizadas. |
| Dependencias §10 y tarea T04 | Alineación entre ramas; confirmar POST independiente y preservar compatibilidad reusable | Hay una dependencia funcional pendiente, no evidencia de integración terminada. |
| Implementación §15, evidencia T06 y §17 | Conectar HU-008 posteriormente; CA-09 PARTIAL | Describe correctamente el faltante. “Técnicamente completa” solo puede referirse al saneamiento implementado, no a todos los CA literalmente satisfechos. |
| Rama HU-008, 46d801e | Puerto, consulta y validador existen allí, sin cambio del POST | Su existencia en otra ref no constituye implementación invocable en TA-036. |

Hay una **inconsistencia temporal/de alcance**: CA-09 expresa una capacidad
presente mientras las decisiones y evidencias reservan su disponibilidad
integrada para una etapa posterior. El texto no permite declarar PASS bajo
la mera preparación documental. Tampoco corresponde FAIL total: la parte de
desacoplamiento/preservación está demostrada y el faltante está identificado.

No se puede decidir unilateralmente que todo CA-09 “pertenece a HU-008”: el
contrato de separación afecta TA-036; implementar/integrar la consulta y su
consumo pertenece al trabajo posterior HU-008/Optimization. La revisión humana
debe aprobar esa delimitación. Mientras tanto, el criterio original permanece
intacto y PARTIAL. Si se decide exigir integración real para cerrar todos los
CA, TA-036 no cumple todavía ese cierre total; ello no impide presentar un PR
de saneamiento que explique expresamente el alcance pendiente.

### Propuesta documental exacta, no aplicada

Si la revisión humana confirma el alcance diferido, se propone sustituir
CA-09 por:

> TA-036 mantiene POST /api/orders independiente de consultas de stock y documenta el contrato de integración posterior de HU-008 con Optimization: planchas disponibles con cantidad positiva, retazos disponibles, geometría canónica y datos desacoplados de los esquemas HTTP/ORM de Orders. La consulta útil existente en HU-008 se preserva sin duplicarla ni integrarla en TA-036; su invocación desde Optimization se verificará en esa integración posterior.

Y registrar como criterio posterior de HU-008/Optimization, sujeto a su propia
revisión:

> Tras integrar HU-008, la consulta compatible puede invocarse desde la capa de aplicación de Optimization mediante un puerto y datos independientes de los esquemas HTTP/ORM de Orders; sus pruebas verifican saldo positivo, retazos disponibles y ausencia de llamadas desde POST /api/orders.

Esto haría explícita la responsabilidad que §6.2/§7/§8 ya difieren. **No se ha
aplicado esta propuesta ni utilizado para recalificar el CA actual.**

## Matriz técnica de aceptación

Se conservan los criterios originales. La [matriz T06](t06-regresion-final.md)
contiene rutas y nombres exactos de tests; estas suites se vuelven a ejecutar
en esta revisión.

| CA | Resultado | Evidencia reproducible contrastada |
| --- | --- | --- |
| CA-01 | PASS | ORD-API: cuadrado/rombo con iguales lados conservan vertices_mm y área; GEO-UNIT: la forma no se infiere de lados. No hay rasterizador propio en esta rama. |
| CA-02 | PASS | GEO-UNIT, convexityValidation, CustomPieceEditor y E2E HU-007: cierre, convexidad, cruce, escala, ángulos y formas distintas. |
| CA-03 | PASS | INV-PG HTTP real: baja 2 de 10→8 con movimiento 2; pruebas adicionales 1→9 y 4→6. |
| CA-04 | PASS | INV-PG: baja total 10→0/false, rollback conjunto y carrera que no excede saldo. |
| CA-05 | PASS | INV-PG: baja retazo registra 1, estado false, fila e historial conservados. |
| CA-06 | PASS | InventoryPage: solo Historial/Editar/Dar de baja; PATCH administrativo preservado y probado. |
| CA-07 | PASS | INV-PG y HU014-UI: estado/saldo disponible primero, fecha/ID determinista y retazo no disponible detrás. |
| CA-08 | PASS | ORD-API registra con Plancha/Retazo vacíos; use case sin stock y validación de catálogo conservada. |
| CA-09 | PARTIAL | Análisis literal anterior; disponibilidad integrada desde Optimization pendiente. |
| CA-10 | PASS | RegistrarRetazoGeometry: tres pruebas del editor real compartido, payload canónico, reset y edición previa. |
| CA-11 | PASS | ORD-PG: cuatro estados no cancelados, fecha/ID DESC, filtros y paginación; ORD-API: cancelado al final. |
| CA-12 | PASS | Migración PostgreSQL: histórico desconocido NULL, backfill veraz unitario, CHECK y downgrade seguro/bloqueado. |
| CA-13 | PASS | SHA, comandos, resultados y límites documentados sin secretos ni artefactos locales versionados. |

## Nueva ejecución completa

Mismo entorno local y comandos reproducibles de [T06](t06-regresion-final.md):
Python **3.11.9** del venv backend instalado, `PYTHON_DOTENV_DISABLED=1`,
`NEWGLASS_REQUIRE_POSTGRES=1`, `PGCTLTIMEOUT=85`. PostgreSQL temporal propio,
loopback y datos sintéticos. No se accede a Supabase, Heroku ni Pages.

| Comando | Resultado de esta revisión |
| --- | --- |
| `python -m alembic heads` | Un único head `ta036a1b2c3d`, padre `fa014e1a2b3c` |
| `python -m pytest -q --tb=short` | 1330 passed, 0 failed/skipped; 314,62 s; 1 warning existente |
| `npm.cmd run test:unit` | 103 passed, 0 failed/skipped; 222,9692 ms |
| `npm.cmd run test:component` | 211 passed, 21 archivos; 42,54 s |
| `npm.cmd run lint` | OK |
| `npm.cmd run build` | OK; 2,40 s |
| `npm.cmd run test:e2e -- --list` | 32 casos descubiertos en cuatro archivos |
| `npm.cmd run test:e2e -- --reporter=list,json` | 31 passed, 0 failed, 1 skipped, 0 flaky; 43783,688 ms |

E2E usa toda la suite, sin filtros; list/json solo cambia el formato de salida.
Inicio `2026-10-13T05:24:10.842Z` (00:24:10,842 America/Lima). Chrome local,
proyectos chromium-desktop (1440×900) y chromium-mobile emulado (390×844):
16/16 y 15/16 casos aprobados respectivamente. El único skip es
`HU-014: Almacenero registra una baja y consulta el movimiento persistido`,
proyecto móvil, por **“La mutación agota un recurso compartido entre viewports.”**
Corresponde exactamente al caso conocido de la plancha #701 agotada en
escritorio. Se informa como omisión; no como éxito. Sin errores globales E2E;
teardown completado y archivo de estado del servidor temporal retirado.

Los conteos frontend coinciden con 103/211. No se modifican tests ni patrones
de descubrimiento para conseguir estos resultados.
Backend terminó con exit 0 y sin errores de teardown. Su único warning es la
deprecación existente de httpx con Starlette TestClient. No apareció ningún
fallo nuevo en las suites ejecutadas.

## Migración, inventario, pedidos y geometría

Se releyeron schemas, servicio, escritor común de movimientos, migración,
CreateOrderUseCase, repositorio de pedidos, funciones geométricas y referencias
de UI. La migración es la única revisión añadida frente a integración;
ninguna revisión histórica cambia.

- Plancha: request entero estricto >0, lock, validación de saldo, movimiento y
  decremento en transacción; estado false al llegar a cero. Tests cubren bajas
  parciales, total, 0/negativo/exceso/fracción/bool/NULL y rollback/concurrencia.
- Retazo: cantidad asignada 1, estado false; fila e historial conservados,
  sin DELETE físico. UI conserva Historial/Editar/Dar de baja y orden operativo;
  no aparecen Activar/Desactivar independientes.
- NULL histórico queda documentado con veracidad: **SQL directo puede insertar
  NULL**; el esquema no distingue fechas de inserción. Schema/request, dominio,
  servicio y repositorio impiden nuevas bajas inválidas por rutas normales.
  CHECK rechaza cantidades conocidas <=0 y retazo conocido distinto de 1.
  La SPEC no requiere triggers; no se añaden.
- POST pedido no depende de stock: prueba API con BD vacía más inspección de
  dependencias productivas y spy unitario. El orden compartido de backend es
  no CANCELADO, CANCELADO, fecha DESC e ID DESC, antes de paginación.
- vertices_mm define la forma; escala uniforme conserva ángulos y disposición.
  Tests cubren extremos, medidas pequeñas válidas, finitud, degenerados,
  teclado, selección línea/etiqueta sincronizada, undo/reset y validación.
  RegistrarRetazoForm importa/reutiliza CustomPieceEditor y transmite el
  formato canónico existente; no se copia otro editor.

## Trabajo paralelo no absorbido

Auditoría solo lectura de refs locales, sin fetch ni mutaciones de ramas:
HU-008 `46d801ed3faacc0f62018584d0d6f8a65900d440`, raster
`5c58321f02c02f693ccb462390a1588952c237bc`. Se repitieron log/diff de ramas y
git show de puerto, consulta, validador, rasterizador y SPEC HU-008.

| Rama | Solapamiento real | Hallazgo y acción posterior |
| --- | --- | --- |
| HU-008 | `backend/app/modules/inventory/application/ports.py`; `backend/app/modules/inventory/infrastructure/repository.py` | TA-036 cambia cantidad/orden, no reimplementa get_compatible_stock ni StockCompatibilityValidator. Preservar ambos contratos al integrar; consulta con estado/saldo positivo, fuera del POST. Riesgo medio. |
| TA-005/TA-006 | Ninguno | TA-036 no modifica Optimization ni incorpora rasterizador. Aguilar ya acepta geometry.vertices_mm; conservar su algoritmo y conectar geometría final persistida. Riesgo textual bajo y funcional al integrar. |

**Conflicto documental adicional de HU-008:** su SPEC en 46d801e todavía exige
bloquear el registro por falta de stock: objetivo, alcance, RN-04, flujo POST,
E-01/E-02 y CA-04. Esto contradice TA-036 §6.2/CA-08. El código de esa ref aún
no conecta la consulta al POST; la discrepancia está en el contrato futuro.
Luis/Andro deberán revisar esos apartados para ubicar la evaluación en
Optimization y retirar el rechazo por stock del registro, conservando la
consulta y validación geométrica útiles. No se modifica su SPEC ni su rama.

## Worktrees: inspección previa y preservación

Al inicio `git worktree list --porcelain` registra exactamente:

1. `optimizador-vidrio`, integration/sprint-01, b7a0175, limpio.
2. `TA036-saneamiento-worktree`, feature/TA-036-saneamiento-funcional, 8520ac7,
   limpio antes de las pruebas/documentación.

La carpeta `TA036-auditoria-58911a6` existe, pero **ya no es un worktree
registrado ni un repositorio Git**: `git -C <ruta> status --short` responde
“not a git repository”. Conserva AUDITORIA-TA036.md, scripts de análisis,
reportes JSON/logs/tar y subdirectorios backend/frontend sin referencia Git
en esa carpeta. Se conserva intacta; su eliminación no satisface la condición
de preservar trabajo no versionado. No se afirma que haya sido eliminada en
esta sesión. No se encontraron otras carpetas TA036 en la raíz de trabajo.

En el worktree activo, los archivos ignorados inspeccionados corresponden
exclusivamente a node_modules, dist, __pycache__, .pytest_cache y resultados
de herramientas. No hay .env ni otros archivos ignorados necesarios. Los
logs transitorios de esta revisión se retiran tras extraer los resultados.

El retiro del worktree activo se realizará desde el repositorio principal,
solo después del commit documental, status limpio y comprobación de que
`feature/TA-036-saneamiento-funcional` apunta al nuevo commit y contiene los
seis commits anteriores. Se usará `git worktree remove`, sin borrar la rama,
sin force y sin checkout de TA-036 en el principal. La comprobación posterior
de paths, rama, commits, prune y status se reportará en la entrega de esta
sesión; no se registra aquí como operación ya realizada antes del commit.

## Riesgos y decisión técnica

Persisten CA-09 PARTIAL y su inconsistencia documental, la SPEC HU-008
incompatible pendiente de revisión, la única baja móvil E2E omitida y las
integraciones futuras. Las refs inspeccionadas no certifican el tip actual
del servidor remoto. El downgrade con cantidades conocidas se bloquea
intencionalmente para preservar historia. La carpeta de auditoría residual
se mantiene por seguridad de sus archivos no versionados.

La revisión humana formal por una persona distinta del autor sigue pendiente.
READY FOR PR significa que el saneamiento puede presentarse con estos límites
explícitos; no equivale a cumplimiento total de CA, aprobación para merge o
estado Verified.

**Conclusión técnica: READY FOR PR**, manteniendo CA-09 PARTIAL y los límites
anteriores explícitos. No se autoriza ni realiza push, PR, merge o deploy en
esta sesión. La publicación y revisión humana formal serán pasos posteriores.
