# SPEC-TA-036 — Saneamiento funcional y alineación de reglas de NewGlass

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | TA-036 — Saneamiento funcional y alineación de reglas |
| Rama de trabajo | `feature/TA-036-saneamiento-funcional` |
| Base local inspeccionada | `origin/integration/sprint-01` — `b7a0175522f5506c11a7782c3a4f8433dd61b4a6` |
| Responsable | Fabricio M. |
| Reviewer | Pendiente |
| Sprint | Sprint 1 |

La referencia remota no se pudo actualizar durante esta sesión: `git fetch origin` falló por falta de conexión a GitHub. El SHA indicado corresponde a la referencia `origin/integration/sprint-01` disponible localmente al iniciar el trabajo. Esta SPEC permanece Draft y no se marca Reviewed.

## 1. Contexto

NewGlass ya cuenta con contratos y flujos para pedidos, inventario, piezas personalizadas y trazabilidad de movimientos. La implementación evolucionó en trabajos paralelos y dejó decisiones de UI y reglas de dominio que no representan la operación acordada. TA-036 fija una línea base funcional común para que el trabajo posterior se integre desde `integration/sprint-01`.

La auditoría de esta SPEC se realizó sobre la base local indicada. Se revisaron `docs/specs/`, `docs/evidence/`, `docs/infrastructure/`, documentación de base de datos, módulos y pruebas relacionadas de backend/frontend y migraciones Alembic. No se encontró un backlog o archivo de refinamiento versionado en el repositorio.

## 2. Problema

Se identificaron discrepancias verificables entre las reglas requeridas y los contratos o comportamientos actuales:

1. **Geometría personalizada:** `CustomPieceEditor` y `segmentGeometry.js` admiten medidas por lado y reconstruyen `vertices_mm` ajustando direcciones desde el boceto. Las longitudes no identifican un polígono de forma unívoca y los ángulos reconstruidos pueden cambiar la forma dibujada. El contrato backend ya almacena polígonos mediante `vertices_mm` y valida su geometría.
2. **Baja de plancha:** `InventoryService.writeoff_plancha` crea un movimiento y cambia `estado` a falso para toda la fila. No reduce `cantidad`; `MovimientoInventario` y la migración HU-014 tampoco contienen cantidad afectada. Actualmente se impide una segunda baja manual para esa plancha.
3. **Estado de plancha con cantidad cero:** `update_plancha` admite cantidad cero sin poner `estado=false`. La evidencia de TA-011 registra una plancha con cantidad cero y estado Activo.
4. **Baja de retazo:** el caso actual marca el retazo como no disponible y conserva el registro, lo que coincide con la unidad concreta; falta alinear la baja parcial de planchas sin perder la semántica individual del retazo.
5. **Acciones de inventario:** `InventoryPage` muestra botones Activar/Desactivar junto a Historial, Editar y Dar de baja. La API PATCH genérica acepta `estado`; esa capacidad también puede tener consumidores fuera de la UI y requiere revisión antes de retirarla.
6. **Orden operacional de inventario:** las consultas de repositorio no declaran orden. Los listados administrativos incluyen filas disponibles y no disponibles sin priorización explícita para la operación.
7. **Editor de retazos:** `RegistrarRetazoForm` solicita coordenadas X/Y en filas de texto para polígonos; no reutiliza el lienzo `CustomPieceEditor` usado en Pedidos.
8. **Stock al registrar pedidos:** el caso `CreateOrderUseCase` valida cliente, catálogo y geometría, y persiste de forma transaccional; no consulta compatibilidad de stock. TA-036 debe preservar este comportamiento y evitar introducir ese bloqueo en POST.
9. **Orden de pedidos:** `OrdersRepository.list_orders` ordena únicamente por fecha descendente. No da prioridad a pedidos no cancelados y no tiene desempate explícito. Los estados persistidos válidos son `PENDIENTE`, `EN_OPTIMIZACION`, `OPTIMIZADO`, `CONFIRMADO` y `CANCELADO`.
10. **Rasterización:** la geometría del pedido ya viaja como `vertices_mm`; no se encontró implementación de rasterización en el esqueleto actual de Optimization. El contrato futuro debe consumir la geometría definitiva y no regenerarla desde longitudes.

