# SPEC-HU-007-T02 — Asociar medidas reales al dibujo

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-007 |
| Tarea relacionada | T02 — Asociar medidas reales al dibujo |
| Responsable | Andro Quispe Cesias |
| Reviewer | Andro Joseph Quispe Cesias |

## 1. Objetivo

Permitir que el Operario asocie dimensiones reales, expresadas en milímetros, al polígono dibujado mediante el editor implementado en HU-007 T01.

El sistema debe utilizar el ancho y alto reales ingresados por el Operario para transformar automáticamente las coordenadas gráficas de los vértices del lienzo a coordenadas equivalentes en milímetros, sin requerir el ingreso manual de coordenadas.

La finalidad de esta tarea es obtener una representación geométrica dimensionalmente consistente que pueda ser utilizada posteriormente por la validación geométrica de HU-007 T03 y por el flujo de registro de piezas.

T02 no determina si el polígono es convexo ni si es geométricamente válido para corte. Esa responsabilidad corresponde a HU-007 T03.

Las dimensiones `Ancho total` y `Alto total` representan las dimensiones exteriores máximas de la pieza respecto al bounding box del polígono y no la longitud de un segmento particular.

Cuando ambas dimensiones sean válidas, la interfaz debe proporcionar una previsualización proporcional de la pieza para que el Operario pueda identificar visualmente relaciones dimensionales extremas o posibles errores de digitación.

## 2. Alcance

### Incluye

- Permitir asociar un ancho real al polígono dibujado.
- Permitir asociar un alto real al polígono dibujado.
- Utilizar milímetros como unidad de medida.
- Solicitar las dimensiones reales después de que el polígono haya sido cerrado gráficamente.
- Validar que el ancho y alto sean valores numéricos mayores que cero.
- Obtener el bounding box del dibujo a partir de sus vértices gráficos.
- Normalizar las coordenadas gráficas respecto al bounding box del polígono.
- Transformar automáticamente cada vértice gráfico a coordenadas expresadas en milímetros.
- Mantener el orden original de los vértices.
- Establecer el origen dimensional del polígono normalizado en `(0, 0)`.
- Recalcular las coordenadas dimensionales cuando el Operario modifique el ancho o el alto.
- Verificar la transformación con al menos un caso conocido cuyo resultado pueda comprobarse manualmente.
- Preparar la geometría dimensional para su posterior utilización por T03 y por la integración del pedido.
- Mostrar las dimensiones como `Ancho total` y `Alto total`.
- Representar visualmente el ancho total mediante una cota horizontal.
- Representar visualmente el alto total mediante una cota vertical.
- Adaptar la previsualización del polígono a la proporción real `widthMm : heightMm` cuando ambas dimensiones sean válidas.
- Ajustar la previsualización proporcional dentro del lienzo sin deformar la relación entre ancho y alto.
- Mostrar el siguiente paso del flujo mediante una acción `Agregar pieza al pedido` deshabilitada mientras la validación geométrica de T03 no haya sido ejecutada.

### Fuera de alcance

- Ingreso manual de coordenadas de los vértices.
- Modificación individual de las coordenadas de cada vértice.
- Validación de convexidad.
- Detección de polígonos cóncavos.
- Detección de autointersecciones.
- Determinar si el polígono está permitido para corte.
- Rasterización de la geometría.
- Ejecución de las heurísticas First Fit, Best Fit o Worst Fit.
- Optimización de corte.
- Cálculo o selección de planchas y retazos.
- Persistencia definitiva de la pieza en base de datos.
- Modificaciones estructurales de base de datos.
- Migraciones Alembic.
- Plantillas de polígonos.
- Reconocimiento automático de formas.
- Recomendaciones automáticas de tipo de figura.
- Implementación de circunferencias o rectángulos mediante este editor.
- Conversión del polígono a `POLIGONO_CONVEXO` validado antes de ejecutar T03.
- Habilitar funcionalmente `Agregar pieza al pedido` antes de completar T03.
- Asignar automáticamente una dimensión física predeterminada al dibujo.
- Utilizar `100 mm` u otro valor como medida real asumida sin intervención del Operario.
- Dimensionar individualmente cada segmento del polígono.
- Resolver restricciones geométricas tipo CAD basadas en longitudes y ángulos.

