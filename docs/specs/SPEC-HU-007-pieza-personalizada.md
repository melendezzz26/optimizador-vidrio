# SPEC-HU-007 — Pieza personalizada: T01 — Implementar lienzo tipo Paint

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-007 — Pieza personalizada |
| Tarea | T01 — Implementar lienzo tipo Paint |
| Responsable | Andro Quispe Cesias |
| Reviewer | Andro Quispe |
| Sprint | Sprint 1 |

## 1. Objetivo

Permitir que el Operario construya visualmente el contorno de una pieza
personalizada mediante un editor poligonal basado en vértices agregados con clics.
El lienzo debe mostrarse directamente, mostrar vértices y segmentos, permitir cerrar el polígono,
deshacer el último vértice y reiniciar el dibujo.

Esta SPEC define únicamente T01 de HU-007. «Tipo Paint» describe la interacción
gráfica del editor; no implica dibujo libre con pincel. El resultado es un
borrador gráfico local, sin medidas reales ni validación de convexidad.

## 2. Alcance

### Incluye

- Mostrar el editor directamente al renderizarse en `NuevoPedido` y en la
  página manual, sin controles para abrirlo u ocultarlo.
- Agregar vértices mediante clics dentro del lienzo, en orden de inserción.
- Mostrar los vértices y segmentos rectos entre puntos consecutivos.
- Cerrar el polígono mediante una acción explícita cuando tenga al menos tres
  vértices, conectando el último con el primero.
- Deshacer el último vértice, incluida la reapertura de un polígono cerrado.
- Reiniciar el dibujo y volver al estado inicial.
- Impedir la inserción de vértices mientras el polígono permanezca cerrado.
- Mantener el estado del borrador en memoria dentro de la feature `orders`.

### Fuera de alcance

- Dibujo libre con pincel, trazos continuos y entrada manual de coordenadas.
- Ingreso de medidas reales, escala física y conversión a milímetros: T02.
- Validación de convexidad, auto-intersecciones y validez geométrica: T03.
  T01 no comprueba ausencia de cruces, área positiva ni aptitud para corte;
  permite cerrar gráficamente cualquier secuencia de al menos tres vértices.
- Arrastrar o mover vértices, insertar vértices intermedios y rehacer acciones.
  La edición de T01 se limita a deshacer el último vértice y continuar dibujando.
- Persistencia local o remota, guardado de pedidos o piezas y consumo de API.
- Cambios de backend, base de datos, migraciones o permisos.
- Rasterización, cálculo de patrones de corte y optimización.
- Plantillas de polígonos, generación de polígonos regulares, reconocimiento
  de formas, circunferencias o aproximación a círculo y sugerencias automáticas.

### Posibles mejoras futuras

Las plantillas de polígonos, los polígonos regulares, el reconocimiento de formas,
las circunferencias o aproximaciones a círculo y las sugerencias automáticas
quedan registradas únicamente como ideas para evaluación futura. No son
entregables ni criterios de aceptación de T01 y no se implementan en esta tarea.
Las medidas reales continúan en T02 y la validación geométrica en T03.

## 3. Actor y precondiciones

**Actor:** Operario.

**Precondiciones:**

- Al renderizar `CustomPieceEditor` en `NuevoPedido`, el lienzo está visible y
  disponible para recibir clics sin una acción previa de apertura.
- La página manual `/hu007-t01.html` muestra el mismo editor directamente,
  sin depender del acceso al flujo contenedor ni modificar su autenticación.
- El dibujo comienza vacío y abierto, sin datos recuperados de almacenamiento.
- La interacción gráfica no requiere un pedido persistido, conexión a la API,
  catálogo remoto ni base de datos disponible.
- La autenticación y autorización del flujo contenedor no se implementan ni
  modifican en T01.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| Clic en el lienzo | Evento de puntero con posición local | Agrega un vértice únicamente dentro del área de dibujo y mientras el polígono esté abierto. |
