# SPEC-TA-040 — Gate E2E efectivo

## Información general

| Campo | Valor |
|---|---|
| ID | TA-040 |
| Nombre | Gate E2E efectivo |
| Tarea | T01 — Eliminar skips silenciosos del gate |
| Sprint | Sprint 2 |
| Épica | EN-005 / Calidad y CI |
| Prioridad / estimación | Alta / 1 SP |
| Estado | **Draft** |
| Responsable | Fabricio Aguilar |
| Reviewer | Por asignar (distinto del autor) |
| Rama | `enabler/TA-040-gate-e2e` |
| Base | `origin/integration/sprint-01` en `f1fd38d` |
| Fecha | 27/10/2026 |
| Dependencia | CI actual (`.github/workflows/ci.yml`), staging E2E (`backend/tests/e2e_server.py`) |
| Dependientes | HU-016 T03 (integración, E2E y cierre del Dashboard) |

## 1. Objetivo

Que un check verde del job `e2e` signifique que **los E2E críticos se ejecutaron
y pasaron de verdad**. El job debe fallar si falta un prerrequisito, si una prueba
se omite sin aprobación o si un spec crítico no llega a ejecutarse.

**Criterio de aceptación del PBI:** el pipeline dispone de prerrequisitos
controlados y falla ante configuración faltante o skips no aprobados; un estado
verde representa la ejecución efectiva de los E2E críticos.

## 2. Situación actual (evidencia)

Revisión de `integration/sprint-01` en `f1fd38d`:

- El job `e2e` ejecuta `npm run test:e2e` (`playwright test`) en escritorio y
  móvil. El último CI de integración aprobado registró 100 E2E aprobados y
  **6 omitidos**.
- Los 6 omitidos son las 3 pruebas de `frontend/tests/e2e/hu015-rasterization.spec.js`
  en los 2 proyectos. Cada una empieza con:

  ```js
  test.skip(!hasHu015Credentials, 'HU-015 real E2E requires configured synthetic test credentials');
  ```

  `hasHu015Credentials` depende de `HU015_E2E_USERNAME` y `HU015_E2E_PASSWORD`,
  que el workflow **nunca define**. La omisión es silenciosa: Playwright termina
  con código 0 y el check queda en verde.
- Playwright no tiene una opción nativa para fallar cuando hay pruebas omitidas.
  Nada impide que mañana otro `test.skip` condicional, un `test.fixme` o un spec
  borrado por error pasen igual en verde.
- `docs/evidence/sprint-01/HU-015/t3-visualizacion-e2e.md` ya reconocía que esa
  omisión "no cuenta como una ejecución E2E exitosa de HU-015 en CI".

**Reproducción (27/10/2026):**

| Corrida de `hu015-rasterization.spec.js` en escritorio | Resultado |
|---|---|
| Sin credenciales, como en el CI actual | `3 skipped`, **exit 0** (verde sin probar nada) |
| Con el Operario sintético de `e2e_server.py` (`O70000001`) | **6 passed** (escritorio y móvil) |

Es decir, las pruebas de HU-015 no estaban rotas: solo nunca se ejecutaban en el CI.

### Prerrequisitos que ya están controlados (se conservan)

| Prerrequisito | Control actual |
|---|---|
| PostgreSQL aislado | El workflow instala los binarios y verifica `initdb` y `pg_ctl` con `test -x`. Con `NEWGLASS_REQUIRE_POSTGRES=1`, si faltan, `postgres_support.py` hace `pytest.fail` en lugar de omitir. |
| Datos y usuarios | `e2e_server.py` crea una base efímera con migraciones, catálogo y actores sintéticos. Nunca lee una `DATABASE_URL` compartida. |
| Navegador | Chromium gestionado (`npx playwright install --with-deps chromium`). |
| Servidores | Si el backend o Vite no levantan dentro del timeout de `webServer`, Playwright falla. |
| Disciplina | `forbidOnly: true` (un `.only` olvidado falla) y `retries: 0` (no se ocultan fallos intermitentes). |

