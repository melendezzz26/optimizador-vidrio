# TA-036 — Regresión final tras integrar TA-005/TA-006

Fecha de registro: 13/10/2026.
Rama: `feature/TA-036-saneamiento-funcional`.
Commit integrado validado: `6c32209aece5fe1972472dc5d31630376daa5ba3`.

El merge local `6c32209` incorporó `origin/integration/sprint-01` en
`cff3db6`, correspondiente a PR #42 de TA-005/TA-006 rasterización.
**PR #42 absorbido sin conflictos textuales.** Padres del merge: `5b5b619`
(TA-036) y `cff3db6` (integración).

## Procedencia y alcance de esta evidencia

Se registran los resultados de la regresión integrada comunicados por el
usuario en su solicitud de cierre. Esta actualización documental no vuelve
a ejecutar las suites ni se atribuye una ejecución nueva de esas pruebas.
Se comprobaron directamente el commit y sus padres, la rama, el working tree
limpio antes de esta actualización, `git diff --check` y, en solo lectura,
el contrato de entrada y salida del rasterizador integrado.

## Resultados de la regresión integrada

| Comprobación | Resultado |
| --- | --- |
| Optimization backend | **62 passed**. |
| Backend completo | **1397 passed**, 1 warning de deprecación Starlette/httpx. |
| Frontend unit | **124 passed**. |
| Frontend component | **223 passed** en la suite completa posterior. |
| Lint | **OK**. |
| Build | **OK**. |
| E2E completo | **46 discovered, 45 passed, 1 skipped, 0 failed**. |
| `git diff --check` | **OK**. |
| Working tree antes de esta actualización documental | **Limpio**. |

El timeout aislado inicial de `RegistrarRetazoGeometry` fue investigado:

- No fue fallo de aserción.
- Tres ejecuciones focalizadas consecutivas: **4/4 passed** en cada una.
- Suite completa posterior: **223/223 passed**.

El único skip E2E es **HU-014 móvil por fixture compartido preexistente**.
Se conserva como skipped, no como passed; no hay nuevos skips reportados.

El E2E real de retazo personalizado confirmó **POST y lectura correctos,
sin Decimal no serializable**.

## Contrato TA-036 → TA-006 confirmado

```text
geometria.vertices_mm
    → rasterize_geometry()
    → rasterize_convex_polygon()
    → RasterMask
```

La rasterización admite el `vertices_mm` canónico generado por TA-036.
`rasterize_geometry()` despacha `POLIGONO_CONVEXO` pasando el campo
`vertices_mm` a `rasterize_convex_polygon()`, que devuelve `RasterMask`.
El cierre es implícito entre el último y el primer vértice. No se reconstruye
la forma exclusivamente desde longitudes o ángulos del editor.

Referencias de código inspeccionadas sin modificaciones:

- `backend/app/modules/optimization/domain/rasterizer.py`:
  `rasterize_geometry()` y `rasterize_convex_polygon()`.
- `backend/app/modules/optimization/domain/raster_mask.py`: `RasterMask`.

## Estado y límites del cierre

La SPEC permanece **Draft**, reviewer pendiente. **CA-09 permanece PARTIAL**;
la incorporación de rasterización no cambia el criterio de compatibilidad
de stock pendiente de HU-008/Optimization. No se modifica la SPEC.

Este cierre solo añade evidencia y actualiza su índice en TA-036. Sin cambios
de código ni tests, sin push, PR, merge adicional ni despliegue. No se modifica
el algoritmo integrado de rasterización ni se atribuye aprobación humana formal.
