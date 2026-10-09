# SPEC-HU-014 — Baja y trazabilidad de inventario

## Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| PBI relacionado | HU-014 — Baja y trazabilidad de inventario |
| Épica | EP-001 — Inventario |
| Rama de trabajo | `feature/HU-014-trazabilidad-inventario` |
| Dependencias | HU-004, HU-005, TA-003, TA-011, TA-013; HU-012 Clientes antes de la futura migración de HU-014 |
| Revisión funcional | Aprobada — 09/10/2026 |

> La especificación está Reviewed tras revisión funcional. No fija `revision` ni `down_revision` de Alembic; HU-012 Clientes debe migrarse antes de HU-014.

## 1. Objetivo

Permitir que personal autorizado dé de baja lógicamente una plancha o un retazo, registre de forma auditable el evento y consulte el historial asociado, preservando el recurso original y evitando que una baja manual se confunda con un consumo por optimización.

## 2. Contexto

Inventory ya registra, lista y edita planchas y retazos mediante FastAPI, capas de aplicación/repositorio y SQLAlchemy. Los modelos actuales tienen `estado: BOOLEAN`, pero no existe una entidad de movimientos ni campos de baja, motivo, usuario de baja o fecha de baja. Los PATCH aceptan `estado: true | false`; las consultas actuales devuelven materiales activos e inactivos.

El ADR-002 establece que las bajas no deben borrar físicamente el material, deben preservar material, tipo de evento, motivo, observación, usuario y fecha, y que una baja manual es distinta del consumo por optimización. La evolución BD v1.3 propone `MOVIMIENTO_INVENTARIO` y deja a esta SPEC precisar la disponibilidad sin sobrecargar `estado` con significados distintos.

### 2.1 Hallazgos y conflicto que la implementación debe resolver

- `Plancha.estado` y `Retazo.estado` son booleanos con valor inicial verdadero. Los PATCH existentes permiten cambiarlo en ambos sentidos. El código no documenta una semántica más precisa que el campo de estado/actividad.
- `GET /api/inventory/planchas` y `GET /api/inventory/retazos` incluyen registros con ambos valores de `estado`; por sí solos no son listados de stock disponible.
- La plancha puede tener `cantidad = 0` (el modelo y PATCH lo permiten), lo cual constituye otra condición que impide ofrecerla como stock.
- Las columnas `estado` participan en índices de compatibilidad de stock, pero no se encontró una regla de trazabilidad de bajas ligada a ellas.
- No existe `MovimientoInventario` en ORM ni movimiento de inventario en el repositorio/servicio. Las respuestas actuales tampoco contienen movimientos.
- El esquema ORM sí tiene `Usuario.id_usuario` y `fecha_registro` con zona horaria para los recursos. La identidad del usuario autenticado debe servir para atribuir al actor del movimiento; el cliente no debe decidir dicho identificador.
- Existe `MaterialUtilizado` con XOR entre plancha y retazo y FK a ejecución. Es un registro de materiales usados por ejecución, no un historial de bajas manuales, por lo que no sustituye a `MOVIMIENTO_INVENTARIO`.

**Decisión revisada para disponibilidad:** la baja manual registra `MOVIMIENTO_INVENTARIO` y establece `estado=false` en la misma transacción. El movimiento es la fuente de verdad de que ocurrió una baja; `estado=false` sin movimiento solo representa el estado inactivo ya admitido por el contrato histórico. Un recurso con movimiento de baja no puede reactivarse mediante PATCH en HU-014.

## 3. Actor principal

**Almacenero**. El Administrador también puede ejecutar la operación por sus permisos actuales de gestión de inventario. Administrador, Almacenero y Operario pueden consultar stock según la matriz vigente; la consulta de historial de HU-014 se propone con permiso `CONSULTAR_STOCK`.

## 4. Precondiciones

- El actor está autenticado y conserva una sesión válida.
- Para dar de baja, posee `GESTIONAR_PLANCHAS` o `GESTIONAR_RETAZOS`, según el recurso.
- Para consultar historial, posee `CONSULTAR_STOCK`.
- El recurso de inventario existe y es identificable por su tipo e ID.
- Para registrar una baja, se recibe un motivo válido y el evento corresponde a uno de los cuatro tipos manuales habilitados.
- La base de datos y el servicio de Inventory están disponibles; el registro del movimiento y su aplicación sobre disponibilidad se confirman en una única transacción.