## 3. Objetivo

Alinear especificaciones y contratos de NewGlass alrededor de la geometría canónica por vértices, la independencia entre registro de pedidos y disponibilidad actual de stock, las bajas con trazabilidad y cantidad, la prioridad operacional de inventario y pedidos, y la reutilización del editor geométrico.

## 4. Alcance

- Documentar las reglas transversales y sus impactos en módulos, contratos, migraciones, UI y pruebas.
- Definir la baja parcial transaccional de planchas agregadas y la baja de una unidad concreta de retazo.
- Definir la prioridad operacional de listados y mantener disponibles las vistas de historial/administración.
- Definir `vertices_mm` como geometría canónica para pieza personalizada y retazo poligonal, incluyendo el futuro consumo por rasterización.
- Definir el uso compartido del editor geométrico en registro de retazos.
- Mantener el registro de pedidos independiente de la existencia actual de stock y reservar la consulta compatible para Optimization.
- Ordenar pedidos no cancelados antes de cancelados, respetando los estados existentes.
- Incorporar pruebas de regresión y evidencia para los flujos afectados.

## 5. Fuera de alcance

- Implementar cualquiera de las tareas T02–T06 en este primer bloque documental.
- Crear estados nuevos de pedido o inventario.
- Eliminar endpoints o reglas genéricas de PATCH antes de identificar consumidores y definir su compatibilidad.
- Implementar algoritmos de optimización, nesting, rasterización, reserva o consumo de stock.
- Cambiar el contrato de catálogo tipo–espesor, clientes, autenticación o permisos no relacionados.
- Alterar secretos, Staging, Heroku, Supabase o bases de datos compartidas.
- Integrar, fusionar, hacer cherry-pick o modificar trabajo de ramas paralelas.
- Hacer push.

## 6. Decisiones y reglas funcionales

### 6.1 Geometría personalizada

- La geometría canónica de un polígono es la secuencia ordenada `vertices_mm`; el último vértice se conecta implícitamente con el primero y no hace falta duplicarlo al final.
- La forma final debe reconstruirse inequívocamente de esa secuencia. Longitudes y ángulos interiores son propiedades derivables; no se agregan columnas `angulo_1`, `angulo_2`, etc. sin una necesidad de dominio aprobada.
- El editor conserva los vértices dibujados y su escala a medidas físicas. Las longitudes y ángulos forman parte de la forma resultante mediante las coordenadas; no se reconstruye una forma alternativa usando solamente longitudes.
- Validación backend conserva convexidad, cierre, ausencia de autointersección, área positiva y límites numéricos. El escalado del lienzo transforma coordenadas sin cambiar la forma ni su orden.
- La rasterización futura consume los `vertices_mm` persistidos, sin reconstruir el polígono a partir de medidas de lados.

### 6.2 Registro de pedidos y compatibilidad de stock

- `POST /api/orders` registra un pedido válido aunque no haya stock compatible en ese momento.
- La ausencia de stock no produce rechazo del POST. El pedido conserva su estado inicial existente (`PENDIENTE`) y la transacción de pedido/piezas sigue siendo atómica.
- La selección o consulta de planchas y retazos compatibles se realiza en una etapa posterior del flujo de Optimization.
- Si hay una implementación útil de compatibilidad al iniciar esa etapa, se preserva y se ofrece como servicio/puerto reutilizable desde Optimization. No se duplica ni se elimina sin auditoría de consumidores.
- La validación de material contra el catálogo tipo–espesor continúa siendo independiente de la existencia de unidades en inventario.

### 6.3 Inventario: planchas agregadas

