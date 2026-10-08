# HU-007 T01 — Validación funcional del lienzo poligonal

## Contexto

- Historia de usuario: HU-007 — Pieza personalizada.
- Tarea: T01 — Implementar lienzo tipo Paint.
- Responsable: Andro Q.
- Rama: `feature/HU-007-lienzo-pieza-personalizada`.
- Componente validado: `CustomPieceEditor`.
- Entorno de prueba: frontend React + Vite.
- Dispositivo principal: PC/laptop.
- Entrada manual: `http://localhost:5173/hu007-t01.html`.

## Objetivo de la validación

Comprobar que el operario pueda construir gráficamente un polígono mediante vértices, visualizar los segmentos, cerrar el contorno, deshacer acciones y reiniciar el dibujo, sin introducir todavía medidas reales ni validación de convexidad.

## Resultados funcionales

| Prueba | Validación realizada | Resultado esperado | Resultado obtenido | Estado |
|---|---|---|---|---|
| P-01 | Estado inicial | 0 vértices y controles Cerrar, Deshacer y Reiniciar deshabilitados | Comportamiento esperado | PASS |
| P-02 | Agregar vértices | Cada clic principal agrega un vértice y genera segmentos consecutivos | Comportamiento esperado | PASS |
| P-03 | Cerrar polígono | Con 3 o más vértices se habilita Cerrar polígono y se une el último vértice con el primero | Comportamiento esperado | PASS |
| P-04 | Deshacer | Elimina el último vértice y, si estaba cerrado, reabre el polígono | Comportamiento esperado | PASS |
| P-05 | Reiniciar | Elimina todos los vértices y devuelve el editor al estado inicial | Comportamiento esperado | PASS |
| P-06 | Bloqueo posterior al cierre | Después de cerrar no se pueden agregar nuevos vértices | Comportamiento esperado | PASS |
| P-07 | Alcance T01 | No existen medidas reales, validación de convexidad, persistencia ni llamadas API | Alcance respetado | PASS |
| P-08 | Comportamiento visual | Editor utilizable en escritorio y adaptable a tamaño reducido | Comportamiento esperado | PASS |

## Validación técnica

### ESLint

Comando:

`npm.cmd run lint`

Resultado: ejecución finalizada sin errores.

Estado: **PASS**.

### Build

Comando:

`npm.cmd run build`

Resultado: Vite compiló correctamente el frontend.

Estado: **PASS**.

### Integridad del diff

Comando:

`git diff --check`

Resultado: sin errores de espacios o formato detectados.

Estado: **PASS**.

## Incidencias encontradas durante el desarrollo

### Bloqueo de npm en PowerShell

PowerShell bloqueó inicialmente la ejecución de `npm.ps1` debido a la política de ejecución de scripts.

La validación pudo continuar utilizando `npm.cmd`, sin modificar la política de seguridad del sistema.

### Acceso al editor desde la aplicación

El flujo actual de autenticación todavía no permite acceder normalmente a `NuevoPedido`.

Como este comportamiento es preexistente y está fuera del alcance de HU-007 T01, se implementó una entrada manual independiente para validar el editor sin modificar autenticación ni navegación.

## Evidencias gráficas

- `t01-editor-closed-desktop.png`
- `t01-editor-closed-mobile.png`

Las pruebas manuales adicionales confirmaron correctamente los estados inicial, abierto, cerrado, deshacer, reiniciar y bloqueo posterior al cierre.

## Observación de alcance

T01 realiza únicamente el dibujo y cierre gráfico del polígono.

La asociación de dimensiones reales corresponde a **HU-007 T02**.

La validación de que el polígono sea convexo corresponde a **HU-007 T03**. Por ello, durante T01 todavía es posible dibujar y cerrar visualmente un polígono cóncavo.

## Conclusión

Los criterios funcionales y técnicos definidos para HU-007 T01 fueron verificados satisfactoriamente.

**Resultado final: PASS.**