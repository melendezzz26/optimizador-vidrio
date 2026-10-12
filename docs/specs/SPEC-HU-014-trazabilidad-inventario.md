# SPEC-HU-014 — Baja y trazabilidad de inventario

## Información general

| Campo | Valor |
|---|---|
| Estado | Implemented |
| PBI relacionado | HU-014 — Baja y trazabilidad de inventario |
| Épica | EP-001 — Inventario |
| Rama de trabajo | `feature/HU-014-trazabilidad-inventario` |
| Dependencias | HU-004, HU-005, TA-003, TA-011, TA-013, HU-012 Clientes |
| Revisión funcional | Aprobada — 09/10/2026 |

> La implementación de HU-014 está completada y documentada aquí. La SPEC aún no está Verified: falta revisión final por otro integrante y el cierre formal del PR.

## 1. Objetivo

Permitir que personal autorizado dé de baja lógicamente una plancha o un retazo, registre de forma auditable el evento y consulte el historial asociado, preservando el recurso original y evitando que una baja manual se confunda con un consumo por optimización.

## 2. Contexto

Inventory registra, lista y edita planchas y retazos mediante FastAPI, capas de aplicación/repositorio y SQLAlchemy. HU-014 añade persistencia de movimientos, baja lógica e historial. Los GET administrativos siguen incluyendo materiales activos e inactivos; `estado` por sí solo no demuestra que exista una baja trazable.

El ADR-002 establece que las bajas no deben borrar físicamente el material, deben preservar material, tipo de evento, motivo, observación, usuario y fecha, y que una baja manual es distinta del consumo por optimización. La evolución BD v1.3 propone `MOVIMIENTO_INVENTARIO` y deja a esta SPEC precisar la disponibilidad sin sobrecargar `estado` con significados distintos.

### 2.1 Línea base previa a HU-014

- `Plancha.estado` y `Retazo.estado` son booleanos; PATCH permite cambiar estado cuando no existe baja manual.
- Los GET administrativos incluyen registros con ambos valores de `estado`; no son contratos de stock disponible.
- Una plancha puede tener `cantidad = 0`.
- Al inicio de HU-014 no existían el ORM, la migración ni las operaciones de movimientos. Este dato describe la línea base histórica, no el estado actual.
- El actor debe provenir de la identidad autenticada; el cliente no decide el identificador ni la fecha del movimiento.
- Existe `MaterialUtilizado` con XOR entre plancha y retazo y FK a ejecución. Es un registro de materiales usados por ejecución, no un historial de bajas manuales, por lo que no sustituye a `MOVIMIENTO_INVENTARIO`.

### 2.2 Implementación vigente

La migración `fa014e1a2b3c` crea `movimientos_inventario` (`down_revision = ef6564220e70`). El ORM, repositorio, servicio, rutas y contratos están implementados. La baja manual bloquea la fila del recurso con `SELECT ... FOR UPDATE`, comprueba el historial, inserta el movimiento y establece `estado=false` dentro de una transacción con un único commit. La baja previa es la fuente de verdad histórica; un recurso inactivo sin baja previa también puede recibir una baja, conservando `estado=false`. La reactivación con historial de baja devuelve conflicto.

La interfaz de Inventory incluye formularios de baja e historial para planchas y retazos. Hay pruebas unitarias, de integración PostgreSQL, API, componentes y E2E. La cobertura detallada y las limitaciones de disponibilidad se registran en los criterios de aceptación y en la evidencia HU-014.

## 3. Actor principal

**Almacenero**. El Administrador también puede ejecutar la operación por sus permisos actuales de gestión de inventario. Administrador, Almacenero y Operario pueden consultar stock según la matriz vigente; el historial HU-014 usa el permiso `CONSULTAR_STOCK`.

## 4. Precondiciones

- El actor está autenticado y conserva una sesión válida.
- Para dar de baja, posee `GESTIONAR_PLANCHAS` o `GESTIONAR_RETAZOS`, según el recurso.
- Para consultar historial, posee `CONSULTAR_STOCK`.
- El recurso de inventario existe y es identificable por su tipo e ID.
- Para registrar una baja, se recibe un motivo válido y el evento corresponde a uno de los cuatro tipos manuales habilitados.
- La base de datos y el servicio de Inventory están disponibles; el registro del movimiento y su aplicación sobre disponibilidad se confirman en una única transacción.

## 5. Alcance por tarea

