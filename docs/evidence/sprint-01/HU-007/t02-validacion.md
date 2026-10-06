# HU-007 T02 — Validación de dimensionamiento por segmentos

## Información general

| Campo | Valor |
|---|---|
| PBI | HU-007 |
| Tarea | T02 — Asociar medidas reales al dibujo |
| Implementación | Dimensionamiento mediante longitudes individuales S1…Sn |
| Estado | Verified |
| Responsable | Andro Quispe Cesias |
| Reviewer | Andro Quispe Cesias |
| Rama | `feature/HU-007-lienzo-pieza-personalizada` |
| Commit SPEC | `b4a9fbd` |
| Commit implementación | `d01bb26` |

## Objetivo

Validar que el editor de pieza personalizada permita asociar longitudes reales en milímetros a cada segmento del polígono elaborado en T01, reconstruir una geometría dimensional cerrada y generar `vertices_mm` para su posterior validación en HU-007 T03.

T02 no valida convexidad, concavidad, autointersecciones ni aptitud para corte.

## Validación técnica

Desde `frontend` se ejecutaron:

```text
node --test tests/unit/geometryScaling.test.js
npm.cmd run lint
npm.cmd run build