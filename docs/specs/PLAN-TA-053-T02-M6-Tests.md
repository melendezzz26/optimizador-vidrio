# PLAN-TA-053 T02 - Pruebas exhaustivas de M6 Beam Search

## Informacion general

| Campo | Valor |
|---|---|
| Estado | Completed |
| SPEC | [SPEC-TA-053-T02-M6-Tests.md](SPEC-TA-053-T02-M6-Tests.md) |
| Base | HEAD local de TA-053 T01 (`1384451`) |
| Rama | `test/TA-053-m6-beam-search` |

## T02.1 - Funcionamiento normal

- **Archivos:** `backend/tests/unit/optimization/test_beam_search_t02.py`.
- **Pruebas:** unidades simples, cantidades, varias fuentes y grupos.
- **Resultado esperado:** `OptimizationResult` completo, con identidades y
  material correctos.
- **Evidencia:** salida parametrizada de SMALL, MEDIUM y COMPLEX.

## T02.2 - Geometria

- **Archivos:** `backend/tests/unit/optimization/test_beam_search_t02.py`.
- **Pruebas:** formas oficiales, orientaciones de 5 grados, margen,
  separacion, bordes y revalidacion con `calculate_metrics`.
- **Resultado esperado:** todas las colocaciones pasan validacion raster y no
  hay solapamientos.
- **Evidencia:** placements canonicos y metricas.

## T02.3 - Inventario y retazos

- **Archivos:** `backend/tests/unit/optimization/test_beam_search_t02.py`.
- **Pruebas:** retazo factible, retazo incompatible/no factible y fallback a
  plancha; snapshots antes/despues.
- **Resultado esperado:** retazos compatibles se priorizan y entradas no
  cambian. El dominio no tiene acceso a repositorios ni confirma stock.
- **Evidencia:** identidades de fuentes y equality de problemas.

## T02.4 - Casos limite

- **Archivos:** `backend/tests/unit/optimization/test_beam_search_t02.py`.
- **Pruebas:** sin fuente suficiente, fuente incompatible, parcial y limites
  de expansion, sondeos, memoria y tiempo.
- **Resultado esperado:** parcial no completo y razon de limite explicita.
- **Evidencia:** `BeamSearchOutcome.stop_reason`, `placed_units`.

## T02.5 - Determinismo y fidelidad

- **Archivos:** `backend/tests/unit/optimization/test_beam_search_t02.py`.
- **Pruebas:** repeticion profunda y comparacion con resultados locales de
  SP-006 para fuente, coordenadas, giro y metricas.
- **Resultado esperado:** igualdad exacta bajo los mismos fixtures/configuracion.
- **Evidencia:** tabla de placements y metricas.

## T02.6 - Recursos

- **Archivos:** test unitario; suites WSL2 oficiales existentes.
- **Pruebas:** limites inyectados en motor puro y runner supervisado en WSL2.
- **Resultado esperado:** no confundir limite con `NO_FIT`; no dejar procesos
  huerfanos en el runner oficial.
- **Evidencia:** conteos pytest y razones de parada.

## T02.7 - Regresiones

- **Archivos:** existentes, no se modifica coordinador.
- **Pruebas:** suite `unit/optimization` sin runner en Windows, suite oficial
  unit/integration/API y runner en WSL2, experimento SP-006.
- **Resultado esperado:** FF/BF/WF, geometria, contratos e inventario pasan.
- **Evidencia:** salidas de los comandos oficiales.

## T02.8 - Evidencias y cierre

- **Archivos:** esta SPEC/PLAN y, si procede, evidencia T02.
- **Pruebas:** `git diff --check`, compileall, revisión de diff prohibido.
- **Resultado esperado:** rama limpia, commits locales convencionales, sin push.
- **Evidencia:** hashes, estado Git y matriz actualizada.

## Comandos oficiales

```text
PYTHONPATH=backend python -m pytest backend/tests/unit/optimization -q
wsl ... python -m pytest tests/unit/optimization tests/integration/optimization tests/api/optimization --ignore=tests/unit/optimization/test_comparison_runner.py -q -ra
wsl ... python -m pytest tests/unit/optimization/test_comparison_runner.py -q -ra
```

Los comandos WSL2 se ejecutan desde `backend`, con
`PYTHON_DOTENV_DISABLED=1`, `NEWGLASS_REQUIRE_POSTGRES=1` y el binario
PostgreSQL oficial. No se usan bases compartidas ni migraciones.

## Resultado de ejecucion

Todos los bloques T02.1 a T02.8 fueron ejecutados. La unica correccion
necesaria fue el manejo de `TIME_LIMIT` durante la preparacion geometrica;
quedo cubierta por una regresion y no altera FF/BF/WF ni el coordinador.
`git diff --check` y `compileall` pasan. La matriz de trazabilidad queda
cubierta por `test_beam_search.py` y `test_beam_search_t02.py`.
