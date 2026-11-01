# Regresión de publicación angular y comparación — 2026-11-01

Este documento registra código y pruebas aisladas. No incluye cuentas, filas,
identificadores, direcciones, huellas ni metadatos de ninguna base remota.
El diagnóstico y la verificación administrativa del destino real se mantienen
en la conversación y en archivos locales bajo `.venv/validation`, ignorados
por Git. La exportación de ese payload remoto al repositorio fue rechazada
por la revisión automática; este informe contiene únicamente resultados de
pruebas sintéticas.

## Contrato del código

`AcceptComparison.execute`, en
`backend/app/modules/optimization/application/comparisons.py`, obtiene
`uow.configuration()` y compara `config.angular_step_deg` con
`SPRINT_2_ANGULAR_STEP_DEG = Decimal(5)`. Si difieren, lanza
`CONFIG_CONFLICT`; `RunRoute.safe` responde 409 antes de bloquear pedidos o
crear una comparación.

`SqlComparisonUnitOfWork` hereda la lectura de configuración vigente de
`SqlRunUnitOfWork`. La tabla `configuraciones` almacena versiones con paso
`NUMERIC(6,2)`; las optimizaciones conservan su referencia a la versión usada.
El [PR #88](https://github.com/melendezzz26/optimizador-vidrio/pull/88) incluye
el publicador administrativo y ya es ancestro del HEAD de esta rama.

El publicador marca la versión anterior como histórica y crea otra a 5°,
copiando resolución, margen, separación y mínimos de retazo. Serializa con
otras publicaciones y el seed, exige una cuenta activa y aplica el cambio
en una transacción. Repetirlo cuando ya hay 5° no crea otra versión. El seed
demo conserva una vigente válida; no sustituye esta operación.

En un destino autorizado, el comando general desde `backend/` es:

```bash
python -m scripts.publish_configuration --responsable USUARIO_ACTIVO
```

Requiere escribir `PUBLICAR`. Verificar primero el destino, el esquema y la
fila vigente con consultas de solo lectura. Si el esquema está al día, una
publicación de parámetros no requiere una migración Alembic. La cuenta indicada
es el nombre de usuario de acceso a NewGlass. Cada nueva aceptación consulta
la vigente, sin necesitar reiniciar Uvicorn.

## Configuración común

FF, BF y WF usan `packing.pack` y `PreparedRunGeometry`, que toman
`problem.config.angular_step_deg`. El supervisor envía el mismo snapshot
congelado a los tres procesos. El frontend envía `order_ids`, lee la
configuración del backend y representa sus eventos y resultados. Los ángulos
de cámara y las fixtures no sustituyen el paso angular del motor.

## Pruebas ejecutadas

Las pruebas con datos usan PostgreSQL temporal loopback, con dotenv
deshabilitado. El caso nuevo prepara una configuración sintética de 90°,
comprueba 409, publica una versión de 5° y reintenta la misma clave: obtiene
201 y tres ejecuciones distintas FF/BF/WF. Valida 5° en cada resultado, sus
rotaciones como múltiplos de 5, inventario idéntico antes/después y liberación
de procesos/admisión. La suite angular incluye colocación real a 70° en
los tres motores.

Desde `backend/` en WSL2:

```bash
.venv/wsl/bin/python -m pytest tests/unit/optimization/test_sprint2_angles.py tests/unit/optimization/test_rotation.py tests/unit/optimization/test_first_fit.py tests/unit/optimization/test_comparison.py -q -ra --junitxml=.venv/validation/angular-pure-unit.xml

export PYTHON_DOTENV_DISABLED=1 NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin
.venv/wsl/bin/python -m pytest tests/integration/optimization/test_configuration_publication.py tests/api/optimization/test_comparisons_api.py::test_publishing_angular_version_unblocks_three_engines_without_inventory_changes -q -ra --junitxml=.venv/validation/angular-prepublication.xml -o junit_family=legacy
.venv/wsl/bin/python -m pytest tests/unit/optimization/test_comparison_runner.py tests/api/optimization/test_comparisons_api.py tests/api/optimization/test_runs_api.py tests/integration/optimization/test_comparison_calculation.py -q -ra --junitxml=.venv/validation/angular-regression.xml -o junit_family=legacy
```

**116 unitarias, 11 previas a publicación y 64 de regresión aprobadas**;
ninguna omitida ni fallida. El caso nuevo se ejecutó dos veces: son 190 casos
backend distintos. Se comprobaron publicación idempotente, historial,
cuenta activa, rechazo de cero/varias vigentes, supervisor real, memoria,
timeouts, fallos parciales y regresión First Fit.

Desde `frontend/` en PowerShell:

```powershell
npm.cmd run test:unit
npm.cmd run test:component -- src/features/optimization
```

**175 unitarias y 173 de componentes aprobadas**. Se repitió el arnés Linux
aislado preparado para WSL2:

```powershell
wsl -d Ubuntu --cd 'C:\Users\fabri\Documents\TALLER INTEGRADOR I\optimizador-vidrio\backend' --exec bash .venv/validation/run-e2e.sh
```

**6 E2E aprobados**, escritorio y móvil, sin retries: pestañas, eventos y
resultados reales, rotación, selección y confirmación en la base temporal.
No se interceptan respuestas para inventar resultados. Los servidores de
prueba se cerraron al terminar. Se observó únicamente la advertencia existente
del TestClient de Starlette/httpx.

## Cambios locales

- `backend/tests/api/optimization/test_comparisons_api.py`: regresión del ciclo
  409 → publicación → 201, conservando las pruebas WSL2 anteriores.
- `backend/README.md`: instrucciones generales del publicador administrativo,
  conservando la documentación WSL2 pendiente.
- Este informe y [test-results.json](test-results.json): resultados de pruebas
  sintéticas aisladas, sin datos de la base remota.

No se modificaron reglas geométricas, políticas FF/BF/WF ni protecciones de
recursos. No hubo commit, push, merge ni despliegue.
