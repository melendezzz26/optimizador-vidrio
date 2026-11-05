# TA-045 — Certificación E2E global completa

**Resultado: PASS, 146/146 escenarios; gate conjunto TA-040 aprobado.**
Ejecución local Linux/WSL del 2026-11-05 (America/Lima). No se integró, no se hizo
push, no se actualizó el PR #102 ni se desplegó.

## Identidad del código y de la ejecución

- Rama inicial: `fix/S2-TA045-precision-geometrica`.
- SHA probado: `04fa083822f1b9e297092a9fa3507f9c8bbe3d08`; árbol inicial limpio.
- Base de recuperación: `2c592296f6ffcc2befc0fef0f05c1024f0d378d4`.
- Árbol Git probado: `c36b20b07259e55325e5ac3d71bafdcb39a3a50f`.
- UUID nuevo: `82919e96-75f1-4625-8694-a64e6d090fb6`.
- Directorio generado por el orquestador: `run-CQKTdX`.
- Digest lógico del inventario: `9a1e20d8eb9767f4e399f5bfc65e613d5d597f5b565d73cb138c712e2fb4c18b`.

Se creó un checkout Git privado en Linux, fijado exactamente al SHA TA-045. Se
ejecutó **`node scripts/run-e2e-phases.js`**, el mismo comando de CI, con los scripts,
la configuración Playwright, los 15 specs críticos y los límites originales.
El propio orquestador habilitó el gate, descubrió todo el inventario y ejecutó las
dos fases. No se usó configuración derivada ni selección manual de escenarios.

`provenance.json` conserva comando, entorno, versiones, estado limpio inicial/final
del checkout probado y SHA-256 de 12 archivos de geometría, gate, configuración,
lockfile y soporte de PostgreSQL. Sus hashes se contrastaron también con los blobs
Git del commit TA-045. No se reutilizaron resultados de `2c59229` ni del E2E focalizado.

## Resultados por fase y proyecto

| Fase | chromium-desktop | chromium-mobile | Total | Resultado |
|---|---:|---:|---:|---|
| B02 aislada | 1 | 1 | 2 | PASS |
| Resto de Playwright | 72 | 72 | 144 | PASS |
| Unión exacta | 73 | 73 | 146 | PASS |

B02: 08:58:14–08:58:37. Resto: 08:58:37–09:05:53, hora de Lima.
Versiones observadas: Node 22.23.2, Python 3.11.9, Playwright 1.63.0,
Chromium 153.0.8010.12, Vite 8.3.1 y PostgreSQL 18.6.

La comprobación conjunta y la auditoría adicional verificaron:

- 146 escenarios descubiertos y 146 resultados, con exactamente los dos proyectos.
- UUID v4, SHA y fecha de contexto comunes a plan, fases y validación final.
- Digest SHA-256 del plan recalculado; `planDigest` coincidente en ambas fases.
- Identidades de escenario iguales al inventario; 0 duplicados, 0 ausentes y 0 extras.
- Los 15 specs críticos ejecutados en desktop y mobile.
- 0 fallos de pruebas, 0 errores globales, 0 skips, 0 omisiones aprobadas y 0 flaky.
- Una sola ejecución `passed` por escenario: **0 reintentos**; configuración `retries: 0`.
- Orquestador y limpieza con exit 0; fuentes probadas sin cambios.

El error sintético de persistencia FF y los escenarios controlados de error que
aparecen en los logs son fixtures explícitos de las pruebas. Los casos verifican
la recuperación esperada y terminaron aprobados; no se reinterpretó ningún test fallido.

## PostgreSQL aislado y migraciones

Se observaron dos clústeres nuevos y distintos, creados por `tests.e2e_server` bajo
el `TMPDIR` privado. Se eliminaron del entorno heredado `DATABASE_URL` y `SECRET_KEY`,
no había archivos `.env` locales en el checkout y `PYTHON_DOTENV_DISABLED=1`.

| Fase | Host:puerto | Base sintética | Usuario |
|---|---|---|---|
| B02 | 127.0.0.1:50291 | r1_bf9540046c2b420889aeac035474ad01 | r1_test |
| Resto | 127.0.0.1:37195 | r1_b858f3edc29a42cfa5d572fc6c2b2ff2 | r1_test |

