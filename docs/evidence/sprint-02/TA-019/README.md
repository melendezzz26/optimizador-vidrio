# TA-019 — Evidencia técnica de Worst Fit T01/T02

| Campo | Valor |
|---|---|
| Fecha | 25/10/2026 |
| Responsable | Fabricio Melendez |
| Rama | `feature/TA-019-worst-fit` |
| Commit base | `b1112a43579961aff52b57cb469607711e10bdf8` |
| Árbol validado | Cambios de TA-019 sin commit sobre la base indicada. |
| SPEC | [SPEC-TA-019-worst-fit.md](../../../specs/SPEC-TA-019-worst-fit.md), Reviewed |
| PLAN y matriz | [PLAN-TA-019-worst-fit.md](../../../specs/PLAN-TA-019-worst-fit.md), Approved |
| Revisor | Pendiente de asignación formal |
| Resultado técnico | **22 PASS / 0 PARTIAL / 0 FAIL** |

## Alcance y criterio

T01 implementa WF de dominio sobre el recorrido y geometría comunes; T02 cubre
selección, compatibilidad, slice backend y retención acotada. Este cierre añade
solo una regresión y evidencia/documentación; no modifica código productivo.

WF evalúa primero retazos factibles. Si no existe ninguno, evalúa planchas.
Cada fuente aporta la primera orientación compartida factible y su primera
posición válida. Se calcula un layout temporal inmutable y se maximiza la suma
de celdas `usable & ~blocked` posteriores a la colocación. Considera ocupación,
separación, margen y material interior. Desempata por `stock_rank`,
`orientation_rank`, fila y columna ascendentes. Solo se aplica el ganador.

## Regresión automatizada CA-12

Prueba: `test_candidate_selection_is_incremental_and_releases_discarded_layouts`
en [test_worst_fit.py](../../../../backend/tests/unit/optimization/test_worst_fit.py).

- Compara 8 y 80 fuentes factibles, grids 4×4 y dos piezas 1×1.
- Instrumenta temporalmente el constructor de candidatos y `SheetLayout.place`
  con funciones simples; evita que mocks con historial retengan argumentos.
- Conserva solo referencias débiles a candidatos y layouts posteriores.
- Verifica intercalado de generación y evaluación: una lista/tupla adelantada
  de candidatos falla antes de generar el siguiente candidato sin puntuar.
- Verifica que el pico de objetos vivos sea menor que las fuentes y que,
  al multiplicarlas por diez, no supere dos veces el pico de referencia pequeño.
  No exige un conteo exacto como cinco objetos ni depende de la cota histórica.
- Comprueba liberación durante el recorrido y ausencia de candidatos/layouts
  retenidos al retornar, con recolección final controlada.
- Verifica que ambos recorridos siguen completos y eligen fuentes 1 y 2.

No es una prueba de carga ni un presupuesto global de bytes. La instrumentación
se restaura al terminar cada caso. No se ejecutan migraciones ni se usa stock real.

## Comandos y resultados reales

Directorio de trabajo: `backend/`, Windows PowerShell, entorno local `venv`,
Python **3.11.9** y pytest **9.1.1** (versiones consultadas en el intérprete usado).

Nueva regresión aislada:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/optimization/test_worst_fit.py -k candidate_selection_is_incremental_and_releases_discarded_layouts -q
```

Resultado observado: `1 passed, 27 deselected in 0.30s`, código de salida 0.

Suite final obligatoria:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/optimization tests/optimization tests/api/optimization/test_run_contract.py tests/integration/optimization/test_worst_fit_slice.py -q
```

Resultado: **`381 passed in 1.59s`**, código de salida 0. La salida real sin
reconstruir está en [backend-tests.txt](backend-tests.txt). Incluye la regresión
CA-12, las 28 pruebas unitarias WF/regresión FF y los dos slices de integración.

Desde la raíz:

```text
git diff --check
git diff --exit-code HEAD -- backend/app/modules/optimization/domain/rotation.py
git status
git diff --stat
git diff --name-status
```

La ejecución real de whitespace y su resultado se registran en
[diff-check.txt](diff-check.txt). Se comprueban también los archivos nuevos sin
hacer staging. `git diff --stat` y `--name-status` ordinarios no incluyen archivos
sin seguimiento; deben leerse junto a `git status`.

## Matriz final y preservación

| Criterios | Resultado | Evidencia |
|---|---|---|
| CA-01 a CA-11 | PASS, los once | Política independiente, geometría compartida, prioridad, score exacto, desempates y evaluación inmutable; pruebas unitarias existentes. |
| CA-12 | PASS | Nueva regresión incremental/de liberación, incluida en la suite final. |
| CA-13 | PASS | `test_first_fit_does_not_score_or_evaluate_later_sources`; FF usa `next()` y mantiene lazy evaluation/salida temprana. |
| CA-14 a CA-21 | PASS, los ocho | No consumo, determinismo, rotación, margen, separación, interior irregular, multimaterial, faltantes y ausencia de cambios de esquema. |
| CA-22 | PASS | Suite final, regresión FF y slice existente reutilizado sin migraciones. |

La matriz detallada CA → función/prueba permanece en el PLAN; este README es
evidencia y no sustituye a la SPEC como fuente normativa.

`rotation.py` no tiene cambios respecto de HEAD. Se conservan rasterizador,
validación geométrica, métricas, RBAC, modelos y confirmación transaccional.
No se ejecutaron migraciones. El slice usa SQLite en memoria y repositorios
reales con metadata de prueba adaptado: verifica preparación/lecturas/resultado
y no consumo, no restricciones ni concurrencia PostgreSQL.

## Riesgos residuales y coordinación

- WF evalúa más fuentes que FF; la prueba protege retención de objetos, no un
  límite global de memoria/CPU. Guardrails globales se coordinan con TA-037.
- El score no representa completamente la fragmentación ni garantiza óptimo.
- TA-016 debe conservar la secuencia determinista de orientaciones y coherencia
  entre ángulo, contorno local y máscara; no se modificó su archivo de rotación.
- TA-018 debe reutilizar candidato/recorrido; coordinar `packing.py` y
  `first_fit.py` para evitar conflictos o motores duplicados. No se implementó BF.
- La identidad WF es solo de dominio. No se integran HTTP/NDJSON multimétodo,
  frontend, TA-025, TA-026, persistencia multimétodo ni nueva confirmación.
- Las referencias formales de SP-002/TA-037 y coordinación del equipo siguen
  pendientes; no se declaran cerradas por este resultado técnico.

SPEC Reviewed y PLAN Approved por aprobación del responsable comunicada en esta
sesión. Revisor y revisión cruzada real pendientes; no se declara Verified.
Commit, push y PR continúan sin autorización.
