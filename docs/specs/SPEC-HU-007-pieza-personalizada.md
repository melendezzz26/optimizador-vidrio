# SPEC-HU-007 — Pieza personalizada: T01 — Implementar lienzo tipo Paint

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-007 — Pieza personalizada |
| Tarea | T01 — Implementar lienzo tipo Paint |
| Responsable | Andro Quispe Cesias |
| Reviewer | Andro Quispe Cesias |
| Sprint | Sprint 1 |

## 1. Objetivo

Permitir que el Operario construya visualmente el contorno de una pieza
personalizada mediante un editor poligonal basado en vértices agregados con clics.
El lienzo debe mostrar vértices y segmentos, permitir cerrar la figura,
deshacer el último vértice y reiniciar el dibujo.

Esta SPEC define únicamente T01 de HU-007. «Tipo Paint» describe la interacción
gráfica del editor; no implica dibujo libre con pincel. El resultado es un
borrador gráfico local, sin medidas reales ni validación de convexidad.

## 2. Alcance

### Incluye

- Agregar vértices mediante clics dentro del lienzo, en orden de inserción.
- Mostrar los vértices y segmentos rectos entre puntos consecutivos.
- Cerrar la figura mediante una acción explícita cuando tenga al menos tres
  vértices, conectando el último con el primero.
- Deshacer el último vértice, incluida la reapertura de una figura cerrada.
- Reiniciar el dibujo y volver al estado inicial.
- Impedir la inserción de vértices mientras la figura permanezca cerrada.
- Mantener el estado del borrador en memoria dentro de la feature `orders`.

### Fuera de alcance

- Dibujo libre con pincel, trazos continuos y entrada manual de coordenadas.
- Ingreso de medidas reales, escala física y conversión a milímetros: T02.
- Validación de convexidad: T03. T01 tampoco certifica validez geométrica,
  ausencia de cruces, área positiva ni aptitud para corte.
- Arrastrar o mover vértices, insertar vértices intermedios y rehacer acciones.
  La edición de T01 se limita a deshacer el último vértice y continuar dibujando.
- Persistencia local o remota, guardado de pedidos o piezas y consumo de API.
- Cambios de backend, base de datos, migraciones o permisos.
- Rasterización, cálculo de patrones de corte y optimización.

## 3. Actor y precondiciones

**Actor:** Operario.

**Precondiciones:**

- El Operario tiene abierto el editor desde el contexto de Pedidos, con el
  lienzo visible y disponible para recibir clics.
- El dibujo comienza vacío y abierto, sin datos recuperados de almacenamiento.
- La interacción gráfica no requiere un pedido persistido, conexión a la API,
  catálogo remoto ni base de datos disponible.
- La autenticación y autorización del flujo contenedor no se implementan ni
  modifican en T01.

## 4. Entradas y datos

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| Clic en el lienzo | Evento de puntero con posición local | Agrega un vértice únicamente dentro del área de dibujo y mientras la figura esté abierta. |
| Vértices | Lista ordenada de puntos gráficos `(x, y)` | Se obtienen del clic respecto al lienzo; son datos internos de pantalla, no milímetros ni campos editables manualmente. |
| Figura cerrada | Booleano | Inicialmente falso; solo pasa a verdadero con al menos tres vértices. |
| Cerrar figura | Acción de UI | Conecta el último vértice con el primero sin duplicar el primer punto en la lista. |
| Deshacer último vértice | Acción de UI | Elimina el último punto; si la figura estaba cerrada, también la reabre. |
| Reiniciar dibujo | Acción de UI | Vacía los vértices y restablece la figura abierta. |

Los segmentos se derivan de la lista y del estado de cierre. Con `n` vértices,
una figura abierta muestra `max(n - 1, 0)` segmentos; una cerrada muestra `n`.
No se genera todavía un payload de API ni una geometría validada de pieza.

## 5. Reglas de negocio

- RN-01: Cada clic aceptado agrega exactamente un vértice al final de la lista.
  Mover o arrastrar el puntero no genera una sucesión de puntos.
- RN-02: Los vértices y segmentos reflejan el orden de inserción. El primer
  vértice se muestra sin segmento; cada nuevo vértice se conecta al anterior.
- RN-03: Cerrar requiere al menos tres vértices. El cierre agrega visualmente
  el segmento entre el último y el primero, sin agregar otro vértice.
- RN-04: Una figura cerrada no acepta nuevos vértices. La inserción se habilita
  nuevamente al reiniciar o al editar mediante Deshacer último vértice.
- RN-05: Deshacer elimina exactamente el último vértice y los segmentos que
  dependían de él. Si la figura estaba cerrada, elimina también el cierre y
  deja una secuencia abierta con los vértices restantes.