## 5. Alcance por tarea

### T01 — Diseñar trazabilidad de inventario

- Definir la entidad conceptual de movimientos y su vínculo exclusivo con una plancha o retazo.
- Definir los cuatro eventos iniciales de baja manual y diferenciarlos de `CONSUMO_OPTIMIZACION`.
- Definir atribución de usuario, fecha, motivo y observación.
- Definir elegibilidad para stock y revisar la interacción con el `estado` booleano actual.
- Especificar errores, consultas, permisos, criterios y pruebas sin cambiar el código en esta etapa.

### T02 — Implementar baja lógica

- Permitir dar de baja una plancha o retazo existente.
- Exigir evento/motivo válido; permitir observación opcional.
- Registrar actor autenticado y fecha de servidor con zona horaria.
- Conservar el recurso y excluirlo de cualquier selección/listado que represente stock utilizable.
- Rechazar una segunda baja del mismo recurso mientras ya tenga una baja vigente.
- Proporcionar respuesta de éxito o error que la interfaz pueda presentar y pedir confirmación antes de enviar la operación.

### T03 — Consultar historial

- Permitir obtener el historial de movimientos de una plancha o retazo.
- Presentar tipo de evento, motivo, observación, usuario y fecha, además de identificar el material.
- Preservar el orden cronológico y la información histórica sin editar ni eliminar movimientos desde este alcance.

## 6. Reglas de negocio

1. **RN-01 — No borrado físico:** la baja no ejecuta `DELETE` sobre `planchas` ni `retazos`; tampoco elimina movimientos.
2. **RN-02 — Un recurso por movimiento:** cada movimiento referencia exactamente una plancha o exactamente un retazo. La otra referencia debe ser `NULL` (regla XOR).
3. **RN-03 — Eventos manuales admitidos:** solo `BAJA_ROTURA`, `BAJA_MERMA`, `BAJA_ERROR_REGISTRO` y `BAJA_RETIRO` se pueden solicitar en HU-014. `tipo_evento` es la categoría obligatoria.
4. **RN-04 — Motivo requerido:** cada baja manual requiere `motivo` como texto libre no vacío después de recortar espacios, que explique la baja. La categoría se registra separadamente en `tipo_evento` y no se infiere del texto libre.
5. **RN-05 — Observación opcional:** si se proporciona, se conserva como texto sin reemplazar el motivo. Longitudes máximas y normalización deben definirse en el contrato de implementación contra el estándar vigente del proyecto antes de codificarse.
6. **RN-06 — Actor confiable:** `id_usuario` se obtiene de la identidad autenticada del backend, no de un valor controlado por el cliente.
7. **RN-07 — Fecha confiable:** `fecha` se asigna en servidor, con zona horaria (UTC normalizado, siguiendo el reloj actual de Inventory), y no se acepta como fecha arbitraria del cliente.
8. **RN-08 — Baja única:** un recurso con baja manual ya registrada no puede recibir otra baja; la segunda solicitud devuelve `409 Conflict` sin insertar un movimiento duplicado ni alterar el recurso.
9. **RN-09 — Disponibilidad:** solo se ofrece como material disponible el que tiene `estado = true`, no tiene movimiento de baja manual y, si es plancha, tiene `cantidad > 0`. La validación de stock para cualquier consumidor debe aplicar esta regla, no basarse únicamente en el listado general.
10. **RN-10 — Baja irreversible en HU-014:** toda baja manual registra el movimiento y establece `estado=false` en la misma transacción. La existencia del movimiento prueba que ocurrió la baja; `estado=false` por sí solo no constituye historial de baja.
11. **RN-11 — PATCH de estado:** para un recurso sin movimiento de baja, el PATCH mantiene el comportamiento histórico y admite los cambios `estado=true` y `estado=false`. Si existe una baja manual, cualquier PATCH que intente establecer `estado=true` devuelve `409 Conflict`; cambiarlo a `false` no crea ni duplica un movimiento. Reactivación, anulación o reversión requieren un evento/flujo futuro explícito y quedan fuera de HU-014.
12. **RN-12 — Cambio atómico:** insertar `MOVIMIENTO_INVENTARIO` y establecer `estado=false` ocurren en una única transacción; ante error se revierte la operación completa.
13. **RN-13 — Consumo separado:** `CONSUMO_OPTIMIZACION` queda reservado/documentado para una etapa futura. No se crea como funcionalidad ni puede ser enviado por los contratos de HU-014.
14. **RN-14 — Historial preservado:** los movimientos se consultan sin alterar su contenido. La información de usuario debe seguir siendo identificable aun si ese usuario posteriormente se inactiva; no se elimina el vínculo histórico.

