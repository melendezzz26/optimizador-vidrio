# PLAN-OPT-MULTIMOTOR-VISUAL — Integración de ejecución y comparación visual

## Información general

| Campo | Valor |
|---|---|
| Estado | **Approved — implementación autorizada por Fabricio Melendez Quezada; T00 en curso** |
| SPEC | [SPEC-OPT-MULTIMOTOR-VISUAL.md](SPEC-OPT-MULTIMOTOR-VISUAL.md) |
| Fecha | 31/10/2026, America/Lima |
| Rama / destino | `feature/optimization-multimotor-visual` → `integration/sprint-01` |
| Base inspeccionada | `afd5f85f9dd1495e4237e1029555f7e56cd53f30` |
| Autor | Fabricio Melendez Quezada |
| Revisor | Andro Quispe; revisión cruzada pendiente de ejecución |
| Autorización de esta entrega | Fabricio Melendez Quezada aprueba el PLAN y autoriza desarrollar su alcance en `feature/optimization-multimotor-visual`; no autoriza merge ni despliegue |
| Estimación | No se fija SP/plazo sin validar contratos y presupuesto agregado; no se traslada automáticamente la estimación histórica de HU-017 |

## 1. Resultado esperado y límites

Entregar un trabajo comparativo con FF/BF/WF concurrentes, eventos separados,
cuatro pestañas, fases visuales claras, medidas originales, elección manual y
confirmación del resultado elegido. Reutilizar los motores y renderizadores.
El cambio a centímetros pertenece a la segunda rama acordada y queda fuera de
los commits de esta primera rama. No se modifica el backlog externo.

## 2. Base técnica y brechas verificadas

Las rutas backend siguientes son relativas a `backend/app/modules/optimization/`;
las frontend a `frontend/src/features/optimization/`.

| Capacidad actual | Reutilización y trabajo pendiente |
|---|---|
| `domain/{first_fit,best_fit,worst_fit,packing}.py` | Los tres calculan y aceptan observación; conservar sus políticas, métricas y salida temprana |
| `application/comparison.py` | Orquesta secuencialmente y no conecta callbacks visuales; conservar el comparador interno y añadir un coordinador concurrente de producto |
| `domain/preparation.py`, `run_geometry.py`, `rotation.py` | Orden, bases y orientaciones existentes; publicar el orden real sin mover decisiones geométricas para animar |
| `application/runs.py`, `calculation.py`, `infrastructure/run_uow.py` | Ciclo y repositorio FF; capturar snapshot común y generalizar el nuevo recorrido por ejecución explícita |
| `infrastructure/run_snapshot.py` | Snapshot V1 no preserva BF/WF; nuevo codec versionado con método explícito y round-trip de los tres |
| `presentation/run_routes.py`, `run_stream.py`, `visual_*` | FF/visual-v2, cola acotada y máscaras reales; nuevo contrato comparativo sin romper consumidores anteriores |
| `infrastructure/visual_store.py` | Retención efímera por proceso; aislar referencias por comparación/ejecución y aplicar presupuesto total |
| `application/confirmation.py`, `infrastructure/confirmation_adapter.py` | Revalidación y consumo transaccional; resolver contexto a partir de la ejecución elegida, sin filtros FF implícitos |
| `OptimizationPage.jsx`, `useFirstFit.js`, `optimizationModel.js` | Un resultado/estado; introducir controlador comparativo estable y estados por ejecución |
| `RunVisualization.jsx`, `RunMaskInspection.jsx`, `PlacementCanvas.jsx` | Visores reales, 2D/3D/raster; componer pestañas/fases sin calcular otra heurística en navegador |
| `RunVisualization.jsx`, `visualState.js` | Orden observado al recibir `piece_started`; falta fase explícita de presentación del orden completo |
| `Orders.PieceResponse` y snapshot actual | Dimensiones/geometría persistidas; ampliar snapshot de solicitud, no reconstruir medidas originales desde colocaciones rotadas |

Referencias normativas: SPEC principal, TA-021, HU-017/DG-01, TA-016/018/019/020,
TA-037 y confirmación S1. Las fronteras históricas de esos documentos no se
reescriben como si este alcance ya estuviera entregado.

## 3. Diseño propuesto

### 3.1 Identidad y captura común

