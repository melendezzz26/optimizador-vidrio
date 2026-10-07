# TA-011 — Integración de inventario

## Bloque 2 — Consulta E2E y navegación por permisos

### Objetivo

Verificar que la interfaz React consulte el inventario mediante FastAPI,
muestre los datos persistidos y respete la visibilidad correspondiente al rol
Almacenero.

### Entorno de prueba

- Rol utilizado: Almacenero.
- Frontend: React + Vite.
- Backend: FastAPI.
- Persistencia: PostgreSQL/Supabase, según el entorno declarado para la prueba.

Esta revisión comprende las cuatro capturas existentes y la ejecución manual
confirmada de las cuatro teclas descrita en la evidencia 4. Se observan datos
en la interfaz y respuestas exitosas de la API; las imágenes por sí solas no
verifican su persistencia en PostgreSQL/Supabase.

### Evidencia 1 — Listado de planchas

Referencia: [TA011-01-listado-planchas-almacenero.png](capturas/TA011-01-listado-planchas-almacenero.png).

Se observa una sesión identificada con el rol Almacenero, la pantalla
Gestión de Inventario y la pestaña Planchas activa. El listado muestra:

| Tipo de vidrio | Espesor | Dimensiones | Cantidad | Estado | Fecha de registro |
| --- | --- | --- | --- | --- | --- |
| Espejo | 6 mm | 3210 × 2250 mm | 2 | Activo | 5 oct. 2026 |

El sidebar muestra Inicio, Gestión de inventario y Consulta de resultados.
No aparecen Registro de pedidos, Panel de roles ni Configuración.
Esta evidencia comprueba la visibilidad del menú para la sesión mostrada;
no constituye una prueba de autorización de rutas o endpoints.

### Evidencia 2 — Listado de retazos

Referencia: [TA011-02-listado-retazos-almacenero.png](capturas/TA011-02-listado-retazos-almacenero.png).

Se observa la pestaña Retazos activa y los siguientes registros con geometría
y área legibles:

| Código | Tipo de vidrio | Espesor | Geometría | Área | Estado | Fecha de registro |
| --- | --- | --- | --- | --- | --- | --- |
| RET-HU005-001 | Incoloro | 6 mm | Rectángulo 850 × 420 mm | 357000 mm² | Activo | 6 oct. 2026 |
| RET-HU005-002 | Incoloro | 6 mm | Rectángulo 600 × 300 mm | 180000 mm² | Activo | 6 oct. 2026 |

### Evidencia 3 — Consulta API

Referencia: [TA011-03-endpoints-inventario-200.png](capturas/TA011-03-endpoints-inventario-200.png).

Los logs del backend muestran respuestas HTTP 200 OK para:

| Método | Endpoint | Resultado observado |
| --- | --- | --- |
| GET | `/api/inventory/tipos-vidrio` | 200 OK |
| GET | `/api/inventory/planchas` | 200 OK |
| GET | `/api/inventory/retazos` | 200 OK |

En conjunto con los listados visibles, esta evidencia documenta la
comunicación exitosa React/FastAPI durante la prueba. La captura muestra
solicitudes GET exitosas, no únicamente OPTIONS. No muestra los cuerpos de
respuesta ni prueba por sí sola la persistencia en PostgreSQL.

### Evidencia 4 — Accesibilidad de pestañas

Referencia: [TA011-04-tabs-accesibles-teclado.png](capturas/TA011-04-tabs-accesibles-teclado.png).

Se observa la pestaña Retazos activa y un contorno de foco visible sobre ella.

La captura demuestra visualmente el foco y la pestaña activa. El comportamiento
de las cuatro teclas se verificó mediante ejecución manual, confirmada por el
usuario, con los siguientes resultados:

| Tecla | Resultado | Comportamiento observado manualmente |
| --- | --- | --- |
| ArrowRight | PASS | Desde Planchas activa Retazos y mueve el foco. |
| ArrowLeft | PASS | Desde Retazos activa Planchas y mueve el foco. |
| Home | PASS | Activa la primera pestaña, Planchas, y mueve el foco. |
| End | PASS | Activa la última pestaña, Retazos, y mueve el foco. |

### Resultado del Bloque 2

Los siguientes resultados PASS corresponden a lo observado en las capturas
y a la ejecución manual confirmada de las cuatro teclas:

| Punto verificado | Resultado | Evidencia y alcance |
| --- | --- | --- |
| Consulta del catálogo | PASS | GET `/api/inventory/tipos-vidrio` con HTTP 200; evidencia 3. |
| Listado de planchas | PASS | Registro visible con sus datos; evidencia 1. |
| Listado de retazos | PASS | Dos registros visibles con sus datos; evidencia 2. |
| Resolución de nombre de tipo de vidrio | PASS | Se muestran los nombres Espejo e Incoloro; evidencias 1 y 2. Se verifica el resultado visible, no el mecanismo interno de resolución. |
| Representación legible de geometría | PASS | Forma y dimensiones legibles para ambos retazos; evidencia 2. |
| Visibilidad por rol Almacenero | PASS | Rol identificado y sidebar con las tres opciones indicadas; evidencia 1. |
| Respuestas HTTP 200 observadas | PASS | Los tres GET de inventario devuelven 200 OK; evidencia 3. |
| Navegación por teclado de pestañas | PASS | ArrowRight, ArrowLeft, Home y End verificados manualmente; evidencia 4 muestra el foco visible. |

**Resultado del Bloque 2: PASS.** La evidencia 4 confirma visualmente el foco
sobre Retazos activa; el comportamiento de las cuatro teclas se verificó
mediante ejecución manual.

No se declaran resultados de registro E2E, edición, cambio de estado, filtros
ni HU-008, que pertenecen a bloques posteriores.

### Privacidad

Las evidencias revisadas no muestran JWT, encabezados Authorization,
contraseñas, hashes ni secretos. La interfaz muestra identificadores de una
cuenta de prueba, que no se reproducen en este documento.

El usuario local y la ruta de Windows visibles en la terminal no se consideran
credenciales y tampoco se reproducen aquí.
