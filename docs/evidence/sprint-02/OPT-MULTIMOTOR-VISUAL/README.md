# Integración visual de FF, BF y WF

Autor: Fabricio Melendez Quezada.
Revisor asignado: Andro Quispe; revisión cruzada pendiente.
Fecha: 31/10/2026.
Rama: `feature/optimization-multimotor-visual`.
Base de código del cierre: `0a2a5441d78f6e06e31383a2cfc7df95e45e6e4c`.
Incluye `59115f4`, `ec3c2b6` y la corrección responsive `0a2a544`.
El backend de esa base es idéntico al probado en `0b30ef4`.

[SPEC](../../../specs/SPEC-OPT-MULTIMOTOR-VISUAL.md) ·
[PLAN](../../../specs/PLAN-OPT-MULTIMOTOR-VISUAL.md) ·
[Guía API](../../../contracts/optimization/comparison-v1.md).

## Resultado y alcance

La ruta principal de Optimización acepta un lote y ejecuta tres procesos reales,
FF/BF/WF, sobre una entrada congelada común. Cada motor tiene su pestaña con
máscaras, orden, giros/colocaciones y resultado. Comparación muestra los tres
estados y métricas; la selección humana se guarda sin consumo de inventario.
Confirmar aplica exclusivamente el elegido, una vez. La solicitud original y
las tres identidades se recuperan sin recalcular.

Estado del cierre: **Implemented — T00–T07 completadas y verificadas localmente**.
SPEC y PLAN reflejan la implementación y esta evidencia. Revisión cruzada de
Andro Quispe y CI remoto pendientes; no se atribuye una aprobación no realizada.

El formulario en centímetros pertenece a `feature/orders-centimeters`, segunda
rama acordada, todavía no creada. Esta entrega mantiene mm/mm²/grados. No se
crearon PR, merges ni despliegues ni se usaron datos de la base remota.

## Validación reproducible

Las pruebas usan PostgreSQL 17 temporal propio, migraciones reales, FastAPI y
motores reales. El entorno medido tiene Linux, Python 3.11.9, Node 24.19.0, Chromium
154.0.8037.57 del sistema, 8 GiB de límite de memoria y cuota de dos CPU. No certifica la
capacidad del despliegue.

| Comprobación del código indicado | Resultado |
|---|---|
| Backend completo | 2453 aprobadas, sin fallos ni skips; 527.00 s |
| Frontend unitarias | 175 aprobadas; 0 fallos, omisiones o cancelaciones |
| Frontend componentes | 514 aprobadas, 49 archivos; 144.80 s después de `59115f4` |
| Avance automático y contrato compartido | 8 aprobadas en 7.35 s; prueba reforzada del paso automático orden → giros → resultado, sin cambiar producción (`095ea67`) |
| Lint / build | Aprobados; advertencia de tamaño de chunk de Vite, build en 474 ms |
| E2E completo, escritorio y móvil | **120 aprobados en 7.6m**, 0 fallos/omisiones; gate de 12 specs críticos en 2 proyectos aprobado |
| E2E enfocados después de correcciones | 8 aprobados en 1.0 min, sin omisiones; comparación y retazo en ambos proyectos |
| API + confirmación enfocadas | 22 aprobadas; 9.22 s; [recursos](t04-api-ui.md) |

Comandos desde `backend/` y `frontend/`, respectivamente, con las dependencias
y binarios PostgreSQL preparados según los README de cada módulo:

```bash
# backend/
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -ra -p no:cacheprovider

# frontend/
node --test --test-isolation=none tests/unit/*.test.js
node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=2
npm run lint
npm run build
NEWGLASS_REQUIRE_POSTGRES=1 NEWGLASS_E2E_GATE=1 npm run test:e2e
```

En esta máquina la ejecución E2E usa un archivo de configuración externo que
importa `frontend/playwright.config.js` y cambia únicamente el ejecutable a
`/usr/bin/chromium`, rutas absolutas y directorio de artefactos. Mantiene los
dos proyectos (1440×900 y 390×844), todos los specs y el reporter del gate.
`workers: 1` evita compartir concurrentemente el servidor exclusivo entre
comparaciones de pruebas distintas; cada comparación sigue lanzando sus tres
procesos. CI puede usar `PLAYWRIGHT_CHANNEL=chromium` con el navegador instalado.

El gate incluye `optimization-comparison.spec.js` entre sus 12 specs críticos;
comprueba su ejecución en ambos proyectos y rechaza omisiones sin aprobación.
Los escenarios FF históricos siguen usando API, BD y componentes reales desde
la entrada de compatibilidad, sin sustituir el nuevo recorrido principal.

## Fallos encontrados y corregidos durante el cierre