Un agregado comparación posee exactamente tres ejecuciones, una por método.
`comparison_id`, `execution_id` y `method` son identificadores explícitos; no
usar la posición en un array como identidad. Crear unicidad por comparación y
método, selección inicialmente nula, versión y recibo de confirmación único.

Aceptar el lote en una sola transacción corta: validar y bloquear pedidos en
orden estable, capturar piezas y configuración, leer stock compatible una vez
bajo una lectura consistente, comprobar límites y persistir snapshot común y
ejecuciones. Cada trabajador recibe un DTO desconectado equivalente y conserva
su estado privado. No mantener sesiones DB durante el cálculo ni releer stock
por motor. La confirmación revalida el inventario real posterior.

El DTO conserva decimales como strings, geometrías canónicas y ranking de stock.
No enviar ORM/sesiones ni asumir que los `MappingProxyType` actuales se pueden
transportar directamente a otro proceso. Definir codec de entrada y hash de
equivalencia determinista, incluyendo cantidades, configuración y stock.

### 3.2 Ejecución concurrente y recursos

Propuesta: supervisor del trabajo y **tres procesos de cálculo acotados**, uno
por motor, con arranque coordinado. Elegir `spawn` y DTO explícito para evitar
heredar conexiones y permitir validar Windows/Linux. Un ThreadPool aislado no
demuestra por sí solo paralelismo de CPU en este backend Python.

- El supervisor posee la persistencia y las identidades. Los trabajadores solo
  calculan y emiten hechos; no acceden a DB ni a inventario mutable.
- La primera entrega propone como máximo **una comparación activa por proceso
  web y una por persona**, con tres trabajadores. Es la decisión técnica
  aprobada; no significa que el límite FF de dos corridas permita seis motores.
- Un coordinador de admisión compartido contabiliza trabajo legacy y comparativo:
  una comparación reserva capacidad para sus tres motores antes de aceptar;
  no se acepta si faltan unidades de capacidad o memoria agregada.
- Conservar inicialmente los máximos de entrada actuales: 20 pedidos, 150
  unidades, 128 vértices y 50 unidades de stock por material. Validar antes de
  expansión. Estos máximos no certifican que el triple peor caso quepa.
- Caché raster 64 MiB y layouts hasta 128 MiB son límites por motor actuales,
  no un presupuesto agregado. Medir la suma de tres trabajadores, proceso web,
  buffers y retención visual antes de aprobar la configuración del runner.
- T00 debe fijar presupuesto agregado de memoria, tamaño de colas, tiempo global
  y comportamiento al superar límites. No triplicar automáticamente el timeout
  de 120 s ni elevar límites existentes sin evidencia.
- Checkpoints cooperativos y terminación supervisada de trabajadores propios.
  Liberar la admisión únicamente cuando terminaron, incluso ante fallo de
  arranque, IPC, timeout, desconexión, persistencia o cierre del proceso.
- Si la plataforma no permite el trabajo concurrente, responder un rechazo claro;
  no cambiar a secuencial mientras la UI afirma ejecutar los tres simultáneamente.

Los umbrales agregados son una salida de medición de T00, pendiente; no se afirma
que el despliegue remoto tenga recursos suficientes. No se introduce aquí una
cola distribuida ni se escala a varios procesos web sin coordinación compartida.

### 3.3 API comparativa versionada

Propuesta de recurso separado de `/runs`, preservando FF V1 y `visual-v2`:

| Operación propuesta | Responsabilidad |
|---|---|
| `POST /api/optimization/comparisons` | Aceptar IDs de pedidos, crear las tres ejecuciones y responder 201 con identidad/URLs; no seleccionar ganador |
| `GET /api/optimization/comparisons/{id}` | Estado agregado, snapshot de solicitud, estados/resúmenes FF/BF/WF, selección, versión y confirmación |
| `GET /api/optimization/comparisons/{id}/executions/{execution_id}` | Resultado durable de un motor y su identidad explícita |
| `GET /api/optimization/comparisons/{id}/events?after_sequence=...` | Observación NDJSON versionada, independiente de la aceptación y del ciclo del cálculo |
| `GET .../{id}/executions/{execution_id}/visual[/masks/{mask_ref}]` | Descriptores y ventanas acotadas de máscaras de esa ejecución |
| `PUT .../{id}/selection` | Elegir `execution_id` con versión esperada; sin consumo de inventario |
| `POST .../{id}/confirm` | Confirmar la selección/version esperada, sin aceptar un layout arbitrario del cliente |
| `POST .../{id}/release` | Reconciliar/liberar lote no confirmado con trabajadores terminados, conservando la historia |