## 7. Modelo conceptual de trazabilidad

Entidad propuesta por la evolución v1.3, pendiente de implementación y de ajuste al esquema definitivo:

| Campo conceptual | Significado funcional | Regla |
|---|---|---|
| `id_movimiento` | Identificador del movimiento | PK generada por persistencia |
| `id_plancha` | Plancha afectada | Nullable; XOR con `id_retazo` |
| `id_retazo` | Retazo afectado | Nullable; XOR con `id_plancha` |
| `tipo_evento` | Categoría del movimiento | Manuales admitidos en RN-03; consumo reservado |
| `motivo` | Justificación de baja | Obligatorio para bajas manuales |
| `observacion` | Detalle complementario | Nullable |
| `id_usuario` | Usuario responsable | FK al usuario autenticado; obligatorio |
| `fecha` | Momento de registro | Asignada por servidor, con zona horaria |
| `id_optimizacion` | Asociación futura con optimización | Nullable; no se usa en baja manual |

Restricción funcional XOR:

```text
(id_plancha IS NOT NULL) XOR (id_retazo IS NOT NULL)
```

`CONSUMO_OPTIMIZACION` requiere asociación a su optimización cuando se implemente esa etapa. HU-014 no crea consumos ni exige implementar flujo de optimización. La semántica exacta de `id_optimizacion` y su FK debe armonizarse con las entidades existentes al diseñar la migración.

## 8. Estados y eventos considerados

### Estado actual de recursos

`Plancha.estado` y `Retazo.estado` son booleanos, inicializados en `true`, editables a `false` y nuevamente a `true`. No son enumeraciones y el sistema actual no contiene `BAJA` como estado persistido. Los endpoints actuales listan recursos `true` y `false`; por tanto, una respuesta de listado no equivale necesariamente a stock utilizable.

### Eventos de HU-014

| Evento | Uso funcional |
|---|---|
| `BAJA_ROTURA` | Plancha o retazo roto y no utilizable |
| `BAJA_MERMA` | Material que dejó de ser utilizable por merma/daño |
| `BAJA_ERROR_REGISTRO` | Registro incorrecto que debe excluirse de operación conservando evidencia |
| `BAJA_RETIRO` | Retiro administrativo del material |
| `CONSUMO_OPTIMIZACION` | Reservado para futura confirmación de una optimización; no implementado en HU-014 |

No se definen nuevos valores para `estado` del material. El pedido conserva su propio estado del dominio Orders y no se modifica por una baja.

## 9. Flujos principales

### Baja manual de material

1. Usuario autorizado abre la acción de baja desde el contexto de una plancha o retazo.
2. La interfaz identifica claramente el material y presenta los cuatro tipos de baja disponibles.
3. El usuario selecciona el tipo, ingresa el motivo obligatorio y, si corresponde, una observación.
4. La interfaz solicita confirmación indicando que el material dejará de ser elegible para stock y que la acción queda en historial.
5. El backend autentica al usuario, valida el permiso, existencia, tipo de evento y datos obligatorios.
6. En una única transacción, el backend valida que el material no tenga ya una baja manual, crea el movimiento con usuario y fecha de servidor y establece `estado=false`.
7. Si falla el movimiento o el cambio de estado, revierte ambos. Si ambos confirman, devuelve el resultado persistido y la interfaz informa éxito y actualiza la disponibilidad sin borrar el recurso.

### Consulta de historial

1. Un usuario con permiso de consulta abre el historial de un recurso.
2. El cliente solicita movimientos del recurso identificado.
3. El backend comprueba autorización y existencia, consulta movimientos vinculados al único recurso y los presenta cronológicamente.
4. El usuario puede reconocer evento, motivo, observación, responsable y fecha de cada movimiento.

## 10. Flujos alternativos y errores