La primera pasada completa terminó con 117 aprobados y tres fallos. Dos eran
la nueva prueba de permisos, que pasaba `page` en vez de `page.request` al
auxiliar de login; `ec3c2b6` corrige esa llamada. El tercero reprodujo el fallo
móvil de retazo que figuraba en la auditoría de la base.

El diagnóstico del editor mostró una columna con mínimo de contenido mayor
que el espacio disponible: a 390 px el documento se extendía a 435 px. Ese
exceso alteraba el viewport móvil y el hit test del botón. `0a2a544` cambia
únicamente el mínimo de la columna responsive a `minmax(0, 1fr)`; no cambia
geometría, unidades ni reglas del inventario. La prueba conserva el clic real,
POST 201 y lectura geométrica, y añade una comprobación de desbordamiento
contra `documentElement.clientWidth`, en vez de un `innerWidth` ya expandido.

Tras corregirlos, los ocho E2E enfocados aprobaron en ambos tamaños. El gate
completo posterior sobre `0a2a544` aprobó los 120 escenarios; su resultado se
registra arriba y en el log del cierre. No se introdujeron clics forzados, skips ni desactivación
del gate. La regresión de componentes mantiene 514 aprobadas; el ajuste
posterior es solo CSS y se verifica con layout/clic real en navegador.

## Matriz de los 26 criterios

Las rutas de pruebas backend siguientes son relativas a `backend/tests/`.
Las frontend son relativas a `frontend/`. Los resultados de las suites de
este cierre, una vez registrados, respaldan la matriz; revisión cruzada y CI
remoto se declaran por separado.

| CA | Comprobación y evidencia trazable |
|---|---|
| 01 | `integration/optimization/test_comparison_persistence.py`: aceptación única, tres métodos, idempotencia concurrente y transición única; API y E2E comparativo |
| 02 | Mismo archivo: una captura SQL de stock, solicitud original y estados independientes; `unit/optimization/test_comparison_snapshot.py`: hash, cantidades, configuración y orden |
| 03 | `unit/optimization/test_comparison_runner.py`: barrera, tres PID y resultados equivalentes; [runner medido](t02-runner.json) y [sonda inicial](t00-concurrency.json) |
| 04 | `src/features/optimization/__tests__/ComparisonWorkspace.test.jsx` y `tests/e2e/optimization-comparison.spec.js`: cuatro pestañas, identidades y pausa conservadas |
| 05 | E2E de rotación verifica un solo POST al cambiar pestañas; E2E de comparación comprueba inventario intacto antes/después de elegir |
| 06 | `api/optimization/test_comparisons_api.py`: máscaras reales por motor y 404 cruzado; fixture compartida backend/frontend y E2E de giro |
| 07 | API y E2E: `piece_ready` precede a `ordering_ready`, que precede a colocación; componentes verifican fases; presentación de hechos completados explícita |
| 08 | E2E rotado verifica 90° y máscara orientada en FF/BF/WF; componente usa contorno original y ángulo real, layout orientado sin segundo giro; aviso de muestras |
| 09 | Runner/coordinador prueban hechos intercalados, fallo aislado y guardado previo a notificación; API valida secuencias por método y resultado completo |
| 10 | Nombres/estado en cada pestaña, fase y resultado; componentes y E2E comparativo/rotado |
| 11 | `integration/optimization/test_comparison_calculation.py`, persistencia y codec: éxito, parcial, fallo y fallo al guardar no se mezclan |
| 12 | Componentes: tres filas y métricas con unidades; motor fallido muestra ausencia y conserva éxitos disponibles |
| 13 | Persistencia, API, componentes y E2E: elección inicialmente nula, solo terminales completos guardados; no hay ganador automático |
| 14 | Persistencia: CAS de elecciones concurrentes y stock intacto; E2E guarda BF, confirma y recupera la selección |
| 15 | `integration/optimization/test_comparison_confirmation.py`: FF/BF/WF, repetición concurrente, rollback y carrera selección/liberación; E2E confirma BF y API confirma WF |
| 16 | Codec hace round-trip sin llamar al optimizador; API y E2E recargan las tres identidades y selección; configuración y resultados durables |
| 17 | Persistencia conserva snapshot original; componentes y E2E recuperan piezas/medidas después de métricas y recarga |
| 18 | E2E multipedido/multimaterial incluye rectángulos, círculos y polígonos; detalles rotulan unidades y diferencian dimensiones guardadas/derivadas |
| 19 | E2E en escritorio/móvil: cuatro pestañas, Home/End, giro real, movimiento reducido; capturas seleccionadas del cierre |
| 20 | [T00](t00-recursos.md), [runner](t02-coordinador.md), [HTTP](t04-api-ui.md): presupuestos agregados, IPC, retención y rechazo previo sin aceptar lote |
| 21 | Runner: crash, timeout, cierre consumidor; coordinador: observador perdido y guardado fallido; API: desconexión y reconciliación de supervisor huérfano por identidad |
| 22 | Persistencia: ningún éxito elegible devuelve pedidos solo tras fin seguro; liberación versionada conserva historia; terminación no demostrada conserva admisión/pedidos |
| 23 | Confirmación: stock cambiado y fallo de remanente hacen rollback; liberación conserva historia y permite nuevo lote |
| 24 | API/RBAC y E2E de consulta: 403 en elección sin permiso; persistencia rechaza ejecución ajena y versión obsoleta; confirmación mantiene permiso independiente |
| 25 | Backend completo y E2E históricos: FF V1/visual-v2 preservados; fixture rechaza relabel de motor; migración conserva históricos y bloquea downgrade con historia comparativa |
| 26 | E2E comparativo real: dos pedidos, dos materiales, ocho unidades de tres formas, máscaras/orden, fases/giros, tres resultados, BF manual, confirmación y recarga; E2E rotado fuerza 90° en los tres |

