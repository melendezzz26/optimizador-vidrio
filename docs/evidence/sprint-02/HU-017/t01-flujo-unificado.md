# HU-017 T01 — Primer incremento del flujo unificado

## Alcance y trazabilidad

27/10/2026, base `4bcf54d` de `integration/sprint-01`. Rama local
`feature/HU-017-proceso-visual-optimizacion`. Inicio autorizado por el solicitante;
sin publicación de esta rama, PR ni merge. SPEC Reviewed y PLAN Approved se
conservan: este incremento no declara HU-017 Implemented/Verified ni cerrada.

- [SPEC y sus 26 CA](../../../specs/SPEC-HU-017-proceso-visual-optimizacion.md).
- [PLAN, T01 y puerta DG-01](../../../specs/PLAN-HU-017-proceso-visual-optimizacion.md).
- `3699435`: alineación documental con la base actual e inicio de T01.
- `d855969`: regresiones de navegación única y ausencia de progreso inventado.
- `1eeff98`: implementación y regresiones E2E del primer incremento.

## Comportamiento implementado

La pantalla principal conserva la única entrada «Optimización», su selección
multipedido/multimaterial, revisión de vidrios, cálculo explícito, recuperación
por ID y confirmación separada. Retira los botones que alternaban dos flujos.
La inspección de piezas aparece dentro de la selección revisada, con selectores
de vidrio y pieza; cambiar la selección descarta la inspección anterior.

Se reutilizan `RasterInspection`, `GeometryPreview`, `RasterComparison` y los
renderizadores existentes. El adaptador real todavía entrega `rasters: {}`:
se muestra la geometría disponible y «Máscara de la ejecución no disponible».
No se calcula una máscara alternativa en frontend, no se toma un preview de
Orders como máscara de corrida y no se exige `/start` o `/rasterize` para `/runs`.
Las máscaras sintéticas de las pruebas conservan su aviso de datos de ejemplo.

Las etapas A–E distinguen selección revisada, colocación observada y resultado
completo/parcial/fallido. V1 no acredita preparación de bases ni orientaciones
evaluadas: ambas permanecen «Sin detalle disponible», incluso al terminar el
cálculo. No se marca una etapa como completada por avanzar a la siguiente.

El componente HU-015 conserva su entrada explícita `initialMode="hu015"` para
pruebas de compatibilidad. `/hu015-compatibility.html` es una entrada técnica de
Vite, sin enlaces en la aplicación y excluida del build de producción. Reutiliza
la autenticación y la aplicación reales. Las regresiones antiguas cambian solo
el acceso a esa entrada; mantienen sus verificaciones de API, geometría, teclado,
respuestas tardías y semántica S1-01. Los contratos backend no cambian.

## Red / green y verificación

Antes de la implementación:

```bash
npm run test:component -- src/features/optimization/__tests__/UnifiedOptimization.test.jsx --reporter=dot
# 6 casos: 4 fallan, 2 pasan. La navegación seguía dividida y las etapas B/C
# no podían distinguir información ausente de etapas completadas/interrumpidas.
```

Después de la implementación, desde `frontend/`:

```bash
npm run test:component -- src/features/optimization --reporter=dot
# 148 passed, 12 archivos.
npm run test:unit
# 161 passed, 0 failed, 0 skipped.
npm run test:component -- --reporter=dot
# Suite frontend completa: 489 passed, 44 archivos, 174.27 s.
npm run lint
# Exit 0.
npm run build
# Exit 0; 1989 módulos; 595 ms. Sin HTML/entrada de compatibilidad en dist/.
```

La base de HU-017 no incluye los seis tests nuevos de Dashboard: pertenecen a
HU-016 y se publicaron por separado. La diferencia 161/167 no elimina pruebas.

E2E con Python 3.11.9, PostgreSQL 17 temporal exclusivo y Chromium local 154:

```bash
PATH="/workspace/optimizador-vidrio/backend/.venv/bin:$PATH" NEWGLASS_TEST_PG_BIN=/tmp/hu016-tools/root/usr/lib/postgresql/17/bin NEWGLASS_REQUIRE_POSTGRES=1 PYTHON_DOTENV_DISABLED=1 PLAYWRIGHT_CHANNEL=chromium PLAYWRIGHT_BROWSERS_PATH=/tmp/hu016-tools/browsers HU015_E2E_USERNAME=O70000001 HU015_E2E_PASSWORD=Orders-test-2026! npm run test:e2e -- hu017-unified-flow.spec.js s1-optimization-ui.spec.js hu015-rasterization.spec.js
# 34 passed (3.0m), 0 skips, retries: 0.
```

Las credenciales anteriores son exclusivamente la cuenta sintética declarada
en `backend/tests/e2e_server.py`, creada en la base temporal; no se usa una cuenta
del usuario ni una base compartida. Se ejecutaron 17 escenarios en dos proyectos:
4 ejecuciones nuevas de HU-017, 24 del flujo S1-01 y 6 históricas de HU-015.
Incluye selección multipedido/multimaterial, geometría sin máscara inventada,
resoluciones/rotaciones reales de los contratos existentes, resultado parcial,
permisos, recuperación, conflictos, confirmación y stock intacto hasta confirmar.
El caso nuevo comprueba ausencia de desborde a 360/768/1440 px; los casos HU-015
mantienen las comprobaciones de teclado. Se inspeccionaron las capturas de las
etapas en escritorio/móvil: B/C permanecen sin detalle y SIN_SOLUCION se rotula
como resultado parcial. Las capturas/resultados generados quedan fuera de Git.

La configuración permanente del gate/los skips condicionados por entorno no
cambian; ejecutar esos seis casos localmente no cierra TA-040. No se atribuyen
resultados de CI remota a HU-017.

## Estado por criterio y tareas restantes

| Alcance | Estado del incremento |
|---|---|
| CA-01 | Flujo principal único implementado; la visualización completa de T04 sigue pendiente. |
| CA-02 | La revisión y el cálculo no requieren rasterización independiente. |
| CA-23 | Compatibilidad UI/API HU-015 y consumidores V1 preservados en este incremento; ampliación visual T03 pendiente. |
| CA-03/04/05/14/15/16/18/21/26 | T02 y sus pruebas de preparación/memoria/búsqueda siguen pendientes. |
| CA-06/07/08/09/10/11/12/13/17/19/24 | Contrato y visualización de T03/T04 pendientes; los estados sin datos no acreditan telemetría nueva. |
| CA-20/22/25 | Se conservan resultados/confirmación actuales y se añade regresión del flujo; T05/T06 deben completar la cobertura de toda la historia. |

El siguiente incremento es T02: bases necesarias con resolución/configuración
únicas y consumo compartido bajo demanda. DG-01 continúa abierta y debe cerrarse
antes de T03. No se modifica TA-021, TA-037, TA-040, la política de candidatos ni
el inventario de una simulación. No hay cambios de CI/despliegue en esta rama.