### T01 — Diseño y persistencia de trazabilidad (implementado)

- Se definió y persistió el vínculo exclusivo del movimiento a plancha o retazo.
- Se fijaron los cuatro eventos manuales y se separaron de `CONSUMO_OPTIMIZACION`.
- Se implementaron actor autenticado, timestamp de servidor, motivo y observación opcional.
- Se estableció que el movimiento acredita la baja y que `estado=false` aislado no la acredita.
- Se implementaron XOR, FKs, restricción de evento, motivo no vacío e índices parciales únicos para baja manual.

### T02 — Implementar baja lógica (implementado)

- Se implementó la baja de plancha y retazo con los cuatro eventos manuales, motivo obligatorio y observación opcional.
- El actor procede de la sesión y la fecha se asigna en servidor con zona horaria.
- El recurso se conserva y queda representado como inactivo. La baja previa impide otra; `estado=false` sin historial no la impide.
- La mutación se serializa mediante bloqueo de fila; índices parciales protegen la unicidad manual.
- La API devuelve el movimiento junto al estado resultante; la interfaz presenta revisión y confirmación antes de enviar.

### T03 — Consultar historial (implementado)

- Permitir obtener el historial de movimientos de una plancha o retazo.
- Presentar tipo de evento, motivo, observación, usuario y fecha, además de identificar el material.
- Preservar el orden cronológico y la información histórica sin editar ni eliminar movimientos desde este alcance.
- La consulta está disponible para plancha y retazo, con permiso `CONSULTAR_STOCK`.

## 6. Reglas de negocio

1. **RN-01 — No borrado físico:** la baja no ejecuta `DELETE` sobre `planchas` ni `retazos`; tampoco elimina movimientos.
2. **RN-02 — Un recurso por movimiento:** cada movimiento referencia exactamente una plancha o exactamente un retazo. La otra referencia debe ser `NULL` (regla XOR).
3. **RN-03 — Eventos manuales admitidos:** solo `BAJA_ROTURA`, `BAJA_MERMA`, `BAJA_ERROR_REGISTRO` y `BAJA_RETIRO` se pueden solicitar en HU-014. `tipo_evento` es la categoría obligatoria.
4. **RN-04 — Motivo requerido:** cada baja manual requiere `motivo` como texto libre no vacío después de recortar espacios, que explique la baja. La categoría se registra separadamente en `tipo_evento` y no se infiere del texto libre.
5. **RN-05 — Observación opcional:** si se proporciona, se conserva como texto nullable sin reemplazar el motivo. El request permite omitirla o enviarla como `null`; la interfaz presenta `Sin observación` en el historial cuando no hay valor.
6. **RN-06 — Actor confiable:** `id_usuario` se obtiene de la identidad autenticada del backend, no de un valor controlado por el cliente.
7. **RN-07 — Fecha confiable:** `fecha` se asigna en servidor, con zona horaria (UTC normalizado, siguiendo el reloj actual de Inventory), y no se acepta como fecha arbitraria del cliente.
8. **RN-08 — Baja única:** un recurso con baja manual ya registrada no puede recibir otra baja; la segunda solicitud devuelve `409 Conflict` sin insertar un movimiento duplicado ni alterar el recurso.
9. **RN-09 — Disponibilidad:** solo se ofrece como material disponible el que tiene `estado = true`, no tiene movimiento de baja manual y, si es plancha, tiene `cantidad > 0`. La validación de stock para cualquier consumidor debe aplicar esta regla, no basarse únicamente en el listado general.
10. **RN-10 — Baja irreversible en HU-014:** toda baja manual registra el movimiento y establece `estado=false` en la misma transacción. La existencia del movimiento prueba que ocurrió la baja; `estado=false` por sí solo no constituye historial de baja.
11. **RN-11 — PATCH de estado:** para un recurso sin movimiento de baja, el PATCH mantiene el comportamiento histórico y admite los cambios `estado=true` y `estado=false`. Si existe una baja manual, cualquier PATCH que intente establecer `estado=true` devuelve `409 Conflict`; cambiarlo a `false` no crea ni duplica un movimiento. Reactivación, anulación o reversión requieren un evento/flujo futuro explícito y quedan fuera de HU-014.
12. **RN-12 — Cambio atómico:** insertar `MOVIMIENTO_INVENTARIO` y establecer `estado=false` ocurren en una única transacción; ante error se revierte la operación completa.
13. **RN-13 — Consumo separado:** `CONSUMO_OPTIMIZACION` queda reservado/documentado para una etapa futura. No se crea como funcionalidad ni puede ser enviado por los contratos de HU-014.
14. **RN-14 — Historial preservado:** los movimientos se consultan sin alterar su contenido. La información de usuario debe seguir siendo identificable aun si ese usuario posteriormente se inactiva; no se elimina el vínculo histórico.

