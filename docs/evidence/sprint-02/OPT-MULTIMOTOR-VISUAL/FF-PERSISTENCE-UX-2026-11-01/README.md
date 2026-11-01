# Auditoría de persistencia FF y confirmación multimétodo

Fecha: 01/11/2026, America/Lima. Rama: `feature/optimization-multimotor-visual`.
HEAD de referencia: `5e836cdd9cc61eb212402d90dbe94a6776afcc75`, con cambios locales.
No se hicieron commits, push, merge ni despliegue. Se conservaron los cambios
anteriores de WSL2 y configuración angular. Esta corrección no publica parámetros,
no migra la base compartida y no escribe registros de Supabase.

## 1. Causa demostrada

El mensaje «No se pudo guardar el resultado de este motor» corresponde a
`RESULT_SAVE_FAILED`, no a un resultado geométrico sin solución. En el log
completo suministrado en Descargas, el bloque que comienza en la línea 2161 sigue
esta cadena:

1. `CalculateComparison.execute`, `comparison_calculation.py`, recibe un paquete
   `kind="result"` del worker. El cálculo y las métricas ya terminaron.
2. Abre `SqlComparisonUnitOfWork` y llama a
   `SqlComparisonRepository.save_result`, `comparison_uow.py:208`.
3. `save_result` llama a `_lock`, `comparison_uow.py:149`, para leer la comparación
   con bloqueo. SQLAlchemy intenta obtener la conexión antes de enviar SQL.
4. Falla con `sqlalchemy.exc.TimeoutError`: pool de tamaño 5, overflow 10,
   espera de 30 segundos. El fallo ocurre antes de serializar o insertar ese
   resultado. La excepción se traduce a `RESULT_SAVE_FAILED`.

El mismo log contiene rechazos `EMAXCONNSESSION` del proveedor (máximo 15 sesiones)
y fallos DNS. No se puede atribuir cada sesión remota a un proceso concreto solo
con ese log. Sí se demuestra la indisponibilidad de conexión en el punto exacto
de guardado. El código anterior no registraba el método/ID junto al encabezado
del traceback; ahora los registra para correlacionar futuros fallos.

**Defecto local reproducido:** la lectura de identidad/permisos retenía una
conexión hasta terminar el endpoint. `scope="function"` la cerraba después del
retorno, no antes de que el endpoint pidiese otra conexión para su UoW. Esto
creaba demanda anidada y podía bloquear un pool ocupado. También ocurría en
Inventario: autorización compartida más repositorio con sesión propia.

**Factores operativos:** el pool podía crecer hasta las 15 sesiones del límite
remoto, sin margen para otras herramientas/instancias. Además, Uvicorn con
recarga sin exclusiones detectaba scripts en `.venv/validation` y reiniciaba.
Estos reinicios eliminan buffers visuales en memoria, explicando respuestas 410.
Un 410 visual no prueba que un resultado previamente guardado se haya perdido.

Esto puede ocurrir en Linux/WSL2 y en Windows: es un problema de conexiones y
transacciones. Es distinto del 503 original de supervisión POSIX, que se resolvió
usando WSL2. No se encontró una transacción especial de FF: los tres métodos
usan el mismo repositorio, serializador y política de guardado independiente.

## 2. Corrección mínima final

- La dependencia compartida `require_permission(...).checker` libera mediante
  `rollback()` su transacción de lectura antes de entrar al endpoint. Conserva
  exactamente las decisiones RBAC existentes y el dueño de `Session.close()`.
  Los endpoints que comparten esa sesión comienzan su transacción de negocio
  normalmente; los que abren otra ya no retienen una conexión innecesaria.
- `run_auth.run_permission.check` pasa la sesión de alcance función a esa misma
  comprobación. No duplica las reglas de autorización.
- El pool PostgreSQL tiene valores predeterminados explícitos 5/0, manteniendo
  la espera de SQLAlchemy de 30 s. No cambia el límite del proveedor. Las
  variables explícitas del entorno conservan precedencia.
- `scripts.dev_server` inicia un proceso estable, sin recarga por defecto. Su
  modo opcional `--reload` excluye entornos virtuales, scripts, tests y Alembic.