Definir claves de idempotencia para aceptación y confirmación, y semántica de
repetición sin efectos duplicados. Versionar validaciones/errores públicos,
pertenencia de ejecución y compare-and-set de selección. Una respuesta ambigua
se resuelve consultando el identificador/idempotencia, no enviando otro POST ciego.

Propuesta de envolvente de eventos `comparison-v1`, `schema_version: 1`, distinta
del perfil FF `visual-v2`: comparación, secuencia global, ejecución/método cuando
corresponda, secuencia por ejecución, instante y payload tipado. Cada evento
declara su ámbito global o de motor; no mezclar secuencias entre los tres.

Eventos mínimos: aceptación; preparación/máscaras; orden disponible;
motor en ejecución; orientación evaluada; colocación/faltante; métricas;
resultado persistido por motor; comparación terminada/incompleta; fallo.
Las denominaciones finales se congelan con fixtures en T00/T01.

Colas IPC y buffers de red acotados; el muestreo solo afecta telemetría de
orientaciones, nunca resultados/colocaciones. Definir heartbeat y recuperación
por snapshot si un cursor queda fuera de retención. No fabricar replay completo
si solo se conservó una muestra. Un cliente lento no comparte estado mutable
ni bloquea indefinidamente a los otros motores. La pausa visual no pausa cálculos.

### 3.4 Persistencia, elección y estados

Evaluar reutilización de `Optimizacion`, `OptimizacionPedido`,
`EjecucionOptimizacion`, métricas y materiales utilizados. SQL ya permite los
tres métodos. Añadir solo los metadatos necesarios mediante una migración
aditiva si no caben en el esquema actual; no crear tablas duplicadas por motor.

Nuevo snapshot de resultado con versión y método explícitos. Reconstruir la
identidad BF/WF sin depender de una propiedad que devuelve FF por defecto.
Mantener lectura de FF V1 y datos históricos: no crear resultados BF/WF ficticios.
Guardar cada resultado y sus métricas atómicamente; notificar «guardado» solo
tras commit. Un resultado calculado pero no guardado no es seleccionable.

Transiciones propuestas para el nuevo recorrido:

| Momento | Pedidos y selección |
|---|---|
| Comparación aceptada | Lote PENDIENTE → EN_OPTIMIZACION una vez; elección nula |
| Un motor termina y otros siguen | Persistir su resultado; conservar lote en ejecución y elección final deshabilitada |
| Todos terminales y algún resultado completo guardado | Lote → OPTIMIZADO una vez; elección manual habilitada; indicar fallos parciales si existen |
| Todos terminales y ninguno completo | Sin confirmación; cierre/reconciliación devuelve lote a PENDIENTE cuando sea seguro |
| Persona elige | Guardar ejecución y versión; no modificar inventario |
| Persona confirma | Bloquear comparación/selección/pedidos/stock y aplicar solo el elegido; lote → CONFIRMADO |
| Conflicto/abandono sin confirmación | Mantener historia; liberación explícita segura permite una comparación nueva |

La confirmación debe resolver el contexto por ejecución elegida, no por un join
`metodo == FF`. Preservar revalidación geométrica, unidad física, remanentes,
movimientos y rollback total. Probar carreras selección/confirmación/liberación.
Tras reinicio, reconciliar trabajos sin supervisor antes de liberar pedidos:
un timeout de observación o un lease vencido no prueba que terminó un trabajador.
La recuperación general de trabajos históricos ajenos conserva su alcance separado.

### 3.5 Experiencia visual

Un controlador estable mantiene el trabajo fuera de componentes desmontables
de las pestañas. Estados por `execution_id`; cambiar de pestaña no abre otro
cálculo, no resetea canvas, no cancela workers y no pierde resultados.