- Una fila de plancha representa unidades agregadas con `cantidad >= 0`.
- Una baja requiere una `cantidad_afectada` entera positiva que no exceda la cantidad disponible. Bajo bloqueo transaccional de la fila, se registra el movimiento y se reduce el saldo en la misma transacción.
- Ejemplo verificable: cantidad inicial 10, baja de 2, saldo final 8 y movimiento con `cantidad_afectada = 2`.
- Si el saldo llega a cero, la plancha queda automáticamente no disponible (`estado=false`). Si conserva saldo, la baja parcial no desactiva ni elimina el registro.
- No se permite una baja parcial cuando la plancha ya no está disponible o no tiene saldo positivo. Una operación fallida no deja movimiento ni cambio de saldo.
- La cantidad afectada se añade al contrato/modelo de movimiento de forma explícita. La decisión de esquema y migración debe preservar la lectura histórica: movimientos históricos sin cantidad conocida no deben recibir una cantidad ficticia.

### 6.4 Inventario: retazos unitarios

- Cada retazo representa una unidad concreta; su baja manual afecta exactamente una unidad (`cantidad_afectada = 1`).
- La baja y el movimiento se confirman en una transacción; el retazo pasa a no disponible automáticamente.
- El registro no se elimina físicamente. Se conserva accesible a historial y administración según permisos y contrato existentes.
- La vista operacional coloca primero retazos disponibles y relega los no disponibles; nunca vuelve a priorizar una unidad ya dada de baja.

### 6.5 Disponibilidad y acciones de UI

- La UI operacional de Inventario ofrece las acciones **Historial**, **Editar** y **Dar de baja** según permisos y estado.
- Se retiran del flujo visible los botones manuales **Activar** y **Desactivar** como acciones independientes.
- La baja controla la disponibilidad. La cantidad cero de plancha produce indisponibilidad automáticamente.
- Antes de cambiar o retirar PATCH genérico de estado, se revisan sus consumidores y se conserva si otros módulos lo necesitan. Su existencia no implica exponer el cambio manual de disponibilidad en esta pantalla.
- No se usa DELETE físico para bajas ni para ocultar registros con historial.

### 6.6 Orden operacional de inventario

- En Planchas, filas disponibles con cantidad positiva aparecen primero. Una baja parcial reduce cantidad y deja la fila en el grupo disponible mientras el saldo sea mayor que cero.
- En Retazos, filas disponibles aparecen primero; los dados de baja quedan detrás y permanecen consultables para historial/administración.
- El orden no debe reemplazar permisos ni filtros; cualquier orden explícito debe tener desempate determinista (fecha/ID) definido en T02.

### 6.7 Orden de pedidos

- Se usan exclusivamente los estados existentes: `PENDIENTE`, `EN_OPTIMIZACION`, `OPTIMIZADO`, `CONFIRMADO` y `CANCELADO`.
- Primero se muestran todos los pedidos distintos de `CANCELADO`; después, los cancelados.
- Dentro de cada grupo, los más recientes aparecen primero. Los empates usan un desempate determinista por identificador descendente.
- Aplicar filtros por estado no altera el orden definido dentro del resultado filtrado.

### 6.8 Registro de retazos poligonales

- El formulario de retazo usa el mismo lienzo/editor geométrico compartido que la pieza personalizada.
- Se reutilizan dibujo, vértices ordenados, cierre explícito, validación, escalado y geometría canónica. No se construye un segundo editor de coordenadas independiente.
- El payload de retazo persiste `geometria.type = POLIGONO_CONVEXO` y `geometria.vertices_mm`; el área sigue siendo derivada por backend.

## 7. Impacto por módulo