## Evidencia por etapa

- [Inicio y barrera T00](t00-inicio.md), [recursos iniciales](t00-recursos.md).
- [Codec T01](t01-codec.md), [persistencia](t01-persistencia.md).
- [Coordinador T02](t02-coordinador.md) y medición de siete escenarios.
- [Confirmación T03](t03-confirmacion.md).
- [API, recursos HTTP e interfaz T04–T06](t04-api-ui.md).

## Capturas y trazas del código final

Son datos sintéticos de los E2E reales; no contienen pedidos ni stock remoto.
Las capturas de giro incluyen ángulo de 90°, máscara exacta y layout del motor.
La tabla móvil mantiene desplazamiento horizontal interno y conserva el ancho
del documento. Las capturas por panel muestran también contenido fuera del
viewport inicial para que sea inspeccionable.

| Vista | Escritorio | Móvil 390 px |
|---|---|---|
| Máscaras FF | [Ver](screenshots/desktop/mascaras-first-fit.png) | [Ver](screenshots/mobile/mascaras-first-fit.png) |
| Orden FF | [Ver](screenshots/desktop/orden-first-fit.png) | [Ver](screenshots/mobile/orden-first-fit.png) |
| Solicitud y medidas originales | [Ver](screenshots/desktop/solicitud-original.png) | [Ver](screenshots/mobile/solicitud-original.png) |
| Comparación y elección BF | [Ver](screenshots/desktop/comparacion-antes-de-confirmar.png) | [Ver](screenshots/mobile/comparacion-antes-de-confirmar.png) |
| Giro First Fit | [Ver](screenshots/desktop/giro-real-first-fit.png) | [Ver](screenshots/mobile/giro-real-first-fit.png) |
| Giro Best Fit | [Ver](screenshots/desktop/giro-real-best-fit.png) | [Ver](screenshots/mobile/giro-real-best-fit.png) |
| Giro Worst Fit | [Ver](screenshots/desktop/giro-real-worst-fit.png) | [Ver](screenshots/mobile/giro-real-worst-fit.png) |

[Eventos reales de la comparación](comparison-events-desktop.json),
[registro estructurado de validación](validation.json) y
[propiedades de recursos HTTP](t04-http-resources.json). Los logs seleccionados
se conservan en `logs/`; no sustituyen las comprobaciones de estado/BD que
ejecutan las pruebas referenciadas en la matriz.

## Límites y revisión pendiente

- Ejecución supervisada en un solo proceso web Linux. No coordinación entre
  varias réplicas; una comparación activa comparte admisión exclusiva con FF.
- Máscaras/eventos efímeros: hasta cinco minutos tras finalizar o sustitución
  por otra comparación. Snapshot de solicitud, resultados y elección son durables.
- RSS muestreado con reserva auxiliar y límites duros de espacio virtual por
  worker. Los escenarios medidos no certifican el peor caso combinado ni un
  despliegue remoto. No se ofrece degradación secuencial silenciosa.
- Los datos históricos solo muestran lo guardado; las medidas derivadas se
  etiquetan. No se corrigen hallazgos generales previos de inventario/RBAC.
- Andro Quispe sigue como revisor asignado. El workflow de CI se activa en PR o
  push a `main`/`integration/sprint-01`, por lo que este push de feature no lo
  dispara. PR/merge/despliegue quedan fuera de esta autorización.
- Los commits nuevos desde `da659f2` usan el correo noreply de GitHub y se
  verificó su asociación a `melendezzz26`. Los publicados antes conservan su
  historia; asociar/verificar `fabrimq2602@gmail.com` en esa cuenta permite a
  GitHub atribuirlos sin reescribirla. El calendario de contribuciones también
  depende de que los commits alcancen la rama predeterminada.