| Vértices | Lista ordenada de puntos gráficos `(x, y)` | Se obtienen del clic respecto al lienzo; son datos internos de pantalla, no milímetros ni campos editables manualmente. |
| Polígono cerrado | Booleano | Inicialmente falso; solo pasa a verdadero con al menos tres vértices. |
| Cerrar polígono | Acción de UI | Conecta el último vértice con el primero sin duplicar el primer punto en la lista. |
| Deshacer último vértice | Acción de UI | Elimina el último punto; si el polígono estaba cerrado, también lo reabre. |
| Reiniciar dibujo | Acción de UI | Vacía los vértices y restablece el polígono abierto. Está deshabilitada cuando no hay vértices. |

Los segmentos se derivan de la lista y del estado de cierre. Con `n` vértices,
un polígono abierto muestra `max(n - 1, 0)` segmentos; uno cerrado muestra `n`.
No se genera todavía un payload de API ni una geometría validada de pieza.

## 5. Reglas de negocio

- RN-01: Cada clic aceptado agrega exactamente un vértice al final de la lista.
  Mover o arrastrar el puntero no genera una sucesión de puntos.
- RN-02: Los vértices y segmentos reflejan el orden de inserción. El primer
  vértice se muestra sin segmento; cada nuevo vértice se conecta al anterior.
- RN-03: Cerrar requiere al menos tres vértices. El cierre agrega visualmente
  el segmento entre el último y el primero, sin agregar otro vértice.
- RN-04: Un polígono cerrado no acepta nuevos vértices. La inserción se habilita
  nuevamente al reiniciar o al editar mediante Deshacer último vértice.
- RN-05: Deshacer elimina exactamente el último vértice y los segmentos que
  dependían de él. Si el polígono estaba cerrado, elimina también el cierre y
  deja una secuencia abierta con los vértices restantes.
- RN-06: Los controles siguen la matriz siguiente. Cerrar un polígono ya
  cerrado queda deshabilitado y no cambia el dibujo.
- RN-07: Reiniciar un dibujo con vértices, abierto o cerrado, deja cero vértices,
  cero segmentos y estado abierto. Los tres controles quedan deshabilitados;
  no se puede volver a activar Reiniciar desde la interfaz hasta agregar un punto.
- RN-08: El cierre es exclusivamente gráfico. No se presenta como validación
  de convexidad, confirmación de pieza válida ni guardado exitoso.
- RN-09: La compatibilidad posterior con `POLIGONO_CONVEXO` requiere completar
  las medidas de T02 y la validación de T03. El borrador de T01 no se etiqueta
  como polígono convexo validado ni se envía a persistencia u optimización.

| Estado | Cerrar polígono | Deshacer último vértice | Reiniciar dibujo |
|---|---|---|---|
| 0 vértices | Deshabilitado | Deshabilitado | Deshabilitado |
| 1–2 vértices | Deshabilitado | Habilitado | Habilitado |
| 3 o más vértices, abierto | Habilitado | Habilitado | Habilitado |
| Polígono cerrado | Deshabilitado | Habilitado | Habilitado |

## 6. Flujo principal

1. Al cargar `NuevoPedido` o la página manual, el Operario observa directamente
   el lienzo vacío, el estado «Polígono abierto» y las instrucciones. Cerrar
   polígono, Deshacer último vértice y Reiniciar dibujo están deshabilitados.
2. Hace clic dentro del lienzo y aparece el primer vértice. Se habilitan
   Deshacer último vértice y Reiniciar dibujo.
3. Agrega vértices mediante clics; se muestran los segmentos que los conectan
   en orden. Al llegar a tres vértices se habilita Cerrar polígono.
4. Activa Cerrar polígono; se dibuja el segmento final hacia el primer vértice,
   se muestra «Polígono cerrado» y se deshabilita Cerrar polígono.
5. Los clics posteriores en el lienzo no modifican el polígono cerrado.
6. Puede deshacer el último vértice para reabrir y continuar el dibujo, o
   reiniciar para comenzar otro borrador vacío. El resultado permanece en memoria.

## 7. Flujos alternativos y errores

- **Menos de tres vértices:** Cerrar polígono permanece deshabilitado y la UI
  informa que se requieren al menos tres; no aparece un segmento de cierre.
- **Dibujo abierto:** Deshacer elimina el último vértice. Si solo había uno,
  el lienzo queda vacío; con cero, los tres controles quedan deshabilitados.
- **Dibujo cerrado:** Deshacer elimina el último vértice, quita el cierre y
  habilita nuevos clics. Se puede volver a cerrar al reunir tres puntos.