| Módulo/artefacto | Estado auditado | Alineación prevista |
|---|---|---|
| `backend/app/modules/inventory` — Application, Domain, Repository, API | La baja de plancha solo cambia estado; los movimientos no guardan cantidad afectada; transacción y bloqueo ya existen. Retazo se marca no disponible y se conserva. | Agregar cantidad afectada al contrato y persistencia; descontar saldo de plancha atómicamente; baja de retazo por una unidad; automatizar estado al saldo cero; ordenar consultas operacionales sin eliminar historial. |
| `backend/app/models.py`, Alembic HU-014 y pruebas | Plancha tiene cantidad no negativa; movimiento no tiene cantidad; HU-014 crea la tabla de movimientos. | Diseñar migración compatible con movimientos históricos y actualizar contratos ORM, tests de migración y restricciones según decisión final. |
| `frontend/src/features/inventory` | UI muestra Activar/Desactivar además de Historial, Editar y Dar de baja; formularios de retazo piden coordenadas X/Y. | Quitar toggles manuales; mostrar cantidad y resultado de baja parcial; priorizar disponibilidad; integrar editor geométrico compartido para polígonos. |
| `backend/app/modules/orders` | `CreateOrderUseCase` comprueba cliente, catálogo y geometría; no comprueba stock. Repositorio ordena fecha descendente. | Mantener POST sin precondición de stock; aplicar orden estado/fecha/ID al listado. |
| `frontend/src/features/orders` | El editor mantiene boceto y longitudes; reconstruye vértices usando longitudes y direcciones ajustadas. | Hacer que las coordenadas finales medidas sean canónicas e inequívocas; preservar validaciones y enviar/persistir la geometría final. |
| `backend/app/modules/optimization` y rasterización futura | Esqueleto de módulo sin flujo implementado encontrado. | Consumir `vertices_mm` definitivos; reutilizar después el contrato/servicio de compatibilidad de inventario sin trasladar el bloqueo a Orders. |
| Documentación/evidencia | SPEC-TA-011 describe cambio de estado, HU-014 difiere compatibilidad elegible a futuro; evidencia TA-011 incluye activación y plancha con cantidad cero Activo y anota que no había editor visual reutilizable para retazos. | Alinear contratos existentes con esta SPEC y registrar evidencia futura sin reescribir resultados históricos. |

## 8. Impacto sobre ramas paralelas

Esta tabla registra coordinación funcional; no autoriza ni realiza cambios en ramas ajenas.

| Responsable / trabajo paralelo | Puede continuar | Alineación requerida para integración |
|---|---|---|
| **Fabricio Aguilar** | Figuras estándar y partes de raster independientes de geometría personalizada. | Pieza personalizada toma `vertices_mm` y ángulos definidos por la geometría final; no debe aceptar una reconstrucción unívoca desde longitudes por sí solas. Raster independiente debe recibir geometría final basada en vértices. |
| **Luis I. + Andro Quispe** | Consulta y compatibilidad de stock que sean reutilizables. | No bloquear `POST` de pedidos por falta de stock. La consulta compatible queda disponible para reutilización posterior desde Optimization, con contrato desacoplado de persistencia/HTTP según corresponda. |
| **Fabricio M.** | Saneamiento transversal de esta línea base. | A cargo de Inventario, baja parcial, retazos, ordenamiento e integración/alineación del editor. |

El equipo deberá integrar estas reglas desde `integration/sprint-01` al retomar cada rama. TA-036 no integra, fusiona ni copia trabajo paralelo.

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación/decisión de diseño |
|---|---|
| La migración de movimientos puede inventar cantidades históricas si usa un default semántico incorrecto. | Mantener cantidad desconocida para historia previa o documentar una política aprobada; probar upgrade/downgrade y preservar trazabilidad antes de implementar. |
| Concurrencia entre bajas parciales puede producir saldo negativo o movimientos duplicados. | Bloquear plancha, validar saldo dentro de la misma transacción y probar carreras/rollback; constraint de BD como defensa adicional si aplica. |
| Cambiar la semántica de `estado` puede afectar consultas administrativas o consumidores futuros. | Mantener la lectura administrativa y revisar usos de PATCH antes de modificar el endpoint; separar elegibilidad operacional de historial. |
| Cambiar el editor de medidas puede afectar UX, escalado, cierre o validación geométrica. | Conservar pruebas de convexidad, cierre, auto-intersección, escala y payload; validar valores degenerados y orden de vértices. |
| Diferentes ramas podrían integrar contratos incompatibles de geometría o inventario. | Usar esta SPEC como línea base y exigir alineación desde `integration/sprint-01` en cada integración. |
| El orden de estado puede ser inconsistente entre API y frontend. | Definir una única regla determinista y probar listados paginados/filtrados con empates. |
| La referencia remota de Sprint 01 pudo avanzar mientras no hubo conectividad. | Confirmar fetch/SHA antes de iniciar implementación en T02; rebasar/recrear la base si cambió, sin incorporar ramas paralelas. |

