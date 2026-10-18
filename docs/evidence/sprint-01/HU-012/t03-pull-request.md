# HU-012 T03 — Asociar cliente al registro de pedido

Base: `integration/sprint-01`
Head: `feature/HU-012-T03-asociar-cliente-pedido`

Implementa HU-012 T03 para asociar clientes al flujo de registro de pedidos.
Todo pedido nuevo exige seleccionar un cliente y persiste/devuelve `id_cliente`;
los pedidos históricos con NULL siguen admitidos en consulta y edición de piezas.

Incluye búsqueda por nombre/documento, registro contextual con selección automática,
cambio de cliente conservando piezas, validación de referencia, clientes activos e
inactivos, permisos existentes y regresiones HU-006 multimaterial/HU-007.

Integra `bf6ca1a` de sprint-01 mediante merge `5103734`. Se trasladó el selector al
FormularioPedido canónico de HU-013, accesible desde GestionPedidos, conservando el
wrapper NuevoPedido. POST y PUT tienen esquemas separados para que la obligatoriedad
de cliente al crear no bloquee editar piezas históricas ni permita reasignación
silenciosa. Se preservaron las pruebas recibidas y las de T03.

Validación final sobre PostgreSQL temporal, sin Supabase:

| Verificación | Resultado |
|---|---|
| Backend focalizado ampliado | 395 passed; 1 warning; 227.82 s |
| Backend completo | 1116 collected/passed, 0 failed/errors/skipped; 1 warning; 332.86 s |
| Frontend unit | 84 passed |
| Frontend component | 148 passed, 17 archivos |
| Lint / build | Ambos exit 0; 1938 módulos |
| E2E T03 | 4 passed, escritorio/móvil |
| E2E completo | 28 passed |
| Alembic | Un único head ef6564220e70; sin migraciones nuevas |
| Revisión visual | Usuario confirmó sin observaciones; sin capturas automáticas |

La primera pasada de componentes tuvo cinco fallos de expectativas/textos, documentados
y corregidos antes de la ejecución final. Se mantiene la advertencia Starlette/httpx.
No se eliminaron pruebas ni se usaron skips/xfail. Estado Verified pendiente del proceso
formal de revisión.

Evidencia: [cierre T03](t03-asociar-cliente-pedido.md),
[resultados exactos](test-results/t03/post-integration/summary.json),
[readiness](readiness-integration-sprint-01.md).

Riesgos: consumidores POST anteriores deben incluir cliente; consulta T02 sin paginación;
cliente inactivo permitido por contrato vigente. Para despliegue público, integración
está **NO LISTO** hasta resolver CORS local, exposición de `/db-test` y validar la
configuración/runtime/esquema del destino. Esos cambios quedan fuera de este PR.

No se modificó main ni integración directamente, no se desplegó ni se aplicaron
migraciones remotas. **No hacer merge automático de este PR.**