B02 ejecutó `--prepare` hacia `s2cmp01a1b2c` y upgrade a `s2cmp02d4e6f8` en ambos
proyectos. Los hashes de las tablas históricas antes/después coinciden, y se
conservó la lectura de comparación v1 y First Fit. Los dos reportes están en
`b02-migrations.json` y también en el archivo completo de artefactos.

El resto arrancó su propio servidor y clúster temporal. Ambos PostgreSQL quedaron
detenidos (`pg_ctl status = 3`, sin `postmaster.pid`); desapareció el archivo de estado
del servidor. Se conservaron opciones de arranque, logs y configuración. El
checkout privado se eliminó al finalizar. **No se utilizó Supabase ni otra base compartida.**

## Evidencias conservadas

Todas las rutas siguientes son relativas a [run-01](run-01/):

| Ruta | Contenido |
|---|---|
| `protocol/context.json` | UUID, SHA y comienzo de la ejecución nueva |
| `protocol/plan.json` | Inventario real completo y digest |
| `protocol/b02.json` | 2 resultados de la fase de migración |
| `protocol/remaining.json` | 144 resultados de la fase restante |
| `protocol/validation.json` | Veredicto del gate conjunto original |
| `gate-audit.json` | Auditoría adicional de identidad, cobertura y resultados |
| `provenance.json` | Checkout, fuentes, versiones, comando y limpieza |
| `database-isolation.json`, `databases/` | Observaciones de los dos PostgreSQL privados |
| `b02-migrations.json` | Migraciones y conservación de tablas por proyecto |
| `execution.txt` | Salida completa, normalizada solo en espacios finales |
| `artifact-inventory.json` | Tamaño y SHA-256 de los 623 artefactos del ZIP externo |
| `external-artifacts.json` | Identidad, tamaño, hash y ubicación lógica del ZIP externo |
| `EXTERNAL-SHA256SUMS` | Hash del ZIP; se verifica desde su directorio de respaldo externo |
| `SHA256SUMS` | Hashes de los 17 archivos ligeros versionados; no exige un ZIP local |

Un clon limpio contiene los JSON, logs y manifiestos indicados, **no `artifacts.zip`**.
Los 623 HTML/capturas/datos y el stdout original están en el ZIP externo de
**54,650,696 bytes**. Durante la certificación se verificaron CRC, nombres únicos y
los 623 hashes; sus cinco JSON de protocolo coinciden byte a byte con los versionados.
`.gitattributes` conserva finales LF/bytes para que los manifiestos sigan siendo
verificables al hacer checkout en Windows o Linux.

El respaldo está fuera de todos los worktrees, en un directorio local cuya raíz
lógica es `newglass-evidence-backups/TA-045/0b759f6ce82516d08f9134ccea540b57f34a2549/`.
Dentro de esa raíz conserva la ruta original
`docs/evidence/sprint-02/TA-045/global-e2e/run-01/artifacts.zip`. La ruta absoluta de
la máquina no se publica; `external-artifacts.json` documenta cómo localizarlo.
Se conserva además `refs/heads/backup/TA-045-e2e-before-zip-exclusion-0b759f6`, que
apunta al commit documental original. El respaldo no forma parte de la rama candidata.

| Evidencia | SHA-256 |
|---|---|
| ZIP externo `artifacts.zip` | `5b49c09234f6377e5f1e1d41ab92c911f5fcb5a6f25de7df04d0bbb03553f92a` |
| `protocol/validation.json` | `d4f1ccefd9e017643125588dcf3f8f9c040c64166585ba3d0cc70e0b3fc371e5` |
| `SHA256SUMS` versionado actual | `b86d3c7a510140351c8d603804d5d72a48f562a5be3778b5005007a3f3872f61` |
| Manifiesto original de `0b759f6` (histórico) | `ca4cae2b8ac3fc4d87593f31b65eb63e716f5867675e4a01921b432a1590030f` |