## 10. Dependencias

- Contratos vigentes de Inventory, Orders, HU-007 y HU-014, incluida la decisión de migración para cantidad afectada.
- Catálogo tipo–espesor TA-013 para validar el material de pedidos, separado de existencia de stock.
- Migraciones Alembic y PostgreSQL temporal aislado para verificar cambios de esquema en T02/T06.
- Componentes de UI compartidos y editor actual de `frontend/src/features/orders`.
- Alineación de las ramas paralelas indicada en la matriz antes de sus integraciones.
- Actualización de `origin/integration/sprint-01` antes de iniciar implementación.

## 11. Tareas

| Tarea | Entregable |
|---|---|
| **T01 — Alinear contratos y especificaciones** | Actualizar SPEC/contratos/evidencia aplicable; precisar cantidad afectada y compatibilidad entre API, dominio, UI y base de datos. No marcar las especificaciones como Reviewed sin revisión explícita. |
| **T02 — Corregir baja y ordenamiento de inventario** | Baja parcial de plancha con movimiento de cantidad y transacción; saldo cero no disponible; baja unitaria de retazo; sin DELETE; prioridad operacional; quitar Activar/Desactivar manual de UI; historial/admin conservados. |
| **T03 — Alinear geometría personalizada y editor reutilizable** | Coordenadas finales canónicas `vertices_mm`; reutilizar lienzo/editor para alta poligonal de retazo; mantener cierre, escalado, convexidad y ausencia de autointersección. |
| **T04 — Corregir ubicación de validación de stock** | Confirmar que POST de pedido no consulta ni exige stock; preservar o extraer compatibilidad reusable para Optimization sin cambiar reglas de catálogo. |
| **T05 — Corregir ordenamiento de pedidos** | No cancelados antes que cancelados, más recientes primero por grupo, desempate determinista y estados existentes únicamente. |
| **T06 — Regresión transversal y evidencia** | Ejecutar pruebas de backend, frontend, migración y flujos afectados; documentar solo resultados observados y evidencia reproducible. |

## 12. Criterios de aceptación verificables

| ID | Criterio |
|---|---|
| CA-01 | La geometría persistida de cada polígono se reconstruye sin ambigüedad desde `vertices_mm`; no existe una ruta de guardado o rasterización que derive la forma usando solo longitudes. |
| CA-02 | El editor valida cierre, convexidad, ausencia de autointersección y escala; dos figuras con mismas longitudes y distintos ángulos conservan vértices/formas distintas. |
| CA-03 | Dar de baja 2 unidades de una plancha con cantidad 10 produce saldo 8 y movimiento con `cantidad_afectada=2`; no se crea DELETE ni desaparece la fila disponible. |
| CA-04 | Una baja lleva cantidad de plancha a cero solo si afecta el saldo restante y en ese caso deja `estado=false`; cualquier error transaccional revierte simultáneamente movimiento y saldo. |
| CA-05 | La baja de retazo registra cantidad afectada 1, deja `estado=false` y conserva la fila y su historial. |
| CA-06 | En la UI operacional de inventario las acciones de gestión disponibles son Historial, Editar y Dar de baja; Activar/Desactivar no aparecen como acción independiente. La API genérica solo cambia después de documentar sus consumidores. |
| CA-07 | El listado operacional ordena planchas con estado disponible y saldo positivo antes de las demás, y retazos disponibles antes de los dados de baja; los registros históricos siguen accesibles. |
| CA-08 | Se puede registrar un pedido válido cuando el inventario compatible está vacío; la solicitud no invoca consulta de stock y conserva la validación de catálogo tipo–espesor. |
| CA-09 | La compatibilidad de stock útil queda invocable desde Optimization sin dependencia innecesaria de los esquemas HTTP/ORM de Orders. |
| CA-10 | Los polígonos de retazo se dibujan en el editor compartido, se cierran y validan en el mismo flujo de pieza personalizada, y se envían como `vertices_mm`. |
| CA-11 | Los pedidos se ordenan en grupo no cancelado y grupo `CANCELADO`, con fecha descendente e ID descendente en empates, tanto en listados sin filtro como filtrados. |
| CA-12 | Migraciones y pruebas conservan filas, movimientos e historial existente; cualquier historia cuya cantidad no sea conocida permanece explícitamente desconocida, sin imputación silenciosa. |
| CA-13 | La evidencia de T06 incluye SHA, comandos/resultados ejecutados y casos funcionales; no contiene secretos ni afirma pruebas no realizadas. |

