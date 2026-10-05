# SPEC-TA-003 — API de inventario de vidrio

## Información general

| Campo | Valor |
|---|---|
| Estado | Draft |
| PBI relacionado | TA-003 — API de inventario de vidrio |
| Responsable | Fabricio A. / Fabricio M. |
| Reviewer | Pendiente |
| Sprint | Sprint 1 |
| Dependencia | TA-002 |

## 1. Objetivo

Implementar la API REST del módulo de inventario de NewGlass para gestionar
tipos de vidrio, planchas comerciales y retazos reutilizables utilizando
FastAPI, SQLAlchemy y PostgreSQL.

La implementación debe permitir registrar y consultar tipos de vidrio;
crear, listar y editar planchas; y crear, listar y editar retazos,
respetando el modelo de datos NewGlass v1.1 y las reglas de negocio
definidas para el inventario.

## 2. Alcance

### Incluye

- Registrar tipos de vidrio.
- Consultar tipos de vidrio.
- Crear planchas comerciales.
- Listar planchas comerciales.
- Editar planchas comerciales.
- Crear retazos reutilizables.
- Listar retazos reutilizables.
- Editar retazos reutilizables.
- Validar espesores, dimensiones, cantidades, geometrías y referencias.
- Validar la existencia y disponibilidad del tipo de vidrio asociado.
- Aplicar permisos de consulta y gestión según el rol autenticado.
- Persistir los cambios mediante SQLAlchemy en PostgreSQL.
- Exponer los endpoints mediante Swagger/OpenAPI.
- Incorporar pruebas unitarias, API e integración necesarias.

### Fuera de alcance

- Desarrollo de interfaces React para inventario.
- Eliminación física de tipos de vidrio, planchas o retazos.
- Consumo o descuento de stock como consecuencia de una optimización.
- Creación automática de retazos resultantes de un patrón de corte.
- First Fit, Best Fit, Worst Fit y selección LEX-V1.
- Rasterización de piezas o materiales.
- Confirmación transaccional de una optimización.
- Modificación del esquema de base de datos v1.1.
- Polígonos cóncavos, geometrías con agujeros o multipolígonos.
- Edición de tipos de vidrio en esta versión de TA-003.

## 3. Actor y precondiciones

**Actores:**

- Administrador.
- Almacenero.
- Operario para operaciones de consulta permitidas.

**Precondiciones:**

- El usuario debe estar autenticado mediante el mecanismo JWT existente.
- PostgreSQL debe encontrarse en el modelo de datos NewGlass v1.1.
- Alembic debe encontrarse en la revisión `b4d5e6f7a8c9`.
- Las tablas `tipos_vidrio`, `planchas` y `retazos` deben estar disponibles.
- Las operaciones de escritura deben ejecutarse únicamente para roles con
  permisos de gestión de inventario.

## 4. Entradas y datos

### 4.1 Tipo de vidrio

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| nombre | string | Obligatorio, máximo 100 caracteres y único |
| descripcion | string / null | Opcional |
| estado | boolean | Se registra activo por defecto |

La fecha y el identificador son gestionados por la persistencia cuando
corresponda al modelo.

### 4.2 Plancha

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| ancho_mm | decimal | Obligatorio y mayor que 0 |
| alto_mm | decimal | Obligatorio y mayor que 0 |
| espesor_mm | decimal | Uno de: 3, 4, 5.5, 6 u 8 mm |
| cantidad | integer | En creaci?n debe ser mayor que 0; en edici?n puede ser mayor o igual que 0 |
| id_tipo_vidrio | integer | Debe referenciar un tipo existente y activo |
| estado | boolean | Activo por defecto |

`id_plancha` y `fecha_registro` no son definidos por el cliente.

### 4.3 Retazo

| Campo / dato | Tipo / formato | Regla |
|---|---|---|
| codigo | string | Obligatorio, máximo 40 caracteres y único |
| espesor_mm | decimal | Uno de: 3, 4, 5.5, 6 u 8 mm |
| geometria | JSON | Obligatoria y conforme al contrato geométrico |
| id_tipo_vidrio | integer | Debe referenciar un tipo existente y activo |
| estado | boolean | Activo por defecto |

`id_retazo`, `area_mm2`, `fecha_registro` e `id_ejecucion_origen` no deben
ser definidos libremente por el cliente durante el registro manual.

### 4.4 Contrato geométrico de retazos v1

Los retazos registrados manualmente en TA-003 admiten únicamente las
siguientes geometrías.

#### RECTANGULO

```json
{
  "type": "RECTANGULO",
  "width_mm": 1000,
  "height_mm": 500
}
```

Reglas:

- `width_mm > 0`.
- `height_mm > 0`.