- El registro del error incluye comparación, ejecución y método. No se añade
  ningún reintento automático ni se marca como completo un guardado fallido.

La validación ampliada detectó que liberar solo la autorización del optimizador
no bastaba: el pool acotado reveló la misma retención en Dashboard/Inventario.
La corrección final centraliza la liberación en el guard compartido. Se añadieron
pruebas reales de los seis tipos de consulta del Dashboard, con ocho lectores,
tanto con una como con cinco conexiones.

No se modificaron FF, BF, WF, geometría, métricas, paso de 5°, presupuestos,
timeouts del supervisor, admisión exclusiva ni aislamiento de workers.

## 3. Evidencia de causalidad y fidelidad

| Prueba controlada | Resultado observado |
|---|---|
| API comparativa con pool 1/0 antes de liberar autorización | HTTP 500 al pedir conexión en `start.find_by_key`; autorización todavía retenía la única conexión |
| Worker FF real y conexión ocupada justo antes del guardado | `TimeoutError` real; FF queda `RESULT_SAVE_FAILED`; BF/WF persisten; no hay consumo por calcular |
| Mismo resultado FF antes del guardado frente al FF directo | Igualdad de resultado geométrico y métricas, normalizando únicamente el tiempo de ejecución |
| Flujo First Fit original y comparativo sobre los mismos IDs/datos de prueba | Ambos persisten 16 piezas con idénticas colocaciones, materiales y configuración |
| FF/BF/WF sobre dos pedidos sintéticos, 8 piezas de 1×1 mm por pedido, 10 planchas de 4×4 mm | FF 1 plancha, BF 1 y WF 10; tres resultados completos e identificados |
| Observación de conexiones de los tres workers por `pg_stat_activity` | 0, 0, 0; la creación perezosa de un engine en un import no abrió conexiones |
| Pool 1 y pool 5 con lectores concurrentes | Picos medidos 1 y 5; conexiones prestadas al terminar: 0; workers detenidos |
| Runtime nuevo sin buffers tras terminar | GET de los tres resultados sigue en 200; eventos/manifiestos temporales en 410 |

La instancia de 16 piezas es **sintética y reproducible**; no se afirma que sus
medidas sean las del pedido privado original. La comparación entre FF original
y adaptado sí usa exactamente la misma entrada dentro de esa instancia.
Las mediciones están en [connection-measurements.json](connection-measurements.json).

Las UoW conservan commit/rollback/cierre por operación. El supervisor no mantiene
una transacción durante la búsqueda. El fallo de un motor no sustituye resultados
de otros. Si la base completa sigue inaccesible, también puede fallar el registro
del error; no se garantiza recuperación de una operación nunca persistida.

## 4. Confirmación de BF y estado residual

El botón invoca `flow.confirm` → `comparisonApi.confirm` →
`POST /api/optimization/comparisons/{id}/confirm` → `ConfirmComparison.execute`.
El backend bloquea y valida comparación, ejecución elegida, pedidos y stock;
consumo, estados y recibo quedan en una misma UoW. La misma clave de idempotencia
devuelve el mismo recibo sin otro descuento.

Se inspeccionó la confirmación reportada mediante una transacción remota
**read-only**, con una sola conexión: la confirmación de BF estaba persistida,
los pedidos confirmados y el consumo coincidía con el recibo, sin grupos de
consumo duplicados. No se exportaron datos, cuentas, IDs ni payloads de esa base
a esta evidencia. El defecto visible estaba en el ciclo de vida del frontend:
después del POST, `sync()` mantenía la comparación y su almacenamiento local.

Ahora, después de una respuesta confirmada y validada:

- Se informa el ID del trabajo y se vuelve al selector actualizado de pendientes.
- Se cancelan observador, solicitudes y temporizadores; se incrementa la
  generación para ignorar respuestas anteriores.
- Se limpian comparación, selección, ejecuciones, resultados, máscaras, progreso,
  mensajes transitorios, pestaña, consulta y diálogo; se elimina la recuperación
  automática de ese trabajo del almacenamiento local.
