# SPEC-HU-012 — Gestión de clientes

## 1. Información general

| Campo | Valor |
|---|---|
| Estado | Reviewed |
| PBI relacionado | HU-012 |
| Reviewer | Fabricio Aguilar Chavez |
| Responsable | Andro Joseph Quispe Cesias |
| Sprint | Sprint 1 |
| Épica | EP-002 — Clientes / Pedidos |
| Dependencia técnica | Evolución BD v1.3 pre-raster |
| Alembic base | `d6e7f8a9b0c1` |

---

## 2. Objetivo

Incorporar la gestión de clientes como una entidad independiente de las cuentas
internas de usuario, permitiendo posteriormente asociar cada pedido con el cliente
que solicita el trabajo.

`CLIENTE` y `USUARIO` representan conceptos distintos:

- `USUARIO` autentica y posee roles/permisos.
- `CLIENTE` identifica a quien solicita el trabajo.
- `CLIENTE` no contiene credenciales ni roles.

---

## 3. Alcance T01 — Modelar y persistir cliente

Crear la entidad persistente `CLIENTE` y establecer la relación entre
`PEDIDO` y `CLIENTE`.

### Entidad CLIENTE

La evolución de base de datos pre-raster establece como base:

- `id_cliente`
- `tipo_documento`
- `numero_documento`
- `nombre_razon_social`
- `telefono`
- `estado`
- `fecha_registro`

### Relación con PEDIDO

Se incorporará:

- `pedidos.id_cliente`
- FK hacia `clientes.id_cliente`

La migración no debe crear clientes ficticios para pedidos históricos.

La obligatoriedad definitiva de `id_cliente` para registros históricos se
resolverá conforme a la decisión de transición definida por el equipo.

---

## 4. Alcance T02 — Consulta y alta de clientes

La API debe permitir:

- registrar un cliente;
- consultar clientes;
- buscar clientes por documento;
- buscar clientes por nombre o razón social;
- evitar duplicidad de documentos cuando corresponda;
- devolver errores comprensibles.

No se reutilizarán endpoints, permisos ni modelos de `USUARIO` para representar
clientes.

---

## 5. Fuera de alcance

Para T01 y T02 no se incluye:

- asociación visual del cliente desde Nuevo Pedido;
- modificación completa del flujo frontend de pedidos;
- listado avanzado de pedidos por cliente;
- edición de pedidos;
- eliminación física de clientes;
- autenticación de clientes.

La asociación funcional del cliente desde Nuevo Pedido corresponde a HU-012 T03.

---

## 6. Reglas de arquitectura

Se mantiene la arquitectura modular:

`Presentation → Application → Domain`

Infrastructure implementa los puertos de persistencia.

El módulo de clientes no debe introducir dependencias desde Domain/Application
hacia FastAPI, SQLAlchemy o Presentation.

Los modelos persistentes reutilizarán la infraestructura SQLAlchemy vigente.

---

## 7. Evolución de base de datos

Toda modificación estructural debe realizarse mediante Alembic.

Base de migración:

`d6e7f8a9b0c1`

La migración T01 deberá:

1. crear `clientes`;
2. definir PK y restricciones acordadas;
3. agregar `pedidos.id_cliente`;
4. crear la FK `pedidos.id_cliente → clientes.id_cliente`;
5. permitir downgrade reproducible;
6. no insertar clientes artificiales;
7. no modificar manualmente el esquema de Supabase.

---

## 8. Decisiones pendientes

Antes de hacer obligatorias ciertas restricciones deberán confirmarse:

- catálogo definitivo de `tipo_documento`;
- obligatoriedad del documento para todos los tipos de cliente;
- política definitiva para pedidos históricos existentes;
- obligatoriedad de teléfono.

Estas decisiones no deben inventarse durante la implementación.

---

## 9. Criterios de aceptación T01

- Existe entidad `CLIENTE` separada de `USUARIO`.
- La estructura puede crearse mediante Alembic.
- `PEDIDO` dispone de referencia FK al cliente.
- La migración upgrade/downgrade funciona sobre PostgreSQL aislado.
- No se crean clientes históricos artificiales.
- ORM y esquema se mantienen alineados.
- Las pruebas de migración y persistencia pasan.

---

## 10. Criterios de aceptación T02

- Se puede registrar un cliente válido mediante API.
- Se pueden consultar clientes.
- Existe búsqueda por documento y/o nombre.
- No se mezclan clientes con usuarios del sistema.
- Los documentos duplicados se rechazan conforme al contrato definido.
- Los errores de validación son controlados.
- Existen pruebas unitarias, API e integración aplicables.

---

## 11. Estrategia de pruebas

### T01

- pruebas de migración Alembic;
- prueba de creación de CLIENTE;
- prueba de FK PEDIDO → CLIENTE;
- prueba de downgrade;
- prueba de restricciones.

### T02

- pruebas de dominio/aplicación;
- pruebas API;
- pruebas de persistencia;
- cliente válido;
- cliente duplicado;
- búsqueda;
- datos inválidos.

Las pruebas de integración deben utilizar PostgreSQL temporal o una BD de pruebas,
nunca datos compartidos de Supabase.

---

## 12. Evidencia

La evidencia se almacenará en:

`docs/evidence/sprint-01/HU-012/`

Se documentarán:

- línea base de BD;
- migración Alembic;
- pruebas T01;
- estructura CLIENTE;
- endpoints FastAPI;
- alta válida;
- rechazo de duplicado;
- búsqueda de clientes;
- pruebas T02.

---

## 13. Definition of Done

- [ ] SPEC revisada.
- [ ] Migración Alembic implementada.
- [ ] ORM actualizado.
- [ ] Pruebas T01 aprobadas.
- [ ] API de clientes implementada.
- [ ] Pruebas T02 aprobadas.
- [ ] Lint y validaciones aplicables aprobadas.
- [ ] Evidencias registradas.
- [ ] Revisión por otro integrante.