| Vista | Contenido |
|---|---|
| Cabecera común | Trabajo, pedidos, configuración, estado de los tres y acceso a piezas solicitadas |
| First Fit / Best Fit / Worst Fit | Nombre y estado del motor; máscaras → orden real → rotaciones/colocación → resultado; inspección accesible de fases completadas |
| Comparación | Tres resultados/estados, distribuciones, métricas comunes, faltantes y control de elección explícita |
| Detalle de solicitud | Snapshot original de formas, cantidades, materiales, medidas y unidades; disponible después del cálculo y recarga |

Publicar `ordering_ready` o equivalente con el orden real y su criterio. El
ordenamiento actual ocurre antes de la preparación geométrica: no afirmar que
se está ejecutando de nuevo después de las máscaras. La UI presenta ese resultado
en la fase solicitada; no introduce sleeps ni altera orden/score para animar.

Interpolar visualmente giros/colocaciones entre hechos conocidos, con ángulo y
contorno del backend. Mantener el muestreo explícito, separación entre inspección
y avance vivo, seguimiento automático de pieza y opción de pausar solo la vista.
Movimiento reducido conserva información sin transiciones. No alternar pestañas
automáticamente ni ocultar un fallo detrás de una animación de éxito.

El detalle original usa el snapshot, no pedidos actuales ni placements girados.
Para polígonos, distinguir medidas calculadas de los metadatos efectivamente
ingresados/persistidos. En esta rama se rotulan mm/mm²/grados; el formulario cm
y su contrato de presentación pertenecen al segundo trabajo.

## 4. Secuencia de implementación propuesta

**T00 en curso** tras aprobación expresa. T01–T07 siguen sin cierre funcional;
no se declaran criterios cumplidos por cambiar este estado.

El codec de T01 (`2323e94`) conserva identidad FF/BF/WF y entrada desconectada;
[evidencia](../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/t01-codec.md).
La persistencia (`d4088e6`) incorpora aceptación idempotente, captura única de
stock, solicitud original, resultados por ejecución y selección/liberación
internas versionadas. La
[evidencia de persistencia](../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/t01-persistencia.md)
registra PostgreSQL temporal y regresión histórica.

El runner/coordinador interno (`6493b15`) ejecuta tres procesos spawn con
admisión compartida/exclusiva, presupuestos iniciales aplicados, persistencia
por motor y hechos visuales/orden reales. Su
[evidencia](../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/t02-coordinador.md)
registra 817 pruebas del módulo, siete escenarios de recursos y sus límites.
T00 conserva pendiente medir el recorrido HTTP/retención completo; siguen
pendientes contratos HTTP, recuperación de reinicios, stores comparativos e
interfaz. La confirmación comparativa interna (`4ccf74a`) ya valida el elegido,
versión e idempotencia, con consumo/rollback exclusivos;
[evidencia](../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/t03-confirmacion.md).
No se declaran T01–T07 cerradas por estos avances.

Inicio de T00: sonda de tres procesos `spawn`, entrada JSON común y comparación
de resultados con ejecución directa en los tres casos congelados, ejecutada y
documentada en [la evidencia inicial](../evidence/sprint-02/OPT-MULTIMOTOR-VISUAL/t00-inicio.md).
La sonda demuestra viabilidad inicial y solapamiento instrumentado; todavía no
cierra los contratos ni el presupuesto agregado de producción. No es el runner
productivo ni satisface por sí sola los CA de integración.

| Tarea | Salida verificable | Dependencias | CA |
|---|---|---|---|
| T00 — Cerrar diseño y presupuesto | Matriz baseline/compatibilidad, contratos propuestos, prueba de viabilidad de tres procesos y límites agregados medidos | Revisión de SPEC/PLAN | 02,03,20,25 |
| T01 — Contratos y persistencia | Fixtures compartidas, snapshot de solicitud, codec multimétodo, identidad/selección versionadas y migración aditiva si procede | T00 | 01,02,14,16,17,18,24,25 |
| T02 — Coordinador concurrente | Captura única, admisión agregada, tres workers, callbacks identificados y ciclo de errores/cierre | T00,T01 | 01,02,03,09,20,21,22 |
| T03 — API, selección y confirmación | Recursos comparativos, idempotencia, elección manual, consumo exclusivo y liberación segura | T01,T02 | 11,13,14,15,16,21,22,23,24,25 |
| T04 — Eventos y máscaras | Streaming comparativo, cursores, orden disponible, muestras de giro y namespaces/presupuestos visuales | T01,T02,T03 | 06,07,08,09,10,20,21 |
| T05 — Pestañas y fases | Controlador estable, cuatro pestañas, máscaras/orden/rotaciones/colocaciones y accesibilidad | T01,T04 | 04,05,06,07,08,09,10,19 |
| T06 — Comparación y solicitud original | Métricas/layouts de tres, elección persistida, detalle de piezas/medidas y recuperación | T03,T05 | 11,12,13,14,15,16,17,18,23,24 |
| T07 — Regresión y evidencia | E2E real de comparación completa, recursos, migraciones, capturas y matriz de CA | T01–T06 | 01–26 |