- Se fuerza una lectura nueva de pendientes y se filtran los IDs confirmados
  incluso si llega una página anterior tardía. El foco va a «Pedidos pendientes».
- La consulta explícita por ID conserva el historial de solo lectura. Una
  recuperación automática de un trabajo ya confirmado vuelve a pendientes.
- Mientras el POST está pendiente, el estado ocupado bloquea otros envíos.
  Un fallo conserva el trabajo y el error. Ante una respuesta ambigua, recuperar
  por GET permite reconocer un commit sin repetirlo.

«Liberar pedidos sin confirmar» opera en backend, devuelve los pedidos a
PENDIENTE sin consumir stock y limpia la vista. «Preparar otro trabajo» cierra
solo la vista de un historial ya confirmado/liberado; no borra datos. «Recuperar
estado» consulta; no descarta ni confirma. No se usa `window.location.reload()`
como implementación del reset.

### Antes y después: PostgreSQL y navegador reales, datos sintéticos

| Antes: confirmado y comparación residual | Después: éxito y pendientes nuevos |
|---|---|
| [Escritorio antes](screenshots/before-desktop-comparar-estado-residual-antes-del-arreglo.png) | [Escritorio después](screenshots/after-desktop-comparar-confirmacion-limpia-pedidos-pendientes.png) |
| [Móvil antes](screenshots/before-mobile-comparar-estado-residual-antes-del-arreglo.png) | [Móvil después](screenshots/after-mobile-comparar-confirmacion-limpia-pedidos-pendientes.png) |

Caso parcial: [FF fallido y BF elegido](screenshots/after-desktop-FF-ff-fallido-bf-elegido.png)
y [BF confirmado, vista limpia](screenshots/after-desktop-FF-confirmacion-parcial-limpia.png).
Las capturas «antes» se obtuvieron con el controlador anterior en una copia
aislada, sin alterar este working tree. El fallo FF del E2E se induce mediante
un trigger exclusivo de PostgreSQL temporal; la integración separada reproduce
el `QueuePool TimeoutError` auténtico. No son resultados ficticios de UI.

## 5. Archivos y propósito

Rutas relativas al repositorio. Se distinguen los cambios de esta auditoría de
los que ya existían al comenzar.

| Archivo/grupo | Propósito de esta corrección |
|---|---|
| `backend/app/modules/authentication/presentation/dependencies.py` | Liberar transacción de autorización antes del endpoint |
| `backend/app/modules/optimization/presentation/run_auth.py` | Reutilizar el guard y pasar su sesión de alcance función |
| `backend/app/shared/config/__init__.py` | Pool predeterminado acotado 5/0 |
| `backend/app/modules/optimization/application/comparison_calculation.py` | Correlación de excepciones por motor |
| `backend/scripts/dev_server.py` | Arranque estable y exclusiones de recarga |
| `backend/tests/api/optimization/test_comparison_connection_lifecycle.py` | Pools acotados, concurrencia, workers sin DB, FF equivalente y recuperación tras pérdida de buffers |
| `backend/tests/integration/optimization/test_comparison_calculation.py` | Fallo real de conexión después de FF válido y confirmación idempotente de BF |
| `backend/tests/unit/shared/test_config.py`, `test_dev_server.py` | Defaults del pool y filtro real de Uvicorn |
| `.github/workflows/ci.yml`, `backend/tests/unit/test_ci_contract.py` | Ejecutar el runner en un proceso pytest independiente, con todas las pruebas y límites originales |
| `backend/tests/optimization_e2e_data.py` | Fallo de persistencia solo en clúster de test verificado |
| `frontend/src/features/optimization/comparisonController.js`, `pendingOrdersSource.js` | Transición explícita, aislamiento de respuestas y refresco forzado |
| `frontend/src/features/optimization/ComparisonWorkspace.jsx` | Reinicio de estado local y foco/feedback |
| Tests `ComparisonLifecycle`, `ComparisonWorkspace`, `PendingOrdersSource` | Éxito, errores, doble envío, respuestas tardías e historial |
| `frontend/tests/e2e/optimization-comparison.spec.js` | Navegador/API/DB: confirmar, nuevo trabajo, liberar, fallo parcial y replay |
| `frontend/tests/e2e/ta-dashboard.spec.js` | Usar origen del `baseURL` configurado en su lista de orígenes permitidos |
| `backend/README.md`, `docs/testing/README.md`, `docs/development/optimization-wsl2.md` | Comandos y límites operativos |
| Esta carpeta | Informe, matriz UI/UX, pruebas y capturas sintéticas |