- Motivo vacío o solo espacios: rechazar con validación; no insertar movimiento.
- Tipo de evento ausente o no permitido, incluido `CONSUMO_OPTIMIZACION`: rechazar; no insertar movimiento.
- Material inexistente: responder como recurso no encontrado; no insertar movimiento.
- Material ya dado de baja: responder `409 Conflict`; conservar el primer movimiento y el estado del recurso sin duplicarlo.
- PATCH `estado=true` sobre un recurso con baja manual: responder `409 Conflict` y conservar `estado=false` y el movimiento.
- PATCH `estado=true` o `estado=false` sobre un recurso sin baja manual: conservar el comportamiento histórico; el PATCH no genera movimiento.
- Usuario sin autenticación: `401`; usuario sin permiso: `403`.
- Observación inválida según límites acordados en el contrato: `422`; no truncar silenciosamente.
- Error de persistencia o conflicto concurrente: rollback completo, respuesta controlada y sin indicar éxito.
- La interfaz recibe error de red/servidor: mantener los datos ingresados, indicar que no se confirmó la operación y permitir consultar nuevamente antes de reintentar.
- Al confirmar, si la baja ocurrió en otra sesión desde que se abrió el formulario, el servidor aplica RN-08 y responde `409`; la interfaz vuelve a consultar el recurso sin duplicar el movimiento.
- En historial vacío: mostrar estado vacío claro; no generar movimientos de forma implícita.
- Usuario responsable inactivo o inaccesible en una pantalla actual: mostrar identificación histórica disponible conforme a la política de usuarios, nunca ocultar la existencia del movimiento.

## 11. Reglas de disponibilidad

Para HU-014, “deja de estar disponible” significa que el recurso deja de ser candidato a stock utilizable y no debe ser elegido por validaciones/consumidores de inventario. La baja no altera dimensiones, geometría, cantidad ni identidad del registro original.

Regla funcional revisada:

```text
plancha disponible = estado = true
                    AND cantidad > 0
                    AND no existe movimiento de baja manual

retazo disponible  = estado = true
                    AND no existe movimiento de baja manual
```

Los endpoints actuales de listado son listados administrativos completos y no filtran por `estado`; deberán conservar su propósito de consulta/gestión o exponer una forma explícita de consultar disponibles y bajas al implementarse. Todo flujo que evalúe stock compatible debe excluir bajas, incluso si solo consulta datos completos.

Una plancha con cantidad cero no está disponible aunque su estado sea verdadero. Un material con `estado=false` tampoco está disponible aunque no tenga movimiento; ese valor, sin movimiento, no acredita que haya ocurrido una baja. Cuando existe movimiento de baja, el PATCH a `estado=true` se rechaza con `409 Conflict`, por lo que la baja no se revierte en HU-014.

## 12. Contratos/API esperados a nivel funcional

La API existente usa el prefijo `/api/inventory`, los recursos `/planchas` y `/retazos`, GET para listado, POST para creación y PATCH `/{id}` para edición, además de permisos por recurso. HU-014 incorpora los siguientes contratos explícitos:

Contratos fijados por revisión funcional (son rutas nuevas; actualmente no están implementadas):

| Operación | Entrada funcional | Resultado |
|---|---|---|
| Registrar baja de plancha | `POST /api/inventory/planchas/{id_plancha}/baja` — `tipo_evento`, `motivo`, `observacion?`; identidad obtenida de sesión | Crea movimiento y establece `estado=false` atómicamente; baja repetida devuelve 409 |
| Registrar baja de retazo | `POST /api/inventory/retazos/{id_retazo}/baja` — `tipo_evento`, `motivo`, `observacion?`; identidad obtenida de sesión | Crea movimiento y establece `estado=false` atómicamente; baja repetida devuelve 409 |
| Consultar movimientos de plancha | `GET /api/inventory/planchas/{id_plancha}/movimientos` | Colección cronológica de movimientos, identificada como historial de esa plancha |
| Consultar movimientos de retazo | `GET /api/inventory/retazos/{id_retazo}/movimientos` | Colección cronológica de movimientos, identificada como historial de ese retazo |

La respuesta del movimiento debe incluir como mínimo los datos auditables (`id_movimiento`, referencia del recurso, `tipo_evento`, `motivo`, `observacion`, identificador/datos de presentación del usuario responsable y `fecha`; `id_optimizacion` puede ser nulo). No se debe aceptar desde el cliente `id_usuario`, `fecha` ni `id_optimizacion` para una baja manual.

