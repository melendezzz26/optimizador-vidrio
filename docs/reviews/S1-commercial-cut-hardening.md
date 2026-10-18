# Cierre P0: corte comercial y trazabilidad

Rama `chore/S1-final-integration`. Cierre: 2026-10-17, America/Lima.
Verificaciones realizadas durante el 16 y 17 de octubre. Base de este ajuste:
`305457e`. Sin push, PR ni cambios en Supabase.

## Causa y corrección del límite

`RasterCache._raster()` aplicaba los límites de la vista previa HU-015 al motor:
**1 000 000 celdas y 2440 celdas por eje**. Una plancha de 2140 × 3300 a 1 mm
requiere 7 062 000 celdas y un eje de 3300: excedía ambos límites antes de colocar
la primera pieza. Además, el preflight del inicio reutilizaba el presupuesto de
respuesta JSON de HU-015 para las piezas.

La representación anterior y posterior es la misma: **tupla de filas, cada fila
un entero Python usado como bitset**. No hay un objeto, tupla o elemento de set
por celda. Una máscara de 4000 × 4000 ocupa 2 272 040 bytes en este entorno.

- HU-015 conserva su presupuesto y su límite de respuesta JSON de 262 144 bytes.
- First Fit admite hasta **4000 mm por dimensión, 4000 celdas por eje y
  16 000 000 celdas por máscara**, a 1 mm en el rango comercial aprobado.
- La caché tiene un presupuesto conservador de 64 MiB, comprobado antes de
  construir cada máscara. Incluye una cota para claves, geometrías y orientaciones.
- Los estados de planchas usadas tienen una cota adicional de 128 MiB. Las
  pruebas fallidas de candidatos no retienen miles de estados vacíos.
- Una dimensión de 4001 mm se rechaza antes de reservar la máscara. Los errores
  de precisión siguen siendo errores; no se traducen a falta de espacio.
- Solo se omiten orientaciones cuya caja excede cualquier rejilla de stock
  admitida. Una diagonal imposible no oculta una orientación válida de 0°/90°.

No se implementó resolución adaptativa: se conserva la resolución configurada
en material, piezas y resultado, incluida **1 mm** en ambos casos de benchmark.

Para evitar un coste por cada columna candidata, la búsqueda intersecta bitsets
de posiciones válidas y elige el primer bit de la primera fila válida. Se mantiene
el orden candidato → orientación → fila → columna. Una regresión compara 200
rejillas irregulares reproducibles contra la búsqueda exhaustiva, incluyendo
margen, separación y una segunda colocación. Las métricas agrupan filas libres
consecutivas idénticas; conservan el rectángulo máximo y sus desempates de R4.

## Tiempo y memoria medidos

[Datos completos y huella del script](../evidence/sprint-01/S1-COMMERCIAL-CUT/benchmark.json).
Windows, CPython 3.11; medición local, no una garantía de latencia del servidor.
El tiempo incluye First Fit y métricas, sin DB, red ni `tracemalloc`. Otra medición
ejecuta tres cálculos idénticos con `tracemalloc` y recoge la memoria retenida
después de GC. El máximo del proceso incluye intérprete/importaciones del
benchmark, no el servidor FastAPI completo.

| Plancha, a 1 mm | Máscara, bytes | Cálculo + métricas | Heap Python máximo | Máximo del proceso | Retenido tras 3 cálculos |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2140 × 3300 | 1 056 040 | 51.933 ms | 3 266 356 bytes | 32 931 840 bytes | 984 bytes |
| 4000 × 4000 | 2 272 040 | 76.374 ms | 6 843 444 bytes | 39 325 696 bytes | 896 bytes |

El script falla si el heap medido supera 64 MiB, si quedan más de 1 MiB retenidos,
si las repeticiones difieren o si no coloca las ocho unidades. No se observó
crecimiento retenido de máscaras entre cálculos.

## Resultado equivalente a #64

Se validó Bronce de 6 mm, stock inicial de 10 planchas activas de 2140 × 3300 y
ocho unidades de 600 × 800 mm. Estas dimensiones de pieza son una entrada de
regresión explícita: no se obtuvo la geometría del pedido #64 remoto.

El recorrido E2E crea el pedido en la interfaz, verifica el espesor al editarlo,
revisa el vidrio, calcula y recibe **8/8**, `COMPLETADA`, métricas y confirmación
habilitada. Revisa 2D, cámara XYZ, merma, confirma y abre el retazo desde inventario.
Finalmente abre el corte persistido desde el retazo y comprueba que no se envía
otro POST de cálculo. Corre en escritorio y móvil, sin respuestas simuladas.

Las posiciones a 1 mm son (x, y, giro):

```text
(0,0,0)       (600,0,0)       (1200,0,0)
(0,800,0)     (600,800,0)     (1200,800,0)
(0,1600,0)    (600,1600,0)
```

El dominio repite el mismo input/configuración y exige el mismo resultado.
Los IDs de nuevas ejecuciones y el tiempo de cálculo no son parte de esa
comparación geométrica.

| Magnitud | Área | Porcentaje del material utilizado |
| --- | ---: | ---: |
| Material utilizado | 7 062 000 mm² | 100 % |
| Área aprovechada | 3 840 000 mm² | 54.376 % |
| Retazo reutilizable | 1 926 000 mm² | 27.273 % |
| Merma no reutilizable | 1 296 000 mm² | 18.352 % |

