# SPEC-TA-007 — Validación geométrica de colocaciones

Estado: Draft
PBI relacionado: TA-007 T01 (límites y superposición) y TA-007 T02 (separación y margen) · EN-004
Responsable: Fabricio A.
Dependencias: SPEC-TA-005-TA-006 (máscaras de piezas), RN-001 (valores configurados de separación y margen)

## 1. Objetivo

Decidir, sobre celdas raster, si una pieza puede colocarse en una posición de un material (plancha o retazo):
dentro de sus límites, sin superponerse con otras piezas y respetando el margen al borde y la separación entre
piezas configurados. Es la regla que usarán las posiciones candidatas (TA-015) y First Fit, Best Fit y Worst Fit.

## 2. Alcance

Incluye:
- Rasterización del material con regla interior: plancha (`RECTANGULO`) y retazo (las tres formas).
- Validación de una colocación: límites y superposición (T01); margen y separación (T02).
- Estado inmutable del material con las piezas colocadas.
- Pruebas unitarias y evidencia gráfica.

Fuera de alcance:
- Rotación (TA-016), posiciones candidatas (TA-015) y heurísticas FF/BF/WF (TA-017 a TA-019).
- Guardar separación y margen en la configuración versionada (RN-001): aquí se reciben como parámetros.
- API, base de datos, migraciones y frontend.

## 3. Actor y precondiciones

- Actor: el motor de optimización (código del backend).
- Precondiciones: las piezas ya están rasterizadas con la regla conservadora (SPEC-TA-005-TA-006) y con la misma
  resolución que el material.

## 4. Entradas / datos

| Campo | Unidad | Regla |
|---|---|---|
| Geometría del material | mm | Mismo formato que `Pieza.geometria` / `Retazo.geometria`; la plancha es un `RECTANGULO` |
| Máscara de la pieza | celdas | `RasterMask` de SPEC-TA-005-TA-006 |
| Posición (fila, columna) | celdas | Esquina superior izquierda de la máscara de la pieza sobre la máscara del material |
| `margin_mm` | mm | ≥ 0 y finito; 0 = sin margen |
| `separation_mm` | mm | ≥ 0 y finito; 0 = sin separación |

## 5. Reglas de negocio

- **RN-01 Material con regla interior:** una celda del material es usable solo si está completamente dentro de él.
  Junto con la regla conservadora de la pieza, garantiza que la pieza real queda dentro del material real.
- **RN-02 Límites:** la colocación es válida solo si todas las celdas de la pieza caen en celdas usables del material.
- **RN-03 Superposición:** ninguna celda de la pieza puede coincidir con una celda ya ocupada por otra pieza.
- **RN-04 Margen:** las celdas usables se reducen en `ceil(margen / resolución)` celdas desde el borde del material.
- **RN-05 Separación:** las celdas ocupadas se amplían en `ceil(separación / resolución)` celdas; la pieza nueva no
  puede tocar esa zona.
- **RN-06 Redondeo hacia arriba:** margen y separación nunca se aplican por debajo del valor configurado
  (3 mm con celdas de 5 mm exigen 1 celda = 5 mm).
- **RN-07 Distancia por celdas:** margen y separación se miden en filas y columnas (vecindad cuadrada). En diagonal la
  distancia real es mayor que la exigida, lo que mantiene el criterio conservador.
- **RN-08 Motivo del rechazo:** se informa uno, en este orden: `FUERA_DE_LIMITE`, `MARGEN_INSUFICIENTE`,
  `SUPERPOSICION`, `SEPARACION_INSUFICIENTE`.
- **RN-09 Inmutabilidad:** colocar una pieza devuelve un estado nuevo; el anterior no cambia.

## 6. Flujo principal

1. Se rasteriza el material con la regla interior y se crea un estado vacío con margen y separación.
2. Para cada posición propuesta se consulta si la pieza cabe y, si no, por qué.
3. Si cabe, se coloca y se obtiene el nuevo estado.

## 7. Flujos alternativos / errores

- Pieza y material con distinta resolución → `PlacementError`.
- Margen o separación negativos o no finitos → `PlacementError`.
- Colocar en una posición no válida → `PlacementError` con el motivo.
- Geometría de material inválida → `RasterizationError` (SPEC-TA-005-TA-006).

## 8. Criterios de aceptación

| CA | Criterio | Tarea |
|---|---|---|
| CA-01 | Una plancha de 2440 × 1830 mm a 5 mm tiene 488 × 366 celdas usables. | T01 |
| CA-02 | En un retazo circular o poligonal, ninguna celda usable sale del material real y el área usable nunca supera la real. | T01 |
| CA-03 | Una colocación totalmente dentro del material y sin solapamiento es aceptada. | T01 |
| CA-04 | Una colocación fuera del límite es rechazada con `FUERA_DE_LIMITE`. | T01 |
| CA-05 | Una colocación superpuesta es rechazada con `SUPERPOSICION`. | T01 |
| CA-06 | Colocar no modifica el estado anterior; colocar en una posición inválida falla. | T01 |
| CA-07 | Con margen configurado, una pieza más cerca del borde que el margen es rechazada con `MARGEN_INSUFICIENTE`, y una que lo cumple es aceptada. | T02 |
| CA-08 | Con separación configurada, una pieza más cerca de otra que la separación es rechazada con `SEPARACION_INSUFICIENTE`, y una que la cumple es aceptada. | T02 |
| CA-09 | Margen y separación se redondean hacia arriba a celdas completas; 0 reproduce el comportamiento de T01. | T02 |
| CA-10 | Valores inválidos o resoluciones distintas lanzan `PlacementError`. | T01/T02 |

## 9. Impacto técnico

- Módulos: `backend/app/modules/optimization/domain/` (`rasterizer.py` con la regla interior; `placement.py` nuevo).
- API, BD / migración y UI: no aplica.

## 10. Pruebas previstas

- `backend/tests/optimization/test_rasterize_material.py`: CA-01 y CA-02.
- `backend/tests/optimization/test_placement.py`: CA-03 a CA-10.
- Comando: `python -m pytest -q tests/optimization`.

## 11. Evidencias requeridas

- Salida de pytest.
- Casos gráficos válidos e inválidos (backlog TA-007 T01).
- Comparación con dos configuraciones de separación y margen (backlog TA-007 T02).
- Ubicación: `docs/evidence/sprint-01/TA-007/`.

## 12. Decisiones / notas

- **Bits por fila:** la comprobación de cada fila es una operación entre enteros (`pieza << columna` frente a las filas
  del material y de las piezas ocupadas); no se recorre celda por celda.
- **RN-001:** el validador recibe margen y separación en mm. RN-001 decidirá dónde se guardan y los pasará al crear el estado.
- **Puerta TA-035 T02:** igual que en SPEC-TA-005-TA-006, sección 13: el smoke de staging está parcial por HU-008.
- La SPEC no tuvo revisión previa porque el equipo no estaba disponible; se revisa en el PR.