El único prerrequisito **no** controlado son las credenciales de HU-015, que se
leen de variables de entorno que nadie define.

## 3. Alcance

### Incluye

- `hu015-rasterization.spec.js`: quitar los 3 `test.skip` y usar el actor
  sintético que ya crea `e2e_server.py`.
- Un reporter de Playwright (`frontend/tests/e2e/e2eGateReporter.js`) que convierte
  en fallo las omisiones no aprobadas y los specs críticos que no se ejecutaron.
- La lista de specs críticos (`frontend/tests/e2e/criticalSpecs.js`).
- Pruebas unitarias del reporter (`frontend/tests/unit/e2eGate.test.js`).

### Fuera de alcance

- Cambios en el código de la aplicación, el backend, la base de datos o las migraciones.
- Cambiar los comandos del workflow: `npm run test:e2e` sigue siendo el mismo.
- Los otros specs E2E y sus aserciones, incluido `ta-dashboard.spec.js` (HU-016).
- Las configuraciones auxiliares (`playwright.hu015.config.js` y similares), que
  son para corridas manuales y no forman parte del gate.

## 4. Alternativas evaluadas

| # | Alternativa | Evaluación |
|---|---|---|
| A | Definir `HU015_E2E_USERNAME/PASSWORD` en el workflow (o como *secrets*) | Arregla las 6 omisiones de hoy, pero la credencial sigue siendo configuración externa: si se pierde, se vuelve a omitir en silencio. Tampoco protege contra futuros skips. |
| B | Quitar el `test.skip` y usar el actor sintético de `e2e_server.py` | Las pruebas dejan de depender de configuración externa. Pero no protege contra futuros skips. |
| C | **B más un gate en el reporter (recomendada)** | Elimina la causa actual y, además, impide que vuelva a pasar con cualquier otra omisión o spec faltante. Sin cambiar el workflow ni la aplicación. |

## 5. Reglas

- **R-01 Credenciales sintéticas.** HU-015 usa el Operario sintético `O70000001`
  que crea `e2e_server.py` en su PostgreSQL efímero de loopback. No son
  credenciales reales ni secretos; el mismo patrón ya lo usa `ta-dashboard.spec.js`.
  Se eliminan `HU015_E2E_USERNAME/PASSWORD`.
- **R-02 Cuándo actúa el gate.** Cuando `CI=true` (GitHub Actions lo define
  siempre) o `NEWGLASS_E2E_GATE=1` (para reproducir el gate en local). Sin esas
  variables, una corrida local de un solo spec funciona como hoy.
- **R-03 Omisión no aprobada = fallo.** Cualquier prueba con resultado `skipped`
  (`test.skip`, `test.fixme`, `describe.skip`, condicional o no) hace fallar la
  corrida, salvo que tenga la anotación `approved-skip` con un ID de PBI o ADR
  (`TA-`, `HU-`, `EN-`, `ADR-`). Las omisiones aprobadas se listan en la salida.
  Hoy no hay ninguna aprobada.
- **R-04 Specs críticos.** Cada spec de `criticalSpecs.js` debe tener al menos una
  prueba aprobada en **cada** proyecto (escritorio y móvil). Si se borra o renombra
  un spec crítico, o una configuración deja de recolectarlo, la corrida falla.
- **R-05 Configuración faltante = fallo.** Se conservan los controles de §2
  (PostgreSQL obligatorio, servidores, `forbidOnly`, `retries: 0`). Como las
  credenciales de HU-015 dejan de ser configuración (R-01), no queda ningún
  prerrequisito que al faltar produzca una omisión.
- **R-06 Mensaje claro.** Si el gate falla, la salida dice qué prueba se omitió o
  qué spec crítico no se ejecutó, y en qué proyecto.

## 6. Diseño técnico

**Ubicación:** infraestructura de pruebas del frontend (`frontend/tests/e2e/`).
No cambia `src/`.

