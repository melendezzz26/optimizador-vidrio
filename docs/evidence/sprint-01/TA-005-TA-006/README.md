# Evidencia TA-005 y TA-006: Rasterización de piezas

| Dato | Valor |
|---|---|
| PBI / tareas | TA-005 T01 (rasterización estándar) y TA-006 T01 (rasterización personalizada) · EN-004 |
| SPEC | docs/specs/SPEC-TA-005-TA-006-rasterizacion.md |
| Responsable | Fabricio Aguilar |
| Fecha | 2026-10-12 |
| Entorno | Local, Windows 11 (Python lo informa como "Windows 10"), Python 3.11.9 (backend/venv) |
| Rama | feature/TA-005-TA-006-rasterizacion |
| Commits | 06b5735 (SPEC), 78be47c (TA-006), 5c58321 (TA-005) y el commit de esta evidencia |

## 1. Qué se entrega

- `RasterMask` (`backend/app/modules/optimization/domain/raster_mask.py`): máscara binaria inmutable;
  cada fila es un entero usado como mapa de bits.
- `rasterizer.py` (misma carpeta):
  - `rasterize_convex_polygon` (TA-006);
  - `rasterize_rectangle` y `rasterize_circle` (TA-005);
  - `rasterize_geometry`, punto de entrada que recibe la `geometria` tal como la guarda el módulo de pedidos.
- Configuración fija según el spike de costo de rasterización: regla conservadora (una celda se ocupa si la
  figura cubre área positiva de ella) y mapa de bits por fila. La resolución es un parámetro; por defecto 5 mm (SP-001).
- Solo biblioteca estándar; sin cambios de API, BD ni frontend.

## 2. Pruebas automatizadas

| Procedimiento | Esperado | Obtenido | Archivo |
|---|---|---|---|
| `python -m pytest -v tests/optimization` | Todas pasan | 62 passed | test-results/pytest-optimization.txt |
| `python -m pytest -q` (backend completo) | 0 failed | 963 passed, 383 skipped, 0 failed | test-results/pytest-completo.txt |

## 3. Trazabilidad con la SPEC

| CA | Prueba |
|---|---|
| CA-01 Rectángulo 800 × 600 a 5 mm = 19 200 celdas | `test_rectangle_aligned_with_the_grid_has_exact_cells` |
| CA-02 Cobertura por exceso | `test_rectangle_not_multiple_of_resolution_is_covered_by_excess` |
| CA-03 Circunferencia, error 0–1.5 % | `test_circle_area_error_is_small_and_never_negative` |
| CA-04 Polígono, error 0–1.5 % | `test_hexagon_area_error_is_small_and_never_negative` |
| CA-05 Regla conservadora | `test_no_interior_point_falls_in_a_free_cell`, `test_no_point_inside_the_circle_falls_in_a_free_cell` |
| CA-06 Traslación y sentido | `test_translation_and_vertex_order_do_not_change_the_mask` |
| CA-07 Tres `geometria` del pedido | `test_geometry_entry_point_accepts_the_three_order_shapes` |
| CA-08 Entradas inválidas | `test_rejects_invalid_*`, `test_geometry_entry_point_rejects_invalid_geometries` |
| CA-09 Contrato de la máscara | `test_raster_mask.py` |

## 4. Comprobación con la resolución configurada

Comando: `python experiments/raster/scripts/raster_evidence.py` (6 figuras × 5 resoluciones; solo varía la resolución).
Tabla completa en `resumen-rasterizacion.md`.

| Figura | Error a 5 mm (resolución de SP-001) | Error a 20 mm |
|---|---|---|
| Rectángulo 800 × 600 | +0.000 % | +0.000 % |
| Rectángulo 802 × 600 | +0.374 % | +2.244 % |
| Circunferencia r = 500 | +1.210 % | +3.896 % |
| Hexágono | +1.363 % | +5.312 % |
| Triángulo (formato HU-007) | +2.222 % | +13.185 % |
| Tira 1500 × 30 | +0.000 % | +33.333 % |

- Todos los errores son **≥ 0**: la máscara nunca pierde área de la pieza (regla conservadora).
- Los errores de la circunferencia y del hexágono coinciden exactamente con los previstos por el spike de costo de rasterización.
- El error crece con la resolución y con la proporción de borde frente al área (el triángulo tiene más borde inclinado por unidad de área).
- La tira a 20 mm confirma la RN-07: una pieza más delgada que la celda se deforma (30 mm → 40 mm).

## 5. Máscaras dibujadas

Carpeta `mascaras/` (20 mm): celdas grises = máscara; línea roja = contorno real.
En todas, el contorno queda dentro de las celdas ocupadas.

## 6. Observaciones

- Los tiempos de la tabla dependen de la máquina; sirven para comparar configuraciones entre sí.
- El criterio de "puede consumirse por la validación geométrica" se confirma por completo cuando TA-007 use la máscara.