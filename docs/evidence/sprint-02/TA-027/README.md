# TA-027 — Casos experimentales reproducibles

Responsable: Andro Quispe. Revisor: Fabricio Melendez Quezada. Fecha: 28/10/2026.
Estado: verificación técnica; review y cierre formal pendientes.
Dependencia SP-002 verificada en `4a4815d`; base integration `4bcf54db8344d4003f115b38646f6fcfd23984a6`.
No se ejecutó TA-028 ni se realizó análisis TA-029. Ningún método se declara ganador.

## Matriz

Piezas = definiciones distintas; unidades = suma de cantidades; retazos/planchas = unidades físicas.
En todos: resolución 1 mm, rotación permitida, residual mínimo 1 × 1 mm.

| Caso | Piezas | Unidades | Retazos | Planchas | Geometrías | Step | Margen | Separación | Estado |
|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| EXP-SMALL-001 | 1 | 3 | 1 | 1 | RECTANGULO | 5° | 0 mm | 0 mm | Válido |
| EXP-MEDIUM-001 | 3 | 9 | 2 | 2 | CIRCUNFERENCIA, RECTANGULO | 5° | 1 mm | 1 mm | Válido |
| EXP-COMPLEX-001 | 6 | 24 | 3 | 4 | CIRCUNFERENCIA, POLIGONO_CONVEXO, RECTANGULO | 5° | 1 mm | 1 mm | Válido |

## Criterios de diseño

Pequeño: control manual, tres cuadrados; primero llena el retazo 2 × 2 y después coloca
los otros dos en la plancha 4 × 4, en (0,0) y (2,0). Mediano: nueve unidades,
dos retazos de capacidades distintas, dos planchas físicas y círculos/rectángulos.
Complejo: 24 unidades, siete fuentes físicas, dos materiales, polígonos convexos y
retazo irregular. La sanidad confirmó giros no ortogonales de 55° y 65°.
La diversidad de capacidad y geometría ofrece decisiones reales a los selectores;
no se ajustaron casos en función de un ganador ni de una métrica de rendimiento.
Todas las rejillas de fuentes tienen como máximo 22 × 16 celdas para mantener CI ligero.

## Fichas congeladas

Dimensiones en mm. Los polígonos se definen mediante todos sus vértices; círculos mediante radio.
La cantidad de cada fuente se expande a índices físicos 1..N. Material = vidrio/espesor.

### EXP-SMALL-001

Fixture: [JSON](../../../../experiments/optimization/cases/EXP-SMALL-001.json).

Configuración: `{"resolution_mm": 1, "angular_step_deg": 5, "margin_mm": 0, "separation_mm": 0}`; rotación `true`; residual `1 × 1 mm`.

| Pieza | Cantidad | Material | Geometría completa |
|---|---:|---|---|
| 1 | 3 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 2, "height_mm": 2}` |

| Fuente | Tipo | Cantidad física | Material | Geometría completa |
|---|---|---:|---|---|
| 1 | RETAZO | 1 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 2, "height_mm": 2}` |
| 2 | PLANCHA | 1 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 4, "height_mm": 4}` |

SHA-256: `8983a8291a272938650bbc0a5c0fb0a5affc33bef5a61ee9afc73a75caa583f5`.

### EXP-MEDIUM-001

Fixture: [JSON](../../../../experiments/optimization/cases/EXP-MEDIUM-001.json).

Configuración: `{"resolution_mm": 1, "angular_step_deg": 5, "margin_mm": 1, "separation_mm": 1}`; rotación `true`; residual `1 × 1 mm`.

| Pieza | Cantidad | Material | Geometría completa |
|---|---:|---|---|
| 1 | 3 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 6, "height_mm": 3}` |
| 2 | 4 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 3, "height_mm": 2}` |
| 3 | 2 | 1 / 6 mm | `{"type": "CIRCUNFERENCIA", "radius_mm": 2}` |

| Fuente | Tipo | Cantidad física | Material | Geometría completa |
|---|---|---:|---|---|
| 1 | RETAZO | 1 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 12, "height_mm": 9}` |
| 2 | RETAZO | 1 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 9, "height_mm": 7}` |
| 3 | PLANCHA | 2 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 16, "height_mm": 12}` |

SHA-256: `eb50a3beaa2312fc94e4cd879b8961401b119f6370c08a5357680bb2b76535d9`.

### EXP-COMPLEX-001

Fixture: [JSON](../../../../experiments/optimization/cases/EXP-COMPLEX-001.json).

Configuración: `{"resolution_mm": 1, "angular_step_deg": 5, "margin_mm": 1, "separation_mm": 1}`; rotación `true`; residual `1 × 1 mm`.

