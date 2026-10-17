# S1-OPT-UI — índice canónico de evidencia

Cierre documental de Sprint 1: **16/10/2026, America/Lima**.
La integración funcional está en `chore/S1-final-integration`, merge `ac13d9e`
(padres `86ed943` y `70a6c36`). Revisión humana y PR hacia
`integration/sprint-01` pendientes; este documento no otorga aprobación nueva.

La aplicación consume endpoints reales, progreso NDJSON y resultados persistidos.
Conserva permisos dinámicos `optimization.view`, `optimization.execute` y
`optimization.confirm`, confirmación explícita y conflictos 409 diferenciados.
La documentación de los primeros fixtures se conserva como **historia**, con
sus límites originales, sin presentar esos fixtures como integración real.

## Evidencia vigente

- [Resultados finales y reproducción](../S1-OPTIMIZATION-FIRST-FIT/integration/final/README.md):
  159 unit, 453 component, 86 E2E sin fallos ni skips, lint sin errores/warnings y build OK.
- [Matriz real, capturas y expedientes](../S1-OPTIMIZATION-FIRST-FIT/integration/README.md):
  N=1, multipedido, multimaterial, unidades físicas, retazo, SIN_SOLUCION, 409,
  RBAC, orientación 2D/3D, inventario y rasterización HU-015.
- [Informe funcional de cierre](../../../reviews/S1-final-integration.md).
- [Auditoría de consolidación](../../../reviews/S1-evidence-consolidation.md):
  criterios de retención, cantidades, búsqueda de referencias y revisión de secretos.

`S1-OPT-UI/integration` no es una ruta del repositorio. El directorio integrado
canónico es el enlazado arriba, bajo `S1-OPTIMIZATION-FIRST-FIT/integration`.

## PBI, SPEC, PLAN y criterios

- [Auditoría UI](../../../specs/AUDIT-S1-OPT-UI.md).
- [SPEC UI y CA01–CA11](../../../specs/SPEC-S1-OPT-UI.md).
- [PLAN UI](../../../specs/PLAN-S1-OPT-UI.md) y [TASKS T01–T10](../../../specs/TASKS-S1-OPT-UI.md).
- [SPEC First Fit y CA-01–28](../../../specs/SPEC-S1-optimization-first-fit.md).
- [PLAN First Fit](../../../specs/PLAN-S1-optimization-first-fit.md).
- [SPEC HU-015](../../../specs/SPEC-HU-015-interfaz-rasterizacion.md).

| Criterio UI | Evidencia consolidada |
|---|---|
| CA01 accesibilidad; CA02 selección | Componentes finales; E2E escritorio/móvil; selección E2E1 |
| CA03 actualización; CA05 snapshot | Unit/component: polling, respuestas obsoletas, cambios durante corrida |
| CA04 grupos; CA08 material | E2E3, E2E4 y E2E10 reales; dimensiones e identidad de unidad física |
| CA06 eventos/progreso | Respuestas NDJSON originales en los expedientes; parser y flujo E2E real |
| CA07 geometría, giro y escala | E2E9 2D/3D y E2E4 unidad física 2; tres geometrías HU-015 |
| CA09 métricas | GET, NDJSON y capturas E2E1/E2E10 |
| CA10 confirmación, inventario, errores | E2E1/E2E7/E2E8, stock y movimientos antes/después |
| CA11 pruebas/evidencia | Resultados finales reproducibles; índice de procedencia por SHA256 |

## Validaciones históricas

Los resultados siguientes son antecedentes independientes; **no se suman ni se
atribuyen al código final**. Sus logs intermedios y capturas repetidas fueron
supersedidos por la evidencia integrada. La historia Git y el índice SHA256
permiten recuperar cada archivo original desde `cbfa6ad` sin reescribir commits.

| Hito | Unit | Component | E2E | Naturaleza |
|---|---:|---:|---:|---|
| UI inicial, `0268677` | 131 | 344 | 4 | Fixtures frontend |
| Compatibilidad de eventos | 132 | 46 focales | 4 | Fixtures, no backend |
| 3D, `f538eeb` | 141 | 351 | 6 | Fixtures visuales |
| Grupos/raster, `e42829d` | 147 | 357 | 8 | Fixtures visuales |
| Sincronización RBAC, `e8d1d14` | 147 | 379 | — | Resolución del merge |
| Contrato T1, `4a3c9c1` | 158 | 429 | 8 UI + 6 HU-015 | UI fixture y HU-015 real, separados |
| UI real, `c5baa8a` | 159 | 446 | 85 + 1 skip | Previo al saneamiento de Orders |
| Cierre funcional, `e1faf3e` | 159 | 453 | 86, 0 skips | Orders y UI integrados |

Los hitos frontend registraron lint/build correctos. Las limitaciones de cada
entrega permanecen en [compatibilidad](compatibility.md),
[grupos/raster](groups-raster.md), [3D](visualization-3d.md) y
[contrato T1/RBAC](contract-v1/README.md). Son registros históricos, no el estado
actual del motor. Los enlaces a salidas supersedidas apuntan al cierre final y
no prueban por sí solos los conteos históricos de esta tabla.

## Capturas históricas que prueban estados distintos

Se conservan seis imágenes fixture. No prueban rasterización ni consumo real.
T1 First Fit entrega contornos/resolución, sin máscaras RLE; su inspector no
inventa una máscara global. HU-015 conserva la rasterización real independiente.

| Estado histórico específico | Escritorio | Móvil |
|---|---|---|
| Inspector raster previo con zoom/celdas | [Preparación](desktop-raster-preparation.png) | [Preparación](mobile-raster-preparation.png) |
| Máscara local por pieza en resultado | [Resultado](desktop-raster-result.png) | [Resultado](mobile-raster-result.png) |
| Retazo circular en 3D ilustrativo | [Retazo](desktop-3d-retazo.png) | [Retazo](mobile-3d-retazo.png) |

Las demás vistas se demuestran con capturas reales de integración. En los
informes históricos, un enlace actualizado a una captura integrada es un
**equivalente de cobertura**, no una atribución a aquella corrida fixture.