## 3. Actor y precondiciones

**Actor:** Operario.

**Precondiciones:**

- El editor de pieza personalizada de HU-007 T01 se encuentra disponible.
- Existe un dibujo con al menos tres vértices.
- El polígono se encuentra gráficamente cerrado mediante la acción `Cerrar polígono`.
- Los vértices mantienen el orden en que fueron ingresados por el Operario.
- Las coordenadas actuales corresponden al sistema gráfico del SVG y todavía no representan milímetros.
- El dibujo dispone de extensión distinta de cero tanto en el eje X como en el eje Y para poder realizar la transformación dimensional.
- No se requiere que el polígono sea convexo en esta tarea.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| `vertices` | Arreglo de objetos `{x, y}` | Coordenadas gráficas obtenidas en T01 y conservadas en el orden de dibujo |
| `isClosed` | Boolean | Debe ser `true` antes de asociar dimensiones reales |
| `widthMm` | Número | Ancho exterior total del bounding box, obligatorio, mayor que 0 y expresado en mm |
| `heightMm` | Número | Alto exterior total del bounding box, obligatorio, mayor que 0 y expresado en mm |
| `minX` | Número calculado | Menor coordenada X de los vértices |
| `maxX` | Número calculado | Mayor coordenada X de los vértices |
| `minY` | Número calculado | Menor coordenada Y de los vértices |
| `maxY` | Número calculado | Mayor coordenada Y de los vértices |
| `drawingWidth` | Número calculado | `maxX - minX`; debe ser mayor que 0 |
| `drawingHeight` | Número calculado | `maxY - minY`; debe ser mayor que 0 |
| `scaledVertices` | Arreglo de pares o puntos dimensionales | Coordenadas resultantes expresadas en milímetros |
| `previewWidth` | Número calculado | Ancho usado únicamente para representar proporcionalmente la pieza en pantalla |
| `previewHeight` | Número calculado | Alto usado únicamente para representar proporcionalmente la pieza en pantalla |

La unidad dimensional utilizada por T02 es exclusivamente **milímetros (mm)**.

Las coordenadas del SVG utilizadas por T01 son únicamente coordenadas gráficas y no deben interpretarse directamente como milímetros.

### Transformación de coordenadas

Para cada vértice gráfico `(x, y)`:

`x_mm = ((x - minX) / (maxX - minX)) * widthMm`

`y_mm = ((y - minY) / (maxY - minY)) * heightMm`

De esta forma:

- el valor mínimo de X se transforma en `0 mm`;
- el valor máximo de X se transforma en `widthMm`;
- el valor mínimo de Y se transforma en `0 mm`;
- el valor máximo de Y se transforma en `heightMm`.

El origen dimensional resultante se establece en la esquina superior izquierda del bounding box normalizado:

`(0, 0)`.

T02 aplica escalamiento independiente en los ejes X e Y para hacer coincidir el dibujo realizado por el Operario con el ancho y alto reales indicados.

### Previsualización proporcional

La previsualización dimensional debe representar visualmente la relación:

`widthMm : heightMm`

La pieza debe escalarse únicamente para caber dentro del área disponible de visualización, manteniendo la relación entre ancho y alto.

Por ejemplo:

- una pieza `1200 × 700 mm` debe verse proporcionalmente más ancha que alta;
- una pieza `200 × 5000 mm` debe verse notablemente alta y estrecha;
- una pieza `5000 × 200 mm` debe verse notablemente ancha y baja.

La adaptación al espacio disponible es únicamente visual y no debe modificar los valores de `scaledVertices`.