Los porcentajes se redondean de manera independiente. Se conserva la semántica
de [SPEC](../specs/SPEC-S1-optimization-first-fit.md) y
[PLAN, R4](../specs/PLAN-S1-optimization-first-fit.md): un rectángulo recuperable
máximo por unidad física utilizada, sujeto a los mínimos configurados. La merma
es material utilizado menos área de piezas menos retazo recuperable.

En 2D se ven las piezas, el rectángulo recuperable verde exacto y el espacio
restante rayado. La ubicación del sombreado de merma se declara **aproximada**,
especialmente en curvas y separación; no se inventan polígonos de merma exactos.
El área numérica conserva el cálculo R4.

Antes de confirmar, el inventario permanece idéntico. Después, la plancha pasa
de **10 a 9** y se crea un retazo **2140 × 900 mm**. Se comprueban la confirmación
atómica, la recuperación por GET y el rechazo 409 de una segunda confirmación.
También se verifica por API el caso máximo de 4000 × 4000, incluida su confirmación.

La [evidencia estructurada](../evidence/sprint-01/S1-COMMERCIAL-CUT/scenario.json)
registra los IDs reales de las corridas locales: escritorio, pedido #22 → trabajo
#11 → retazo #8, ejecución de origen #11; móvil, pedido #44 → trabajo #22 → retazo
#16, ejecución de origen #22. Son registros sintéticos del servidor de pruebas.

## Vistas, origen y espesor

La cámara usa el vidrio en **XY** (misma convención de la vista 2D) y **Z** para
grosor/elevación visual y altura de cámara. La proyección perspectiva admite
órbita de 360°, elevación de 5° a 90°, pan, zoom, rueda, teclado y arrastre en ambos
ejes, también en móvil. Incluye Vista superior, Vista en perspectiva, Centrar
corte y Restablecer vista, además de indicadores X/Y/Z. Las coordenadas, los
giros y las geometrías del resultado no se modifican; no se añade Z al algoritmo.

La geometría de retazos ya estaba guardada en `residual_rectangles`. Se añade
`residual_regions` opcional a la respuesta v1, con referencias físicas y
rectángulos validados. Los resultados antiguos sin ese campo siguen siendo
admitidos. No se añaden métricas ni se cambia su significado.

`GET /api/inventory/retazos/{id}/origen`, protegido por `inventory.view`, deriva
el trabajo/pedidos desde **`id_ejecucion_origen`** y obtiene la plancha/retazo
físico del recibo de confirmación. No se duplica la relación en la DB. El historial
muestra origen, trabajo, pedidos, fecha, vidrio/espesor, área y dimensiones.
`Ver corte de origen` respeta `optimization.view` y consulta el resultado guardado.
Los retazos sin ejecución muestran `Registro manual o histórico`.

La vista previa usa una copia de `geometria`: rectángulo, circunferencia y
polígono con coordenadas negativas, también cuando Inventory devuelve medidas
Decimal como strings. Se conservan los valores persistidos y se indica la escala
de pantalla, con dimensiones en mm.

En Orders, `6.0` en el estado del grupo no coincidía con la opción del catálogo
`6`: el navegador mostraba el placeholder, aunque el estado conservaba el valor
y el payload lo convertía a número 6. Era una desincronización visual. Se normaliza
la lectura del espesor al valor canónico del selector. La regresión abre el grupo,
comprueba la opción visible y verifica que el PUT conserva **6 mm**.

## Validación

| Comprobación | Resultado |
| --- | --- |
| Backend completo | **1993 passed, 1 warning**, 462.99 s |
| Raster, rotaciones, First Fit y dominio, reconfirmados | **313 passed**, 1.52 s |
| API comercial 2140 × 3300 y 4000 × 4000, reconfirmada | **2 passed, 1 warning**, 12.17 s |
| Frontend unit | **159 passed**, sin fallos ni skips |
| Frontend component | **468 passed**, 41 archivos |
| ESLint | **0 errores, 0 warnings** |
| Build | **OK** |
| E2E focalizados, escritorio/móvil | **46 passed, 0 failed, 0 skips**, 2.1 min, salida nativa 0 |
| Alembic | Única head **`s1opt02b4c6d`** |
| `git diff --check` | **OK** |

El warning backend es la deprecación existente de `httpx` en Starlette TestClient.
Los avisos de color y cierre de conexiones del servidor local Windows se
conservaron en los logs temporales; no causaron fallos de Playwright.

Reproducir desde `backend/`, con el venv y PostgreSQL de pruebas disponibles:

```text
python -m pytest -q
python -m pytest tests/unit/optimization tests/optimization -q
python -m pytest tests/api/optimization/test_commercial_cut.py -q
python -m scripts.benchmark_commercial_cutting
python -m alembic heads
```

Desde `frontend/`, con el Python del venv en PATH y las credenciales sintéticas
HU-015 indicadas en su spec E2E:

```text
npm run test:unit
npm run test:component
npm run lint
npm run build
npm run test:e2e -- hu007-order-integration.spec.js hu012-client-order.spec.js s1-optimization-ui.spec.js hu015-rasterization.spec.js hu014-inventory-writeoff.spec.js ta036-retazo-personalizado.spec.js
```

Las pruebas usan PostgreSQL temporal y APIs locales. Se conservan solo cuatro
capturas, un JSON del escenario y un JSON del benchmark, con su
[índice](../evidence/sprint-01/S1-COMMERCIAL-CUT/README.md). No se modifican
migraciones ni evidencia histórica. [Manifiesto final](S1-final-integration-files.txt).