## 7. Modelo persistido de trazabilidad

La entidad `MovimientoInventario` está implementada en ORM y en la migración `fa014e1a2b3c` (parent `ef6564220e70`). Sus campos vigentes son:

| Campo conceptual | Significado funcional | Regla |
|---|---|---|
| `id_movimiento` | Identificador del movimiento | PK generada por persistencia |
| `id_plancha` | Plancha afectada | Nullable; XOR con `id_retazo` |
| `id_retazo` | Retazo afectado | Nullable; XOR con `id_plancha` |
| `tipo_evento` | Categoría del movimiento | Cuatro bajas manuales o `CONSUMO_OPTIMIZACION` reservado |
| `motivo` | Justificación de baja | Obligatorio para bajas manuales |
| `observacion` | Detalle complementario | Nullable |
| `id_usuario` | Usuario responsable | FK obligatoria; se obtiene de la identidad autenticada |
| `fecha` | Momento de registro | Timestamp generado por la base de datos/servidor, con zona horaria |
| `id_optimizacion` | Asociación con optimización | FK nullable; no se acepta ni se usa en una baja manual |

Restricción funcional XOR:

```text
(id_plancha IS NOT NULL) XOR (id_retazo IS NOT NULL)
```

La base de datos aplica la regla XOR, FKs, restricción de eventos y restricciones/índices de unicidad parcial de baja manual. `CONSUMO_OPTIMIZACION` queda reservado; no hay endpoint manual que lo acepte ni flujo de consumo implementado en HU-014.

## 8. Estados y eventos considerados

### Estado actual de recursos

`Plancha.estado` y `Retazo.estado` siguen siendo booleanos, no enumeraciones. Los GET administrativos listan tanto recursos activos como inactivos y la interfaz muestra su estado. Una baja manual añade un movimiento y establece `estado=false`; la interfaz conserva la fila. No se usa el booleano aislado para inferir que ocurrió una baja histórica.

### Eventos de HU-014

| Evento | Uso funcional |
|---|---|
| `BAJA_ROTURA` | Plancha o retazo roto y no utilizable |
| `BAJA_MERMA` | Material que dejó de ser utilizable por merma/daño |
| `BAJA_ERROR_REGISTRO` | Registro incorrecto que debe excluirse de operación conservando evidencia |
| `BAJA_RETIRO` | Retiro administrativo del material |
| `CONSUMO_OPTIMIZACION` | Reservado para futura confirmación de una optimización; no implementado en HU-014 |

No se definen nuevos valores para `estado` del material. El pedido conserva su propio estado del dominio Orders y no se modifica por una baja. El evento de consumo permanece reservado y separado de la baja manual.

## 9. Flujos principales implementados

### Baja manual de material

1. Usuario autorizado abre la acción de baja desde el contexto de una plancha o retazo.
2. La interfaz identifica claramente el material y presenta los cuatro tipos de baja disponibles.
3. El usuario selecciona el tipo, ingresa el motivo obligatorio y, si corresponde, una observación.
4. La interfaz solicita confirmación indicando que el material dejará de ser elegible para stock y que la acción queda en historial.
5. El backend autentica al usuario, valida permiso, existencia, tipo de evento y datos obligatorios; el actor se toma del principal autenticado.
6. En una única transacción, el backend ejecuta `SELECT ... FOR UPDATE` sobre la fila del recurso, vuelve a comprobar que no exista baja manual previa, crea el movimiento con fecha de servidor y establece `estado=false`.
7. Si falla el movimiento o el cambio de estado, revierte ambos. Si ambos confirman, devuelve el resultado persistido y la interfaz informa éxito y actualiza la disponibilidad sin borrar el recurso.

### Consulta de historial

1. Un usuario con permiso de consulta abre el historial de un recurso.
2. El cliente solicita movimientos del recurso identificado.
3. El backend comprueba autorización y existencia, consulta movimientos vinculados únicamente al recurso y los presenta por `fecha ASC, id_movimiento ASC`.
4. El usuario puede reconocer evento, motivo, observación, responsable y fecha de cada movimiento.