Las respuestas actuales `PlanchaResponse` y `RetazoResponse` exponen `estado`, pero no movimientos ni un estado de baja. La baja debe comunicar tanto el `estado=false` resultante como el movimiento creado; no se debe presentar `estado=false` aislado como evidencia histórica. Los PATCH actuales mantienen el comportamiento para recursos sin baja y rechazan `estado=true` con 409 para recursos con baja. Los GET generales mantienen sus contratos de listado.

Errores esperados conforme al patrón Inventory: `401`, `403`, `404`, `409` y `422`, con mensajes controlados. `409 Conflict` aplica a doble baja y a PATCH `estado=true` después de una baja. La operación de baja es un comando explícito; PATCH `estado=false` no crea un movimiento.

## 13. Criterios de aceptación verificables

- **CA-01:** La baja acepta exclusivamente los eventos `BAJA_ROTURA`, `BAJA_MERMA`, `BAJA_ERROR_REGISTRO` y `BAJA_RETIRO`; rechaza `CONSUMO_OPTIMIZACION` y valores desconocidos sin persistir.
- **CA-02:** Toda baja manual requiere motivo no vacío y conserva observación cuando se proporciona.
- **CA-03:** Una baja de plancha crea un movimiento ligado a exactamente esa plancha; `id_retazo` queda nulo.
- **CA-04:** Una baja de retazo crea un movimiento ligado a exactamente ese retazo; `id_plancha` queda nulo.
- **CA-05:** La integridad de persistencia rechaza movimientos con ambas referencias nulas o ambas presentes.
- **CA-06:** La identidad del movimiento corresponde al usuario autenticado y su fecha es asignada en servidor con zona horaria.
- **CA-07:** Después de una baja confirmada el material permanece persistido, aparece en consultas históricas/administrativas y no puede utilizarse como stock disponible.
- **CA-08:** La baja establece `estado=false` y persiste el movimiento en una única transacción. Ante falla de cualquiera de las dos escrituras, no se confirma ninguna.
- **CA-09:** Un PATCH `estado=true` después de una baja manual devuelve `409 Conflict` y mantiene `estado=false` y el movimiento.
- **CA-10:** Para un recurso sin baja, PATCH `estado=true` y `estado=false` conservan el comportamiento histórico y no generan movimientos.
- **CA-11:** Una segunda baja del mismo recurso devuelve `409 Conflict`, no cambia el registro inicial y no crea otro movimiento.
- **CA-12:** La consulta de historial devuelve tipo de evento, motivo, observación (incluido null), usuario responsable y fecha para cada movimiento, en orden cronológico estable.
- **CA-13:** Una consulta de historial de plancha no mezcla movimientos de retazo y viceversa.
- **CA-14:** La operación de baja exige permiso de gestión del tipo de material; la consulta exige `CONSULTAR_STOCK`.
- **CA-15:** Las respuestas de error incluyen `401` sin sesión, `403` sin permiso, `404` para material inexistente, `409` para doble baja o PATCH de reactivación y `422` para datos inválidos.
- **CA-16:** Las planchas con cantidad cero y los materiales con `estado=false` no se ofrecen como stock disponible, aunque no tengan movimiento de baja.
- **CA-17:** Los registros existentes de planchas y retazos continúan listándose y consultándose conforme a los contratos actuales; no se ejecuta `DELETE` físico.
- **CA-18:** `CONSUMO_OPTIMIZACION` no descuenta cantidad ni cambia estado como parte de HU-014 y permanece reservado para etapa futura.
- **CA-19:** La confirmación de baja es explícita en UI y presenta el material afectado, tipo, motivo y efecto de dejarlo fuera de disponibilidad.

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

## 15. Impacto esperado en Inventory

- **Presentation:** nuevos contratos de solicitud/respuesta para baja e historial, validación de entrada y permisos; los endpoints actuales se mantienen explícitos.
- **Application:** casos de uso para registrar baja y listar historial, validando motivo, evento, existencia, duplicados y disponibilidad; actor y reloj se reciben de forma confiable.
- **Domain:** tipo/eventos de movimiento y reglas de XOR/disponibilidad sin introducir estados contradictorios.
- **Infrastructure:** repositorio transaccional para movimientos, carga del usuario necesario para presentar historial y persistencia relacional con restricciones.
- **ORM/BD:** entidad propuesta `MovimientoInventario` y claves/restricciones, pendientes de migración en el orden de ramas indicado en Dependencias.
- **Frontend:** acción de baja con confirmación, feedback de éxito/error, identificación visual de baja y consulta del historial; no borrar la fila.
- **Consumidores de stock:** verificar que validación/candidatos excluyan bajas, `estado=false` y planchas con cantidad cero. La integración exacta con futuros módulos de optimización permanece fuera de alcance, pero ningún consumidor actual de stock puede tratar una baja como candidata.