## 5. Reglas de negocio

- RN-01: Las dimensiones reales solo pueden asociarse cuando el polígono se encuentra gráficamente cerrado.
- RN-02: El Operario no debe ingresar manualmente coordenadas de vértices.
- RN-03: El ancho real debe expresarse en milímetros y ser mayor que cero.
- RN-04: El alto real debe expresarse en milímetros y ser mayor que cero.
- RN-05: No se permite realizar la conversión si el ancho gráfico del bounding box es igual a cero.
- RN-06: No se permite realizar la conversión si el alto gráfico del bounding box es igual a cero.
- RN-07: La transformación debe utilizar el bounding box formado por los vértices dibujados, no el tamaño total del SVG.
- RN-08: El vértice ubicado en `minX` debe corresponder dimensionalmente a `x = 0 mm`.
- RN-09: El vértice ubicado en `maxX` debe corresponder dimensionalmente a `x = widthMm`.
- RN-10: El vértice ubicado en `minY` debe corresponder dimensionalmente a `y = 0 mm`.
- RN-11: El vértice ubicado en `maxY` debe corresponder dimensionalmente a `y = heightMm`.
- RN-12: La transformación debe conservar el orden original de los vértices.
- RN-13: Si el Operario modifica el ancho o alto, las coordenadas dimensionales deben recalcularse utilizando los nuevos valores.
- RN-14: Las coordenadas gráficas originales utilizadas por el lienzo no deben ser reemplazadas por las coordenadas en milímetros.
- RN-15: Las coordenadas dimensionales generadas por T02 deben mantenerse separadas de las coordenadas gráficas de T01.
- RN-16: T02 no debe declarar que el polígono es convexo o válido para optimización.
- RN-17: La validación de convexidad corresponde exclusivamente a HU-007 T03.
- RN-18: Las dimensiones deben utilizar una única unidad consistente: milímetros.
- RN-19: El sistema debe poder verificar la conversión mediante al menos un caso de prueba con valores conocidos.
- RN-20: T02 no realiza persistencia definitiva de la pieza en base de datos.
- RN-21: `widthMm` representa el ancho exterior máximo de la pieza y no la longitud de uno de sus lados.
- RN-22: `heightMm` representa el alto exterior máximo de la pieza y no la longitud de uno de sus lados.
- RN-23: El sistema no debe asignar automáticamente una medida física predeterminada al polígono.
- RN-24: Los campos pueden utilizar ejemplos o placeholders, pero estos no deben considerarse dimensiones ingresadas.
- RN-25: Cuando ancho y alto sean válidos, la previsualización debe conservar la relación proporcional `widthMm : heightMm`.
- RN-26: La previsualización proporcional debe ajustarse al área disponible del lienzo sin deformarse.
- RN-27: Las cotas visuales deben mostrar claramente qué medida corresponde al ancho total y cuál al alto total.
- RN-28: La acción `Agregar pieza al pedido` permanecerá deshabilitada durante T02 y deberá informar que requiere la validación geométrica de T03.

## 6. Flujo principal

1. El Operario dibuja el contorno de la pieza utilizando el editor desarrollado en T01.
2. El Operario agrega al menos tres vértices.
3. El Operario selecciona `Cerrar polígono`.
4. El sistema cierra gráficamente el polígono.
5. El sistema habilita o muestra la sección `Dimensiones reales`.
6. El Operario ingresa el ancho exterior total de la pieza en milímetros.
7. El Operario ingresa el alto exterior total de la pieza en milímetros.
8. El sistema valida que ambos valores sean números mayores que cero.
9. El sistema calcula `minX`, `maxX`, `minY` y `maxY` utilizando los vértices gráficos.
10. El sistema calcula el ancho y alto gráficos del bounding box.
11. El sistema normaliza cada vértice respecto al bounding box.
12. El sistema escala las coordenadas normalizadas según el ancho y alto reales indicados.
13. El sistema obtiene los vértices equivalentes expresados en milímetros.
14. El sistema mantiene las coordenadas gráficas originales para conservar el borrador realizado por el Operario.
15. El sistema conserva temporalmente la geometría dimensional para su posterior validación en T03.
16. El sistema genera una previsualización proporcional utilizando la relación entre ancho total y alto total.
17. El sistema ajusta la previsualización dentro del área disponible conservando la proporción dimensional.
18. El sistema muestra una cota horizontal correspondiente al ancho total.
19. El sistema muestra una cota vertical correspondiente al alto total.
20. La interfaz informa al Operario las dimensiones reales asociadas, por ejemplo: `1200 × 700 mm`.
21. La interfaz muestra la acción `Agregar pieza al pedido` como siguiente paso.
22. La acción `Agregar pieza al pedido` permanece deshabilitada hasta que HU-007 T03 valide geométricamente el polígono.