## 10. Flujos alternativos y errores

- Motivo vacío o solo espacios: rechazar con validación; no insertar movimiento.
- Tipo de evento ausente o no permitido, incluido `CONSUMO_OPTIMIZACION`: rechazar; no insertar movimiento.
- Material inexistente: responder como recurso no encontrado; no insertar movimiento.
- Material con baja manual previa: responder `409 Conflict`; conservar el primer movimiento y el estado del recurso sin duplicarlo. El resultado también es 409 si hay carrera concurrente.
- Material `estado=false` sin baja manual previa: se permite registrar la primera baja trazable y se mantiene `estado=false`.
- PATCH `estado=true` sobre un recurso con baja manual: responder `409 Conflict` y conservar `estado=false` y el movimiento.
- PATCH `estado=true` o `estado=false` sobre un recurso sin baja manual: conservar el comportamiento histórico; el PATCH no genera movimiento.
- Usuario sin autenticación: `401`; usuario sin permiso: `403`.
- El request rechaza campos adicionales, incluidos `id_usuario`, `fecha` e `id_optimizacion`; no se aceptan valores de auditoría aportados por el cliente.
- Error de persistencia: rollback completo, respuesta controlada y sin indicar éxito. La segunda operación concurrente termina en conflicto; los errores inesperados no se presentan como conflicto de negocio.
- La interfaz recibe error de red/servidor: mantener los datos ingresados, indicar que no se confirmó la operación y permitir consultar nuevamente antes de reintentar.
- Al confirmar, si la baja ocurrió en otra sesión desde que se abrió el formulario, el servidor aplica RN-08 y responde `409`; la interfaz vuelve a consultar el recurso sin duplicar el movimiento.
- En historial vacío: mostrar estado vacío claro; no generar movimientos de forma implícita.
- Usuario responsable inactivo o inaccesible en una pantalla actual: mostrar identificación histórica disponible conforme a la política de usuarios, nunca ocultar la existencia del movimiento.

## 11. Disponibilidad y límite de cobertura vigente

Para HU-014, “deja de estar disponible” significa que el recurso deja de ser candidato a stock utilizable y no debe ser elegido por validaciones/consumidores de inventario. La baja no altera dimensiones, geometría, cantidad ni identidad del registro original.

Regla funcional revisada:

```text
plancha disponible = estado = true
                    AND cantidad > 0
                    AND no existe movimiento de baja manual

retazo disponible  = estado = true
                    AND no existe movimiento de baja manual
```

Los endpoints actuales de listado son administrativos y devuelven todos los registros; la pantalla permite distinguir estado activo/inactivo y conserva filas dadas de baja. El repositorio actual no ofrece un endpoint separado de candidatos de stock ni integra planchas/retazos con una selección activa de stock para optimización. Por ello, esta SPEC deja constancia del estado false producido por la baja, pero no afirma que la exclusión esté demostrada para todo consumidor futuro.

Una plancha con cantidad cero no representa stock utilizable. Un material con `estado=false` tampoco debe presentarse como disponible, aunque no tenga movimiento; ese valor sin movimiento no acredita una baja. La UI mantiene los valores estado y cantidad visibles, pero los listados siguen siendo administrativos. La exclusión explícita de candidatos de stock para todas las integraciones se marca parcial en CA-07 y CA-16. Cuando existe movimiento de baja, el PATCH a `estado=true` se rechaza con `409 Conflict`.

## 12. Contratos/API implementados

La API usa el prefijo `/api/inventory`. Las cuatro rutas HU-014 implementadas son:

| Operación | Entrada funcional | Resultado |
|---|---|---|
| Registrar baja de plancha | `POST /api/inventory/planchas/{id_plancha}/baja` — `BajaManualRequest`: `tipo_evento`, `motivo`, `observacion?` | `201 BajaManualResponse`; actor autenticado; movimiento y `estado=false` atómicos |
| Registrar baja de retazo | `POST /api/inventory/retazos/{id_retazo}/baja` — `BajaManualRequest`: `tipo_evento`, `motivo`, `observacion?` | `201 BajaManualResponse`; actor autenticado; movimiento y `estado=false` atómicos |
| Consultar movimientos de plancha | `GET /api/inventory/planchas/{id_plancha}/movimientos` | `200 list[MovimientoHistorialResponse]`, cronológico y aislado por plancha |
| Consultar movimientos de retazo | `GET /api/inventory/retazos/{id_retazo}/movimientos` | `200 list[MovimientoHistorialResponse]`, cronológico y aislado por retazo |