#### CIRCUNFERENCIA

```json
{
  "type": "CIRCUNFERENCIA",
  "radius_mm": 250
}
```

Regla:

- `radius_mm > 0`.

#### POLIGONO_CONVEXO

```json
{
  "type": "POLIGONO_CONVEXO",
  "vertices_mm": [
    [0, 0],
    [500, 0],
    [430, 300],
    [100, 420]
  ]
}
```

Reglas:

- Debe contener al menos tres vértices.
- Debe formar un polígono válido.
- No debe presentar auto-intersecciones.
- Debe ser convexo.
- Su área debe ser mayor que 0.

Los polígonos cóncavos y geometrías más complejas quedan fuera de
TA-003 v1.

## 5. Reglas de negocio

- RN-01: Los espesores admitidos son exclusivamente 3, 4, 5.5, 6 y 8 mm.
- RN-02: Una plancha debe tener ancho y alto mayores que cero.
- RN-03: Una plancha nueva debe registrarse con cantidad mayor que 0. En edici?n, la cantidad puede llegar a 0, pero nunca ser negativa.
- RN-04: Una plancha o retazo debe asociarse a un tipo de vidrio existente
  y activo.
- RN-05: El nombre de un tipo de vidrio debe ser único.
- RN-06: El código de un retazo debe ser único.
- RN-07: Un retazo solo puede utilizar RECTANGULO, CIRCUNFERENCIA o
  POLIGONO_CONVEXO en TA-003 v1.
- RN-08: El área del retazo se calcula en el backend a partir de su geometría
  y no se acepta como un valor confiable proporcionado por el cliente.
- RN-09: Para RECTANGULO, el área es `width_mm * height_mm`.
- RN-10: Para CIRCUNFERENCIA, el área es `pi * radius_mm^2`.
- RN-11: Para POLIGONO_CONVEXO, el área se calcula a partir de sus vértices.
- RN-12: `id_ejecucion_origen` permanece NULL en un retazo registrado
  manualmente. Su asignación corresponderá posteriormente a la generación
  automática de sobrantes al confirmar una optimización.
- RN-13: Las fechas de registro son asignadas por el backend y deben contener
  información de zona horaria.
- RN-14: Los registros no se eliminan físicamente como operación normal.
- RN-15: Administrador y Almacenero pueden gestionar planchas y retazos.
- RN-16: Administrador, Almacenero y Operario pueden consultar stock.
- RN-17: Administrador y Almacenero pueden gestionar tipos de vidrio.
- RN-18: Administrador, Almacenero y Operario pueden consultar tipos de vidrio.
- RN-19: Los identificadores y fechas de registro no pueden modificarse mediante
  los endpoints de edición.
- RN-20: Si se modifica la geometría de un retazo, su área debe recalcularse.

## 6. Flujo principal

1. El cliente autenticado realiza una solicitud a un endpoint de inventario.
2. La capa de presentación valida el contrato HTTP y obtiene al usuario actual.
3. Se verifica que el rol posea el permiso requerido para la operación.
4. La capa de aplicación valida las reglas de negocio.
5. Cuando corresponda, se comprueba la existencia y estado del tipo de vidrio.
6. Para retazos se valida la geometría y se calcula el área.
7. La infraestructura realiza la operación mediante SQLAlchemy.
8. La transacción se confirma si la operación finaliza correctamente.
9. La API devuelve el recurso resultante utilizando su esquema de respuesta.
10. Una consulta posterior debe recuperar los mismos datos persistidos.

## 7. Flujos alternativos y errores

- Solicitud sin autenticación: HTTP 401.
- Usuario autenticado sin permiso: HTTP 403.
- Recurso solicitado inexistente: HTTP 404.
- Tipo de vidrio referenciado inexistente: HTTP 404.
- Tipo de vidrio inactivo para un nuevo material: HTTP 422.
- Nombre de tipo de vidrio duplicado: HTTP 409.
- Código de retazo duplicado: HTTP 409.
- Dimensiones no positivas: HTTP 422.
- Cantidad menor o igual que 0 al crear una plancha, o negativa al editarla: HTTP 422.
- Espesor no permitido: HTTP 422.
- Geometría no soportada o inválida: HTTP 422.
- PATCH sin ningún campo modificable: HTTP 422.
- Error inesperado de persistencia: rollback de la transacción y respuesta
  controlada sin exponer detalles internos de PostgreSQL.

## 8. Criterios de aceptación

