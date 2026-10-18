# Sprint 1 — cierre post-revisión

Auditoría y validación: 18/10/2026. Base local: `2b21562`.

## Alcance y trazabilidad

Se auditó primero y se corrigieron solo pendientes. No se modificaron arquitectura,
First Fit, RBAC, Supabase, migraciones, persistencia de aplicación ni coordenadas
del corte. No se hizo deploy, push ni PR. Las pruebas usan PostgreSQL temporal local;
las consultas sobre la BD de prueba configurada fueron de solo lectura y terminaron
con rollback. No se exportaron clientes, credenciales ni evidencia masiva.

Se consultaron el [frontend desplegado](https://melendezzz26.github.io/optimizador-vidrio/)
y el [contrato público del backend](https://newglass-api-staging-5f52e8e9b00c.herokuapp.com/openapi.json).
Bundle observado: `assets/index-CHQPF7Oa.js`, SHA-256
`a4192d1ee6aa9b9ace880d842591e81046991dbb567b206252f25d98f445049e`.
El bundle confirma la rama de edición que llama a `PUT /api/orders/{id}`, la
deduplicación por ID, el texto «Documento exacto», la vista dimensional pendiente y
la ausencia del nuevo texto explicativo. El contrato desplegado expone GET, PUT y
DELETE para el detalle de pedidos. No se hicieron escrituras en staging ni una
edición autenticada sobre ese entorno; las regresiones funcionales corresponden
al código local actual contra la API y PostgreSQL temporales.

## Diagnóstico previo a los cambios

| Observación | Estado inicial | Evidencia y causa |
| --- | --- | --- |
| 1. Editar pedidos y posibles duplicados | **Ya está corregido** en el flujo vigente | `FormularioPedido` diferencia crear/editar; `ordersApi.updateOrder` usa PUT con el ID existente. El repositorio conserva la cabecera y reemplaza sus piezas en una transacción. La consulta de listado no une piezas y no multiplica filas. `pendingOrdersSource` deduplica por `id_pedido`, incluso entre páginas. No se encontró un bug que justificara cambiar persistencia. |
| 2. Actualización progresiva del polígono | **Sigue ocurriendo** | `buildConstrainedGeometry` devolvía vértices nulos ante cualquier lado faltante; la UI reutilizaba únicamente el boceto. Además, cerrar el boceto mostraba «Geometría calculada» antes de tener medidas. |
| 3. Propósito del boceto | **Sigue ocurriendo** | Las instrucciones de dibujo no explicaban de forma directa la relación entre boceto y geometría ajustada. |
| 4. Búsqueda de clientes | **Sigue ocurriendo** | El selector mostraba «Documento exacto». La búsqueda por nombre/documento ya funcionaba y se conserva. |
| 5. Vista 3D | **Parcialmente corregido** | Órbita, pan, zoom, Z, teclado y vistas predefinidas ya estaban implementados. Había dimensiones de la plancha, pero solo IDs en las piezas. Una guía de dimensión omitía recibir la cámara y no seguía elevación/pan. |
| 6. Consistencia visual | **Parcialmente corregido** | Usuarios, Pedidos, Inventario y Optimización ya usan AppShell, PageLayout, tokens, botones y estados compartidos. Los modales tienen su composición propia con foco y Escape. El editor de polígonos conservaba colores, fuente y controles propios. |

### Revisión de datos históricos

El usuario aclaró que `backend/.env` apunta a su **BD de prueba**, y autorizó su
consulta. No está disponible la variable de conexión de staging.

- BD de prueba: 25 pedidos y 25 IDs distintos; ninguno pendiente.
- Estados: 15 cancelados, 5 en optimización, 4 optimizados y 1 confirmado.
- No se encontraron grupos de pedidos del mismo cliente con contenido idéntico
  de piezas, tanto entre pendientes como en el historial completo.
- La comparación incluyó material, espesor, forma, cantidad, geometría y dimensiones,
  excluyendo los IDs de piezas. Coincidencias de nombre de cliente por sí solas no
  demostrarían duplicación; pedidos con IDs distintos pueden ser legítimos.
- No hay evidencia para atribuir duplicados históricos a una edición. Tampoco se
  puede extrapolar el resultado de la BD de prueba a los datos de staging.

## Correcciones aplicadas

- Se reconstruye inmediatamente una vista provisional con medidas válidas y
  proporciones del boceto para los lados pendientes. Se reutiliza el solucionador
  existente, incluida la validación convexa y las restricciones angulares.
- El boceto permanece como referencia tenue; los segmentos medidos se resaltan y
  muestran su valor en mm. El estado accesible informa cuántas medidas hay.
- Las estimaciones se devuelven en `preview_vertices_mm`; nunca se publican como
  `vertices_mm`, no rellenan campos pendientes ni habilitan guardar. Si una
  estimación no admite una reconstrucción válida, se conserva el boceto y el
  feedback de medidas. Con todas las medidas se ejecuta inmediatamente el cálculo
  exacto y las validaciones originales. Los lados aún libres impiden afirmar una
  solución exacta a partir de las restricciones actuales.
- Se añadió: «Dibuja la forma aproximada de la pieza. Luego ajusta sus medidas y
  ángulos para definirla con precisión.»
- Búsqueda: «Buscar por nombre, DNI o RUC» y opción «DNI o RUC». Se mantienen los
  modos y parámetros HTTP existentes.
- Las piezas 3D muestran dimensiones en mm en el dibujo y la leyenda accesible.
  Se toman de la geometría original del pedido/unidad, para que la rotación del
  corte no cambie las medidas informadas. Los círculos muestran diámetro; los
  polígonos indican ancho × alto de su envolvente original. Se conserva mm como
  única unidad y se corrige la cámara de la segunda guía de dimensión.
- El editor reutiliza los tokens de fuente, colores, foco, altura mínima de
  controles y radios compartidos. Cada módulo conserva su estructura funcional.

## Archivos modificados y regresiones

Rutas relativas a la raíz del repositorio:

| Archivo | Cambio |
| --- | --- |
| `frontend/src/features/orders/constrainedGeometry.js` | Vista provisional separada de geometría guardable. |
| `frontend/src/features/orders/CustomPieceEditor.jsx` | Referencia, medidas, copy y estados progresivos. |
| `frontend/src/features/orders/CustomPieceEditor.css` | Tokens compartidos, controles accesibles y referencia visual. |
| `frontend/src/features/orders/OrderClientSelector.jsx` | Texto de búsqueda. |
| `frontend/src/features/optimization/PlacementScene3D.jsx` | Dimensiones por pieza y corrección de guía de cámara. |
| `backend/tests/api/orders/test_orders_api.py` | Tres PUT conservan ID, cliente, fecha, total de pedidos y número de piezas. |
| `frontend/tests/unit/constrainedGeometry.test.js` | Vista parcial convexa, lados medidos y ángulo fijado; sin geometría guardable estimada. |
| `frontend/src/features/orders/__tests__/ConstrainedPieceEditor.test.jsx` | Actualización de contorno antes del último lado, referencia estable e invalidación al borrar una medida. |
| `frontend/src/features/orders/__tests__/CustomPieceEditor.test.jsx` | Expectativas de estado provisional actualizadas. |
| `frontend/src/features/orders/__tests__/OrderClientSelector.test.jsx` | Copy claro; ambas búsquedas conservan parámetros y selección por teclado. |
| `frontend/src/features/optimization/__tests__/PlacementScene3D.test.jsx` | Dimensiones de rectángulos, polígonos y círculos; rotación, ambas guías e inmutabilidad. |
| `frontend/src/features/optimization/__tests__/PendingOrdersSource.test.jsx` | Deduplicación entre páginas y conservación de pedidos legítimos del mismo cliente con IDs distintos. |
| `frontend/tests/e2e/s1-post-review.spec.js` | Tres ediciones → mismo ID → cálculo real → dimensiones 3D; dibujo → cambios parciales → geometría válida, en escritorio y móvil. |
| `docs/reviews/S1-post-review.md` | Diagnóstico, causas, alcance y resultados. |

## Validación final

| Comando | Resultado |
| --- | --- |
| `venv/Scripts/python.exe -m pytest tests/api/orders tests/unit/modules/orders tests/integration/modules/orders -q` (backend) | **151 passed**. |
| `npm run test:unit` | **160 passed**. |
| `npm run test:component` | **471 passed**, 42 archivos; incluye Orders, geometría, clientes y 3D. |
| `npm run lint` | **OK**. |
| `npm run build` | **OK**. |
| `npx playwright test tests/e2e/s1-post-review.spec.js --workers=1 --reporter=list` | **4 passed**, escritorio y móvil. |
| `git diff --check` | **OK**. |

La primera ampliación del E2E hasta ejecutar el cálculo encontró `CONFIG_CONFLICT`:
el servidor temporal de Orders no carga configuración de optimización por defecto.
El test ahora invoca el helper existente `tests.optimization_e2e_data`, restringido
a la BD temporal local, para cargar la configuración aprobada. La ejecución final
pasó sin modificar código de aplicación ni la configuración de ninguna BD compartida.

Avisos no bloqueantes: deprecación existente Starlette/httpx y conflicto de variables
de color del runner. No hubo fallos finales. Los cambios quedan en un commit local;
no están desplegados.
