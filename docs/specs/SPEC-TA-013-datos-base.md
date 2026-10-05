# SPEC-TA-013 — Datos base de tipos y espesores de vidrio

## 1. Identificación

- **PBI:** TA-013
- **Título:** Datos base
- **Tarea:** T01 — Preparar catálogos de tipo y espesor
- **Épica:** EP-002 — Gestión de inventario de vidrio
- **Sprint:** Sprint 1
- **Prioridad:** Alta
- **Dependencias:** TA-002, SP-005
- **Estado inicial:** Doing
- **Responsable:** Fabricio M.
- **Esfuerzo estimado:** 0.5 SP

---

## 2. Objetivo

Implementar un catálogo central y persistente de tipos de vidrio y espesores admitidos que pueda ser reutilizado por los módulos de Inventario y Pedidos.

El catálogo debe:

- evitar registros duplicados;
- poder consultarse mediante la API;
- representar qué espesores son válidos para cada tipo de vidrio;
- impedir combinaciones tipo–espesor no admitidas;
- ser la única fuente de verdad para Inventario y Pedidos;
- mantener integridad tanto en la capa de aplicación como en PostgreSQL.

---

## 3. Antecedentes

La versión 1.1 del diseño de base de datos estableció inicialmente los espesores:

- 3 mm
- 4 mm
- 5.5 mm
- 6 mm
- 8 mm

Estos espesores fueron implementados como restricciones globales para `PLANCHA`, `RETAZO` y `PEDIDO`.

Posteriormente, el SP-005 “Comparación y selección de tipos y espesores de vidrio” determinó que el catálogo debe depender del tipo de vidrio.

Por ello, TA-013 introduce una evolución del modelo de datos. Esta decisión debe documentarse como versión 1.2 del diseño de base de datos y aplicarse mediante una nueva migración Alembic.

---

## 4. Catálogo aprobado por SP-005

| Tipo de vidrio | Espesores admitidos |
|---|---|
| Incoloro | 3, 4, 5.5, 6, 8, 10, 12 mm |
| Bronce | 4, 5.5, 6, 8, 10 mm |
| Gris | 4, 5.5, 6, 8, 10 mm |
| Catedral | 3, 3.5, 5 mm |
| Reflejante | 4, 5.5, 6, 8 mm |
| Espejo | 2, 3, 4, 6 mm |

Los siguientes materiales no forman parte del catálogo inicial:

- templado;
- laminado;
- doble acristalamiento.

---

## 5. Cambio de modelo de datos

### 5.1 Nueva entidad: TIPO_VIDRIO_ESPESOR

Se incorporará una relación entre los tipos de vidrio soportados y sus espesores permitidos.

Nombre físico propuesto:

`tipos_vidrio_espesores`

Campos:

| Campo | Tipo | Restricción |
|---|---|---|
| `id_tipo_vidrio` | INTEGER | NOT NULL, FK a `tipos_vidrio.id_tipo_vidrio` |
| `espesor_mm` | NUMERIC(4,1) | NOT NULL, CHECK > 0 |

Clave primaria compuesta:

`(id_tipo_vidrio, espesor_mm)`

Esta clave garantiza que una misma combinación tipo–espesor no pueda registrarse más de una vez.

No se crea una entidad independiente `ESPESOR`, ya que el dominio relevante para NewGlass es la combinación entre tipo de vidrio y espesor permitido.

---

## 6. Integridad referencial

Las tablas:

- `planchas`;
- `retazos`;
- `pedidos`;

mantendrán sus columnas existentes:

- `id_tipo_vidrio`;
- `espesor_mm`.

Se eliminarán los `CHECK` globales:

`espesor_mm IN (3, 4, 5.5, 6, 8)`

y la validez se comprobará mediante la combinación:

`(id_tipo_vidrio, espesor_mm)`

Cada una de las tres tablas deberá referenciar una combinación existente en `tipos_vidrio_espesores`.

Restricciones propuestas:

- `fk_planchas_tipo_espesor`
- `fk_retazos_tipo_espesor`
- `fk_pedidos_tipo_espesor`

Esto garantiza que PostgreSQL rechace una combinación no incluida en el catálogo aunque la solicitud no provenga de la interfaz web.

Ejemplo válido:

`Espejo + 4 mm`

Ejemplo inválido:

`Espejo + 10 mm`

Ejemplo válido:

`Incoloro + 10 mm`

---

