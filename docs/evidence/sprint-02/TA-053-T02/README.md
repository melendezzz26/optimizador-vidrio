# TA-053 T02 - Evidencia de pruebas M6

## Alcance

Esta evidencia cubre la bateria exhaustiva de pruebas de M6 sobre la rama
`test/TA-053-m6-beam-search`, basada en el HEAD local de T01. No integra M6 al
coordinador de seis motores.

## Pruebas ejecutadas

| Entorno | Comando/resumen | Resultado |
|---|---|---|
| Windows/Python 3.11 | `test_beam_search.py` + `test_beam_search_t02.py` | 19 passed |
| Windows/Python 3.11 | `unit/optimization`, sin `test_comparison_runner.py` | 508 passed |
| WSL2/Python 3.11.9/PostgreSQL aislado | unit + integration + API, sin runner | 874 passed |
| WSL2/Python 3.11.9 | `test_comparison_runner.py` | 14 passed |
| Windows/venv SP-006 | `experiments/sp-006-m6/tests` | 47 passed |

Las advertencias de SP-006 son deprecaciones de pyparsing de matplotlib. El
runner se ejecuta en WSL2 porque requiere procfs, RLIMIT_AS y prctl.

## Cobertura demostrada

- Rectangulos, circulos y poligonos convexos.
- Multiples grupos de material/espesor.
- Rotaciones configuradas en pasos de 5 grados.
- Margen, separacion, bordes y revalidacion raster.
- Retazo factible antes de plancha y fallback ante retazo no factible.
- Stock insuficiente, resultado incompleto y limites de expansion, sondeos,
  memoria y tiempo.
- Igualdad de fuentes, posiciones, rotaciones y metricas frente a los registros
  BS-2 de SP-006.
- Repetibilidad exacta e inmutabilidad de snapshots.

## Defecto corregido

Un limite de tiempo alcanzado durante `prepare_run_geometry` se propagaba como
`BeamSearchStopped`, en vez de producir un `BeamSearchOutcome` con
`stop_reason="TIME_LIMIT"`. La correccion captura solamente ese tipo de
interrupcion en la fase de preparacion. No cambia la politica de fuentes, la
funcion de puntuacion ni la generacion de candidatos.

## Limitacion de evidencia experimental

`experiments/sp-006-m6/evidence/README.md` identifica sus mediciones como
`measured_local_notebook_cpu` en Windows. No existe una exportacion verificable
de una sesion real de Google Colab en el repositorio; por tanto esta evidencia
no afirma resultados de Colab.