1. `criticalSpecs.js`: exporta la lista de nombres de archivo de specs críticos (P-01).
2. `e2eGateReporter.js`: reporter de Playwright.
   - `onBegin` guarda los proyectos y la suite.
   - `onEnd` evalúa R-03 y R-04 y devuelve `{ status: 'failed' }` si hay
     problemas. Esto hace que `playwright test` termine con un código distinto de 0.
   - La lógica de evaluación es una función pura exportada, para probarla sin
     levantar navegador.
3. `playwright.config.js`: agrega el reporter a la lista existente (`list` y `html`
   se conservan).
4. `hu015-rasterization.spec.js`: constantes del actor sintético; se borran las 3
   líneas `test.skip` y la lectura de variables de entorno.

**Prototipo validado (27/10/2026):** con el gate activo, la misma corrida sin
credenciales terminó con **exit 1** y listó las 3 omisiones y los 2 proyectos sin
ejecución de HU-015.

## 7. Criterios de aceptación

| CA | Criterio |
|---|---|
| CA-01 | Las 3 pruebas de HU-015 se ejecutan y pasan en escritorio y móvil dentro del job `e2e` (0 omitidas). |
| CA-02 | Una prueba omitida sin `approved-skip` hace fallar `npm run test:e2e` con el gate activo y la salida la identifica. |
| CA-03 | Una omisión con `approved-skip` y un ID válido no hace fallar la corrida y aparece listada; sin ID válido, falla. |
| CA-04 | Si un spec crítico no tiene una prueba aprobada en algún proyecto (borrado, renombrado o filtrado), la corrida falla. |
| CA-05 | Si faltan los binarios de PostgreSQL con `NEWGLASS_REQUIRE_POSTGRES=1`, la corrida falla en lugar de omitir (comportamiento existente, verificado). |
| CA-06 | Sin `CI` ni `NEWGLASS_E2E_GATE`, una corrida local de un solo spec se comporta como hoy. |
| CA-07 | El CI del PR queda en verde, con todos los E2E aprobados, 0 omitidos y el mensaje del gate en el log. Las suites de frontend y backend no cambian. |

## 8. Pruebas previstas

- **Unitarias** (`frontend/tests/unit/e2eGate.test.js`, con `node --test` como las
  existentes): CA-02, CA-03, CA-04 y CA-06 sobre objetos de prueba simulados.
- **Demostración del gate:** la corrida de HU-015 sin credenciales con el código
  anterior (exit 0) frente al gate activo (exit 1). Es la evidencia en rojo.
- **E2E completo** con el gate activo, en local y en el CI del PR (CA-01 y CA-07).
- CA-05: corrida sin binarios de PostgreSQL con `NEWGLASS_REQUIRE_POSTGRES=1`.

## 9. Evidencia requerida

`docs/evidence/sprint-02/TA-040/README.md` con:

- el antes (6 omitidos y verde) y el después (0 omitidos);
- la salida del gate fallando en la demostración;
- el enlace al CI del PR;
- la tabla CA → prueba.

## 10. Decisiones y preguntas abiertas

- **P-01:** ¿qué specs son críticos? Propuesta: **los 10 actuales**
  (`hu007-custom-piece`, `hu007-order-integration`, `hu012-client-order`,
  `hu014-inventory-writeoff`, `hu015-rasterization`, `s1-optimization-ui`,
  `s1-post-review`, `ta-dashboard`, `ta036-retazo-personalizado`,
  `ta037-load-feedback`). Cada uno cubre una HU o tarea cerrada. Un spec nuevo se
  agrega a la lista en el mismo PR que lo crea.
- **P-02:** aprobar la alternativa C frente a A o B.
- **P-03:** avisar a Luis (HU-016 T03), porque su cierre depende de este gate.
  `ta-dashboard.spec.js` no se modifica y hoy no tiene omisiones.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 27/10/2026 | 0.1 | Draft | Borrador: diagnóstico de las 6 omisiones de HU-015, alternativas, reglas y prototipo validado. |
