# HU-017 DG-01 — Perfil visual optativo

| Campo | Valor |
|---|---|
| Estado | **Closed — alternativa B seleccionada** |
| Fecha / base | 27/10/2026 / `315d71c`, rama local `feature/HU-017-proceso-visual-optimizacion` |
| Decisión del solicitante | «Vamos por B», después de explicar A/B y recomendar el perfil visual separado. |
| Responsable de la elección | Solicitante; elección expresa de B. |
| Concreción técnica | Codex, a partir de la SPEC/PLAN y auditoría de los consumidores actuales. |
| Revisión | Alternativa confirmada por el solicitante; implementación y pruebas locales completadas el 28/10. Revisión cruzada humana pendiente. |
| Alcance | Decisión de arquitectura y reglas de T03. La implementación posterior se acredita en la evidencia final, sin atribuirla a la elección de B. |
| Evidencia posterior | [T03–T06: verificación local, recursos y límites](../evidence/sprint-02/HU-017/t03-t06-visualizacion-y-cierre-local.md). |

Referencias: [SPEC HU-017](SPEC-HU-017-proceso-visual-optimizacion.md),
[PLAN HU-017](PLAN-HU-017-proceso-visual-optimizacion.md) y
[evidencia T02](../evidence/sprint-02/HU-017/t02-bases-y-rotaciones-lazy.md).

## 1. Decisión y compatibilidad

Se adopta **B: `visual-v2` optativo**, con V1 como formato predeterminado.
La pantalla nueva solicitará el perfil cuando su lector y estado visual estén
implementados. Se conserva un único optimizador, problema aceptado y ciclo de
corrida. Elegir un formato visual no selecciona heurística ni crea otra corrida.

La alternativa A no se elige: `runContract.js` admite ocho nombres de evento y
`schema_version === 1`; `run_schemas.py` usa contratos congelados y
`extra="forbid"`. Introducir hechos nuevos directamente en V1 no es una extensión
compatible demostrada. B permite esquemas/lectores explícitos y regresiones de
ambos formatos, a cambio de mantener dos contratos de eventos.

| Solicitud futura | Comportamiento requerido |
|---|---|
| `POST /api/optimization/runs`, sin perfil o con `stream_profile=v1` | V1 actual, sin nuevos tipos/campos visuales. |
| Mismo POST con `stream_profile=visual-v2` | NDJSON visual; cada evento lleva `schema_version: 2`. |
| Perfil desconocido, vacío o duplicado | 422 `INVALID_INPUT` antes de reservar recursos/aceptar pedidos; sin degradación silenciosa a V1. |
| `GET /runs/{id}` y `POST /runs/{id}/confirm` | Contratos canónicos V1 actuales; consulta y confirmación separadas del stream visual. |

El body del POST conserva `{order_ids}`. Se reutilizan NDJSON, `Location`,
`sequence`, `id_optimizacion`, `occurred_at`, autenticación y permisos actuales.
El lector V2 comprueba versión, secuencia, corrida y datos; nunca introduce un
evento V2 directamente en el reducer/lector V1. Un perfil solicitado con una
respuesta de otro perfil es un error de contrato.

V2 puede reutilizar validadores comunes de identificadores, geometría, unidades
y medidas, sin relajar V1. La primera integración HTTP continúa siendo FF:
BF/WF de dominio y TA-021 no habilitan por sí solos persistencia multimétodo.
Las rutas históricas HU-015 conservan su semántica y representación de errores.

## 2. Hechos reales, orden y progreso

V2 conserva los ocho hitos existentes con envolvente versión 2 y añade los siete
hechos propuestos en SPEC §9. Sus datos deben provenir del snapshot/cache real,
sin rasterización frontend ni consumo anticipado de iteradores.

| Hecho | Momento y correlación |
|---|---|
| `preparation_started` | Comienzo real de preparación; método/configuración efectivos y totales. |
| `piece_rasterizing` | Inicio de la base de una pieza única; pedido/pieza y cantidad. |
| `piece_ready` | Base real lista; referencia de máscara, resolución, ángulo, dimensiones y cantidad. |
| `preparation_completed` | Todas las bases necesarias listas; antes de la primera evaluación de colocación. No acredita todas las rotaciones. |
| `orientation_testing` | Evaluación real de una unidad en una fuente/ángulo; ordinal de evaluación y referencia de la máscara usada. |
| `source_selected` | Fuente y orientación ganadoras, antes de `piece_placed`; identidad física y score solo si existe. FF no recibe score inventado. |
| `piece_unplaced` | Finalización real de la búsqueda de una unidad sin posición: `NO_FIT`. Un fallo técnico utiliza `optimization_failed`. |