| Pieza | Cantidad | Material | Geometría completa |
|---|---:|---|---|
| 1 | 5 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 9, "height_mm": 3}` |
| 2 | 6 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 4, "height_mm": 3}` |
| 3 | 4 | 1 / 6 mm | `{"type": "CIRCUNFERENCIA", "radius_mm": 2}` |
| 4 | 4 | 1 / 6 mm | `{"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [6, 0], [4, 4], [0, 3]]}` |
| 5 | 3 | 2 / 8 mm | `{"type": "RECTANGULO", "width_mm": 7, "height_mm": 2}` |
| 6 | 2 | 2 / 8 mm | `{"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [5, 0], [0, 4]]}` |

| Fuente | Tipo | Cantidad física | Material | Geometría completa |
|---|---|---:|---|---|
| 1 | RETAZO | 1 | 1 / 6 mm | `{"type": "POLIGONO_CONVEXO", "vertices_mm": [[0, 0], [16, 0], [12, 12], [0, 9]]}` |
| 2 | RETAZO | 1 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 10, "height_mm": 16}` |
| 3 | PLANCHA | 2 | 1 / 6 mm | `{"type": "RECTANGULO", "width_mm": 22, "height_mm": 16}` |
| 4 | RETAZO | 1 | 2 / 8 mm | `{"type": "RECTANGULO", "width_mm": 7, "height_mm": 12}` |
| 5 | PLANCHA | 2 | 2 / 8 mm | `{"type": "RECTANGULO", "width_mm": 16, "height_mm": 14}` |

SHA-256: `c844a23d849a8f0f1903a827bb7d2f1b6782a386610dda14c2789520a5670478`.

## Equivalencia y reproducibilidad

`loader.py` reutiliza prepare_persisted_problem y with_compatible_stock.
Cada método recibe un problema recién reconstruido del mismo JSON. Pruebas comparan
igualdad semántica y distinta identidad de problema/geometría, modifican el diccionario
fuente tras la construcción y verifican que los snapshots no cambian. Se rechaza
mutación directa de geometría. Se comprueban bytes del archivo, cantidades, material,
resolución, 5°, margen y separación. Ejecuciones en orden inverso no contaminan resultados.
calculate_metrics revalida placements reales; no se comparan sus valores entre métodos.

## Pruebas y sanidad

Desde backend:

```text
python -m pytest tests/unit/optimization/test_experimental_cases.py -q -ra
23 passed, 0 failed, 0 skipped in 1.61s
```

CA-01/02: carga, conteos y diversidad; CA-03: entradas separadas y constantes explícitas;
CA-04: igualdad de resultados repetidos, orden inverso y archivo inalterado;
CA-05: nueve pares ejecutan y revalidan geometría sin ranking.

| Caso | Método | Colocadas / total | Completo |
|---|---|---:|---|
| EXP-SMALL-001 | FF | 3 / 3 | Sí |
| EXP-SMALL-001 | BF | 3 / 3 | Sí |
| EXP-SMALL-001 | WF | 3 / 3 | Sí |
| EXP-MEDIUM-001 | FF | 9 / 9 | Sí |
| EXP-MEDIUM-001 | BF | 9 / 9 | Sí |
| EXP-MEDIUM-001 | WF | 9 / 9 | Sí |
| EXP-COMPLEX-001 | FF | 24 / 24 | Sí |
| EXP-COMPLEX-001 | BF | 24 / 24 | Sí |
| EXP-COMPLEX-001 | WF | 24 / 24 | Sí |

Resultados estructurados: [sanity.json](sanity.json). Son sanidad, no ejecución experimental formal ni benchmark.

## Verificación final local

`python -m pytest tests -q -ra` desde backend: **1641 passed, 0 failed,
636 skipped, 1 warning en 55.16s**. Omisiones por binarios PostgreSQL locales ausentes;
warning de deprecación Starlette/httpx existente. CI exige PostgreSQL: pendiente al registrar esta evidencia.
Las 32 pruebas nuevas (9 SP-002 + 23 TA-027) están incluidas, no se suman otra vez.
`git diff --check`: correcto. Cambios limitados a documentos, dos suites y experimentos;
sin modificaciones en backend/app, frontend o CI. Sin secretos, temporales ni salidas grandes.
Los hashes anteriores corresponden a JSON UTF-8 con finales LF, como se almacenan en Git.

Entrega: PR hacia integration/sprint-01 y review melendezzz26. No merge, rebase,
force push, auto-merge, cierre formal ni smoke post-merge.

## Entrega para revisión

PR [#82](https://github.com/melendezzz26/optimizador-vidrio/pull/82), base integration/sprint-01.
Reviewer `melendezzz26` solicitado mediante GitHub y confirmado en requested_reviewers.
CI backend/frontend/E2E en ejecución al registrar esta nota; resultado definitivo en
los checks y descripción del PR, vinculados al HEAD revisable. Sin merge ni cierre formal.
