# SPEC-HU-007-T02 — Asociar medidas reales al dibujo

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-007 |
| Tarea relacionada | T02 — Asociar medidas reales al dibujo |
| Responsable | Andro Q. |
| Reviewer | Pendiente |

## 1. Objetivo

Permitir que el Operario asocie dimensiones reales, expresadas en milímetros, al polígono dibujado mediante el editor implementado en HU-007 T01.

El sistema debe utilizar el ancho y alto reales ingresados por el Operario para transformar automáticamente las coordenadas gráficas de los vértices del lienzo a coordenadas equivalentes en milímetros, sin requerir el ingreso manual de coordenadas.

La finalidad de esta tarea es obtener una representación geométrica dimensionalmente consistente que pueda ser utilizada posteriormente por la validación geométrica de HU-007 T03 y por el flujo de registro de piezas.

T02 no determina si el polígono es convexo ni si es geométricamente válido para corte. Esa responsabilidad corresponde a HU-007 T03.

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
| `widthMm` | Número | Obligatorio, mayor que 0 y expresado en mm |
| `heightMm` | Número | Obligatorio, mayor que 0 y expresado en mm |
| `minX` | Número calculado | Menor coordenada X de los vértices |
| `maxX` | Número calculado | Mayor coordenada X de los vértices |
| `minY` | Número calculado | Menor coordenada Y de los vértices |
| `maxY` | Número calculado | Mayor coordenada Y de los vértices |
| `drawingWidth` | Número calculado | `maxX - minX`; debe ser mayor que 0 |
| `drawingHeight` | Número calculado | `maxY - minY`; debe ser mayor que 0 |
| `scaledVertices` | Arreglo de pares o puntos dimensionales | Coordenadas resultantes expresadas en milímetros |

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
- RN-14: Las coordenadas gráficas originales utilizadas por el lienzo no deben ser reemplazadas por las coordenadas en milímetros, debido a que el editor debe conservar su representación visual.
- RN-15: Las coordenadas dimensionales generadas por T02 deben mantenerse separadas de las coordenadas gráficas de T01.
- RN-16: T02 no debe declarar que el polígono es convexo o válido para optimización.
- RN-17: La validación de convexidad corresponde exclusivamente a HU-007 T03.
- RN-18: Las dimensiones deben utilizar una única unidad consistente: milímetros.
- RN-19: El sistema debe poder verificar la conversión mediante al menos un caso de prueba con valores conocidos.
- RN-20: T02 no realiza persistencia definitiva de la pieza en base de datos.

## 6. Flujo principal

1. El Operario dibuja el contorno de la pieza utilizando el editor desarrollado en T01.
2. El Operario agrega al menos tres vértices.
3. El Operario selecciona `Cerrar polígono`.
4. El sistema cierra gráficamente el polígono.
5. El sistema habilita o muestra la sección `Dimensiones reales`.
6. El Operario ingresa el ancho real de la pieza en milímetros.
7. El Operario ingresa el alto real de la pieza en milímetros.
8. El sistema valida que ambos valores sean números mayores que cero.
9. El sistema calcula `minX`, `maxX`, `minY` y `maxY` utilizando los vértices gráficos.
10. El sistema calcula el ancho y alto gráficos del bounding box.
11. El sistema normaliza cada vértice respecto al bounding box.
12. El sistema escala las coordenadas normalizadas según el ancho y alto reales indicados.
13. El sistema obtiene los vértices equivalentes expresados en milímetros.
14. El sistema mantiene las coordenadas gráficas originales para continuar representando el dibujo en el SVG.
15. El sistema conserva temporalmente la geometría dimensional para su posterior validación en T03.
16. La interfaz informa al Operario las dimensiones reales asociadas, por ejemplo: `1200 × 700 mm`.

## 7. Flujos alternativos y errores

- Si el polígono todavía se encuentra abierto, la sección de dimensiones reales no debe permitir la conversión.
- Si el ancho está vacío, el sistema debe indicar que el ancho real es obligatorio.
- Si el alto está vacío, el sistema debe indicar que el alto real es obligatorio.
- Si el ancho es igual o menor que cero, debe considerarse inválido.
- Si el alto es igual o menor que cero, debe considerarse inválido.
- Si el usuario ingresa un valor no numérico, no debe generarse la geometría dimensional.
- Si `maxX - minX = 0`, no debe ejecutarse la transformación para evitar una división entre cero.
- Si `maxY - minY = 0`, no debe ejecutarse la transformación para evitar una división entre cero.
- Si el Operario cambia el ancho después de una conversión válida, el sistema debe recalcular las coordenadas X en milímetros.
- Si el Operario cambia el alto después de una conversión válida, el sistema debe recalcular las coordenadas Y en milímetros.
- Si el Operario utiliza `Deshacer` y el polígono vuelve al estado abierto, las dimensiones asociadas no deben considerarse una geometría confirmada.
- Si el Operario utiliza `Reiniciar dibujo`, deben eliminarse los vértices y las dimensiones reales asociadas al borrador actual.
- Un polígono cóncavo puede llegar a esta etapa y recibir dimensiones reales; su rechazo corresponde a T03.
- El sistema no debe presentar mensajes que indiquen `polígono válido`, `polígono convexo` o equivalentes durante T02.

## 8. Criterios de aceptación

- CA-01: La sección de dimensiones reales solo permite asociar medidas cuando el polígono se encuentra gráficamente cerrado.
- CA-02: El Operario puede ingresar ancho y alto reales expresados en milímetros sin ingresar manualmente coordenadas de vértices.
- CA-03: El sistema rechaza ancho o alto vacíos, no numéricos o menores o iguales que cero.
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

Este caso debe utilizarse como prueba verificable de la transformación implementada en T02.

## 9. Impacto técnico

### Módulos

Frontend:

- `frontend/src/features/orders/`
- Extensión del editor de pieza personalizada desarrollado en T01.

La lógica de transformación dimensional debe mantenerse dentro del feature `orders` y separarse de la lógica puramente visual cuando resulte conveniente para facilitar sus pruebas.

No se debe introducir lógica de optimización ni rasterización dentro del componente del editor.

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