# B08: selección manual con respuesta asíncrona

Fecha: 2026-11-05. Rama: `fix/S2-B08-mobile-selection`.
Base publicada: `62b2ed8d1ae960c9ec61935b073bb0c9fb73f925`.

## Investigación y procedencia

El [run #222](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/42049958202)
del PR #102 ejecutó el merge sintético
`40c68c36bf6884e750e182cf04204c0cf5a8fb8c`. Sus padres son
`d85a8d3c4fa2ba1b3f70c401ed947adcfbe2470b` y el HEAD publicado.
Ambos commits, merge y HEAD, tienen el mismo árbol Git:
`80f742ebb0b15d6e2f51042f7b077750f1ab39b4`.

Se descargó el artefacto original `13425999033` mediante nightly.link y se
contrastó con la API de GitHub. SHA-256 coincidente:
`ca0b16d460ffee6d9e23664de4124817277def121e68050fad7fa56092633e1e`.
Los reportes originales contienen B02 2/2, restantes 143/144 y el gate conjunto
fallido. El error-context móvil muestra todos los motores completos, ningún
radio marcado y todos deshabilitados, con la acción «Procesando…».
El artefacto incluye HTML y capturas de escenarios completados; no contiene
trace ni captura automática del fallo móvil: esa configuración tenía ambos
desactivados. La reproducción local sí guardó trace.

## Causa demostrada

1. El navegador marca el radio y dispara `onChange`.
2. `flow.choose` activa `busy` y espera el PUT de selección.
3. `useSyncExternalStore` provoca el render de la vista. `checked` todavía se
   calcula desde `current.selected_execution_id`, que conserva el valor anterior
   hasta recibir la respuesta.
4. React restaura ese valor controlado al finalizar el evento: el radio vuelve
   a quedar desmarcado. Además, `disabled={state.busy}` retiraba su foco.
5. Playwright comprueba el estado después del clic, antes de recibir el PUT, y
   falla con `Clicking the checkbox did not change its state`.

La reproducción retiene **la respuesta del backend real** al PUT después de
`route.fetch()`, hasta comprobar el control nativo. No sustituye resultados del
motor ni respuestas por fixtures. Con el componente original falla en Chromium
mobile de Linux y también falla una regresión de componente con promesa diferida.
En esta última se comprueba la identidad del nodo antes de comprobar `checked`.
El diagnóstico E2E original registra:

```json
{"connected":true,"checked":false,"focused":false,"disabled":true}
```

El nodo sigue conectado: no fue desmontado ni reemplazado por el clic. Con el
arreglo, mientras la misma respuesta sigue retenida, el diagnóstico es:

```json
{"connected":true,"checked":true,"focused":true,"disabled":false}
```

| Hipótesis | Resultado |
| --- | --- |
| Defecto funcional de selección | Confirmado en la representación del control durante el guardado; el PUT de persistencia es asíncrono. |
| Carrera de interfaz | Confirmada entre la restauración del input controlado y la respuesta del PUT. |
| Carrera del test por seleccionar antes del cierre | No explica el fallo: ya se observa cierre terminal en API y vista, todos los resultados persistidos y radio habilitado. Mantener pendiente solo la respuesta de selección reproduce el problema. |
| Exclusivo de CI | Descartado como causa necesaria: se reproduce en WSL/Chromium sin retries. La latencia influye en la ventana observable. |

Se revisaron `ComparisonWorkspace`, `comparisonController`, los transportes v1/v2,
los fixtures `single`, los snapshots de inventario y los handlers/efectos.
Las lecturas de recuperación actualizan la comparación canónica; `apply` rechaza
versiones anteriores a la ya aplicada. La selección incrementa versión. Los
efectos de resultados/visualización no eligen motores. El fallo también ocurre
sin una recuperación concurrente, reteniendo exclusivamente la respuesta del PUT.
Un B08 original sin intervención pasó localmente; ese resultado por sí solo no
se utilizó para clasificar el fallo.

## Corrección

`ComparisonView` conserva una elección visual pendiente desde el propio evento,
separada de la comparación persistida. El radio, la fila y el resumen reflejan
esa elección. Solo el radio pendiente permanece habilitado durante el guardado
para conservar su foco; el controlador mantiene la exclusión de operaciones.
La confirmación sigue dependiendo de `busy` y de `current.confirmable`.
Al terminar la operación se elimina la elección pendiente y se muestra el estado
canónico, también ante errores de red o conflictos 409.

No cambian contratos, controladores, backend, algoritmos, límites, migraciones,
Supabase, configuración Playwright ni gate TA-040.

## Regresiones y validación

- B08 conserva `check()` y comprueba marcado/foco antes y después de liberar la
  respuesta real. Recorre por teclado los seis motores con wraparound y vuelve
  a M5. Confirma elección persistida, inventario intacto en simulación/selección,
  consumo exacto de una plancha, un movimiento, replay idempotente sin delta,
  recuperación histórica y conservación de las distribuciones originales.
- Componentes: selección pendiente para los seis motores; mismo nodo, marcado,
  foco, confirmación bloqueada; rollback a elección persistida ante red/409.
- Pruebas relacionadas v1/v2/ciclo de vida: **35/35**.
- B08 Linux: desktop **PASS**, mobile **PASS**, sin retries, con trace.
- Frontend completo: **213/213 unitarias**, **589/589 componentes** (57 archivos),
  **ESLint PASS**, **build PASS**. Build conserva el aviso de bundle mayor de 500 kB.
- `git diff --check`: **PASS**.
- E2E global original `node scripts/run-e2e-phases.js`: **B02 2/2**, resto
  **144/144**, **146/146** (73 por proyecto), **gate conjunto TA-040 PASS**.
  Cero fallos, skips o retries. PostgreSQL temporal nuevo en cada fase.
  Run local `65f51f7d-4959-4fd3-8305-a8ee1330ed6a`, directorio `run-LI92pX`,
  `validation.json`: `ok: true`, `planned: 146`, `validated: 146`, `problems: []`.

Entorno: WSL2 Linux, Node 22.23.2, Python 3.11.9, PostgreSQL 18.6,
Chromium administrado de Playwright (Chrome for Testing 153.0.8010.12).
Todas las versiones backend coinciden con `backend/requirements.txt`;
dependencias frontend del mismo lockfile. PostgreSQL exclusivo en loopback,
temporal por fase, `PYTHON_DOTENV_DISABLED=1`; sin `DATABASE_URL` remoto.

La validación usa un clon local aislado de la misma rama con las modificaciones
sin commit copiadas y contrastadas. El protocolo registra el HEAD base; el commit
local se crea después de finalizar las pruebas, conforme a la instrucción.

Reproducción global desde `frontend`, con dependencias y binarios PostgreSQL:

```bash
export NEWGLASS_TEST_PG_BIN="$(pg_config --bindir)"
export NEWGLASS_REQUIRE_POSTGRES=1
export PYTHON_DOTENV_DISABLED=1
export PLAYWRIGHT_CHANNEL=chromium
node scripts/run-e2e-phases.js
```

Evidencia completa local ignorada en
`frontend/test-results/b08-investigation/`: `remote/`, `before-mobile.log`,
`before-component.log`, `focused.log`, `test-unit.log`, `test-component.log`,
`lint.log`, `build.log`, `environment.json`, `full-e2e.log` y `linux-artifacts/`.
Los traces, capturas, snapshots y artefactos originales no se incorporan a Git.

El hash SHA-256 de cada archivo de código y pruebas coincide entre el workspace
y el clon Linux; se conserva el manifiesto `tested-sources.json`. La rama de
corrección parte directamente del HEAD de `recovery/sprint-02`, por lo que permite
fast-forward desde esa referencia. El cierre crea un único commit local con este
informe y los tres archivos de código/pruebas, sin push ni cambios al PR #102 o a
ramas oficiales.