## 7. Migración Alembic

La revisión manual `1c8754481a08`, posterior a `b4d5e6f7a8c9`, implementa este cambio. No se reemplazan ni modifican las migraciones históricas.

La migración deberá:

1. crear `tipos_vidrio_espesores`;
2. registrar los seis tipos definidos por SP-005 sin generar duplicados;
3. registrar todas las combinaciones tipo–espesor aprobadas;
4. comprobar los datos existentes de `planchas`, `retazos` y `pedidos`;
5. abortar con un mensaje explícito si existen combinaciones incompatibles con el nuevo catálogo;
6. no eliminar ni modificar silenciosamente datos incompatibles;
7. eliminar los `CHECK` globales antiguos de espesor;
8. crear las restricciones de integridad tipo–espesor;
9. permitir que la carga del catálogo sea reproducible sin producir duplicados.

No deben modificarse migraciones Alembic históricas ya aplicadas.

---

## 8. Carga idempotente

La carga de datos base debe ser idempotente.

Ejecutar nuevamente la lógica de inicialización no debe producir:

- tipos de vidrio duplicados;
- combinaciones tipo–espesor duplicadas.

`tipos_vidrio.nombre` continuará siendo único.

`tipos_vidrio_espesores` tendrá unicidad garantizada mediante su clave primaria compuesta.

Si un nombre ya existe, la carga preserva su ID, descripción (incluso NULL) y estado, sin reactivar tipos inactivos. La coincidencia utiliza la unicidad existente de `nombre`; no renombra ni fusiona variantes del nombre.

---

## 9. Capa de aplicación

La validación global actual de espesor será sustituida por una validación de compatibilidad tipo–espesor.

Conceptualmente:

`validate_tipo_espesor(id_tipo_vidrio, espesor_mm)`

La operación deberá comprobar:

1. que el tipo de vidrio exista;
2. que esté habilitado cuando corresponda;
3. que el espesor sea positivo;
4. que la combinación `(id_tipo_vidrio, espesor_mm)` exista en el catálogo.

Esta regla debe poder reutilizarse posteriormente desde el módulo de Pedidos.

El contrato público es `GlassCatalog.get_tipo_vidrio`, que devuelve `TipoVidrioData` con `espesores_mm` persistidos. La función `validate_tipo_espesor(catalog, id_tipo_vidrio, espesor_mm, *, require_active=True)` reside en Application y no depende de SQLAlchemy ni FastAPI. El consumidor controla la transacción; Pedidos podrá utilizar este puerto sin duplicar reglas ni implementar ahora su flujo funcional.

Crear material o cambiar su combinación exige un tipo activo. Un PATCH calcula la pareja efectiva: tipo nuevo y espesor actual, espesor nuevo y tipo actual, o ambos nuevos. Si la pareja no cambia, se conserva la posibilidad de actualizar otros atributos de material cuyo tipo haya sido desactivado.

Los tipos creados manualmente sin combinaciones registradas devuelven `espesores_mm: []`; no reciben espesores implícitos y no permiten crear material hasta disponer de una combinación persistida.

La base de datos seguirá siendo la última barrera de integridad mediante las restricciones correspondientes.

---

## 10. API de catálogo

El backend deberá permitir consultar el catálogo mediante API.

La respuesta deberá permitir conocer los tipos de vidrio y sus espesores asociados.

Formato conceptual:

```json
[
  {
    "id_tipo_vidrio": 1,
    "nombre": "Incoloro",
    "descripcion": "...",
    "estado": true,
    "espesores_mm": [3, 4, 5.5, 6, 8, 10, 12]
  },
  {
    "id_tipo_vidrio": 2,
    "nombre": "Espejo",
    "descripcion": "...",
    "estado": true,
    "espesores_mm": [2, 3, 4, 6]
  }
]
```

El contrato amplía `GET /api/inventory/tipos-vidrio`. Conserva los campos existentes e incorpora `espesores_mm` como números JSON en orden ascendente, consultados desde PostgreSQL. Los IDs no son constantes del catálogo. Se conservan los tipos inactivos en la consulta, identificados por `estado: false`.

El frontend no mantendrá una lista independiente de tipos o espesores.

---

## 11. Inventario

Al crear o modificar una plancha o retazo:

- `id_tipo_vidrio` deberá corresponder a un tipo existente;
- `espesor_mm` deberá corresponder a un espesor admitido para ese tipo;
- una combinación inválida será rechazada antes de persistirse;
- PostgreSQL deberá impedir igualmente una combinación inválida.