Mantener commits por contrato/persistencia, coordinador, API, eventos, UI y
pruebas/evidencia. El PR será hacia `integration/sprint-01`; crear PR/merge o
desplegar no forman parte de la autorización de desarrollo actual.

### Convención de commits acordada

Cada cambio concreto y verificado mantiene trazabilidad con esta SPEC/PLAN:
`docs:` para documentación/estado/evidencia, `feat:` para funcionalidad,
`fix:` para correcciones, `test:` para pruebas/sondas y `refactor:` para
reestructuración sin cambio funcional. Puede indicarse el módulo, por ejemplo
`feat(optimization): ...`. La autoría de los nuevos commits corresponde a
Fabricio Melendez Quezada; Andro Quispe es revisor asignado, sin atribuirle
revisiones no realizadas. Se conservan los commits anteriores sin reescribirlos.

## 5. Estrategia de pruebas

1. **Contratos y codecs:** round-trip FF/BF/WF con métricas y cantidades; snapshot
   original intacto; rechazo de motor ajeno, versión antigua y máscara de otra ejecución.
2. **Dominio:** mismos resultados con observación activada/desactivada; prioridad
   retazo, separación/margen, ángulos, salida temprana FF, scores BF/WF y determinismo.
3. **Concurrencia:** barrera instrumentada demuestra que los tres entraron antes
   de liberar ninguno. Probar eventos intercalados, órdenes distintos de fin,
   fallo de un worker, cancelación técnica y liberación exacta de capacidad.
4. **PostgreSQL temporal:** aceptar lote una vez; tres resultados sin consumo;
   elegir sin consumo; confirmar solo elegido; repetir confirmación sin duplicar;
   carreras de selección/confirmación/liberación; rollback y recuperación tras reinicio.
5. **API/stream:** autenticación y permisos reales; idempotencia, heartbeat,
   reconexión/cursor vencido, resultados parciales, fallo de guardado y compatibilidad FF.
6. **Componentes:** fases guiadas por eventos, identidad por pestaña, rotación
   fiel, respuesta tardía descartada, pausa visual, medidas originales, elección
   solo elegible y ninguna elección automática por orden de llegada.
7. **E2E real:** escenario multipedido/multimaterial con cantidad y las tres
   formas; máscaras → orden → giros/colocaciones → tres métricas → elección BF o
   WF → confirmación → recarga. Comprobar stock/pedidos/identidades en servidor.
8. **Recursos y presentación:** medir pico agregado y colas con tres motores;
   rechazos sin mutaciones; escritorio/móvil, teclado, movimiento reducido y
   fases rápidas. Registrar discrepancias de navegador con evidencia, no ocultarlas.

Actualizar el gate E2E con los nuevos specs críticos. Adaptar las pruebas de UI
al nuevo flujo sin eliminar sus invariantes; conservar pruebas API del contrato
legacy y escenarios históricos. Un skip no aprobado o un spec crítico ausente
no cuenta como validación. El fallo móvil de retazo observado en la auditoría
se registra como baseline conocido; el cierre no puede declarar esa suite verde
sin reproducirla y resolver o delimitar formalmente la discrepancia.

## 6. Riesgos y decisiones abiertas concretas

