# TA-036 — Evidencia consolidada

Rama: `feature/TA-036-saneamiento-funcional`. Implementación sometida a T06:
`0e67631896ac37e7ef043247f1b20656a3b83689`, sobre integración `b7a0175`.

**Validación manual final — 13/10/2026:** el usuario confirmó que el retest
final de TA-036 fue satisfactorio y autorizó organizar los cambios en commits
locales, sin push ni merge. Véase el cierre en
[Correctivo angular y JSON de retazo](correctivo-angular-json.md).
Esta confirmación funcional no sustituye la revisión formal independiente.

**Regresión integrada final — 13/10/2026:** tras el merge local `6c32209` de
`origin/integration/sprint-01`, que incorporó PR #42 (TA-005/TA-006), se registra
la [regresión posterior a integrar rasterización](regresion-post-integracion-ta005-ta006.md).
Backend completo: 1397 passed; frontend: 124 unitarias y 223 componentes;
E2E: 46 descubiertos, 45 passed, 1 skip preexistente, 0 failed. Lint/build OK.

| Evidencia | Contenido |
| --- | --- |
| [Implementación T02–T05](implementacion-validacion.md) | Cambios por bloque, migración y resultados históricos de la primera validación. |
| [Correctivo de regresión](correctivo-regresion.md) | Causa de la pérdida de cobertura, matriz test anterior/equivalente actual y refuerzo de cantidad_afectada. |
| [T06: regresión final](t06-regresion-final.md) | Ejecución completa backend/frontend/E2E, omisión explícita, matriz de CA, decisiones, revisión Git y riesgos residuales del cierre T06. |
| [Revisión técnica final](revision-tecnica-final.md) | Nueva ejecución completa, análisis literal de CA-09, conflicto documental HU-008 y preservación antes de retirar worktrees. No constituye revisión humana formal. |
| [Ajuste de editor y navegación](ajuste-editor-navegacion.md) | Solicitud posterior: lados independientes, restricción angular/cíclica, retazo compartido y módulos solo desde sidebar. Sus cambios requieren nueva revisión; la revisión anterior no los certifica. |
| [Correctivo angular y JSON de retazo](correctivo-angular-json.md) | Hallazgos posteriores de validación manual: hasta n−3 ángulos fijados y Decimal dentro de tuplas; diagnóstico, regresión HTTP/PostgreSQL y guía de retest final. |
| [Regresión postintegración TA-005/TA-006](regresion-post-integracion-ta005-ta006.md) | Resultados sobre `6c32209`, investigación del timeout aislado y contrato canónico de TA-036 hacia rasterización confirmado. |
| [Ramas paralelas](auditoria-ramas.md) | Tips inspeccionados, solapamientos, contratos e instrucciones para compañeros después del merge de TA-036. |
| [SPEC](../../../specs/SPEC-TA-036-saneamiento-funcional.md) | Contratos funcionales y criterios de aceptación. |

La SPEC permanece **Draft**, con **Reviewer pendiente**. La evidencia técnica
no constituye aprobación formal ni cambia el flujo
`Draft → Reviewed → Implemented → Verified`. Los resultados anteriores se
conservan como historia. La regresión postintegración identifica sus propios
resultados y SHA, sin sustituir los registros históricos de T06.

Los cierres anteriores no realizaron push, PR, merge, rebase ni despliegue.
La integración local posterior ya existente es `6c32209`; esta actualización
solo registra evidencia, sin push, PR ni merge adicional. Las pruebas usan datos
sintéticos locales; no se ejecutan migraciones contra Supabase ni se usan
Heroku/Pages. Los logs transitorios y reportes locales generados no forman
parte del commit documental.