## 13. Plan de pruebas

- **Geometría/backend:** vértices ordenados, cierre implícito, formas con mismas longitudes y ángulos diferentes, polígono convexo válido, cóncavo, autointersección, vértices duplicados, área nula y coordenadas fuera de rango.
- **Geometría/frontend:** dibujo, undo/reinicio, escalado responsive, cierre, medidas y ángulos resultantes, edición/reapertura si aplica, payload `vertices_mm`, y reutilización del mismo editor en retazos.
- **Inventario unitario/API:** baja parcial, baja exacta del saldo, exceso, cantidad cero, recurso no disponible, usuario/fecha de movimiento, retazo unitario, sin reactivación accidental, permisos y respuestas de conflicto.
- **Transacción/concurrencia:** movimiento y actualización se confirman o revierten juntos; bajas concurrentes no exceden saldo y cada movimiento refleja la cantidad realmente descontada.
- **Persistencia/migración:** upgrade desde HU-014 con historial existente, compatibilidad PostgreSQL, restricciones, valores históricos sin imputar, rollback seguro y downgrade bloqueado o seguro según política aprobada.
- **Inventario frontend:** sin toggles manuales; acciones por permiso; lista priorizada; saldo visible tras baja parcial; retazo no disponible relega a historial/admin; estados vacíos/error y filtros conservados.
- **Orders:** POST exitoso sin stock compatible y sin llamada de compatibilidad; rechazo de catálogo inválido sigue intacto; listado ordenado en estados reales, empate de fecha, filtros y paginación.
- **Regresión transversal:** suites relacionadas de Inventory, Orders, CustomPieceEditor, geometría, migraciones y E2E; revisar evidencia sin acceder/modificar servicios Staging.

## 14. Evidencia de auditoría y archivos base consultados

La lista identifica los puntos de auditoría principales; la búsqueda completa cubrió los directorios `docs/specs/`, `docs/evidence/`, `docs/infrastructure/`, `docs/database/`, `backend/app/modules/{inventory,orders,optimization}`, `frontend/src/features/{inventory,orders}`, `backend/alembic/versions/` y las pruebas relacionadas.

