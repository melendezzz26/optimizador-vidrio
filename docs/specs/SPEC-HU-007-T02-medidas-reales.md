# SPEC — HU-007 T02: medidas reales por segmento

## Información general

| Campo | Valor |
|---|---|
| Estado | Verified |
| PBI relacionado | HU-007 |
| Tarea relacionada | T02 — Asociar medidas reales al dibujo |
| Implementación | Dimensionamiento mediante longitudes individuales S1…Sn |
| Responsable | Andro Quispe Cesias |
| Reviewer | Andro Quispe Cesias |
| Rama | `feature/HU-007-lienzo-pieza-personalizada` |
| Commit de redefinición | `b4a9fbd` |
| Commit de implementación | `d01bb26` |

## 1. Objetivo y alcance

Permitir al Operario dimensionar una pieza irregular mediante la **longitud real de cada lado**, en milímetros, a partir del boceto cerrado de HU-007 T01.

El boceto actúa como referencia de forma y orientación. Sus coordenadas gráficas no representan directamente medidas físicas.

El flujo funcional de T02 es:

```text
dibujar
→ cerrar polígono
→ identificar S1…Sn
→ seleccionar segmentos
→ ingresar longitudes reales
→ revisar la vista dimensional progresiva
→ completar las medidas
→ reconstruir la geometría cerrada
→ preparar vertices_mm
→ esperar la validación de T03

Esta decisión sustituye el modelo de escalamiento independiente de ejes. No existen entradas de ancho exterior ni alto exterior. Las restricciones dimensionales son las longitudes individuales.

T02 incluye segmentación, selección, edición, estimaciones provisionales, reconstrucción cerrada y comprobación de consistencia dimensional. **T02 no valida convexidad**, concavidad, autointersecciones ni aptitud para corte. Completar las dimensiones no equivale a aprobar una pieza.

Fuera de alcance: T03, rechazo de concavidad, arrastre de vértices, ingreso de ángulos o coordenadas, solver CAD genérico, rasterización, optimización, persistencia, backend, base de datos, migraciones y registro de piezas en el pedido. No se agregan dependencias.

## 2. Actor y precondiciones

- Actor: Operario.
- Se conserva T01: creación de vértices mediante clic, segmentos, cierre con al menos tres vértices, Deshacer y Reiniciar.
- Las medidas se habilitan después del cierre gráfico.
- Se conserva el orden de creación de los vértices.
- Para usar un lado como referencia de dirección y escala, sus extremos deben ser finitos y distintos. Los vértices consecutivos coincidentes requieren corregir el boceto; esto no constituye validación de convexidad.
- No se exige extensión gráfica positiva en ambos ejes. Una referencia colineal puede intentar dimensionarse; no se declara por ello válida para corte.

## 3. Modelo de datos y separación de responsabilidades

| Dato | Representación | Responsabilidad |
|---|---|---|
| `vertices` | Objetos `{x, y}` ordenados | Boceto gráfico de T01; nunca se sustituye por el resultado dimensional |
| `isClosed` | Booleano | Habilita las medidas por segmento |
| `segments` | `{id: "S1", index: 0, lengthMm: ""}` por lado | Valores originales del Operario; cadenas para conservar campos vacíos y edición |
| `badInput` | Booleano opcional por segmento | Conserva el error de un input numérico que el navegador entrega como cadena vacía |
| `activeSegmentIndex` | Índice o `null` | Selección compartida por lista y ambas vistas; no representa validación |
| `lengths` | Números positivos | Longitudes objetivo: reales donde existen y provisionales donde faltan |
| `measured` / `measuredCount` | Booleanos / cantidad | Distinguen medidas ingresadas de estimaciones |
| `provisionalScale` | Número o `null` | Mediana de escalas reales/gráficas; nunca rellena campos |
| `vertices_mm` | Pares `[x, y]` ordenados o `null` | Geometría reconstruida en mm, con el primer vértice en `(0, 0)` |
| Puntos del preview | Objetos `{x, y}` | Ajuste visual uniforme y centrado; nunca modifica `vertices_mm` |

S1 une V1 con V2, S2 une V2 con V3 y Sn une Vn con V1. El orden no se clasifica por orientación, longitud o posición. Los campos se crean vacíos al cerrar.

`vertices_mm` omite el punto final repetido. Puede contener coordenadas negativas: el origen es el primer vértice, no la esquina del bounding box. Conserva el sistema de orientación del SVG (Y crece hacia abajo).

Estados dimensionales:

- `unscaled`: ninguna medida real; solo se normaliza visualmente el boceto, sin coordenadas en mm.
- `provisional`: cierre logrado con al menos una longitud estimada.
- `complete`: todas las longitudes son reales y el cierre numérico se logró.
- `error`: entrada inválida, inconsistencia dimensional o imposibilidad numérica de reconstruir; no se conserva una geometría anterior como si siguiera vigente.

La salida debe mantener explícito su estado provisional o completo. Una salida provisional no es una geometría definitiva para T03 ni para registro.

## 4. Reglas de entrada, selección y edición

- Cada longitud real debe ser un número finito estrictamente mayor que cero, en mm.
- Se permiten decimales positivos, incluso menores que `0.01`. Los controles usan `step="any"`; no se establece un mínimo artificial.
- Un campo vacío es una medida pendiente. Una entrada inválida no se reemplaza silenciosamente por una estimación.
- Se muestra `3 de 5 medidas ingresadas`, contando únicamente entradas positivas finitas.
- La selección desde cada fila/control es obligatoria y accesible por teclado. Seleccionar S3 resalta su control, el lado S3 en el boceto y el lado S3 en la vista dimensional disponible.
- La identidad de selección es azul/cyan y está separada del estado de dimensiones completas. Los controles tienen nombres como `Longitud del segmento S3 en milímetros`.
- Cambiar de selección conserva todas las medidas y no recalcula el solver innecesariamente.
- Cambiar o borrar una longitud recalcula inmediatamente el resultado y el progreso; no modifica los otros campos ni el boceto.
- Deshacer elimina el último vértice, reabre el boceto e invalida todas las medidas y la selección. Al volver a cerrar se regenera la colección S1…Sn vacía.
- Reiniciar elimina vértices, medidas, selección y preview.
- Agregar vértices o modificar el contorno mediante nuevas capacidades CAD no pertenece a T02.

## 5. Longitudes provisionales

Para cada segmento gráfico:

```text
drawingLength_i = hypot(x2 - x1, y2 - y1)
scale_i = realLength_i / drawingLength_i
provisionalScale = median(scale_i de los segmentos medidos)
provisionalLength_i = drawingLength_i * provisionalScale
```

Para una cantidad par de escalas, la mediana es el promedio de los dos valores centrales. Para una cantidad impar, es el valor central. No se utiliza el promedio de todas las escalas.

El solver usa la longitud real en cada lado medido y la provisional en los pendientes. Al completar todas las medidas usa exclusivamente longitudes reales. Las estimaciones nunca se escriben en `lengthMm` ni aumentan el progreso.

Sin ninguna medida real, `provisionalScale` y `vertices_mm` son `null`. Se muestra el boceto ajustado al espacio disponible con el mensaje `Sin escala física`. No se inventan medidas predeterminadas.

Si una escala o longitud derivada no puede representarse como número positivo finito, se informa una limitación de precisión numérica en vez de emitir puntos inválidos.

## 6. Reconstrucción dimensional cerrada

La función específica `reconstructPolygonFromSegmentLengths(vertices, targetLengths)` realiza un ajuste determinista de direcciones, sin dependencias externas.

### Consistencia previa

Con todas las longitudes objetivo positivas y finitas:

```text
maxLength < sum(otherLengths)
```

Si el lado más largo es mayor o igual que la suma de los demás, no se ejecuta el ajuste. Esta es una comprobación dimensional de T02, no validación de convexidad.

Con medidas completas se informa:

> Las longitudes ingresadas no permiten formar un polígono cerrado. Revisa las medidas de los segmentos.

En estados provisionales se aclara que la incompatibilidad incluye lados estimados y que completar las medidas pendientes puede resolverla.

### Ajuste de direcciones

1. Obtener los ángulos de referencia `theta_i = atan2(dy_i, dx_i)`.
2. Normalizar las longitudes objetivo por la mayor, para mejorar el acondicionamiento numérico.
3. Calcular el vector de cierre y el Jacobiano:

```text
closure = sum(L_i * [cos(theta_i), sin(theta_i)])
Jx_i = -L_i * sin(theta_i)
Jy_i =  L_i * cos(theta_i)
delta = -Jᵀ * inverse(J * Jᵀ + lambda * I) * closure
```

4. Aplicar correcciones pequeñas con regularización `1e-12`, límite angular por paso de `0.35` radianes y reducción del paso hasta disminuir el residuo.
5. Limitar cada intento a 160 iteraciones y cada búsqueda de paso a 16 reducciones. La tolerancia de convergencia normalizada es `1e-11` respecto a la mayor longitud.
6. Probar las direcciones originales y dos perturbaciones deterministas pequeñas (`±0.025 * sin(i + 1)` radianes) para escapar de referencias singulares. Entre las soluciones cerradas, escoger la de menor desviación angular cuadrática respecto al boceto.
7. Acumular los segmentos con sus longitudes reales/provisionales, comenzando en `(0, 0)`. El extremo final debe coincidir con el origen dentro de la tolerancia numérica; no se fuerza el último vértice a cerrar una cadena con un hueco significativo.

La salida incluye `closureErrorMm` y `toleranceMm` (`1e-9 * maxLength`). La discrepancia de longitud del último lado implícito queda acotada por ese residuo de cierre. Se rechazan resultados no finitos o fuera de tolerancia.

Las longitudes por sí solas no determinan una figura única, especialmente con cuatro o más lados. El boceto orienta una solución local que intenta conservar sus direcciones; el método no garantiza el mínimo angular global ni la conservación exacta de todos los ángulos. Una falta de convergencia se informa como limitación del ajuste, no como prueba de imposibilidad dimensional o invalidez para corte.

## 7. Vista dimensional y experiencia

- El dibujo original permanece visible y sin alteraciones dimensionales.
- La sección de entrada se llama `Dimensiones por segmento`.
- La segunda vista está debajo del área de dibujo/medidas y se llama `Vista dimensional`. No es otro editor.
- Mientras falten medidas se indica `Vista dimensional provisional` y la cantidad de segmentos medidos. Sin medidas reales se aclara la ausencia de escala física.
- Solo con todas las medidas y cierre numérico correcto se indica `Vista dimensional completa`.
- Si hay error, se sustituye la geometría por un mensaje accionable. No se muestran una cadena abierta ni un resultado anterior como completos.
- S1…Sn se identifican en ambas vistas. La etiqueta del lado activo tiene prioridad; en contornos densos se omiten etiquetas que colisionarían, manteniendo todos los lados accesibles en la lista.
- Los lados pendientes usan trazo discontinuo en la vista inferior. La medida del lado activo aparece junto a su identificador, como medida ingresada o como `≈ … mm · Estimación provisional`.
- La cuadrícula es solo una referencia visual, no una escala en mm.
- El ajuste al preview usa su bounding box, una escala uniforme y centrado, sin mutar entradas. No hay escalamiento independiente de X/Y.
- Las etiquetas mantienen tamaño legible al redimensionar. Las relaciones extremas se conservan, incluidas figuras rectangulares de lados alternados `200, 5000, 200, 5000` y `5000, 200, 5000, 200`.
- Se conserva NewGlass: navy, azul, cyan, fondos claros y alto contraste, sin animación decorativa ni nuevas librerías.
- PC/laptop es prioritario; tablet y móvil no deben tener overflow horizontal. La lista puede desplazarse verticalmente para muchos lados.
- Se conserva foco visible y simultáneo con el borde de error. Cerrar por teclado lleva al primer campo; cerrar mediante puntero revela las medidas sin abrir automáticamente el teclado virtual.
- La navegación completa del dibujo por teclado sigue siendo una limitación heredada de T01. La selección y edición de medidas sí son accesibles por teclado.
- Se respeta `prefers-reduced-motion`.

## 8. Dependencia de T03

`Agregar pieza al pedido` permanece deshabilitado durante toda T02, incluso con cierre dimensional completo. En ese estado se muestra:

> Las dimensiones están completas. Falta validar la geometría en T03.

No se usan afirmaciones como “polígono válido”, “polígono convexo” o “pieza válida para corte”. T02 no rechaza figuras por concavidad y no verifica autointersecciones. La validación posterior y el registro pertenecen a tareas posteriores.

El borrador permanece solo en memoria y se pierde al salir o recargar. No se crea API ni persistencia.

Ejemplo conceptual de geometría dimensional completa, pendiente de T03:

```json
{
  "status": "complete",
  "vertices_mm": [[0, 0], [1000, 0], [1000, 500], [0, 500]]
}
```

## 9. Criterios de aceptación

- CA-01: Se preservan clics, vértices, segmentos, cierre, Deshacer y Reiniciar de T01.
- CA-02: Después del cierre se generan S1…Sn en el orden V1→V2…Vn→V1, con medidas vacías.
- CA-03: Cada lado admite una longitud individual positiva finita, con decimales y sin mínimo artificial.
- CA-04: No existen entradas ni estados de dimensionado exterior por dos ejes.
- CA-05: La lista permite seleccionar cualquier lado y sincroniza el resaltado del control y ambas vistas disponibles.
- CA-06: La selección no borra medidas ni se interpreta como aprobación geométrica.
- CA-07: Se informa el número de medidas reales ingresadas; las estimaciones no cuentan.
- CA-08: Sin medidas se muestra exclusivamente un boceto normalizado sin escala física ni `vertices_mm`.
- CA-09: Las medidas faltantes se estiman usando la mediana de las escalas de los lados medidos, sin rellenar sus campos.
- CA-10: La vista provisional distingue las estimaciones y no se declara completa mientras falten datos.
- CA-11: Se aplica estrictamente la desigualdad de polígono, tanto a objetivos provisionales como completos, con mensajes diferenciados.
- CA-12: La reconstrucción es determinista, conserva el orden y produce un cierre dentro de tolerancia con cada longitud objetivo respetada numéricamente.
- CA-13: Cambiar cualquier medida recalcula la geometría inmediatamente y conserva el resto de campos y el boceto original.
- CA-14: Las coordenadas gráficas, `vertices_mm` y puntos de visualización son representaciones separadas y no se mutan entre sí.
- CA-15: El primer vértice dimensional es `(0, 0)`; no se repite el punto final en `vertices_mm`.
- CA-16: La vista inferior conserva proporción, centra la figura y maneja relaciones extremas en desktop y móvil.
- CA-17: Las etiquetas S1…Sn y la medida activa son legibles; en contornos densos prevalece la selección y la lista conserva todos los lados.
- CA-18: Entradas inválidas, vértices consecutivos coincidentes, valores no representables y falta de convergencia producen feedback explícito y no resultados engañosos.
- CA-19: Deshacer invalida medidas y selección; volver a cerrar regenera segmentos. Reiniciar limpia todo el borrador.
- CA-20: Foco, error, estados pendientes y dimensiones completas se distinguen sin depender exclusivamente del color.
- CA-21: `Agregar pieza al pedido` siempre está deshabilitado y explica la dependencia de T03.
- CA-22: No se implementan convexidad, rechazo de concavidad, autointersecciones, registro ni persistencia.

### Casos verificables

1. Boceto `(100,100), (500,100), (500,300), (100,300)` con S1=1000, S2=500, S3=1000, S4=500 mm: resultado aproximado `(0,0), (1000,0), (1000,500), (0,500)`.
2. En ese boceto, solo S1=800 mm: escala provisional 2; objetivos `[800,400,800,400]`; los últimos tres campos permanecen vacíos.
3. En ese boceto, S1=800 y S2=800 mm: escalas 2 y 4; mediana 3; objetivos `[800,800,1200,600]`, pendientes S3/S4.
4. Cambiar únicamente S1 de 1000 a 1200 mm reconstruye un contorno cerrado con lados `[1200,500,1000,500]`; no queda el hueco de 200 mm que producirían las direcciones originales sin ajustar.
5. `[2000,500,1000,500]` y `[2001,500,1000,500]` fallan la desigualdad estricta.
6. El pentágono `(0,0), (300,0), (400,200), (150,400), (-100,200)` con `[850,420,600,510,730]` se reconstruye cerrado y respeta los cinco lados.
7. Lados alternados `[200,5000,200,5000]` o `[5000,200,5000,200]` sobre un boceto rectangular mantienen relaciones 1:25 y 25:1 en el preview.

## 10. Arquitectura y verificación

- `CustomPieceEditor.jsx`: estado de dibujo/medidas/selección, controles accesibles y representación SVG. El solver se recalcula al cambiar medidas o boceto, no por selección o tamaño del preview.
- `CustomPieceEditor.css`: estilos y adaptación local NewGlass.
- `segmentGeometry.js`: segmentos, validación dimensional, estimaciones, solver y estados del resultado.
- `geometryScaling.js`: bounding box y transformación visual uniforme.
- `geometryScaling.test.js`: cobertura de longitudes gráficas, orden, mediana, estimaciones, cierre, longitudes reales reconstruidas, entradas inválidas, desigualdad, edición, inmutabilidad, orientación, figuras de 3/4/5+ lados, concavidad sin validación T03 y preview responsive.

### Verificación técnica realizada

Desde `frontend` se ejecutaron:

```text
node --test tests/unit/geometryScaling.test.js
npm.cmd run lint
npm.cmd run build
