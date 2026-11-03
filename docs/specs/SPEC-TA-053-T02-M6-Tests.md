# SPEC-TA-053 T02 - Pruebas exhaustivas de M6 Beam Search

## Identificacion

| Campo | Valor |
|---|---|
| Codigo | TA-053 T02 |
| Responsable | Fabricio Melendez |
| Revisor humano esperado | Andro Joseph Quispe Cesias; el PR #91 no registra una review aprobatoria al 2026-11-02 |
| Dependencia | TA-053 T01 |
| Rama | `test/TA-053-m6-beam-search` |
| Estado | Implementada y validada |
| Motor bajo prueba | `BeamSearchOptimizer`, M6-BS, `k=2` |

## Objetivo y alcance

Construir una bateria reproducible que demuestre el comportamiento funcional,
geometrico, determinista y acotado de M6 sin modificar el motor, FF/BF/WF,
M4/M5, el coordinador publico, endpoints, frontend, persistencia o
confirmacion. Las pruebas ejercitan el contrato interno
`OptimizationProblem -> OptimizationResult` y el adaptador de application.

Se incluyen casos normales, geometria, prioridad de retazos, ausencia de
fuente, resultados parciales, limites, inmutabilidad de entradas, paridad con
los fixtures oficiales y regresiones de los motores existentes. No se prueba la
integracion de seis motores; corresponde a TA-043.

## Contratos verificados

- `OptimizationResult` conserva identidad de pieza/unidad, fuente, posicion,
  giro y completitud.
- La geometria se valida mediante `SheetLayout` y `calculate_metrics`, sin
  aceptar una colocacion solo por AABB.
- Los grupos respetan `(glass_type_id, thickness_mm)`.
- Retazos factibles preceden a planchas; un retazo incompatible no participa.
- La simulacion no modifica el `OptimizationProblem` ni consume inventario.
- `stop_reason` distingue limites de `NO_FIT`.
- La ejecucion es determinista y no invoca baselines.

## Casos de prueba

| ID | Caso | Entrada | Resultado esperado |
|---|---|---|---|
| T02-F01 | Unidad colocable | SMALL | Resultado completo, identidad conservada |
| T02-F02 | Cantidades y fuentes | SMALL/MEDIUM | Todas las unidades expandidas, varias fuentes válidas |
| T02-F03 | Grupos materiales | COMPLEX | Grupos independientes y claves preservadas |
| T02-G01 | Formas | MEDIUM/COMPLEX | Rectangulo, circulo y poligono sin solapamiento |
| T02-G02 | Giro y bordes | fixtures oficiales | Giros en paso de 5 grados y posiciones dentro del material |
| T02-G03 | Margen/separacion | MEDIUM/COMPLEX | Validacion raster sin violaciones |
| T02-S01 | Retazo factible | SMALL | Retazo elegido antes de plancha |
| T02-S02 | Retazo no factible | problema sintetico | Fallback a plancha |
| T02-S03 | Stock incompatible | problema sintetico | No se usa fuente de otro material |
| T02-L01 | Sin colocacion | fuente menor que la pieza | Incompleto, sin falso exito |
| T02-L02 | Limite de expansion | `max_expansions=1` | `EXPANSION_LIMIT`, no `NO_FIT` |
| T02-L03 | Memoria/sondeos | limites inyectados | Resultado controlado y razon explicita |
| T02-D01 | Determinismo | SMALL/MEDIUM/COMPLEX | Placements y metricas iguales |
| T02-D02 | Paridad SP-006 | tres fixtures | Fuentes, posiciones, giros y metricas equivalentes |
| T02-R01 | No regresion | suite optimizacion | FF/BF/WF y contratos sin cambios |

## Criterios de aceptacion

1. Los casos oficiales son completos, deterministas y conservan la identidad
   exacta de cada unidad.
2. Se prueban las tres formas canonicas, rotaciones, margen, separacion y
   bordes mediante verificadores compartidos.
3. La prioridad de retazos se prueba tanto en uso como en fallback.
4. No se acepta stock incompatible ni se presenta un parcial como completo.
5. Se distinguen ausencia geometrica y agotamiento de recursos.
6. La paridad compara fuente, coordenadas, rotacion, orden y metricas, no solo
   cantidad colocada.
7. Las entradas permanecen inmutables y no se introducen efectos de inventario.
8. Las regresiones de FF/BF/WF y contratos existentes pasan.

## Evidencia y limitaciones

Cada resultado debe conservar comando, entorno, fixture, conteo y salida de
pytest. Las pruebas supervisadas se ejecutan en WSL2/Linux con la configuracion
oficial. La evidencia versionada de SP-006 declara ejecución local en Windows;
no existe en el repositorio una exportacion verificable de una sesión real de
Google Colab, por lo que T02 no inventa esa evidencia.

## Matriz de trazabilidad

| Requisito | Pruebas |
|---|---|
| Funcionamiento y contrato | T02-F01..F03 |
| Geometria y restricciones | T02-G01..G03 |
| Stock y retazos | T02-S01..S03 |
| Casos limite | T02-L01..L03 |
| Determinismo y fidelidad | T02-D01..D02 |
| No regresion | T02-R01 |

## Exclusiones y riesgos

TA-043, coordinacion publica, seis motores, frontend, confirmacion, migraciones,
benchmarks industriales y certificacion de Colab quedan excluidos. Los limites
dependen del sistema operativo para el supervisor; se separan resultados del
motor puro de resultados de workers supervisados.

## Resultado de ejecucion

La bateria T02 agrego 13 regresiones sobre formas, grupos, fidelidad exacta,
retazos, no-fit, limites y determinismo. Se detecto y corrigio un defecto de
T01: un `TIME_LIMIT` durante la preparacion geometrica escapaba como excepcion.
Ahora se devuelve como `BeamSearchOutcome.stop_reason`, sin cambiar la
generacion de candidatos ni la puntuacion.

Resultados verificados:

- 19 pruebas M6 T01/T02.
- 508 pruebas de `unit/optimization` en Windows, excluyendo el runner que
  requiere Linux.
- 874 pruebas unit/integration/API en WSL2 con PostgreSQL aislado (861 de la
  regresion previa mas 13 nuevas de T02).
- 14 pruebas del runner supervisado en WSL2.
- 47 pruebas portables de SP-006.

La evidencia de SP-006 versionada continua siendo local; no se presenta como
una ejecucion Colab verificable.
