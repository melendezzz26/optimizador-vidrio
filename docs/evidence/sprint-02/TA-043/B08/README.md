# TA-043 / B08 — Selección y confirmación transaccional

**Estado: COMPLETADO en el alcance técnico de B08; revisión de Fabricio
pendiente.** SPEC/PLAN permanecen **Draft** y conservan 36 requisitos, 36
criterios de aceptación, 36 filas de trazabilidad y once bloques. No se inicia
B09.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md) ·
[PLAN](../../../../specs/PLAN-TA-043-integracion-seis-motores.md) ·
[contrato comparison-v2](../../../../contracts/optimization/comparison-v2.md) ·
[validación reproducible](validation.json) ·
[smoke B08](smoke/execution.txt)

## Alcance y cambios recuperados

B08 continúa la implementación local existente en
`feature/TA-043-integracion-seis-motores`, sobre la base `integration-02`
(`d85a8d3`). Se conservaron los cambios de Codex; no se modificaron heurísticas,
límites, modelos ni migraciones.

- Selección manual versionada de una sola ejecución completa, durable y elegible.
- Confirmación v2 con pertenencia, permisos, snapshot y stock revalidados dentro
  de una transacción PostgreSQL.
- Consumo exclusivo de planchas/retazos del resultado seleccionado; los otros
  cinco resultados se conservan sin consumo.
- Recibo e idempotencia por clave, conflictos de versión/stock y rollback ante
  errores de escritura.
- Lectura de retazos recuperables coherente con los umbrales de Inventario:
  un retazo descartado por ser demasiado pequeño no se vuelve a publicar como
  recuperable.
- Recuperación histórica del mismo recibo sin recalcular motores.

## Evidencia backend

Los XML de este directorio corresponden al candidato validado y no contienen
`failure`, `error` ni `skipped`:

| Reporte | Casos PASS |
|---|---:|
| `backend-focused.xml` | 50 |
| `backend-confirmed-residual-review.xml` | 43 |
| `backend-connection-review.xml` | 2 |
| `backend-regression.xml` | 179 |
| **Casos backend distintos** | **183** |

La cobertura incluye los seis métodos, selección sin consumo, un único
movimiento, idempotencia, concurrencia, conflictos de stock, rollback,
pertenencia/permisos, recuperación durable y regresiones v1/`/runs`. Los casos
de retazos recuperables y descartados están en
`test_comparison_v2_confirmation.py`.

## Evidencia frontend y smoke

`frontend-focused.xml` acredita **54/54** casos PASS. Incluye selección manual,
diálogo de confirmación, estados de error, recuperación por clave/recarga y
conservación de la historia.

ST-INC-08 se ejecutó con Chromium real, FastAPI y PostgreSQL aislado:

| Perfil | Resultado | Duración |
|---|---|---:|
| Chromium escritorio | PASS | 9.1 s |
| Chromium móvil | PASS | 8.8 s |

En ambos escenarios:

- la selección dejó planchas, retazos, movimientos y pedidos sin cambios;
- la confirmación creó exactamente un movimiento y un retazo, consumiendo una
  unidad del resultado `M5`;
- el pedido quedó `CONFIRMADO`;
- el reintento devolvió el mismo recibo sin delta adicional;
- la recuperación posterior no ejecutó nuevamente los motores.

Los manifiestos SHA-256 de `smoke/cleanup.json` verifican las fuentes ejecutadas.
El runner terminó con código 0, `processes_after: []` y
`temporary_copy_removed: true`.

ST-INC-07 quedó acreditado en
[B07](../B07/README.md), con 2/2 escenarios PASS y la misma limpieza.

## Validaciones adicionales y límites del entorno

- `optimization_b08_validation.py`: PASS; verifica AST, `git diff --check`,
  SPEC/PLAN sin cambios, archivos protegidos sin cambios, hashes y evidencias.
- Frontend focalizado: 13/13 PASS.
- ESLint: PASS.
- Build Vite: PASS; solo permanece el warning existente de bundle mayor de
  500 kB.
- Backend local Windows: 20/20 casos de confirmación PASS. Las 2 pruebas API
  que requieren el supervisor real no pueden iniciar en Windows y devuelven el
  bloqueo esperado `RESOURCE_UNAVAILABLE`; su ejecución autorizada en WSL2 está
  acreditada en los XML PASS anteriores. No se reinstaló WSL, Docker ni
  PostgreSQL.

## Incidencias y correcciones

El primer intento de ST-INC-07 buscó controles fuera de la pestaña activa; se
conserva como antecedente en `../B07/attempts/`. Se corrigió el contexto del
smoke. Durante B08 también se corrigió la lectura de retazos para respetar el
descarte de Inventario y se añadieron pruebas de regresión. No quedan incidencias
funcionales abiertas dentro de B08.

## Pendientes reales

Quedan fuera de este cierre los bloques B09, B10 y B11, incluido el smoke
integral ST-INT. No se implementan ni se declaran en este trabajo.