Se conservan las modificaciones previas de `comparison_runner.py`,
`check_comparison_environment.py`, sus pruebas y las carpetas de evidencia
WINDOWS-WSL2 / ANGULAR-CONFIG-409. No son cambios de algoritmo de esta auditoría.

## 6. Ejecución local segura

En Ubuntu WSL2, desde `backend/`, reiniciar manualmente el servidor de desarrollo
con el código corregido (el proceso estable que ya estaba abierto no recarga):

```bash
.venv/wsl/bin/python -m scripts.check_comparison_environment
.venv/wsl/bin/python -m scripts.dev_server
```

En PowerShell, desde `frontend/`:

```powershell
$env:VITE_API_URL = 'http://127.0.0.1:8000'
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Usar una única instancia web, sin `--workers` adicionales. La configuración de
5° y la base autorizada ya deben existir; estos comandos no requieren seed ni
migración. En el navegador seleccionar pedidos pequeños, comparar y verificar
POST 201, tres execution IDs/métodos, métricas reales y stock intacto antes de
confirmar. Para demostrar consumo, usar exclusivamente una base propia de prueba.

Pruebas backend (Linux/WSL2, PostgreSQL local disponible):

```bash
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN="$(pg_config --bindir)"
unset DATABASE_URL SECRET_KEY
.venv/wsl/bin/python -m pytest tests --ignore=tests/unit/optimization/test_comparison_runner.py -q -ra
.venv/wsl/bin/python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra
```

Ambos comandos son obligatorios para la validación completa. El proceso separado
evita que el consumo acumulado del arnés de miles de pruebas se evalúe como RSS
del servidor que supervisa los tres workers. No modifica los límites operativos.

Las fixtures fijan sus propias variables y crean PostgreSQL loopback. Para
reducir el coste de I/O, ejecutar las suites extensas desde una copia en el
sistema de archivos Linux, con su entorno Linux; no compartir `node_modules`
de Windows. En frontend:

```text
npm run test:unit
npm run test:component
npm run lint
npm run build
```

Con Python/PostgreSQL/Node/Chromium Linux y puertos 5173/8017 libres:

```bash
export PATH="$(realpath ../backend/.venv/wsl/bin):$PATH"
export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1 PLAYWRIGHT_CHANNEL=chromium
export NEWGLASS_TEST_PG_BIN="$(pg_config --bindir)"
npm run test:e2e -- tests/e2e/optimization-comparison.spec.js tests/e2e/s1-optimization-ui.spec.js tests/e2e/hu017-unified-flow.spec.js tests/e2e/ta037-load-feedback.spec.js tests/e2e/ta-dashboard.spec.js
```

La validación de esta entrega usó 5187/8017 mediante configuración equivalente
aislada para no ocupar el frontend del usuario. [ui-audit.spec.js](ui-audit.spec.js)
es el recorrido observacional usado: copiarlo temporalmente a
`frontend/tests/e2e/` y seleccionarlo en Playwright para repetir la auditoría.
No sustituye una evaluación completa con lector de pantalla.

## 7. Validación y límites

El resumen final de pruebas se registra junto a este informe. La matriz y las
mejoras propuestas están en [UI-UX-AUDIT.md](UI-UX-AUDIT.md).

| Validación | Resultado real |
|---|---|
| Backend completo, grupo general | 2456 aprobadas, 0 omitidas; 387,48 s |
| Supervisor real en proceso separado | 14 aprobadas, 0 omitidas; 3,89 s |
| Regresión focalizada de autorización/pools | 267 aprobadas; incluidas también en la suite completa |
| Frontend unitario | 175 aprobadas |
| Frontend componentes | 526 únicas aprobadas; revalidación final de 203 casos en 20 archivos con dos workers, sin aumentar timeouts |
| E2E afectados, 5 suites, desktop/móvil | 64 aprobados, 0 omitidos y 0 reintentos; 383,61 s |
| E2E después del ajuste final de foco/desplazamiento | 8 aprobados, 0 omitidos/reintentos; 77,50 s; éxito dentro del viewport desktop/móvil |
| Auditoría UI real | 2 recorridos aprobados, 23 estados por viewport, 0 errores JS/HTTP; 46,49 s |
| Lint, build y diff | Lint/build aprobados; `git diff --check` sin errores |

La primera ejecución monolítica tuvo 2460 aprobadas y 10 rechazos de memoria en
el runner. No se ocultó ese intento: [test-summary.json](test-summary.json).
La medición posterior del mismo tramo de suite encontró RSS de pytest de
261.038.080–261.193.728 bytes, superior al máximo del supervisor de 251.658.240,
con unos 4,9 GB disponibles: [perfil](pytest-memory-profile.json). La colección
sola medía 118.661.120 bytes; el consumo crece al ejecutar la suite. El gate
completo ahora ejecuta los 2456 casos restantes y los 14 del runner en dos
procesos, sin omitir casos ni aumentar memoria. CI remoto sigue pendiente.

Durante la verificación hubo también fallos del arnés corregidos: dimensiones
inadecuadas en la primera fixture de 16 piezas, exclusiones absolutas de
directorios inexistentes en FileFilter y un selector E2E que comprobaba el radio
antes de la respuesta API. La ampliación detectó y corrigió la retención de
autorización de Inventario. El puerto fijo de Dashboard bloqueaba 5187 antes de
usar el `baseURL`. Se conservaron los resultados de intentos y no se atribuyen
fallos sintéticos o rechazos esperados al algoritmo.

La repetición concurrente de Vitest/Playwright alcanzó dos timeouts de 5 s en
componentes geométricos no modificados y un timeout global E2E de 30 s. Se
registran en el resumen; después aprobaron los 203 casos focalizados con dos
workers y los ocho E2E por separado, con las esperas originales. El último
ajuste mantiene foco en pendientes y desplaza al inicio del workspace para no
dejar el éxito fuera del viewport móvil. Las capturas «después» corresponden a
esa validación final. [Hashes](code-hashes.json) comprueban que 13 archivos clave
del working tree coinciden con la copia Linux ejecutada.

`GET /api/orders` tiene varias fuentes legítimas: Inicio hace tres lecturas
(pendientes, en optimización y recientes); el selector de optimización pagina
por 100 y refresca 15 s después de terminar cada lectura, además de las
transiciones explícitas. No hay `setInterval` que acumule consultas simultáneas;
se aborta al desmontar y se invalidan páginas anteriores al confirmar. StrictMode
puede repetir el montaje inicial en desarrollo. La regresión de Dashboard
verifica el número de fuentes y las pruebas del selector cubren cancelación y
refresco. Las respuestas 500 por saturación del log no prueban un bucle React.

- El límite de conexiones es por proceso; herramientas ajenas y otras
  instancias siguen consumiendo cuota remota. DNS/proveedor pueden fallar.
- Ninguna prueba aislada certifica la capacidad de toda una base compartida.
  La carga probada y los picos están descritos, sin prometer carga ilimitada.
- Reiniciar descarta la animación histórica en memoria; el resultado persistido
  se consulta por ID. No se regeneran eventos inexistentes.
- Una confirmación puede hacer commit y perder después su respuesta HTTP; se
  conserva la clave y se recupera estado canónico antes de otra operación.
- CI remoto, revisión cruzada humana y despliegue no se ejecutaron.
- Vite conserva la advertencia de un chunk JavaScript minificado de unos 535 kB
  (umbral de aviso 500 kB); build termina correctamente. No se cambió bundling.
- No se investigó ampliar la capacidad geométrica ni se añadieron heurísticas.