## 7. Flujos alternativos y errores

- Si el polígono todavía se encuentra abierto, la sección de dimensiones reales no debe permitir la conversión.
- Si el ancho está vacío, no debe generarse geometría dimensional.
- Si el alto está vacío, no debe generarse geometría dimensional.
- Si el ancho es igual o menor que cero, debe considerarse inválido.
- Si el alto es igual o menor que cero, debe considerarse inválido.
- Si el usuario ingresa un valor no numérico, no debe generarse la geometría dimensional.
- Si `maxX - minX = 0`, no debe ejecutarse la transformación para evitar una división entre cero.
- Si `maxY - minY = 0`, no debe ejecutarse la transformación para evitar una división entre cero.
- Si el Operario cambia el ancho después de una conversión válida, el sistema debe recalcular las coordenadas X en milímetros.
- Si el Operario cambia el alto después de una conversión válida, el sistema debe recalcular las coordenadas Y en milímetros.
- Si el Operario cambia cualquiera de las dimensiones, la previsualización proporcional debe actualizarse automáticamente.
- Si el Operario introduce una relación dimensional extrema, la pieza debe ajustarse al espacio disponible sin perder la proporción real.
- Si el Operario utiliza `Deshacer` y el polígono vuelve al estado abierto, las dimensiones asociadas no deben considerarse una geometría confirmada.
- Si el Operario utiliza `Reiniciar dibujo`, deben eliminarse los vértices y las dimensiones reales asociadas al borrador actual.
- Un polígono cóncavo puede llegar a esta etapa y recibir dimensiones reales; su rechazo corresponde a T03.
- El sistema no debe presentar mensajes que indiquen `polígono válido`, `polígono convexo` o equivalentes durante T02.
- La acción `Agregar pieza al pedido` no debe habilitarse aunque las dimensiones sean válidas mientras no se haya ejecutado T03.
- El sistema debe informar de forma comprensible que la pieza requiere validación geométrica antes de poder agregarse al pedido.

## 8. Criterios de aceptación