Los POST documentan `201`, `401`, `403`, `404`, `409` y `422`. Los GET de historial documentan `200`, `401`, `403`, `404` y `422`; no documentan `409`. El esquema de error conserva el formato real FastAPI `{ "detail": ... }`.

`BajaManualResponse` comunica `estado=false` y un `MovimientoInventarioResponse` con ID, referencia, evento, motivo, observación, actor, fecha e `id_optimizacion` nullable. `MovimientoHistorialResponse` expone los mismos campos históricos; `CONSUMO_OPTIMIZACION` solo puede aparecer como evento histórico persistido, no como solicitud manual.

El request prohíbe campos adicionales, incluyendo `id_usuario`, `fecha` e `id_optimizacion`. El PATCH de estado mantiene el comportamiento anterior si no hay baja, rechaza reactivación histórica con `409`, y `PATCH estado=false` no crea movimiento. Los GET generales mantienen sus contratos administrativos.

## 13. Criterios de aceptación y evidencia

La numeración siguiente es la vigente de CA-01 a CA-19. `Parcial` identifica requisitos cuyo efecto está cubierto en la baja/UI, pero cuya aplicación general a selección de stock no está demostrada por una interfaz de stock disponible o consumidor activo en Inventory.

| CA | Estado | Evidencia |
|---|---|---|
| CA-01 | Cumplido | `backend/tests/unit/inventory/test_writeoff.py`; `backend/tests/api/inventory/test_writeoff_schema.py`; prueba API de baja. Request limitado a los cuatro eventos manuales y rechaza consumo/valores desconocidos. |
| CA-02 | Cumplido | Pruebas de dominio, API y componentes HU-014: motivo no vacío, observación nullable y preservación de valores. |
| CA-03 | Cumplido | `backend/tests/integration/inventory/test_repository.py` y `backend/tests/api/inventory/test_writeoff_api.py`: movimiento plancha con referencia XOR correcta. |
| CA-04 | Cumplido | `backend/tests/integration/inventory/test_repository.py` y `backend/tests/api/inventory/test_writeoff_api.py`: movimiento retazo con referencia XOR correcta. |
| CA-05 | Cumplido | `backend/tests/unit/inventory/test_movement_model.py` y `backend/tests/integration/test_hu014_movement_migration.py`: constraint XOR verificado en PostgreSQL aislado. |
| CA-06 | Cumplido | Pruebas de baja API/repositorio: actor autenticado, timestamp de servidor y persistencia auditada. |
| CA-07 | Parcial | Integración PostgreSQL demuestra retención del recurso, `estado=false` y movimiento consultable; UI conserva la fila. No hay verificación de exclusión en todos los consumidores de stock. |
| CA-08 | Cumplido | `backend/tests/integration/inventory/test_repository.py`: persistencia atómica y fallos con rollback para plancha y retazo. |
| CA-09 | Cumplido | Prueba de integración PostgreSQL de baja y reactivación: 409; el estado y movimiento persisten intactos. |
| CA-10 | Cumplido | `backend/tests/integration/inventory/test_repository.py`: recurso inactivo sin historial puede reactivarse; PATCH no crea movimiento. |
| CA-11 | Cumplido | Pruebas de integración de duplicado y concurrencia con lock de fila e índice parcial de defensa. |
| CA-12 | Cumplido | `backend/tests/integration/inventory/test_repository.py`, `backend/tests/api/inventory/test_movement_history_api.py` y componentes: campos auditables y orden cronológico estable. |
| CA-13 | Cumplido | Prueba PostgreSQL de historial aislado plancha/retazo en `test_repository.py`. |
| CA-14 | Cumplido | Pruebas API de permisos para baja/historial; E2E HU-014 verifica que Operario puede consultar pero no ve acción de baja. |
| CA-15 | Cumplido | Pruebas API y OpenAPI: 401/403/404/409/422 aplicables a baja e historial; 409 no se documenta para GET de historial. |
| CA-16 | Parcial | La UI muestra cantidad y estado, y la baja deja el recurso inactivo. Los GET administrativos devuelven todos los registros y no existe contrato separado de stock disponible que pruebe la exclusión general por cantidad/estado. |
| CA-17 | Cumplido | Pruebas de repositorio/API e E2E: los recursos se conservan y siguen consultables; HU-014 no ejecuta DELETE físico. |
| CA-18 | Cumplido | Enum/schema restringen el comando manual; `CONSUMO_OPTIMIZACION` está reservado y no existe flujo funcional de consumo en HU-014. |
| CA-19 | Cumplido | `frontend/src/features/inventory/__tests__/Hu014Inventory.test.jsx` y `frontend/tests/e2e/hu014-inventory-writeoff.spec.js`: revisión explícita con recurso, evento, motivo y efecto antes de confirmar. |

