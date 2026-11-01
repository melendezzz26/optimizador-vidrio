# API, observación y experiencia comparativa

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión pendiente.
Fecha: 31/10/2026.

## Código y contratos

- `da659f2`: API comparativa, admisión previa, supervisión, observación NDJSON,
  cursores, máscaras aisladas y recuperación de procesos detenidos.
- `d9d0ee4`: trazabilidad física del remanente elegido y reconciliación antes de
  sustituir una comparación retenida.
- `0b30ef4`: controlador frontend, cuatro pestañas, fases, giros reales,
  comparación, solicitud original, elección/confirmación y pruebas compartidas.

La [guía del contrato](../../../contracts/optimization/comparison-v1.md) describe
rutas, versiones, permisos, idempotencia y límites. La
[fixture compartida](../../../contracts/optimization/comparison-v1.json) conserva
resultados y hechos reales FF/BF/WF. Backend y frontend verifican el mismo
archivo. Su captura de serialización es secuencial; no constituye evidencia de
concurrencia. Esta se verifica con tres procesos reales y barrera en
`test_comparison_runner.py`, el coordinador y los E2E.

## Verificación enfocada previa al gate completo

En `backend/`, con Python 3.11.9 y PostgreSQL 17 temporal propio:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest \
  tests/api/optimization/test_comparisons_api.py \
  tests/integration/optimization/test_comparison_confirmation.py \
  -q -ra -p no:cacheprovider -o junit_family=xunit1 \
  --junitxml=/tmp/comparison-http-resources.xml
```

Resultado: **22 passed in 9.22s**, sin fallos ni skips. Advertencia existente de
Starlette/httpx sobre TestClient. El XML registra propiedades de recursos del
recorrido HTTP; la salida seleccionada se conserva en
[t04-http-resources.json](t04-http-resources.json).

Cobertura relevante: tres resultados con identidad y máscaras propias, eventos
tipados/secuencias, rechazo de referencia de otro motor, elección sin consumo,
confirmación WF idempotente, origen físico del retazo vía API de inventario,
reconexión/cursor vencido, presupuesto visual agotado sin perder resultados,
CORS con clave de idempotencia, desconexión que libera observador y deja seguir
el cálculo, supervisor huérfano y rechazo de memoria antes de aceptar pedidos.
La confirmación se parametriza con FF, BF y WF y prueba carreras y rollback.

## Recursos a través de FastAPI

Escenario sintético HTTP: dos pedidos pequeños, tres motores reales con
PostgreSQL, obtención de máscaras, elección y confirmación WF. Se mide el
proceso que sirve FastAPI dentro de TestClient —incluye pytest— y los tres
trabajadores. No es una medición de capacidad del despliegue.

| Magnitud | Observado |
|---|---:|
| Máximo de sumas RSS muestreadas + reserva auxiliar | 175800320 bytes (167.66 MiB) |
| Pico RSS del supervisor/TestClient | 99696640 bytes (95.08 MiB) |
| Pico por worker FF / BF / WF | 19951616 / 19931136 / 19927040 bytes |
| Muestras / mayor intervalo observado | 12 / 38.31 ms |
| Mayor paquete / máxima cola por worker | 3468 bytes / 1 paquete |
| Máscaras retenidas entre los tres | 56484 bytes |
| Eventos retenidos | 53988 bytes, 89 eventos |
| Tiempo incluyendo IPC y limpieza | 368.70 ms |
| Trabajadores detenidos al finalizar | Los tres, comprobados |

Complementa los siete escenarios de límites del
[runner](t02-coordinador.md) y las sondas [T00](t00-recursos.md). El recorrido
HTTP aplica un presupuesto visual **total**, no 32 MiB por motor; su agotamiento
se prueba con un presupuesto deliberadamente pequeño. Eventos: hasta 8 MiB y
4096 registros. Dos observadores como máximo, lotes de 16 eventos, ventanas
de máscaras de hasta 256 KiB. El rechazo previo de memoria conserva pedidos y
no crea comparación, y devuelve la admisión.

RSS se muestrea y puede omitir picos; las páginas compartidas se cuentan varias
veces. La reserva auxiliar no es una medición del `resource_tracker`. Los casos
grandes se ejercitan por separado; esta evidencia no certifica el triple peor
caso ni una infraestructura remota. T00 queda cerrado como presupuesto inicial
aplicado y medido en este entorno, sujeto a esas limitaciones.

La regresión completa posterior del backend, con el mismo código funcional,
aprobó **2453 pruebas en 527.00 s**, sin fallos ni skips. El
[cierre](README.md) conserva el registro y los comandos.

## Interfaz y compatibilidad

El controlador mantiene una comparación fuera de los paneles. Cada panel
permanece montado al cambiar de pestaña, conservando pausa e inspección. La
aceptación ambigua se recupera por clave; la recarga obtiene el estado guardado.
No se selecciona automáticamente el primero en terminar ni el de mejor métrica.

Las fases recorren solo hechos disponibles. Una transición de presentación
de 550 ms no detiene los motores y se identifica como pasos observados cuando
el cálculo ya terminó. El contorno usa el ángulo real del backend; el layout
usa geometría ya orientada sin un segundo giro. Movimiento reducido conserva
ángulos/máscaras con transición desactivada. Pausar solo congela la vista.

Los datos originales distinguen metadatos guardados de dimensiones derivadas;
se rotulan mm/mm²/grados. La tabla de métricas muestra fallos como ausencia,
conserva éxitos elegibles después de terminar los tres y exige elección expresa.
Los controles de ejecución y confirmación respetan permisos; backend vuelve a
comprobarlos.

El recorrido principal usa `/comparisons`. Los E2E históricos de FF usan una
entrada dedicada `first-fit-compatibility.html` que renderiza el mismo componente
legacy y llama la API real, sin sustituir el flujo comparativo de producción.
Ese HTML no es una entrada del build productivo. No se eliminaron escenarios
históricos ni se añadieron skips para obtener un gate verde.

El [cierre consolidado](README.md) registra el gate completo, capturas, matriz
de los 26 criterios y los límites pendientes de revisión/despliegue.

La corrección `59115f4` renueva la clave al iniciar otro lote después de
confirmar, incluso usando directamente los pedidos pendientes. La prueba de
componentes cubre esta segunda intención con un pedido diferente; no reutiliza
la identidad de aceptación del trabajo confirmado. `ec3c2b6` corrige el cliente
HTTP del auxiliar de login del E2E de permisos y amplía capturas/recuperación.

La regresión móvil previa de retazo se reprodujo y se diagnosticó como
desbordamiento del mínimo de una columna CSS del editor compartido. La
corrección `0a2a544` conserva geometría y reglas de inventario; ocho E2E
enfocados posteriores pasaron en 1.0 min, con clic real y POST 201. El
[cierre](README.md) explica el diagnóstico y registra el gate completo posterior.