Se mantiene `optimization_started` antes de la preparación, orden monotónico de
secuencia, `piece_started` antes de evaluar su unidad y un único terminal.
`piece_placed` continúa probando una colocación aceptada; `source_selected` no
representa una fuente simplemente examinada. El resultado final se consulta por
GET y no se calcula otra vez para dibujarlo o confirmarlo.

`processed_units` aumenta una vez por unidad colocada o NO_FIT; `placed_units`
solo por colocación. Se cumple `0 <= placed_units <= processed_units <= total_units`.
Se conserva el significado de `progress_pct` de colocadas/total; un resultado
parcial puede terminar de procesar todas las piezas sin colocar el 100 %.

## 3. Entrega y presupuesto visual

Parámetros iniciales de diseño para T03, no mediciones ni nuevos límites del
algoritmo. T03 debe probarlos y registrar cualquier ajuste antes de habilitar el
perfil; el número de SP/horas no cambia por elegir B.

| Recurso | Regla inicial |
|---|---|
| Evento NDJSON | Máximo 64 KiB UTF-8 serializados; descriptores/referencias, sin matrices densas. |
| Cola de entrega | Tamaño 1 y acknowledgement existentes; no cola paralela ilimitada ni espera de animaciones. |
| Orientaciones | Primera evaluación real por unidad cuando exista, hasta las 150 unidades admitidas; más hasta 128 muestras adicionales por corrida. |
| Muestras adicionales | Máximo 10/s por corrida usando reloj monotónico; sin sleeps ni trabajo geométrico para llenar una cuota. |
| Hechos críticos | Preparación, pieza iniciada/lista, fuente ganadora, colocación, NO_FIT, error y terminal se conservan íntegros. No se descartan por el cupo de muestras. |
| Estado visual frontend futuro | Pieza/muestra actual y proyección del resultado; sin historial infinito ni un elemento por celda. |

La primera orientación por unidad puede producir ráfagas acotadas por el límite
de unidades; el límite de 10/s aplica a las muestras **adicionales**, no a los
hechos obligatorios. El stream identifica que las orientaciones son muestras e
informa ordinales/conteos; nunca presenta el conjunto como reproducción exhaustiva.
Un ángulo solo generado/cacheado que no se evalúa no dispara ese hecho.

La observación, registro de referencias, serialización y entrega visual se
descuentan de los relojes de cálculo/presupuesto de forma consistente. Preparar
bases y buscar sí forman parte del trabajo geométrico medido. Ocultar o pausar
la animación mantiene el consumo del stream; salir/cortar transporte conserva
la semántica de interrupción cooperativa ya existente.

## 4. Máscaras autoritativas y recuperación

Cada `mask_ref` identifica una representación inmutable de esa corrida,
geometría original, resolución efectiva y orientación. Las unidades idénticas
pueden compartir los bits; su identidad pedido/pieza/unidad se mantiene en los
eventos. Una fuente añade tipo/ID/unidad física de stock. El descriptor distingue
pieza/material, dimensiones, ángulo y disponibilidad; no repite la máscara.

La implementación conservará referencias a las máscaras efectivamente usadas,
sin volver a ejecutar el optimizador ni usar `/rasterize` sobre Orders en vivo.
La ventana devuelta debe corresponder a esos mismos bits y geometría normalizada.
La resolución algorítmica permanece fija aunque la vista solicite una ventana.

Contratos autenticados a implementar dentro del mismo prefijo `/runs`:

- `GET /{id}/visual`: manifiesto paginado de referencias disponibles, con revisión
  monotónica, hasta 64 descriptores por página. No es un replay de eventos.
- `GET /{id}/visual/masks/{mask_ref}`: ventana exacta solicitada mediante
  `row_start`, `row_count`, `column_start`, `column_count`; máximos 256 filas y
  1024 columnas. JSON hasta 256 KiB, con `spans_by_row`, offsets, dimensiones
  completas, geometría/contexto y versión 2; sin matriz densa.