- CA-01: La API permite registrar un tipo de vidrio válido en PostgreSQL.
- CA-02: La API permite consultar los tipos de vidrio registrados.
- CA-03: La API permite crear una plancha válida y recuperarla posteriormente.
- CA-04: La API permite listar las planchas registradas.
- CA-05: La API permite editar los campos autorizados de una plancha.
- CA-06: La API rechaza anchos, altos, espesores o cantidades inválidas.
- CA-07: La API permite crear un retazo válido y recuperarlo posteriormente.
- CA-08: La API permite listar los retazos registrados.
- CA-09: La API permite editar los campos autorizados de un retazo.
- CA-10: Un retazo RECTANGULO, CIRCUNFERENCIA o POLIGONO_CONVEXO válido
  almacena su geometría y área calculada.
- CA-11: Un polígono inválido, cóncavo o con menos de tres vértices es rechazado.
- CA-12: Los códigos de retazo duplicados son rechazados.
- CA-13: Los nombres de tipo de vidrio duplicados son rechazados.
- CA-14: No se puede registrar material asociado a un tipo inexistente o inactivo.
- CA-15: Las operaciones respetan la matriz de permisos vigente.
- CA-16: Los cambios realizados mediante la API persisten en PostgreSQL.
- CA-17: Los endpoints y contratos son visibles en Swagger/OpenAPI.
- CA-18: La implementación no requiere una nueva migración Alembic.
- CA-19: La suite de pruebas existente continúa pasando después de TA-003.

## 9. Impacto técnico

### Módulos

La funcionalidad nueva se implementará principalmente en:

```text
backend/app/modules/inventory/
├── domain/
│   ├── exceptions.py
│   └── geometry.py
├── application/
│   └── service.py
├── infrastructure/
│   └── repository.py
└── presentation/
    ├── dependencies.py
    ├── schemas.py
    └── router.py
```

El módulo respetará la dirección:

`presentation -> application -> domain`

La infraestructura implementará el acceso PostgreSQL requerido por la
capa de aplicación.

Los modelos SQLAlchemy existentes permanecerán en `app/models.py` durante
TA-003. Su traslado a módulos no forma parte de esta tarea.

### API

Endpoints previstos:

```text
POST  /api/inventory/tipos-vidrio
GET   /api/inventory/tipos-vidrio

POST  /api/inventory/planchas
GET   /api/inventory/planchas
PATCH /api/inventory/planchas/{id_plancha}

POST  /api/inventory/retazos
GET   /api/inventory/retazos
PATCH /api/inventory/retazos/{id_retazo}
```

`backend/main.py` registrará el router del módulo de inventario.

### Base de datos / migración

TA-003 consume el modelo v1.1 existente:

- `tipos_vidrio`;
- `planchas`;
- `retazos`.

No se prevén cambios estructurales ni una nueva revisión Alembic.

La implementación debe utilizar las columnas y restricciones existentes
sin incorporar campos adicionales.

### UI

No se modifica React en TA-003.

La integración de los formularios y pantallas del inventario se realizará
en las historias correspondientes posteriores.

## 10. Pruebas previstas

### Unitarias

- Validación de espesores.
- Validación de dimensiones.
- Cálculo de área de rectángulos.
- Cálculo de área de circunferencias.
- Cálculo de área de polígonos convexos.
- Detección de polígonos inválidos o cóncavos.
- Reglas de servicio de tipos, planchas y retazos.
- Traducción de errores de dominio.

### API

- Registro y consulta de tipo de vidrio.
- Alta, listado y edición de plancha.
- Alta, listado y edición de retazo.
- Datos obligatorios ausentes.
- Valores fuera de dominio.
- Duplicados.
- Recursos inexistentes.
- Autenticación y permisos.

### Integración PostgreSQL

- Persistencia real de tipos de vidrio.
- Persistencia real de planchas.
- Persistencia real de retazos y JSONB.
- Relectura de los registros almacenados.
- Rollback ante errores.
- Comprobación de restricciones relevantes de PostgreSQL.

Las pruebas que escriben datos deben ejecutarse únicamente sobre el entorno
PostgreSQL temporal/aislado preparado para tests. No deben utilizar Supabase
como destino de pruebas automatizadas.

## 11. Evidencias requeridas

- Swagger/OpenAPI mostrando los endpoints de inventario.
- Registro válido de tipo de vidrio.
- Registro válido de plancha.
- Consulta posterior de la plancha registrada.
- Casos inválidos de plancha.
- Registro válido de retazo.
- Consulta posterior del retazo registrado.
- Caso inválido de geometría de retazo.
- Resultado de las pruebas automatizadas.
- `git diff --check` sin incidencias.
- Evidencia reproducible en `docs/evidence/sprint-01/TA-003/`.
- Capturas seleccionadas para la Presentación de Avances del Sprint 1.

## Historial de estado

- Draft — 2026-10-04.
- Reviewed — pendiente.
- Implemented — pendiente.
- Verified — pendiente.