- **Clic fuera del lienzo o sobre controles:** No modifica la lista de vértices.
- **Polígono cerrado:** Los clics interiores no agregan puntos; la UI indica que
  se debe deshacer o reiniciar para continuar.
- **Reinicio:** Funciona sobre un dibujo con vértices, abierto o cerrado; no
  conserva segmentos ni estado de cierre. En vacío permanece deshabilitado.
- **Contorno cóncavo, con cruces o degenerado:** T01 permite cerrar gráficamente
  cualquier secuencia de al menos tres vértices; no comprueba convexidad,
  auto-intersecciones ni validez geométrica, reservadas para T03.
- **Recarga o salida de la página:** El borrador se pierde. El estado vive
  únicamente en memoria y la interfaz comunica esta limitación.

## 8. Criterios de aceptación

- **CA-01 — Agregar vértices:** Al renderizar el componente en `NuevoPedido` o
  en `/hu007-t01.html`, el lienzo aparece directamente vacío y abierto, sin
  controles Abrir/Ocultar editor y con los tres controles de dibujo deshabilitados.
  Dado ese lienzo, al hacer tres
  clics en posiciones distintas dentro de él, se muestran exactamente tres
  vértices en esas posiciones y en ese orden. Un clic fuera del lienzo o en
  un control no agrega vértices; mover el puntero sin hacer clic tampoco.
- **CA-02 — Visualizar segmentos:** Con un vértice no hay segmentos; al agregar
  el segundo aparece uno y con el tercero aparecen dos, conectando únicamente
  puntos consecutivos. Antes de cerrar no hay segmento entre el último y el
  primero. La representación se actualiza después de cada acción.
- **CA-03 — Cerrar el polígono:** Con cero, uno o dos vértices, Cerrar polígono está
  deshabilitado y se informa el mínimo requerido. Con tres o más y abierto,
  los tres controles están habilitados. Al activar Cerrar polígono,
  aparece el segmento del último al primero, se mantiene el número de vértices
  y se indica «Polígono cerrado». Cerrar queda deshabilitado; Deshacer y Reiniciar
  permanecen habilitados. Volver a intentar cerrar no altera el resultado.
- **CA-04 — Deshacer último vértice:** Con una secuencia abierta de tres puntos,
  Deshacer deja los dos primeros y un segmento. Repetir deja un punto sin
  segmentos y luego el lienzo vacío. Con uno o dos vértices, Deshacer y Reiniciar
  siguen habilitados y Cerrar está deshabilitado; con cero, los tres quedan
  deshabilitados. En un polígono cerrado de cuatro puntos, Deshacer deja los
  tres primeros, dos segmentos y estado «Polígono abierto», con los tres controles
  habilitados; un clic posterior puede agregar un nuevo vértice.
- **CA-05 — Reiniciar dibujo:** Desde un dibujo con vértices, abierto o cerrado,
  Reiniciar deja cero vértices, cero segmentos y estado «Polígono abierto».
  Cerrar, Deshacer y Reiniciar quedan deshabilitados; no puede repetirse Reiniciar
  desde la interfaz en vacío. El siguiente clic crea el primer punto de un nuevo
  dibujo y habilita Deshacer y Reiniciar, manteniendo Cerrar deshabilitado.
- **CA-06 — Bloquear inserción tras el cierre:** Dado un polígono cerrado, varios
  clics en distintas posiciones del lienzo conservan sus vértices, segmentos y
  estado. La inserción se recupera únicamente tras Reiniciar o Deshacer, con
  los resultados definidos en CA-04 y CA-05.
- **CA-07 — Respetar el alcance gráfico:** La interfaz no ofrece pincel, entrada
  manual de coordenadas, medidas reales, plantillas, generación de polígonos
  regulares, reconocimiento de formas, circunferencias o aproximación a círculo,
  ni sugerencias automáticas. Cualquier secuencia de al menos tres vértices
  puede cerrarse gráficamente, sin comprobar convexidad, auto-intersecciones ni
  validez geométrica. Completar el flujo no realiza
  solicitudes de guardado, no persiste el dibujo y no muestra una confirmación
  de convexidad o de pieza validada.