- RN-06: Deshacer sin vértices y cerrar con menos de tres están deshabilitados.
  Cerrar una figura ya cerrada no cambia el dibujo.
- RN-07: Reiniciar deja cero vértices, cero segmentos y estado abierto,
  independientemente del estado previo; repetirlo conserva ese resultado.
- RN-08: El cierre es exclusivamente gráfico. No se presenta como validación
  de convexidad, confirmación de pieza válida ni guardado exitoso.
- RN-09: La compatibilidad posterior con `POLIGONO_CONVEXO` requiere completar
  las medidas de T02 y la validación de T03. El borrador de T01 no se etiqueta
  como polígono convexo validado ni se envía a persistencia u optimización.

## 6. Flujo principal

1. El Operario abre el editor y observa el lienzo vacío, las instrucciones y
   las acciones Cerrar figura, Deshacer último vértice y Reiniciar dibujo.
2. Hace clic dentro del lienzo y aparece el primer vértice.
3. Agrega vértices mediante clics; se muestran los segmentos que los conectan
   en orden. Al llegar a tres vértices se habilita Cerrar figura.
4. Activa Cerrar figura; se dibuja el segmento final hacia el primer vértice
   y se indica que la figura está cerrada.
5. Los clics posteriores en el lienzo no modifican la figura cerrada.
6. Puede deshacer el último vértice para reabrir y continuar el dibujo, o
   reiniciar para comenzar otro borrador vacío. El resultado permanece en memoria.

## 7. Flujos alternativos y errores

- **Menos de tres vértices:** Cerrar figura permanece deshabilitado y la UI
  informa que se requieren al menos tres; no aparece un segmento de cierre.
- **Dibujo abierto:** Deshacer elimina el último vértice. Si solo había uno,
  el lienzo queda vacío; con cero, la acción queda deshabilitada.
- **Dibujo cerrado:** Deshacer elimina el último vértice, quita el cierre y
  habilita nuevos clics. Se puede volver a cerrar al reunir tres puntos.
- **Clic fuera del lienzo o sobre controles:** No modifica la lista de vértices.
- **Figura cerrada:** Los clics interiores no agregan puntos; la UI indica que
  se debe deshacer o reiniciar para continuar.
- **Reinicio:** Funciona sobre un dibujo vacío, abierto o cerrado; no conserva
  segmentos ni estado de cierre del dibujo anterior.
- **Figura cóncava o con cruces:** T01 puede mostrarla y cerrarla gráficamente;
  no la declara válida para el dominio ni implementa la validación de T03.
- **Recarga o salida del editor:** No se garantiza conservar el borrador,
  porque la persistencia está fuera del alcance.

## 8. Criterios de aceptación

- **CA-01 — Agregar vértices:** Dado un lienzo vacío y abierto, al hacer tres
  clics en posiciones distintas dentro de él, se muestran exactamente tres
  vértices en esas posiciones y en ese orden. Un clic fuera del lienzo o en
  un control no agrega vértices; mover el puntero sin hacer clic tampoco.
- **CA-02 — Visualizar segmentos:** Con un vértice no hay segmentos; al agregar
  el segundo aparece uno y con el tercero aparecen dos, conectando únicamente
  puntos consecutivos. Antes de cerrar no hay segmento entre el último y el
  primero. La representación se actualiza después de cada acción.
- **CA-03 — Cerrar la figura:** Con cero, uno o dos vértices, Cerrar figura está
  deshabilitado y se informa el mínimo requerido. Con tres o más, al activarlo
  aparece el segmento del último al primero, se mantiene el número de vértices
  y se indica el estado cerrado. Volver a intentar cerrar no altera el resultado.
- **CA-04 — Deshacer último vértice:** Con una secuencia abierta de tres puntos,
  Deshacer deja los dos primeros y un segmento. Repetir deja un punto sin
  segmentos y luego el lienzo vacío, con Deshacer deshabilitado. En una figura
  cerrada de cuatro puntos, Deshacer deja los tres primeros, dos segmentos y
  estado abierto; un clic posterior puede agregar un nuevo vértice.
- **CA-05 — Reiniciar dibujo:** Desde un dibujo abierto o cerrado, Reiniciar
  deja cero vértices, cero segmentos y estado abierto. Cerrar y Deshacer quedan
  deshabilitados, y el siguiente clic crea el primer punto de un nuevo dibujo.
  Reiniciar nuevamente sobre el lienzo vacío no produce errores ni cambios.
- **CA-06 — Bloquear inserción tras el cierre:** Dada una figura cerrada, varios
  clics en distintas posiciones del lienzo conservan sus vértices, segmentos y
  estado. La inserción se recupera únicamente tras Reiniciar o Deshacer, con
  los resultados definidos en CA-04 y CA-05.