| Punto | Tratamiento antes de declarar entrega completa |
|---|---|
| Triple CPU/memoria y serialización de snapshots | T00 mide plataforma, codecs y tres procesos; fija límites y prueba rechazo previo; no afirmar capacidad por los límites individuales |
| Desconexión del visor y reinicio del web | Desacoplar observación del trabajo nuevo; persistir estados/resultados y demostrar reconciliación sin workers vivos |
| Preservación BF/WF | Codec versionado y repositorio por ejecución; no reutilizar decode FF como clonado genérico |
| Confirmación de otra selección o stock cambiado | Versión y locks; solo elegido, transacción única y salida explícita de liberación/reintento |
| Históricos sin medidas digitadas | Mostrar únicamente lo conservado; etiquetar derivaciones; coordinar metadatos de la futura rama cm |
| Máscaras efímeras o presupuesto visual | Contrato de disponibilidad y namespaces; resultado durable independiente; no sustituir referencias entre motores |
| Semántica al fallar uno de tres | SPEC RN-07 aprobada: comparación incompleta y éxitos elegibles tras tres terminales; verificar mediante pruebas |
| Integridad general de inventario | Reactivación de retazos consumidos y ajustes sin movimiento son hallazgos previos; no se declaran corregidos por esta rama |

No quedan abiertas la elección humana, las cuatro pestañas ni la ejecución
concurrente: son requisitos expresos del solicitante. Las rutas, versionado,
regla de fallo parcial y supervisión quedan aprobados para implementación;
T00 debe concretar los umbrales agregados con mediciones. Registrar cualquier
ajuste técnico y su evidencia, conservando los requisitos de la SPEC aprobada.

## 7. Cierre y evidencia

- Matriz de los 26 CA, contratos/fixtures, migraciones y comandos/entorno reales.
- Trazas de concurrencia, medición agregada y comprobaciones DB del elegido.
- Capturas por motor/fase, comparación, selección y medidas originales.
- Suites y gate de CI del commit final; ninguna afirmación de funcionalidad se
  apoya únicamente en lint/build o en la auditoría de la base.
- Guías actualizadas para la API comparativa, recuperación, límites y distinción
  entre contratos legacy, selección y confirmación.

La SPEC queda Reviewed y este PLAN Approved por autorización expresa de Fabricio
Melendez Quezada. Implemented/Verified exigen implementación y evidencia; Andro
Quispe figura como revisor asignado, sin atribuirle una revisión ya ejecutada.
No atribuir cambios de estado a herramientas externas que no se actualizaron.

## Historial de estado

| Fecha | Estado | Registro |
|---|---|---|
| 31/10/2026 | Draft | PLAN preparado junto con la SPEC; ninguna tarea de implementación ejecutada |
| 31/10/2026 | Approved | Fabricio Melendez Quezada aprueba el PLAN, confirma su autoría y asigna revisión a Andro Quispe. Desarrollo autorizado únicamente en la rama acordada; T00 en curso |
| 31/10/2026 | Approved — T00 en curso | Sonda inicial `eb40a21`: tres procesos y resultados equivalentes en los casos SMALL/MEDIUM/COMPLEX. Evidencia registrada; umbrales agregados y contratos pendientes |
| 31/10/2026 | Approved — desarrollo en curso | Codec parcial T01 `2323e94` y ampliación T00 `795c588`; 123 pruebas aprobadas. Medición de supervisor y tres workers en siete escenarios; T00 y la integración de producto siguen pendientes. Convención de commits documentada por indicación de Fabricio Melendez Quezada |
| 31/10/2026 | Approved — desarrollo en curso | Persistencia interna `d4088e6`: tres ejecuciones, idempotencia, solicitud original y selección versionada sin consumo. Regresión 159 pruebas y selección específica posterior 22 pruebas, con superposición. API, runner, confirmación comparativa e interfaz pendientes |
| 31/10/2026 | Approved — desarrollo en curso | Runner/coordinador `6493b15`: tres procesos supervisados, presupuestos aplicados, orden real y guardado independiente. 817 pruebas del módulo aprobadas. Ajuste de head en pruebas `9b960ca`: 81 pruebas afectadas aprobadas; repetición completa pendiente de registrar. API, confirmación comparativa, recuperación y UI pendientes |
| 31/10/2026 | Approved — desarrollo en curso | Regresión completa de backend de la base `9b960ca`: 2429 pruebas aprobadas en 258.69s, sin fallos ni skips. Confirmación comparativa y recorrido HTTP/UI siguen pendientes de integrar |
| 31/10/2026 | Approved — desarrollo en curso | Confirmación interna `4ccf74a`: consumo exclusivo FF/BF/WF elegido, recibo idempotente, carreras y rollback. Selección de regresión: 74 pruebas aprobadas. Rutas, recuperación, streaming y frontend pendientes |