## 9. Impacto técnico

### Módulos

- La implementación del lienzo, controles, estado y estilos se ubica
  en `frontend/src/features/orders/`,
  siguiendo las [convenciones de features](../../frontend/src/features/README.md).
- `frontend/src/pages/NuevoPedido.jsx` ya renderiza `CustomPieceEditor`.
  El componente muestra el lienzo directamente, sin controles Abrir/Ocultar.
- `frontend/hu007-t01.html` y `frontend/tests/manual/hu007-t01/main.jsx` ofrecen
  una entrada manual independiente con el mismo componente. La apertura directa
  no requiere opciones especiales ni cambios en esos archivos o en `NuevoPedido`.
- No se requiere migrar toda la pantalla ni colocar lógica específica de
  Pedidos en `frontend/src/shared/`. No hay cambios previstos en módulos backend.

### API

- No se crean, modifican ni consumen endpoints para el lienzo de T01.
- El borrador es estado local de interfaz; la serialización para una API futura
  queda fuera de esta tarea.

### Base de datos / migración

- No se modifican modelos, tablas ni migraciones, ni se ejecutan seeds.
- El modelo `Pieza` existente admite `POLIGONO_CONVEXO`, pero requiere geometría,
  área y asociación a un pedido. T01 no genera un registro persistible completo.

### UI

- Mostrar directamente el área de dibujo con vértices visibles, segmentos rectos
  y los estados «Polígono abierto» o «Polígono cerrado», sin controles Abrir/Ocultar.
- Incorporar controles identificables para cerrar, deshacer y reiniciar, con
  estados habilitados según RN-06 y ayuda sobre el mínimo de tres vértices.
  Usar «polígono» de forma consistente en etiquetas, instrucciones y títulos.
- Comunicar que el borrador se pierde al abandonar o recargar la página.
- Calcular la posición local del clic para que el punto coincida con la posición
  señalada, incluso con desplazamiento de página. Este ajuste de pantalla no
  es la conversión física a milímetros de T02.
- El lienzo utiliza SVG y coordenadas gráficas locales; no requiere una
  biblioteca de dibujo adicional ni realiza conversión a unidades físicas.

### Dependencias

- React/Vite y la estructura actual del frontend; consultar la
  [guía de desarrollo](../../CONTRIBUTING.md) y el [README del frontend](../../frontend/README.md).
- Integración con la pantalla de Pedidos para acceder al editor, sin depender
  del guardado ni de la disponibilidad de la API.
- T02 consumirá el borrador para incorporar medidas y conversión a milímetros;
  T03 incorporará validación de convexidad. Son tareas posteriores, no requisitos
  para implementar o verificar la interacción de T01.

### Riesgos

| Riesgo | Tratamiento previsto |
|---|---|
| Confundir cierre gráfico con una pieza geométricamente válida. | Mostrar estado de cierre sin afirmar convexidad ni aptitud para corte; reservar esa validación para T03. |
| Confundir posiciones de pantalla con medidas reales. | Mantener los puntos como datos gráficos internos y no mostrar unidades físicas; definir la conversión en T02. |
| Desalineación entre clics y vértices por tamaño o posición del lienzo. | Usar posiciones relativas al área de dibujo y comprobarlas con distintos tamaños de ventana y desplazamiento de página. |
| Inconsistencias al deshacer después del cierre. | Verificar que se eliminen el último punto y el cierre, y que se habilite la inserción nuevamente. |
| Pérdida del borrador al salir o recargar. | Comunicar que el dibujo es temporal; no prometer guardado o recuperación en T01. |
| Ampliación del alcance hacia pincel, medidas, API o validación geométrica. | Mantener la implementación y la revisión sujetas a los límites y criterios de esta SPEC. |

## 10. Pruebas previstas

Las pruebas siguientes deben comprobar la implementación con las decisiones
de UX actualizadas. Esta SPEC en Draft no declara resultados de ejecución ni
criterios aprobados; los resultados reales se registran en las evidencias.