- **CA-07 — Respetar el alcance gráfico:** La interfaz no ofrece pincel, entrada
  manual de coordenadas ni medidas reales. Completar el flujo no realiza
  solicitudes de guardado, no persiste el dibujo y no muestra una confirmación
  de convexidad o de pieza validada.

## 9. Impacto técnico

### Módulos

- La implementación futura del lienzo, controles, estado y estilos se ubicará
  en `frontend/src/features/orders/`, actualmente reservada mediante `.gitkeep`,
  siguiendo las [convenciones de features](../../frontend/src/features/README.md).
- `frontend/src/pages/NuevoPedido.jsx` es el punto previsto de integración con
  la pantalla actual. Sus ajustes se limitarán a dar acceso al editor;
  `NuevoPedido.css` solo se ajustará si la integración visual lo requiere.
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

- Incorporar un área de dibujo con vértices visibles, segmentos rectos y una
  indicación de estado abierto o cerrado.
- Incorporar controles identificables para cerrar, deshacer y reiniciar, con
  estados habilitados coherentes y ayuda sobre el mínimo de tres vértices.
- Calcular la posición local del clic para que el punto coincida con la posición
  señalada, incluso con desplazamiento de página. Este ajuste de pantalla no
  es la conversión física a milímetros de T02.
- La tecnología de renderizado se decidirá durante la implementación; esta SPEC
  no exige una biblioteca de dibujo adicional.

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

Las pruebas corresponden a la implementación futura. Esta SPEC en Draft no
declara resultados de ejecución ni criterios aprobados.

| Prueba | Escenario y resultado a comprobar | Criterios |
|---|---|---|
| P-01 | Agregar puntos con clics interiores; probar movimiento sin clic, clics exteriores y controles sin inserciones adicionales. | CA-01 |
| P-02 | Dibujar uno, dos, tres y cuatro puntos; comprobar orden, posiciones y número de segmentos abiertos. | CA-01, CA-02 |
| P-03 | Intentar cerrar con cero, uno y dos puntos; cerrar con tres y cuatro; verificar el segmento final sin duplicar vértices. | CA-03 |
| P-04 | Deshacer sucesivamente hasta vaciar; deshacer una figura cerrada, continuar agregando y volver a cerrar. | CA-04, CA-06 |
| P-05 | Reiniciar desde vacío, abierto y cerrado; repetir y comenzar un dibujo nuevo sin restos anteriores. | CA-05 |
| P-06 | Hacer varios clics después del cierre y comprobar que la figura no cambia; repetir tras deshacer y reiniciar. | CA-06 |
| P-07 | Completar el flujo sin backend y comprobar ausencia de solicitudes de guardado, persistencia y controles fuera de alcance. | CA-07 |
| P-08 | Repetir inserción y cierre con distintos tamaños de ventana y desplazamiento de página; comprobar coincidencia visual entre clics y vértices. | CA-01, CA-02 |

- Verificar los escenarios en navegador. Las pruebas automatizadas futuras de
  estado e interacción, si se incorporan, deben comprobar estos comportamientos.
- Ejecutar `npm run lint` y `npm run build` desde `frontend/` después de la
  implementación y registrar sus resultados reales. No sustituyen las pruebas
  funcionales; actualmente no existe un script `npm test`.
- Comprobar que la integración mantiene el acceso a la pantalla y el comportamiento
  previo de selección de material y listado de piezas de NuevoPedido.
- Seguir las [convenciones de pruebas](../testing/README.md); no se requieren
  pruebas de API, base de datos, rasterización u optimización para T01.

## 11. Evidencias requeridas

La evidencia futura se ubicará en `docs/evidence/sprint-01/HU-007/`, identificando
explícitamente T01 y siguiendo las [convenciones de evidencia](../evidence/README.md).
Esta SPEC no crea esa carpeta ni implica que las pruebas ya se hayan realizado.

- Registro de validación enlazado a esta SPEC, con rama, commit, presencia de
  cambios sin commit, entorno, navegador y tamaños de ventana realmente utilizados.
- Matriz de ejecución de P-01 a P-08 y CA-01 a CA-07, con pasos, resultado esperado,
  resultado observado y limitaciones o incidencias.
- Capturas o una grabación breve del lienzo vacío, inserción de vértices,
  segmentos abiertos, cierre, bloqueo de nuevos puntos, deshacer y reinicio.
  El bloqueo debe sustentarse en una secuencia de acciones, no solo en una imagen.
- Comandos, directorio de ejecución y resultados reales de lint y build; incluir
  resultados de pruebas automatizadas únicamente si se incorporan y ejecutan.
- Registro de la comprobación de ausencia de solicitudes de guardado durante el
  flujo y de la integración con NuevoPedido, sin incluir datos sensibles.

## Historial de estado

- Draft — Alcance de HU-007 T01 documentado; pendiente de revisión,
  implementación y verificación.