- Especificaciones: `SPEC-TA-003-api-inventario.md`, `SPEC-TA-011-integracion-inventario.md`, `SPEC-HU-004-registrar-plancha.md`, `SPEC-HU-005-registrar-retazo.md`, `SPEC-HU-006-registrar-pedido.md`, `SPEC-HU-007-pieza-personalizada.md`, `SPEC-HU-007-T02-medidas-reales.md`, `SPEC-HU-007-T03-validar-poligono-convexo.md`, `SPEC-HU-013-gestion-pedidos.md`, `SPEC-HU-014-trazabilidad-inventario.md`, `SPEC-TA-013-datos-base.md`.
- Base de datos/migraciones: `docs/database/convergencia-orders-multimaterial.md`, `docs/database/convergencia-v1-1.md`, `backend/app/models.py`, `backend/alembic/versions/fa014e1a2b3c_hu014_movimientos_inventario.py`, migraciones HU-006, TA-013, R1–R4.
- Backend: Inventory `domain/writeoff.py`, `application/{service.py,dto.py,ports.py}`, `infrastructure/repository.py`, `presentation/{router.py,schemas.py}`; Orders `application/use_cases.py`, `infrastructure/repositories.py`, `presentation/router.py`, `domain/geometry.py`; módulos actuales de Optimization.
- Frontend: `InventoryPage.jsx`, `WriteoffDialog.jsx`, `RegistrarRetazoForm.jsx`, `inventoryApi.js`, `CustomPieceEditor.jsx`, `segmentGeometry.js`, `geometryScaling.js`, `convexityValidation.js`, `NuevoPedido.jsx`, `GestionPedidos.jsx`.
- Evidencia: `docs/evidence/sprint-01/TA-011/{prueba-funcional.md,operaciones-api-bd.md}`, `docs/evidence/sprint-01/HU-005/{formulario-retazo.md,prueba-funcional.md}`, evidencias HU-007 y HU-014.
- Pruebas consultadas: tests API/unitarios/integración de Inventory y Orders, `CustomPieceEditor.test.jsx`, pruebas de geometría, E2E HU-007 y E2E HU-014.

## Historial

- **Draft — 12/10/2026:** Línea base documental creada a partir de la auditoría local de `origin/integration/sprint-01`. Sin implementación de T02–T06. Reviewer pendiente. No se obtuvo conexión para actualizar el remoto.

## 15. Implementación T02–T05 — 12/10/2026

Se implementan T02–T05 en la rama indicada, después de auditar en lectura los tips paralelos `46d801e` (HU-008) y `5c58321` (TA-005/TA-006). La SPEC continúa Draft, con reviewer pendiente. El detalle está en `docs/evidence/sprint-01/TA-036/auditoria-ramas.md`.

- **Inventario:** POST de plancha exige `cantidad_afectada` entera estricta positiva. La fila se bloquea, se valida disponibilidad/saldo, se registra cantidad y se descuenta en una transacción. Admite varias bajas mientras quede saldo. Respuesta: `estado`, `cantidad` restante confirmada y `movimiento`. Retazo conserva request sin cantidad editable; el movimiento registra 1. La UI conserva saldo incluso si falla el GET posterior; solo ofrece Historial, Editar y Dar de baja. PATCH genérico se conserva por compatibilidad administrativa; cantidad cero fuerza indisponibilidad y permanece la protección contra reactivación tras baja total. Los listados priorizan disponibilidad, luego fecha descendente e ID descendente, sin ocultar historia ni cambiar filtros.
- **Migración:** `ta036a1b2c3d`, hija directa de `fa014e1a2b3c`, agrega columna nullable sin default. Planchas históricas y eventos de optimización desconocidos permanecen NULL; solo bajas manuales históricas de retazo reciben 1 porque representan unidades concretas. Agrega restricciones de cantidad positiva y retazo unitario y retira la unicidad manual de plancha. Conserva la unicidad de retazo. Downgrade bloqueado bajo lock si perdería cantidades conocidas o múltiples bajas; se prueba también downgrade seguro de base vacía. No se modifica historia ni se usa stamp.
- **Pedidos:** POST ya estaba desacoplado de stock y se preserva, con regresión API sobre inventario vacío. Listado ordenado en backend antes de paginar: no CANCELADO, CANCELADO, fecha DESC, ID DESC; se mantienen filtros.
- **Geometría y retazo:** la escala transforma uniformemente las coordenadas del contorno; cambiar una longitud recalcula todos los lados conservando ángulos. Para cambiar la disposición se corrige/redibuja el contorno. Se retira el ajuste numérico de direcciones desde longitudes independientes: medidas incompatibles con un boceto previo se rechazan y pueden corregirse eligiendo una escala. Funciones puras derivan longitudes, ángulos, finitud y degeneración. No hay columnas de ángulos. El retazo reutiliza `CustomPieceEditor`, incluida edición de geometría previa, y recibe solo el resultado válido actual: reiniciar/incompletar invalida el payload anterior. Persiste el formato existente `geometria = {type: POLIGONO_CONVEXO, vertices_mm}`.
- **Raster:** la base TA-036 no contiene rasterizador; la rama de Aguilar ya acepta `rasterize_geometry(geometria, resolution_mm)` y `rasterize_convex_polygon(vertices_mm, resolution_mm)`. El consumidor posterior debe pasar la geometría persistida final, sin inferirla de lados o guardar ángulos aparte. No es necesario añadir otro algoritmo ni commit de raster.