- CA-01: La sección de dimensiones reales solo permite asociar medidas cuando el polígono se encuentra gráficamente cerrado.
- CA-02: El Operario puede ingresar ancho y alto reales expresados en milímetros sin ingresar manualmente coordenadas de vértices.
- CA-03: El sistema rechaza ancho o alto no numéricos o menores o iguales que cero y no genera geometría dimensional mientras falte alguna dimensión requerida.
- CA-04: El sistema calcula el bounding box utilizando exclusivamente los vértices dibujados.
- CA-05: El sistema normaliza automáticamente los vértices respecto a `minX`, `maxX`, `minY` y `maxY`.
- CA-06: El sistema transforma automáticamente los vértices gráficos a coordenadas equivalentes expresadas en milímetros.
- CA-07: El resultado dimensional tiene origen `(0, 0)` respecto al bounding box del dibujo.
- CA-08: El ancho máximo de la geometría transformada coincide con el ancho real ingresado.
- CA-09: El alto máximo de la geometría transformada coincide con el alto real ingresado.
- CA-10: El orden de los vértices transformados coincide con el orden de los vértices gráficos originales.
- CA-11: Modificar el ancho o alto provoca el recálculo de las coordenadas dimensionales.
- CA-12: Reiniciar el dibujo elimina también las dimensiones asociadas al borrador.
- CA-13: T02 no ejecuta validación de convexidad ni declara la geometría como válida para corte.
- CA-14: Al menos un caso de prueba conocido demuestra que la conversión gráfica a milímetros produce el resultado esperado.
- CA-15: La interfaz identifica las dimensiones como `Ancho total` y `Alto total`, entendidas como las dimensiones exteriores máximas del bounding box.
- CA-16: Cuando ancho y alto son válidos, la previsualización conserva la relación proporcional entre ambas dimensiones.
- CA-17: Una relación extrema, por ejemplo `200 × 5000 mm`, se visualiza como una pieza proporcionalmente alta y estrecha, ajustada al espacio disponible sin deformación.
- CA-18: La interfaz muestra cotas visuales para identificar el ancho total y el alto total.
- CA-19: Los campos no contienen una medida real predeterminada; cualquier ejemplo se presenta únicamente como placeholder.
- CA-20: `Agregar pieza al pedido` permanece deshabilitado durante T02 e informa que requiere la validación geométrica de T03.

### Caso de aceptación conocido

Dado el siguiente dibujo:

- A = `(100, 100)`
- B = `(500, 100)`
- C = `(500, 300)`
- D = `(100, 300)`

El bounding box gráfico es:

- `minX = 100`
- `maxX = 500`
- `minY = 100`
- `maxY = 300`
- ancho gráfico = `400`
- alto gráfico = `200`

Cuando el Operario indique:

- ancho real = `1000 mm`
- alto real = `500 mm`

El resultado dimensional esperado será:

- A = `(0, 0)`
- B = `(1000, 0)`
- C = `(1000, 500)`
- D = `(0, 500)`

La relación proporcional de la previsualización será:

`1000 : 500 = 2 : 1`

Por tanto, la pieza debe visualizarse proporcionalmente con un ancho aproximado al doble de su alto, independientemente del tamaño de píxel utilizado para ajustarla al lienzo.

Este caso debe utilizarse como prueba verificable de la transformación implementada en T02.

### Caso de aceptación de relación extrema

Cuando el Operario indique:

- ancho total = `200 mm`
- alto total = `5000 mm`

la relación dimensional será:

`200 : 5000 = 1 : 25`

La previsualización debe representar una pieza claramente alta y estrecha, ajustada al área disponible sin alterar la relación dimensional.

Este caso no debe considerarse inválido únicamente por presentar una proporción extrema.

## 9. Impacto técnico

### Módulos

Frontend:

- `frontend/src/features/orders/`
- Extensión del editor de pieza personalizada desarrollado en T01.
- Lógica dimensional separada en `geometryScaling.js`.
- Pruebas unitarias de transformación dimensional dentro de `frontend/tests/unit/`.

La lógica de transformación dimensional debe mantenerse dentro del feature `orders` y separarse de la lógica puramente visual para facilitar sus pruebas.

No se debe introducir lógica de optimización ni rasterización dentro del componente del editor.

La previsualización proporcional debe utilizar las dimensiones reales únicamente para ajustar la representación visual, sin modificar las coordenadas originales almacenadas como borrador de T01.

### API

T02 debe preparar una representación dimensional consistente en milímetros para que pueda ser utilizada posteriormente por el flujo de pedidos.

La integración con una API de persistencia definitiva no forma parte obligatoria de esta tarea mientras el flujo de órdenes correspondiente no se encuentre disponible.

La estructura dimensional preparada debe ser compatible conceptualmente con una geometría basada en:

```json
{
  "vertices_mm": [
    [0, 0],
    [1000, 0],
    [1000, 500],
    [0, 500]
  ]
}