# E2E integrado de Sprint 2: coordinación B02 y TA-040

El reporter anterior comprobaba todos los specs críticos al terminar cada proceso
Playwright. El primer proceso solo ejecuta B02 en escritorio y móvil; por ello
fallaba por ausencia del resto y el shell no llegaba a la segunda ejecución.

## Protocolo

Desde `frontend`, `node scripts/run-e2e-phases.js` realiza lo siguiente:

1. Crea un directorio nuevo, UUID, SHA del checkout y fecha de inicio. En Actions
   verifica además que `GITHUB_SHA` coincida con el checkout.
2. Descubre la suite completa con Playwright `--list`. Guarda un inventario con
   IDs de escenario, archivo, título, proyecto, estado esperado y fase, protegido
   por SHA-256. Exige ambos proyectos y todos los specs críticos registrados.
3. Ejecuta únicamente el título exacto B02 con `--grep`, en un servidor nuevo.
4. Ejecuta el complemento con `--grep-invert`, en otro servidor nuevo. Cada
   servidor conserva `reuseExistingServer: false` y el PostgreSQL temporal propio.
5. Valida la unión exacta de IDs frente al inventario y aplica el gate global.

Cada fase valida sus escenarios y estados sin exigir todavía los specs de la
otra. Un fallo real de la primera fase detiene el inicio de la segunda; el gate
conjunto sigue fallando por ejecución incompleta. No se ignoran códigos de salida.
Se rechazan escenarios ausentes, duplicados, ajenos, fallidos, inestables, sin
resultados, skips sin aprobación TA-040 válida, errores globales, proyectos
incompletos y reportes ausentes/corruptos. Un fallo declarado como esperado no
certifica un escenario exitoso. El comportamiento de omisiones aprobadas de
TA-040 se conserva; un spec crítico sigue necesitando ejecución exitosa por proyecto.

Los archivos se escriben una sola vez. Ambos reportes deben coincidir con el UUID,
SHA, fechas y digest del inventario de esta invocación. No se buscan reportes por
glob ni se reutilizan reportes de ejecuciones anteriores.

## Evidencia

- `frontend/test-results/e2e-phases/run-*/context.json`: identidad del intento.
- En el mismo directorio: `plan.json`, `b02.json`, `remaining.json` y
  `validation.json`; esta última contiene el veredicto conjunto.
- Subdirectorios `b02/` y `remaining/`: artefactos de pruebas separados.
- `frontend/playwright-report/e2e-phases/run-*/{b02,remaining}/`: HTML separado.

Actions sube esos directorios aun si falla el job, con nombre que incluye SHA,
run ID y run attempt. La ausencia de archivos también hace fallar la publicación
del artefacto. El log de Actions conserva la salida de cada proceso.

## Reproducción

En Ubuntu, con Node 22, Python 3.11, dependencias de `backend/requirements.txt`,
dependencias frontend del lockfile y Chromium administrado de Playwright:

```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
export NEWGLASS_TEST_PG_BIN="$(pg_config --bindir)"
export NEWGLASS_REQUIRE_POSTGRES=1
export PYTHON_DOTENV_DISABLED=1
export PLAYWRIGHT_CHANNEL=chromium
node scripts/run-e2e-phases.js
```

El intérprete `python` debe tener las dependencias backend instaladas. Se necesitan
`initdb` y `pg_ctl` locales y puertos 8017 y 5173 libres. Nunca se proporciona un
`DATABASE_URL` remoto. No se cambia la protección de downgrade B02 ni las reglas
de negocio, motores o presupuestos de recursos.

Para comprobar solo descubrimiento y partición, sin ejecutar navegadores:

```bash
node scripts/run-e2e-phases.js --plan-only
```

El checkout integrado `8672408` descubre **146 escenarios: 2 B02 + 144 restantes**,
73 por proyecto y 15 specs. La cifra 2 + 134 corresponde a un inventario anterior;
la coordinación no fija esos totales y no elimina los diez escenarios adicionales.
`--plan-only` no certifica resultados E2E.

La ejecución real en Linux también detectó un selector ambiguo en el smoke B07:
`getByRole('table')` encontraba medidas originales y métricas. El test ahora usa
el nombre accesible exacto `Métricas de 6 motores`; se conservan sus aserciones
de métricas, seis distribuciones, recuperación y simulación sin consumo.
La misma corrida detectó timeouts del pool durante los snapshots globales de
inventario de B06/B07 en móvil. El colector E2E ahora lee secuencialmente todos
los historiales, en el mismo orden y con las mismas aserciones HTTP 200 y de
igualdad. Esto limita la concurrencia del colector según crece el inventario
creado por la suite; no cambia el pool del backend ni omite datos o reintenta fallos.

Regresiones locales del gate: `node --test tests/unit/e2eGate.test.js
tests/unit/e2ePhases.test.js`. El contrato de workflow se ejecuta desde backend con
`python -m pytest tests/unit/test_ci_contract.py -q -ra`.

## Certificación en GitHub Actions

El workflow se activa por PR o `workflow_call`; un push únicamente a la rama de
recuperación no dispara el filtro de push actual. Se necesita un run autorizado
que haga checkout del SHA candidato (o del merge ref del PR que lo contenga),
complete ambas fases y publique `validation.json` con `ok: true`, el SHA correcto
y los 146 escenarios validados. Un descubrimiento local, una corrida de regresión
unitaria o un run de otro SHA no equivalen a CI verde.
