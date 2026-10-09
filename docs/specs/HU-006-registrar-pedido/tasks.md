# Tareas HU-006 — estado de convergencia

HU-006: Reviewed, implementación parcial. No Verified.
El aporte 80a4fa4 y su autoría permanecen en la historia. Los checkboxes anteriores
no demostraban cierre; se distinguen subtareas realizadas y pendientes reales.

- [x] Definir contrato multimaterial y plan de migración sin ejecutarlo.
- [x] Consolidar pantalla mixta en features/orders conservando editor HU-007, catálogo y App.
- [x] Bloquear POST con parejas distintas, conservando datos y explicando la restricción.
- [x] Corregir imports tempranos de BD y mantener dependencias HTTP en Presentation.
- [x] Retirar tests API duplicados con overrides globales; conservar cobertura existente.
- [ ] T01: completar frontend sin restricción temporal cuando HTTP/BD soporten multimaterial; evidencia visual/accesibilidad.
- [ ] T02: adaptar API/caso de uso; concretar e implementar recuperación completa CA-02.
- [ ] T03: implementar/verificar migración, ORM y repositorio por pieza, conservando transacción/geometrías.
- [ ] T04: adaptar pruebas al contrato definitivo, validar migración en PostgreSQL temporal y ejecutar regresión global/evidencias.
- [ ] Revisión formal para Implemented/Verified cuando se cumpla todo el alcance.

## Verificación de esta fase — 2026-10-08

| Comprobación ejecutada | Resultado |
|---|---|
| Backend: `python -B -m pytest -q -p no:cacheprovider tests/unit/modules/orders tests/api/inventory/test_lazy_db_import.py` | 29 passed |
| Frontend: `npm.cmd run test:unit` | 84 passed |
| Frontend: `npm.cmd run test:component` | 44 passed |
| `npm.cmd run lint` | PASS |
| `npm.cmd run build` | PASS |

Se conservan los casos heredados HU-007 de errores 401/403/422/500/red y doble
envío. Se añaden cuatro casos para comportamiento nuevo: las tres formas y sus
cantidades en un POST compatible, bloqueo de otro espesor, bloqueo de otro
material y rechazo de cantidad decimal/medidas no positivas. El test apunta a
la pantalla canónica de la feature, la misma que monta App.

No se ejecutaron E2E ni integración PostgreSQL: sus fixtures aplican Alembic en
entornos temporales y esta fase prohíbe ejecutar migraciones. Estos resultados
no acreditan persistencia multimaterial ni sustituyen la regresión global pendiente.
No se hicieron commits, push ni cambios a Supabase.
