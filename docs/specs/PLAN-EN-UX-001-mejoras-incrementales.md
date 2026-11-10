# PLAN-EN-UX-001 — Mejoras UI/UX del optimizador en incrementos revisables

| Campo | Valor |
|---|---|
| Estado | Draft |
| Responsable | Fabricio Melendez Quezada |
| PBI | [EN-UX-001 — Notion](https://app.notion.com/p/414e0c471a448146b8c9f5f87e578c52) |
| SPEC | [SPEC-EN-UX-001](SPEC-EN-UX-001-resultados-operativos.md) |
| Auditorías | `Auditoria_NewGlass_2026-11-10.pdf` y `Auditoria_Complementaria_NewGlass_2026-11-10.pdf`, archivos originales aportados por el responsable |
| Integración | PR [frontend #2](https://github.com/melendezzz26/newglass-frontend/pull/2), sin merge ni deploy |
| Frontera | React/Vite en repositorio frontend; FastAPI/SQLAlchemy/Alembic exclusivamente en backend |

## Objetivos y límites

Entregar una interfaz de inspección útil en escritorio que conserve toda trazabilidad. Los motores FF, BF, WF, HF, M5 y M6-BS, sus resultados persistidos, reglas de elegibilidad, autorización, confirmación y descuentos de stock **no cambian**. No se utilizarán optimizaciones reales ni inventario productivo como fixtures de QA. No se modificará `main` directamente.

La documentación histórica, ADR y SPEC permanecen en el monorepo, según decisión del responsable. La implementación nueva vive en `newglass-frontend`, y los cambios de dominio/HTTP únicamente en `newglass-backend`.

## Incremento I1 — Contexto, resultados y comparación

| Tarea | Archivos / responsabilidad | Validación |
|---|---|---|
| I1-T01 Barra de contexto | `ComparisonWorkspace.jsx`, CSS; no fijar cabecera general | tabs, foco y cambio de motor; contextual visible con scroll |
| I1-T02 Resumen al lado del patrón | `ComparisonWorkspace.jsx`; distinguir cobertura/aprovechamiento y escala | completas, parciales, resultado recuperado |
| I1-T03 Consulta única de medidas | `OriginalRequest` / `OriginalMeasuresTable` | búsqueda, dimensiones originales, cantidad, pedido y vidrio; resolver diferencia con SPEC-TA-046 RN-07 mediante revisión |
| I1-T04 Pendientes agrupadas | `UnplacedSummary.jsx`, `unplacedModel.js` | 220 unidades compactadas por pedido/pieza/motivo y recuperables exactas |
| I1-T05 Visor único | `MaterialTrace.jsx` | no segundo patrón; conservar áreas, dimensiones y etiquetas de vidrio |
| I1-T06 Comparación compacta | `CompactComparisonTable.jsx`, `comparisonResultModel.js` | seis motores, estados, elegibilidad, áreas operativas, exactos en detalle |
| I1-T07 Regresiones | Vitest, React Testing Library, lint, build y Playwright en dos checkouts | gates verdes sin skips; no se quita confirmación, inventario ni recuperación |
| I1-T08 Evidencia visual | 1366×768 y 1920×1080 con comparaciones completas y parciales | capturas antes/después, scroll requerido, sticky sin ocultar foco y contenido |

**Criterio de parada:** un fallo de tests críticos, regresión de selección/confirmación o cambio de contrato no acordado bloquea el merge. El PR permanece en Draft mientras haya fallos.

## Incremento I2 — Selección 2D/3D e inspector

1. Auditar identidad única `comparison + execution + source + stock_unit_index + order + piece + unit_index`; evitar colisiones de piezas con IDs repetidos.
2. Incorporar selección persistente sin mover zoom/scroll.
3. Vincular lista compacta y patrones 2D/3D con un solo inspector.
4. Mostrar ID, rotación, material/vidrio, espesor, geometría y medidas de la unidad; conservar accesibilidad por teclado.
5. Reducir etiquetas 3D superpuestas, mostrar detalle al seleccionar.
6. Tests geométricos, modelos puros, componentes y E2E. Sin cambios de geometría del motor.

## Incremento I3 — Bugs y accesibilidad (en PR pequeños)

- B01: comparar histórico #85: obtener diagnóstico reproducible en backend de prueba; no alterar registros ni aplicar SQL manual; especificación correctiva si hace falta.
- B02: comparar progreso provisional frente a resultado definitivo, fuentes coherentes; I1 reduce el 0% falso pero no certifica sincronización completa.
- B03: unificar FF/BF/WF/HF/M5/M6-BS en etiquetas públicas, manteniendo alias como ayuda.
- B05 y UX07: `html lang='es-PE'`, título del documento, prueba accesibilidad sin asumir WCAG certificada.
- C01: máscaras temporales expiradas fuera del detalle persistido; no confundir ausencia de máscara con ausencia de resultado.
- C03: fondo desacoplado de altura de contenido.
- UX03/UX04/UX05/UX06/UX09: estados comerciales versus cálculo, acciones/labels, historial y datos técnicos legibles.
- No inventar ranking de motores, ni clasificar parciales como defectos.

## Incremento I4 — Cancelación real (prioridad P1, dependencia backend)

1. Inspeccionar en `newglass-backend` rutas y contratos existentes; actualmente `comparison_supervision_v2.py` contiene `Event` interno de cancelación y `sequential_runner.py` reconoce `CANCELLED`, pero `comparison_v2_routes.py` no expone un endpoint de cancelación. Esta inspección **no acredita** cancelación HTTP segura.
2. Nueva SPEC backend: endpoint idempotente y autenticado, operación durable, carreras `finalizada vs cancelación`, reanudación/reconciliación tras reinicio y prevención de motores pendientes.
3. Ajustar supervisor para certificar detención del trabajo/descendientes antes de liberar admisión, sin confiar en PID aislado; preservar resultados terminados, inventario y orden comercial.
4. Si cambia esquema/estados: migración Alembic documentada y reversible (sin DDL ni seed manual).
5. Tests unitarios/API/integración backend de cancelación, error, autorización, doble solicitud, reinicio y carreras.
6. Solo tras contrato verificado: botón visible, confirmación, feedback exacto y pruebas E2E frontend; ninguna cancelación simulada.

## Gates de calidad y evidencia

- CI del PR: 215 unitarias existentes, 616 componentes tras I1, lint, builds y E2E con backend congelado por SHA; cifras sujetas a cambios verificables en futuros commits.
- Historias sintéticas/temporales de PostgreSQL en CI; no tocar Heroku ni Supabase durante tests.
- Revisar en escritorio exacto 1366×768 y 1920×1080, con y sin historial expandido.
- Verificar resultados completos, parciales, técnicos fallidos, sin permisos y recuperados.
- Conservar la diferencia entre `mm²` exactos y `m²` de visualización, y entre cobertura de piezas y aprovechamiento de material.
- Comparar snapshots antes/después de cada incremento; no afirmar los valores o interacciones no probados.
- Evidencia por bloque: hallazgo, archivo/commit, captura, test, resultado, dependencia y gate.
- Solicitar review antes de cerrar PR; la aprobación de SPEC no reemplaza pruebas.

## Registro inicial

- 2026-11-10: I1 implementado en PR [frontend #2](https://github.com/melendezzz26/newglass-frontend/pull/2) a partir de `main@816aeddb`. Se corrigieron discrepancias de test y lint mediante commits en esa misma rama. Al registrar este PLAN, el CI del último commit con E2E adaptado a la tabla compacta seguía pendiente de terminar; **no se declara I1 Verified**.
- I2, I3 e I4 no han comenzado. Solo trabajo frontend independiente y revisión de rutas backend de lectura.
