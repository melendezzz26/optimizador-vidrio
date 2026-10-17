# Sincronización UI con RBAC

> **Registro histórico.** Este documento conserva decisiones, cifras y límites de su entrega original. El estado vigente y los resultados integrados están en el [índice canónico](../README.md). Los logs supersedidos se consolidaron y las capturas enlazadas a integración son equivalentes de cobertura de una corrida posterior, no imágenes de este hito. Los originales se pueden recuperar desde `cbfa6ad` con el índice SHA256 de consolidación.

UI inicial: e42829d8b695d97434542205871703106ca646f9.
Base incorporada mediante merge normal: c4c5e5c (PR #50 RBAC).
No hay commits posteriores al merge RBAC en la base observada.
Core 3aca3c8 y Orders 2a5d835 se consultaron solo en lectura; no se integraron.

Conflicto único: OptimizationPage.test.jsx. Se conservaron todas las pruebas
funcionales UI de Quispe (selección, preparación, progreso, 2D/3D/raster, fixtures,
interacción y cleanup) y se incorporó withPermissions del sistema RBAC integrado.
GroupRasterInspection.test.jsx también usa el helper de permisos. No se conservan
mocks de la antigua página de rasterización dentro de pruebas del nuevo flujo FF;
la cobertura HU-015 se revisa por separado en la adaptación contractual siguiente.

Antes del commit de sincronización: unit 147 passed, component 379 passed (35 files),
lint/build exit 0. Conteos conservados en el resumen histórico de UI. Primer intento de component durante la resolución
vio marcadores de conflicto; los conteos finales de esa entrega se conservan en el resumen histórico RBAC del índice canónico.
No se oculta un fallo funcional ni se eliminan pruebas para lograr el resultado.

El diff entrante de RBAC contiene whitespace previo en backend/app/models.py,
backend/seed.py y dos fixtures backend. No se corrige código backend ajeno:
los blobs backend se conservan exactamente como integration. El diff propio UI
se revisa sin whitespace; git diff --check del working tree final es limpio.
No se creó migración ni se implementó backend. SPEC no se modifica.