CA-07 y CA-16 quedan parciales hasta que exista evidencia de una ruta/consumidor de stock disponible que aplique estas reglas de forma integral; esa deuda no cambia los contratos administrativos de listado.

## 14. Casos límite

- Plancha con `cantidad=0` y `estado=true`: ya no es stock utilizable; una baja sigue registrando y explicando su retiro lógico.
- Material con `estado=false` previo a la baja: no es stock; el movimiento agrega trazabilidad sin asumir que `estado=false` equivale a baja.
- Material con baja y luego PATCH a `estado=true`: respuesta `409 Conflict`, mantiene `estado=false` y conserva el movimiento; no existe flujo de reactivación en HU-014.
- Material sin baja con PATCH de `estado=true` o `estado=false`: conserva la respuesta y efecto históricos sin crear movimiento.
- Doble solicitud simultánea: solo una baja se confirma; la otra recibe conflicto por unicidad/validación transaccional.
- Tipo válido con motivo vacío, motivo de espacios o evento mal formado: no deja movimiento parcial.
- Movimiento para ID inexistente: no crea referencia huérfana.
- Usuario responsable posteriormente inactivo: movimiento y referencia histórica permanecen.
- Material con uso anterior en `materiales_utilizados` o relacionado con ejecución: HU-014 conserva esos registros y no modifica resultados ni optimizaciones previas.
- Historial con varios eventos históricos permitidos por evolución futura: ordenar por fecha y un criterio secundario estable (por ejemplo, ID del movimiento) para fechas iguales. En HU-014 se previene una segunda baja manual vigente.

## 15. Implementación por capa

- **Presentation:** rutas de baja e historial, schemas cerrados, validación, permisos y respuestas documentadas en OpenAPI.
- **Application:** operaciones para baja e historial; valida evento/motivo, existencia, duplicados y reactivación. El actor llega desde el principal autenticado.
- **Domain:** `BajaManual`, enum de cuatro eventos admitidos y reglas de validación.
- **Infrastructure:** repositorio SQLAlchemy con transacción, `SELECT ... FOR UPDATE`, movimiento y estado atómicos; historial ordenado por fecha e ID.
- **ORM/BD:** `MovimientoInventario` y restricciones persisten mediante revisión `fa014e1a2b3c`, parent `ef6564220e70`.
- **Frontend:** gestión de baja e historial para planchas y retazos; fila conservada y estado reflejado como inactivo.
- **Disponibilidad:** la exclusión general de candidatos de stock sigue pendiente de verificación, según CA-07 y CA-16.

## 16. Compatibilidad y regresión con TA-011 y funcionalidades actuales

- TA-011 integra listados, formularios y PATCH de estado. Para recursos sin baja, los PATCH `estado=true/false` conservan el comportamiento histórico y no generan eventos. Con una baja registrada, PATCH `estado=true` responde 409; el PATCH `estado=false` no crea un movimiento. La baja usa sus endpoints explícitos y no elimina registros de la lista administrativa.
- La interfaz conserva la fila y muestra `Activo`/`Inactivo`; el historial se consulta de forma separada. `estado=false` aislado no se interpreta como una baja histórica.
- Consultas generales siguen pudiendo devolver activos e inactivos. Si una nueva vista filtra stock disponible, debe usar todas las reglas de RN-09.
- Registro/edición de dimensiones de plancha, cantidad, tipo y espesor; registro/edición de código, geometría y área de retazo; validación tipo-espesor y reglas geométricas permanecen vigentes.
- Las autorizaciones actuales permanecen: gestión por Administrador/Almacenero y consulta por Administrador/Almacenero/Operario según permisos configurados.
- Los IDs, fechas de registro, `id_ejecucion_origen`, geometrías y persistencia de recursos no deben alterarse al escribir un movimiento.
- Las pruebas de contrato/API y regresión Inventory verifican los schemas y PATCH; la suite HU-014 cubre permisos de los roles aplicables. La selección de stock de futuros consumidores queda fuera del cierre funcional de esta HU.