Ejemplo:

`POST plancha: Espejo + 4 mm` → permitido.

`POST plancha: Espejo + 8 mm` → rechazado.

El mismo comportamiento aplica para retazos.

---

## 12. Pedidos

TA-013 no implementará el flujo funcional completo de Pedidos.

Sin embargo, dejará disponible el mismo catálogo y mecanismo de validación para que el módulo de Pedidos pueda reutilizarlo posteriormente.

No se deberá crear una segunda lista hardcodeada de espesores dentro del módulo de Pedidos.

---

## 13. Fuera de alcance

TA-013 no incluye:

- interfaces React;
- formularios de planchas;
- formularios de retazos;
- integración React → FastAPI;
- optimización FF/BF/WF;
- actualización de stock por confirmación;
- incorporación de templado;
- incorporación de laminado;
- incorporación de doble acristalamiento;
- administración dinámica de nuevos espesores desde el frontend.

La integración frontend corresponde a HU-004, HU-005 y TA-011.

---

## 14. Pruebas mínimas

### Catálogo

- los seis tipos requeridos existen;
- no existen tipos duplicados;
- cada tipo devuelve exactamente sus espesores configurados;
- una segunda inicialización no genera duplicados.

### Validación

- Incoloro + 12 mm → válido;
- Incoloro + 2 mm → inválido;
- Espejo + 2 mm → válido;
- Espejo + 8 mm → inválido;
- Catedral + 3.5 mm → válido;
- Catedral + 4 mm → inválido.

### Inventario

- crear plancha con combinación válida;
- rechazar plancha con combinación inválida;
- crear retazo con combinación válida;
- rechazar retazo con combinación inválida;
- modificar tipo manteniendo espesor compatible;
- rechazar modificación que genere incompatibilidad;
- modificar espesor manteniendo tipo compatible;
- rechazar modificación que genere incompatibilidad.

### Base de datos

- PostgreSQL rechaza directamente una combinación no registrada;
- las restricciones compuestas existen;
- los antiguos `CHECK IN (3, 4, 5.5, 6, 8)` dejan de ser la regla de dominio.

### API

- la consulta del catálogo devuelve HTTP 200;
- cada tipo incluye sus espesores admitidos;
- los errores de combinación inválida producen una respuesta de validación controlada.

### Regresión

Al finalizar:

`pytest`

debe completar sin introducir regresiones en las pruebas existentes.

---

## 15. Criterios de aceptación de TA-013

TA-013 se considera terminado cuando:

1. los seis tipos definidos por SP-005 están disponibles como datos base;
2. cada tipo tiene registrados sus espesores permitidos;
3. no pueden existir combinaciones duplicadas;
4. el catálogo puede consultarse mediante API;
5. Inventario utiliza el catálogo para validar planchas y retazos;
6. la misma estructura queda disponible para Pedidos;
7. PostgreSQL impide combinaciones tipo–espesor no permitidas;
8. los datos existentes incompatibles no son modificados automáticamente;
9. la migración correspondiente está versionada mediante Alembic;
10. todas las pruebas nuevas y preexistentes finalizan correctamente;
11. existe evidencia técnica del catálogo, migración, API y pruebas.

---

## 16. Evidencias requeridas

Guardar bajo:

`docs/evidence/sprint-01/TA-013/`

Como mínimo:

- `catalogo-tipos-espesores.md`
- `migracion-catalogo.md`
- `api-catalogo.md`
- `pruebas-ta013.md`

Las evidencias deben demostrar:

- catálogo cargado;
- ausencia de duplicados;
- consulta mediante API;
- combinación válida;
- combinación inválida;
- protección de integridad desde PostgreSQL;
- resultado final del conjunto de pruebas.

---

## 17. Trazabilidad

`SP-005 → TA-013 → HU-004 / HU-005 → TA-011`

SP-005 determina qué tipos y espesores utilizar.

TA-013 materializa esa decisión como catálogo compartido.

HU-004 y HU-005 utilizan dicho catálogo en las funciones de inventario.

TA-011 integra posteriormente las interfaces React con la API y PostgreSQL.

La evolución documental del modelo se detalla en [Evolución v1.2 por TA-013](../database/evolucion-v1-2-ta013.md). La documentación v1.1 y los documentos DOCX se conservan como línea base histórica.