- Las consultas requieren `optimization.view` y las mismas reglas de acceso
  de la consulta canónica de la corrida. La referencia no sustituye autorización.
  Iniciar conserva `optimization.execute`; confirmar, `optimization.confirm`.
- Ventana inválida/demasiado grande: 422; corrida/ref desconocida dentro de un
  contexto disponible: 404; datos visuales de una corrida existente expirados,
  desalojados o nunca conservados: 410 explícito. Sin cambiar su resultado.

Retención inicial en el proceso único actual:

- Hasta 2 contextos visuales retenidos; 64 MiB contabilizados de máscaras por
  contexto y hasta 1024 descriptores. Se comparten objetos inmutables del cache
  real, sin copiar matrices. Es un presupuesto visual, no un nuevo límite de stock.
- Se reservan recursos antes de aceptar una corrida visual, liberando la reserva
  si la aceptación falla. Los contextos activos no se desalojan para otra corrida.
- Al terminar el worker, disponibilidad consultable máxima de 300 s. La limpieza
  es perezosa al reservar/consultar; en reposo no hay temporizador de borrado y
  la memoria sigue acotada a dos contextos. Un contexto terminado puede
  desalojarse antes para admitir otro: disponibilidad temporal explícita, sin
  prometer un mínimo de cinco minutos ni persistencia entre reinicios.
- La proyección de máscaras no conserva todos los intentos; los descriptores se
  deduplican por corrida/geometría/resolución/ángulo. Los límites se prueban contra
  la cota de bases, muestras y ganadores; no se amplían silenciosamente.
- Si no puede conservarse un detalle visual, se informa indisponibilidad y se
  preservan hechos críticos/resultado. No se omiten candidatos, cambia precisión
  ni convierte esa falta de detalle en NO_FIT. Un presupuesto del motor agotado
  mantiene su fallo técnico explícito de T02/TA-037.

Estos límites no afirman un presupuesto global de RAM de API/DB/layouts. La
validación de T03 debe medir coexistencia de caches, referencias y respuestas.
Escalado multiproceso/distribuido requiere decisión adicional, como TA-037.

Tras desconexión se consulta primero `GET /runs/{id}` usando el ID/Location ya
aceptado, después el manifiesto y la máscara visible si siguen disponibles.
El resultado guardado sigue siendo autoritativo aunque falten datos visuales.
Una respuesta de otra corrida/revisión/orientación se ignora en la UI. No se
inicia otro POST automáticamente ni se añade cancelación distribuida/replay.

## 5. Validación obligatoria de T03

1. V1 por defecto: schemas, eventos, GET/confirmación, errores y HU-015 iguales.
2. Negociación: V2 solo por petición explícita; perfil inválido rechazado antes
   de aceptar; lectores separados y rechazo de mezcla de versiones/corridas.
3. Orden real: bases listas antes de búsqueda, ordinales de evaluaciones,
   procesadas/colocadas coherentes y NO_FIT separado de fallos técnicos.
4. Con/sin observación: mismas decisiones FF/BF/WF, rotaciones bajo demanda,
   prioridad de retazos y métricas geométricas; relojes excluyen trabajo visual.
5. Muestreo/cotas: primer intento por unidad, 128 adicionales, reloj controlado,
   límites exactos/+1, hechos críticos íntegros y consumidor lento/desconectado.
6. Máscaras: bits/contorno/resolución/ángulo reales, material irregular,
   deduplicación y ventanas; permisos, referencias cruzadas y respuesta acotada.
7. Retención: dos contextos, reserva/liberación, TTL y desalojo de terminados,
   reinicio/410 y GET persistido conservado; ninguna modificación de inventario.
8. Evidencia backend/contratos y frontend de lectura aplicables. T04 implementa
   la pantalla y sus estados; T05 conserva resultado/confirmación; T06 completa
   cobertura transversal. No se atribuye implementación a esta decisión.

DG-01 quedó cerrada antes de T03 por la elección expresa de B y estas reglas.
La implementación posterior `1ec14f7`/`3574609` y su verificación se registran
en la evidencia final del 28/10. SPEC/PLAN quedan Verified local, sin cambiar
los 26 CA, publicar HU-017 ni atribuir revisión cruzada humana.