## 17. Seguridad y permisos

- Requerir JWT/sesión válida para baja e historial.
- Baja de plancha: `GESTIONAR_PLANCHAS`; baja de retazo: `GESTIONAR_RETAZOS`.
- Historial: `CONSULTAR_STOCK`, alineado con consulta de recursos. Cualquier restricción diferente exige ajuste explícito de matriz, no un permiso inventado por endpoint.
- El ID de usuario proviene del principal autenticado. El schema cerrado rechaza campos de entrada que intenten suplantar usuario, fecha o asociación de optimización.
- Validar autorización antes de exponer el recurso o su historial según la política existente, evitando filtración entre identidades sin permiso.
- No incluir secretos ni datos de autenticación en movimientos, respuestas o logs.
- Auditar errores sin guardar una baja fallida como movimiento válido.

## 18. Trazabilidad y auditoría

Cada baja conserva el material referenciado, evento, motivo, observación opcional, usuario y fecha. El movimiento es append-only desde la API de HU-014. La consulta del historial debe conservar precisión de zona horaria y mostrar claramente el responsable. La baja no reemplaza ni sobrescribe la fecha original de registro del material.

`CONSUMO_OPTIMIZACION` se reserva para vincular en el futuro un movimiento con una optimización, pero no forma parte de los comandos admitidos ni de pruebas funcionales de HU-014.

## 19. Fuera de alcance

- DELETE físico de planchas, retazos o movimientos.
- Consumo real por optimización, decremento de cantidades por optimización o asignación de retazos resultantes.
- Confirmación de optimización.
- Rasterización o selección de heurísticas.
- TA-033 editor poligonal compartido.
- HU-005 T04 retazo poligonal.
- Reactivación, reversión o anulación de bajas con historial; el PATCH de reactivación se rechaza.
- Modificaciones de arquitectura no necesarias para baja e historial.
- Consumo de inventario por optimización y definición de la elegibilidad integral de stock para consumidores futuros, reflejada como cobertura parcial en CA-07 y CA-16.
- Ejecutar migraciones contra Supabase como parte de las pruebas HU-014; la migración se valida mediante PostgreSQL aislado.

## 20. Dependencias

- ADR-002 — Operación pre-raster, aprobado.
- Evolución de Base de Datos v1.3, aprobada.
- Módulo Inventory actual (TA-003), formularios/contratos integrados de TA-011 y catálogo tipo-espesor de TA-013.
- Autenticación JWT y permisos actuales.
- La migración HU-014 `fa014e1a2b3c` tiene como parent `ef6564220e70` y es el head de Alembic reportado para esta rama.
- Plancha y Retazo existentes y sus claves foráneas.

## 21. Riesgos

- Interpretar `estado=false` como baja perdería motivo, actor y fecha, y haría ambigua la reactivación; debe evitarse.
- Los GET administrativos no filtran estado y no equivalen a stock disponible. CA-07 y CA-16 permanecen parciales hasta probar la exclusión en un contrato/consumidor de stock disponible.
- La concurrencia queda protegida por lock de fila y unicidad parcial; futuras modificaciones deben conservar ambas defensas.
- La referencia histórica a un usuario eliminado físicamente rompería auditoría; se necesita preservar la FK/registro conforme a la política de usuarios.
- `id_optimizacion` apunta a un modelo de optimización existente, pero el flujo de consumo no está definido para HU-014. No asociar bajas manuales a una optimización.
- El historial presenta el ID de usuario como actor (`Usuario #...`); una presentación con nombre legible requeriría otra decisión/contrato y no se afirma en esta HU.
- Los listados administrativos completos y la elegibilidad de stock son conceptos distintos; una futura vista de disponibles debe aplicar RN-09 explícitamente.

## 22. Verificación realizada