| Prueba | Escenario y resultado a comprobar | Criterios |
|---|---|---|
| P-01 | Cargar NuevoPedido y la página manual: lienzo visible sin Abrir/Ocultar, vacío y con tres controles deshabilitados. Agregar puntos con clics interiores; probar movimiento sin clic, clics exteriores y controles sin inserciones adicionales. | CA-01 |
| P-02 | Dibujar uno, dos, tres y cuatro puntos; comprobar orden, posiciones y número de segmentos abiertos. | CA-01, CA-02 |
| P-03 | Comprobar Cerrar polígono deshabilitado con cero, uno y dos puntos; cerrar con tres y cuatro; verificar el segmento final sin duplicar vértices y los estados de controles de RN-06. | CA-03 |
| P-04 | Deshacer sucesivamente hasta vaciar y comprobar RN-06 en cada paso; deshacer un polígono cerrado, continuar agregando y volver a cerrar. | CA-04, CA-06 |
| P-05 | Comprobar Reiniciar deshabilitado en vacío; reiniciar desde abierto y cerrado con vértices, verificar los tres controles deshabilitados y comenzar un dibujo nuevo sin restos anteriores. | CA-05 |
| P-06 | Hacer varios clics después del cierre y comprobar que el polígono no cambia; repetir tras deshacer y reiniciar. | CA-06 |
| P-07 | Completar el flujo sin backend, incluido cerrar secuencias cóncavas, con cruces o degeneradas de al menos tres puntos sin validarlas; comprobar ausencia de solicitudes de guardado, persistencia y controles fuera de alcance. | CA-07 |
| P-08 | Repetir inserción y cierre con distintos tamaños de ventana y desplazamiento de página; comprobar coincidencia visual entre clics y vértices. | CA-01, CA-02 |

- Verificar los escenarios en navegador. Las pruebas automatizadas futuras de
  estado e interacción, si se incorporan, deben comprobar estos comportamientos.
- Ejecutar `npm run lint` y `npm run build` desde `frontend/` después de la
  implementación y registrar sus resultados reales. No sustituyen las pruebas
  funcionales; actualmente no existe un script `npm test`.
- Comprobar que la integración mantiene el acceso a la pantalla y el comportamiento
  previo de selección de material y listado de piezas de NuevoPedido.
- Comprobar los textos «Polígono abierto», «Polígono cerrado» y «Cerrar polígono»,
  y que recargar la página elimina el borrador y restablece el estado inicial.
- Seguir las [convenciones de pruebas](../testing/README.md); no se requieren
  pruebas de API, base de datos, rasterización u optimización para T01.

## 11. Evidencias requeridas

La evidencia futura se ubicará en `docs/evidence/sprint-01/HU-007/`, identificando
explícitamente T01 y siguiendo las [convenciones de evidencia](../evidence/README.md).
La existencia de capturas anteriores no implica que la revisión de UX ya esté
validada. Registrar nuevas evidencias sin atribuirles ejecuciones no realizadas.

- Registro de validación enlazado a esta SPEC, con rama, commit, presencia de
  cambios sin commit, entorno, navegador y tamaños de ventana realmente utilizados.
- Matriz de ejecución de P-01 a P-08 y CA-01 a CA-07, con pasos, resultado esperado,
  resultado observado y limitaciones o incidencias.
- Capturas o una grabación breve de la carga directa sin Abrir/Ocultar y del
  lienzo vacío con los tres controles deshabilitados, inserción de vértices,
  segmentos abiertos, cierre, bloqueo de nuevos puntos, deshacer y reinicio.
  El bloqueo debe sustentarse en una secuencia de acciones, no solo en una imagen.
- Evidenciar la matriz de RN-06 y la terminología actualizada a «polígono».
- Comandos, directorio de ejecución y resultados reales de lint y build; incluir
  resultados de pruebas automatizadas únicamente si se incorporan y ejecutan.
- Registro de la comprobación de ausencia de solicitudes de guardado durante el
  flujo y de la integración con NuevoPedido, sin incluir datos sensibles.

## Historial de estado

- Draft — Alcance de HU-007 T01 documentado; pendiente de revisión,
  implementación y verificación.
- Revisión UX aprobada — Editor visible directamente en uso normal y manual,
  eliminación de Abrir/Ocultar, terminología «polígono» y matriz de controles
  actualizada. Se conserva el alcance gráfico de T01; la validación de estos
  ajustes debe registrarse por separado antes de cerrar la tarea.