## 16. Compatibilidad y regresión con TA-011 y funcionalidades actuales

- TA-011 integra listados, formularios y PATCH de estado. Para recursos sin baja, los PATCH `estado=true/false` conservan el comportamiento histórico y no generan eventos. Con una baja registrada, PATCH `estado=true` responde 409; el PATCH `estado=false` no crea un movimiento. La baja usa sus endpoints explícitos y no elimina registros de la lista administrativa.
- La interfaz debe diferenciar “estado” existente de “baja con historial”; si ambos se muestran, sus etiquetas deben evitar que un booleano se interprete como motivo de baja.
- Consultas generales siguen pudiendo devolver activos e inactivos. Si una nueva vista filtra stock disponible, debe usar todas las reglas de RN-09.
- Registro/edición de dimensiones de plancha, cantidad, tipo y espesor; registro/edición de código, geometría y área de retazo; validación tipo-espesor y reglas geométricas permanecen vigentes.
- Las autorizaciones actuales permanecen: gestión por Administrador/Almacenero y consulta por Administrador/Almacenero/Operario según permisos configurados.
- Los IDs, fechas de registro, `id_ejecucion_origen`, geometrías y persistencia de recursos no deben alterarse al escribir un movimiento.
- Probar serialización compatible de respuestas, consumo de las API por TA-011, usuarios con los tres roles y comportamiento de stock utilizado por Orders/HU-008 donde aplique.

## 17. Seguridad y permisos

- Requerir JWT/sesión válida para baja e historial.
- Baja de plancha: `GESTIONAR_PLANCHAS`; baja de retazo: `GESTIONAR_RETAZOS`.
- Historial: `CONSULTAR_STOCK`, alineado con consulta de recursos. Cualquier restricción diferente exige ajuste explícito de matriz, no un permiso inventado por endpoint.
- El ID de usuario proviene del principal autenticado. Rechazar o ignorar campos de entrada que intenten suplantar usuario o fecha; preferiblemente contrato cerrado que los rechace.
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
- Reactivación, reversión o anulación de bajas.
- Modificaciones de arquitectura no necesarias para baja e historial.
- Cambios manuales en Supabase o revisión/migración Alembic en esta tarea de especificación.
- Definir ahora `revision`/`down_revision` de HU-014.

## 20. Dependencias

- ADR-002 — Operación pre-raster, aprobado.
- Evolución de Base de Datos v1.3, aprobada.
- Módulo Inventory actual (TA-003), formularios/contratos integrados de TA-011 y catálogo tipo-espesor de TA-013.
- Autenticación JWT y permisos actuales.
- HU-012 Clientes será la migración siguiente antes de HU-014. El head aplicado informado para el entorno compartido es `d6e7f8a9b0c1`; no usarlo como base definitiva de una migración HU-014.
- Plancha y Retazo existentes y sus claves foráneas.

## 21. Riesgos

- Interpretar `estado=false` como baja perdería motivo, actor y fecha, y haría ambigua la reactivación; debe evitarse.
- La consulta actual de materiales no filtra estado y no equivale a stock disponible. Todo consumidor que omita la regla nueva podría utilizar material dado de baja.
- Concurrencia entre solicitudes de baja puede generar duplicados si el control solo se hace en aplicación; debe protegerse en transacción y, si el esquema lo permite, con integridad de BD.
- La referencia histórica a un usuario eliminado físicamente rompería auditoría; se necesita preservar la FK/registro conforme a la política de usuarios.
- `id_optimizacion` apunta a un modelo de optimización existente, pero el flujo de consumo no está definido para HU-014. No asociar bajas manuales a una optimización.
- Las ramas/migraciones HU-012 y HU-014 secuenciales hacen riesgoso fijar el grafo Alembic antes de integrar HU-012.
- Los listados administrativos completos y una futura vista de disponibles pueden confundirse en UI si no se etiquetan claramente.

## 22. Pruebas requeridas