- **Dominio/aplicación:** las pruebas unitarias cubren eventos, motivo, observación, estado legado, reactivación, duplicado y rollback.
- **Repositorio/integración PostgreSQL aislado:** las pruebas verifican XOR/FKs, persistencia, transacción, rollback, concurrencia, conservación, historial estable y aislamiento. No se usa Supabase como destino.
- **API:** las pruebas cubren permisos, schemas, respuestas, errores, campos de auditoría no aceptados desde el cliente y documentos OpenAPI.
- **Regresión Inventory:** la suite comprueba alta/lista/PATCH de planchas y retazos, catálogos, geometría y las reglas de baja/reactivación.
- **Frontend/E2E:** las pruebas cubren confirmación, doble envío, errores/reintento, historial vacío/poblado, campos de actor/fecha y recurso conservado.
- **Disponibilidad/consumidores:** la exclusión general en una selección de stock sigue sin evidencia; se registra como parcial en CA-07 y CA-16, no como prueba aprobada.
- Resultados informados para el cierre: Inventory API 46 passed; Inventory unit 350 passed; Inventory integration 59 passed; backend completo 1181 passed. Frontend: unit 84/84, component 166/166, lint y build PASS.
- E2E HU-014: 3 passed, 1 skipped, 0 failed. La ejecución real de la baja se limita a desktop porque el fixture tiene una sola plancha con baja única; el caso de permisos corre en ambos viewports.
- La suite E2E global tiene fallos de HU-007. No se presenta como verde ni se atribuye esos fallos a HU-014.
- Los comandos, resultados y salvedades se registran en [`docs/evidence/sprint-01/HU-014/test-results/README.md`](../evidence/sprint-01/HU-014/test-results/README.md). Los conteos de suites se documentan como resultados reportados; este cierre documental no vuelve a ejecutarlas.

## 23. Evidencia

- La evidencia documental de cierre se encuentra en [`docs/evidence/sprint-01/HU-014/README.md`](../evidence/sprint-01/HU-014/README.md) y en su `test-results/README.md`.
- La prueba de migración y las pruebas de integración usan PostgreSQL aislado; no se presentan salidas/logs o capturas no existentes.
- Los tests unitarios, de integración, API, componentes y E2E nombrados en la matriz sustentan los criterios cumplidos. CA-07 y CA-16 quedan expresamente parciales.
- La suite E2E global contiene fallos HU-007 y queda pendiente de revisión separada.

## 24. Referencias

- [ADR-002 — Operación pre-raster](../../adr/ADR-002-operacion-pre-raster.md), en particular decisión 2.7 sobre baja lógica y trazabilidad.
- [Evolución de Base de Datos v1.3 — Operación pre-raster](../../database/evolucion-v1.3-pre-raster.md), secciones 6 a 8 sobre movimientos, XOR, disponibilidad y diferencia con consumo.
- [SPEC-TA-011 — Integración de stock](../SPEC-TA-011-integracion-inventario.md).
- [SPEC-TA-003 — API de inventario](../SPEC-TA-003-api-inventario.md).
- [SPEC-HU-004 — Registrar plancha comercial](../SPEC-HU-004-registrar-plancha.md).
- [SPEC-HU-005 — Registrar retazo](../SPEC-HU-005-registrar-retazo.md).
- Implementación: `backend/app/models.py`; `backend/alembic/versions/fa014e1a2b3c_hu014_movimientos_inventario.py`; `backend/app/modules/inventory/{presentation,application,infrastructure}`.
- Pruebas: `backend/tests/unit/inventory/`, `backend/tests/integration/inventory/`, `backend/tests/integration/test_hu014_movement_migration.py`, `backend/tests/api/inventory/`, `frontend/src/features/inventory/__tests__/` y `frontend/tests/e2e/hu014-inventory-writeoff.spec.js`.
- Evidencia y trazabilidad de commits: [`docs/evidence/sprint-01/HU-014/README.md`](../evidence/sprint-01/HU-014/README.md).

## Historial de estado

- **Draft — 09/10/2026:** Especificación funcional contrastada con ADR-002, evolución v1.3, SPECs actuales, modelos, API, repositorio y pruebas existentes. Implementación, migración y verificación pendientes.
- **Reviewed — 09/10/2026 (estado histórico previo a implementar):** Revisión funcional aprobada. Se fijó baja atómica con movimiento y `estado=false`, PATCH de reactivación bloqueado con 409 después de una baja, distinción entre movimiento histórico y `estado=false` aislado, formato de `tipo_evento`/`motivo`/`observacion`, y rutas de baja e historial. En esa fecha aún no se habían definido `revision`/`down_revision`.
- **Implemented — 12/10/2026:** Backend, migración `fa014e1a2b3c`, OpenAPI, interfaz y E2E HU-014 completados. CA-07 y CA-16 quedan parciales por falta de evidencia de exclusión general en consumidores de stock. La SPEC no está Verified: queda revisión final por otro integrante y cierre formal del PR.