El manifiesto actual se regeneró para el conjunto versionado. Sus 15 evidencias
originales ligeras conservan sus bytes; se agregan solamente el descriptor externo
y `EXTERNAL-SHA256SUMS`. La limpieza y revisión de privacidad se describen en
[cleanup/README.md](cleanup/README.md).

## Reproducción

Desde un checkout Linux limpio de **04fa083**, con Node/Python/PostgreSQL en PATH,
dependencias de `backend/requirements.txt` y `frontend/package-lock.json` instaladas:

```bash
unset DATABASE_URL SECRET_KEY NEWGLASS_E2E_PHASE NEWGLASS_E2E_RUN_DIR
unset NEWGLASS_E2E_SCHEMA_REVISION NEWGLASS_OPTIMIZATION_EVIDENCE_DIR
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
export CI=true PLAYWRIGHT_CHANNEL=chromium NEWGLASS_E2E_GATE=1
export GITHUB_SHA=04fa083822f1b9e297092a9fa3507f9c8bbe3d08
export TMPDIR="$(mktemp -d -t newglass-ta045-e2e.XXXXXX)"
cd frontend
node scripts/run-e2e-phases.js
```

Cada invocación genera su propio UUID y directorio; debe conservarse su nuevo
paquete completo, sin mezclar fases de ejecuciones distintas. La ejecución registrada
reutilizó únicamente runtimes/dependencias locales: copió `node_modules` a la zona
privada y las tres dependencias Python ya declaradas del overlay de TA-045. No se
modificó el entorno compartido para obtener el resultado.

Para verificar las evidencias disponibles en un clon limpio, desde la raíz Git:

```bash
(cd docs/evidence/sprint-02/TA-045/global-e2e/run-01 && sha256sum -c SHA256SUMS)
node --input-type=module -e '
import {readEvidence,readCombinedEvidence} from "./frontend/tests/e2e/e2ePhases.js";
import {evaluateE2EGate} from "./frontend/tests/e2e/e2eGateReporter.js";
const d="docs/evidence/sprint-02/TA-045/global-e2e/run-01";
const c=readEvidence(d+"/context.json");
const e=readCombinedEvidence(d,c);
const g=evaluateE2EGate({tests:e.tests,projects:e.plan.projects});
if(c.sha!=="04fa083822f1b9e297092a9fa3507f9c8bbe3d08" || e.tests.length!==146 || !g.ok ||
   !e.tests.every(t=>t.outcome==="expected" && t.statuses.length===1 && t.statuses[0]==="passed"))
  throw new Error("La certificacion no coincide");
console.log("PASS 146/146; gate, UUID, SHA, digest, cobertura y ejecucion unica verificados");'
```

Solo si se dispone del respaldo externo, definir `TA045_BACKUP_ROOT` con su raíz
local (la que termina en `0b759f6ce82516d08f9134ccea540b57f34a2549`) y ejecutar:

```bash
versioned_manifest="$PWD/docs/evidence/sprint-02/TA-045/global-e2e/run-01/EXTERNAL-SHA256SUMS"
(cd "$TA045_BACKUP_ROOT/docs/evidence/sprint-02/TA-045/global-e2e/run-01" &&
 sha256sum -c "$versioned_manifest" && unzip -t artifacts.zip)
```

La comprobación de integridad y la certificación del gate se realizaron después
de la ejecución. Esta limpieza no volvió a ejecutar ni alteró escenarios, algoritmos
o pruebas. La certificación versionada se verifica sin disponer del ZIP externo;
abrir sus HTML/capturas sí requiere ese respaldo.

## Cierre

La condición E2E global queda satisfecha para TA-045. Tras su integración local,
`recovery/sprint-02` contiene `04fa083` y la documentación certificada. La limpieza
reconstruye exclusivamente el commit documental no publicado `0b759f6`, con padre
`04fa083` intacto. El nuevo historial candidato excluye el ZIP; la referencia de
respaldo conserva la versión anterior localmente. `origin/recovery/sprint-02` sigue
en `2c59229`, por lo que el candidato sigue siendo fast-forward respecto de esa
referencia remota. No se hizo push, actualización del PR #102 ni despliegue.