Pendiente de coordinación: HU-008 conservará su puerto de consulta y lo conectará al futuro flujo de Optimization; Aguilar conectará los vértices persistidos finales. TA-036 no integra estas ramas. Las pruebas y el inventario completo de archivos se registran en la evidencia de ejecución.

## 16. Correctivo de regresión previo a T06

Se separan dos garantías de `cantidad_afectada`:

- **Integridad histórica (CA-12):** la columna nullable preserva cantidades desconocidas sin imputarlas. `ta036a1b2c3d` y su padre `fa014e1a2b3c` no se alteran. El CHECK `cantidad_afectada IS NULL OR cantidad_afectada > 0` rechaza valores conocidos no positivos; el CHECK unitario limita cantidades conocidas de retazo a 1.
- **Nuevas bajas de la aplicación (6.3/6.4):** plancha exige entero positivo y saldo suficiente; retazo registra exactamente 1. Request, dominio y servicio mantienen sus validaciones. El escritor común de movimientos del repositorio también rechaza NULL, booleanos, fracciones, valores no positivos y retazo distinto de 1 antes de insertar, incluso en llamadas internas.

Esta SPEC no exige distinguir temporalmente inserciones SQL directas nuevas y filas históricas mediante una restricción de BD. NULL permanece permitido por compatibilidad histórica a nivel de esquema, sin una garantía temporal en SQL; su uso para nuevas bajas de la aplicación está prohibido y validado. No se agregan triggers, columnas legacy ni fechas/cutoffs artificiales. Las nuevas rutas de escritura se verifican contra PostgreSQL aislado y HTTP real, y se conserva la lectura del histórico NULL.

Se restaura cobertura vigente de preview, escalado, extremos numéricos, interacción de ambos SVG y flujos actuales de inventario. Los casos que exigían resolver una forma desde lados independientes o usar Activar/Desactivar permanecen retirados. La matriz anterior→equivalente y los resultados del correctivo se registran en `docs/evidence/sprint-01/TA-036/correctivo-regresion.md`. Este correctivo no ejecuta T06 ni cambia el estado Draft/reviewer pendiente.

## 17. T06 — regresión transversal, 13/10/2026

T06 se ejecutó sobre `0e67631`: backend completo 1330 passed; frontend unit
103 passed; component 211 passed; lint/build correctos. E2E completo descubrió
32 casos: 31 passed, cero fallos y un skip móvil conocido de HU-014 por baja
de un fixture compartido. Alembic conserva un único head `ta036a1b2c3d`, padre
`fa014e1a2b3c`. No se modificó producción ni migraciones durante este cierre.

La implementación del alcance TA-036 está técnicamente completa y pendiente
de revisión formal. La matriz de aceptación registra CA-01–CA-08 y
CA-10–CA-13 PASS; CA-09 PARTIAL porque conectar la consulta compatible desde
Optimization pertenece a la integración posterior de HU-008. No se integra
trabajo ajeno para completar ese punto. Los límites, comandos y evidencias
están consolidados en `docs/evidence/sprint-01/TA-036/README.md`.

**Estado formal conservado: Draft. Reviewer: Pendiente.** La conclusión
READY FOR HUMAN REVIEW no representa aprobación ni transición a Verified.
La revisión humana decidirá los pasos Reviewed/Implemented y, posteriormente,
Verified conforme al flujo establecido.
