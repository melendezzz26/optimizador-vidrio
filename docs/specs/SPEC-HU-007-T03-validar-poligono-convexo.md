# SPEC — HU-007 T03: validar polígono convexo

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | HU-007 |
| Tarea | T03 — Validar polígono convexo |
| Responsable | Andro Quispe Cesias |
| Dependencia | T02 — Medidas reales por segmento |
| Rama | feature/HU-007-lienzo-pieza-personalizada |

---

## 1. Objetivo

Validar que la geometría dimensional generada en T02 represente un polígono cerrado,
simple y convexo antes de permitir que la pieza personalizada continúe dentro del flujo
del pedido.

La validación debe operar sobre `vertices_mm` generados por T02 y no debe modificar
la geometría original.

---

## 2. Alcance

### Incluye

- Validar que exista una geometría dimensional completa proveniente de T02.
- Validar cantidad mínima de vértices.
- Validar coordenadas numéricas finitas.
- Detectar geometrías degeneradas.
- Detectar autointersecciones entre segmentos no adyacentes.
- Validar convexidad mediante orientación/producto cruzado.
- Aceptar polígonos convexos independientemente de su orientación horaria o antihoraria.
- Mostrar al Operario el resultado de la validación.
- Mantener bloqueado el flujo cuando la geometría no sea válida.
- Exponer un resultado reutilizable por el flujo posterior de Orders.

### Fuera de alcance

- Modificar automáticamente el polígono para volverlo convexo.
- Calcular convex hull.
- Mover vértices automáticamente.
- Triangular la figura.
- Rasterizar la pieza.
- Ejecutar First Fit, Best Fit o Worst Fit.
- Persistir la pieza.
- Crear endpoints.
- Modificar backend.
- Modificar base de datos.
- Crear migraciones Alembic.

---

## 3. Actor y precondiciones

### Actor

Operario.

### Precondiciones

- El editor de pieza personalizada está disponible.
- El polígono fue cerrado en T01.
- Todas las longitudes reales fueron ingresadas en T02.
- T02 produjo una geometría dimensional completa mediante `vertices_mm`.

Si la geometría dimensional está incompleta, T03 no debe considerarla válida.

---

## 4. Entrada

La entrada principal será:

```js
vertices_mm = [
  [x1, y1],
  [x2, y2],
  ...
]

```

Reglas:

- Las coordenadas están expresadas en milímetros.
- El primer vértice no debe repetirse al final.
- El cierre del polígono se interpreta entre el último vértice y el primero.
- Las coordenadas pueden incluir valores negativos.
- Todos los valores deben ser números finitos.

T03 no reconstruye las longitudes ni modifica `vertices_mm`.

---

## 5. Resultado de validación

La función de dominio deberá devolver un resultado explícito equivalente a:

```js
{
  isValid: true,
  isSimple: true,
  isConvex: true,
  orientation: "CW",
  reason: "VALID",
  message: "Geometría convexa validada."
}
```

Los nombres exactos pueden ajustarse durante implementación siempre que el contrato
mantenga información equivalente.

---

## 6. Estados de validación

Se utilizarán como mínimo los siguientes motivos:

| Código | Significado |
|---|---|
| `INCOMPLETE` | T02 todavía no genera una geometría completa |
| `TOO_FEW_VERTICES` | Existen menos de 3 vértices |
| `INVALID_COORDINATES` | Existe alguna coordenada no finita |
| `DEGENERATE` | El polígono tiene área prácticamente nula o una geometría inválida |
| `SELF_INTERSECTION` | Dos lados no adyacentes se intersectan |
| `NON_CONVEX` | El polígono es simple pero presenta concavidad |
| `VALID` | El polígono es simple y convexo |

Los mensajes de interfaz deberán ser entendibles para el Operario y no mostrar detalles
internos del algoritmo.

---

## 7. Validación estructural

Antes de validar convexidad se comprobará:

1. Existen al menos 3 vértices.
2. Todas las coordenadas son finitas.
3. No existen vértices consecutivos equivalentes.
4. El lado de cierre entre el último y el primer vértice tiene longitud distinta de cero.
5. El área del polígono no es prácticamente cero.

Una geometría que no cumpla estas condiciones no continuará hacia la comprobación de
convexidad.

---

## 8. Área y tolerancia numérica

La validación debe considerar errores normales de punto flotante.

La tolerancia debe depender de la escala de la geometría y no utilizar comparaciones
exactas como:

```js
cross === 0
```

La implementación deberá centralizar las tolerancias numéricas y documentar su propósito.

No se debe utilizar una tolerancia arbitraria diferente en cada función.

---

## 9. Polígono simple

Antes de comprobar convexidad debe verificarse que el polígono sea simple.

Se compararán los segmentos no adyacentes.

Se rechazará cuando:

- dos lados no adyacentes se crucen;
- dos lados no adyacentes se superpongan;
- un vértice no adyacente toque el interior de otro segmento.

Los lados adyacentes pueden compartir su vértice común.

Una autointersección devolverá:

```text
SELF_INTERSECTION
```

---

## 10. Convexidad

Para cada conjunto consecutivo de tres vértices:

```text
A → B → C
```

se evaluará la orientación mediante el producto cruzado:

```text
(B - A) × (C - B)
```

Un polígono será convexo cuando todos los giros significativos mantengan la misma
orientación.

Se aceptarán tanto:

- orientación horaria;
- orientación antihoraria.

Si existen giros significativos con signos opuestos, el resultado será:

```text
NON_CONVEX
```

---

## 11. Vértices colineales

Los vértices intermedios colineales podrán formar parte de un polígono convexo siempre
que:

- no produzcan retroceso sobre el mismo segmento;
- no generen solapamiento;
- no provoquen autointersección;
- el área total del polígono continúe siendo válida.

Los giros considerados numéricamente colineales se ignorarán para determinar el signo
global de la convexidad.

Si todos los vértices son colineales, el resultado será:

```text
DEGENERATE
```

---

## 12. Integración con T02

T03 consume exclusivamente la geometría dimensional completa producida por T02.

Flujo:

```text
T01
Dibujar y cerrar polígono
        ↓
T02
Ingresar longitudes S1...Sn
        ↓
Reconstruir vertices_mm
        ↓
T03
Validar geometría
        ↓
¿Simple y convexa?
     ↙        ↘
   No          Sí
rechazar     validar
```

T03 no debe alterar las medidas introducidas por el usuario ni volver a ejecutar el
proceso de dimensionamiento de T02.

---

## 13. Comportamiento de interfaz

Mientras T02 esté incompleto:

```text
Pendiente de completar dimensiones.
```

Si T03 rechaza la geometría:

- debe mostrarse un mensaje entendible;
- el flujo posterior debe permanecer bloqueado;
- el Operario puede modificar nuevamente las medidas de T02.

Ejemplos:

```text
La geometría se intersecta consigo misma.
```

```text
La figura resultante no es convexa.
```

Si T03 acepta:

```text
Geometría convexa validada.
```

La validación debe actualizarse automáticamente si el usuario modifica alguna longitud.

---

## 14. Criterios de aceptación

### CA-01
T03 no valida una geometría mientras T02 permanezca incompleto.

### CA-02
Un polígono con menos de tres vértices es rechazado.

### CA-03
Una geometría con coordenadas no finitas es rechazada.

### CA-04
Una geometría de área prácticamente nula es rechazada.

### CA-05
Un triángulo válido es aceptado como convexo.

### CA-06
Un cuadrilátero convexo es aceptado.

### CA-07
Un pentágono convexo es aceptado.

### CA-08
La validación acepta orientación horaria.

### CA-09
La validación acepta orientación antihoraria.

### CA-10
Un polígono cóncavo es rechazado como `NON_CONVEX`.

### CA-11
Un polígono con autointersección es rechazado como `SELF_INTERSECTION`.

### CA-12
Una geometría completamente colineal es rechazada como `DEGENERATE`.

### CA-13
Un vértice colineal intermedio puede aceptarse si la geometría continúa siendo simple
y convexa.

### CA-14
T03 no modifica `vertices_mm`.

### CA-15
Al cambiar una longitud en T02, la validación de T03 se recalcula.

### CA-16
La interfaz informa de manera visible si la geometría fue aceptada o rechazada.

### CA-17
Los errores mostrados al usuario no exponen detalles internos del algoritmo.

---

## 15. Impacto técnico

### Frontend

Se espera crear una utilidad independiente para la lógica geométrica, por ejemplo:

```text
frontend/src/features/orders/convexityValidation.js
```

e integrarla posteriormente con:

```text
frontend/src/features/orders/CustomPieceEditor.jsx
```

### Backend

No aplica.

### API

No aplica.

### Base de datos

No aplica.

### Migraciones

No aplica.

---

## 16. Pruebas previstas

### Unitarias

Crear:

```text
frontend/tests/unit/convexityValidation.test.js
```

Casos mínimos:

- triángulo convexo;
- rectángulo convexo;
- orientación horaria;
- orientación antihoraria;
- pentágono convexo;
- pentágono cóncavo;
- polígono autointersectado;
- todos los puntos colineales;
- vértice colineal intermedio;
- menos de tres vértices;
- coordenada NaN;
- coordenada Infinity;
- vértices consecutivos repetidos;
- coordenadas negativas;
- inmutabilidad de entrada.

Técnica principal:

```text
Unitarias + caja blanca + valores límite
```

### Componente

Actualizar las pruebas de `CustomPieceEditor` para verificar:

- estado pendiente;
- geometría válida;
- geometría no convexa;
- mensaje visible;
- recálculo después de modificar una medida.

Técnica:

```text
Component + caja negra
```

### E2E

Actualizar el flujo E2E de HU-007 para comprobar:

```text
dibujar
→ cerrar
→ dimensionar
→ validar convexidad
```

Debe existir al menos:

- caso válido;
- caso rechazado.

El E2E continúa siendo frontend mientras no exista integración con backend y BD.

### No aplica actualmente

- API;
- integración backend;
- PostgreSQL;
- Supabase;
- Alembic;
- persistencia;
- smoke post-deploy;
- benchmark.

---

## 17. Evidencias requeridas

La evidencia de T03 debe registrar:

- PBI y tarea;
- commit;
- entorno;
- casos ejecutados;
- comando utilizado;
- resultado esperado;
- resultado obtenido;
- PASS/FAIL;
- pruebas automatizadas;
- lint;
- build;
- limitaciones encontradas.

Ubicación:

```text
docs/evidence/sprint-01/HU-007/
```

---

## 18. Estado actual

```text
Draft
```

La SPEC debe ser revisada antes de iniciar la implementación.