# Evidencia — HU-007 T03: validación de polígono convexo

## Información general

| Campo | Valor |
|---|---|
| PBI | HU-007 |
| Tarea | T03 — Validar polígono convexo |
| Rama | feature/HU-007-lienzo-pieza-personalizada |
| Commit base | 49a9344 |
| Entorno | Windows 11 |
| Frontend | React + Vite |
| Pruebas de componente | Vitest + React Testing Library |
| E2E | Playwright + Google Chrome estable |

---

## 1. Objetivo

Verificar que la geometría dimensional generada por T02 sea clasificada correctamente
antes de continuar con el flujo de una pieza personalizada.

T03 valida:

- geometría incompleta;
- cantidad mínima de vértices;
- coordenadas inválidas;
- geometrías degeneradas;
- colinealidad;
- autointersección;
- concavidad;
- convexidad;
- orientación horaria y antihoraria;
- tolerancia numérica;
- inmutabilidad.

---

## 2. Implementación

Se agregó la validación geométrica independiente en:

`frontend/src/features/orders/convexityValidation.js`

La validación se integró con:

`frontend/src/features/orders/CustomPieceEditor.jsx`

T03 consume la geometría `vertices_mm` producida por T02 y no modifica el algoritmo
de dimensionamiento.

La validación se recalcula automáticamente cuando cambian las medidas.

---

## 3. Prioridad de clasificación

La implementación utiliza la siguiente prioridad:

1. `INCOMPLETE`
2. `TOO_FEW_VERTICES`
3. `INVALID_COORDINATES`
4. `DEGENERATE` por lados o vértices degenerados
5. `DEGENERATE` para geometría completamente colineal
6. `DEGENERATE` para retroceso colineal inválido
7. `SELF_INTERSECTION`
8. `DEGENERATE` para área prácticamente nula restante
9. `NON_CONVEX`
10. `VALID`

La comprobación de área algebraica no clasifica inmediatamente una figura como
degenerada, ya que un bow-tie simétrico puede presentar área algebraica cercana a cero
por cancelación y debe clasificarse como `SELF_INTERSECTION`.

---

## 4. Pruebas unitarias

Comando:

`npm.cmd run test:unit`

Resultado:

- 84 pruebas ejecutadas.
- 84 PASS.
- 0 FAIL.
- 0 skipped.

Las 38 pruebas existentes de T02 continúan pasando.

Se incorporaron 46 pruebas adicionales relacionadas con T03.

Casos cubiertos:

- triángulos CW y CCW;
- rectángulos CW y CCW;
- pentágonos convexos;
- polígonos cóncavos;
- bow-tie;
- autointersecciones;
- geometría colineal;
- vértices colineales intermedios;
- retroceso colineal;
- 0, 1 y 2 vértices;
- entrada ausente;
- NaN;
- Infinity;
- -Infinity;
- coordenadas mal formadas;
- vértices repetidos;
- lado de cierre degenerado;
- coordenadas negativas;
- escalas extremadamente pequeñas y grandes;
- contacto entre lados no adyacentes;
- solapamientos;
- tolerancia numérica;
- área casi nula;
- inmutabilidad;
- determinismo.

Técnica:

Unitarias + caja blanca + valores límite.

Estado:

PASS.

---

## 5. Pruebas de componente

Comando:

`npm.cmd run test:component`

Resultado:

- 28 pruebas ejecutadas.
- 28 PASS.
- 0 FAIL.

Distribución:

- T01: 7 pruebas.
- T02: 13 pruebas.
- T03: 8 pruebas.

T03 verifica:

- estado pendiente;
- geometría convexa válida;
- geometría cóncava;
- autointersección;
- recálculo al editar medidas;
- eliminación de un resultado válido al borrar medidas;
- invalidación al usar Deshacer;
- invalidación al usar Reiniciar;
- mensajes accesibles;
- bloqueo del registro posterior.

Técnica:

Component + caja negra.

Estado:

PASS.

---

## 6. Pruebas E2E

Comando:

`npm.cmd run test:e2e`

Resultado:

- 20 pruebas ejecutadas.
- 20 PASS.
- 0 FAIL.

Se ejecutaron los casos en:

- desktop;
- mobile emulado.

Casos T03 añadidos:

- `T03-E05`: validación automática de geometría convexa.
- `T03-E06`: rechazo de concavidad y posterior autointersección.
- `T03-E07`: bow-tie rechazado como autointersección.
- `T03-E08`: regresión de descripción accesible del bloqueo.

Los E2E continúan siendo exclusivamente frontend.

No representan todavía el flujo completo frontend → backend → base de datos.

Estado:

PASS.

---

## 7. Incidencias encontradas

### Incidencia 1 — prioridad área/autointersección

Se detectó una ambigüedad contractual:

un bow-tie simétrico puede presentar área algebraica prácticamente cero.

Se aclaró la SPEC para establecer que la autointersección debe clasificarse como
`SELF_INTERSECTION` antes del rechazo final por área nula.

Resultado:

RESUELTO.

### Incidencia 2 — descripción accesible del botón

Los primeros E2E detectaron que el botón `Agregar pieza al pedido` recibía como
descripción accesible el texto genérico:

`Resultado de validación geométrica`

en lugar del mensaje dinámico de T03.

Se separó el rol accesible del estado y el elemento que contiene el mensaje dinámico.

Resultado:

20 E2E PASS.

### Incidencia 3 — Playwright Chromium

La descarga del navegador Chromium administrado por Playwright presentó timeout.

La ejecución local utiliza Google Chrome estable mediante `channel: "chrome"`.

Resultado:

RESUELTO PARA ENTORNO LOCAL.

---

## 8. Validaciones adicionales

### Lint

Comando:

`npm.cmd run lint`

Resultado:

PASS.

### Build

Comando:

`npm.cmd run build`

Resultado:

PASS.

### Git

Comando:

`git diff --check`

Resultado:

PASS.

---

## 9. Total de pruebas automatizadas

| Nivel | PASS | FAIL |
|---|---:|---:|
| Unitarias | 84 | 0 |
| Componentes | 28 | 0 |
| E2E | 20 | 0 |
| **Total** | **132** | **0** |

---

## 10. Elementos no aplicables a T03

| Elemento | Estado |
|---|---|
| API | No aplica |
| Backend | No aplica |
| PostgreSQL / Supabase | No aplica |
| Alembic | No aplica |
| Persistencia | No aplica |
| Benchmark | No aplica |
| Smoke post-deploy | No aplica actualmente |

T03 pertenece al frontend y a la lógica geométrica local.

---

## 11. Limitaciones

El botón `Agregar pieza al pedido` continúa deshabilitado aunque T03 determine una
geometría válida, debido a que el registro definitivo de la pieza todavía no dispone
de un flujo downstream implementado.

No se agregó persistencia ni comportamiento ficticio para habilitarlo.

Las pruebas E2E actuales cubren el flujo frontend y no sustituyen el E2E completo que
posteriormente deberá atravesar frontend, backend y base de datos.

---

## 12. Resultado

HU-007 T03 cumple la validación técnica prevista:

- lógica geométrica validada;
- regresiones T01/T02 preservadas;
- pruebas unitarias aprobadas;
- pruebas de componente aprobadas;
- E2E aprobados;
- accesibilidad verificada;
- lint aprobado;
- build aprobado;
- sin modificaciones de backend o base de datos.

Resultado técnico:

**PASS**