- **Dominio/aplicación:** eventos válidos e inválidos, categoría `tipo_evento`, motivo libre obligatorio, observación nullable, usuario/reloj confiables, XOR, recurso inexistente, doble baja 409, transiciones PATCH de estado con/sin baja, plancha cantidad cero, conflicto y rollback.
- **Repositorio/integración PostgreSQL aislado:** restricciones XOR, FKs, persistencia y lectura del movimiento, transacción atómica de movimiento más `estado=false`, rollback ante fallo de cualquiera, concurrencia/doble baja 409, conservación del recurso y orden estable del historial. No utilizar Supabase como destino de tests.
- **API:** autenticar y autorizar los cuatro contratos fijados; validar `401/403/404/409/422`, respuestas, rechazo de `id_usuario`/fecha/control de consumo enviados por cliente y compatibilidad OpenAPI. Verificar PATCH `estado=true` con baja => 409 y PATCH `true/false` sin baja => contrato histórico sin movimiento.
- **Regresión Inventory:** tests existentes de alta/lista/PATCH para planchas y retazos, catálogos y geometría; comprobar que PATCH de `estado=false/true` para recursos sin baja conserva su contrato y no crea movimientos; con baja, `estado=true` falla con 409.
- **Disponibilidad/consumidores:** bajas siempre excluidas; `estado=false` excluido aunque no haya movimiento; cantidad cero de plancha excluida; `estado=true` y sin baja mantiene elegibilidad bajo las reglas existentes.
- **Frontend/E2E:** confirmación explícita, doble clic/reintento, éxito, error/red, historial vacío y poblado, usuario/fecha visibles, recurso conservado y actualización de vista sin DELETE.
- Ejecutar pruebas existentes de Inventory y las nuevas pruebas correspondientes antes de declarar HU-014 implementada/verificada.

## 23. Evidencias esperadas

- Captura o evidencia reproducible de baja de plancha y de retazo con confirmación, motivo y resultado.
- Consulta persistida del movimiento que demuestre XOR y sus campos de auditoría.
- Evidencia de baja duplicada rechazada sin movimiento adicional.
- Evidencia de consulta de historial para ambos tipos con evento, motivo, observación, usuario y fecha.
- Evidencia de que el material continúa almacenado, pero queda excluido del stock disponible.
- Evidencia de permisos y errores `401`, `403`, `404`, `409` y `422` según casos aplicables.
- Reporte de pruebas de Inventory, integración aislada y regresión TA-011.
- `git diff --check` limpio al entregar el trabajo de implementación; esta SPEC no anticipa resultados de pruebas de implementación.

## 24. Referencias

- [ADR-002 — Operación pre-raster](../../adr/ADR-002-operacion-pre-raster.md), en particular decisión 2.7 sobre baja lógica y trazabilidad.
- [Evolución de Base de Datos v1.3 — Operación pre-raster](../../database/evolucion-v1.3-pre-raster.md), secciones 6 a 8 sobre movimientos, XOR, disponibilidad y diferencia con consumo.
- [SPEC-TA-011 — Integración de stock](../SPEC-TA-011-integracion-inventario.md).
- [SPEC-TA-003 — API de inventario](../SPEC-TA-003-api-inventario.md).
- [SPEC-HU-004 — Registrar plancha comercial](../SPEC-HU-004-registrar-plancha.md).
- [SPEC-HU-005 — Registrar retazo](../SPEC-HU-005-registrar-retazo.md).
- Código actual: `backend/app/models.py`; `backend/app/modules/inventory/{presentation,application,infrastructure}`; `backend/tests/unit/inventory/`, `backend/tests/integration/inventory/` y `backend/tests/api/inventory/`.

## Historial de estado

- **Draft — 09/10/2026:** Especificación funcional contrastada con ADR-002, evolución v1.3, SPECs actuales, modelos, API, repositorio y pruebas existentes. Implementación, migración y verificación pendientes.
- **Reviewed — 09/10/2026:** Revisión funcional aprobada. Se fijó baja atómica con movimiento y `estado=false`, PATCH de reactivación bloqueado con 409 después de una baja, distinción entre movimiento histórico y `estado=false` aislado, formato de `tipo_evento`/`motivo`/`observacion`, y rutas de baja e historial. Se mantiene pendiente implementación y migración; `revision`/`down_revision` no definidos.
