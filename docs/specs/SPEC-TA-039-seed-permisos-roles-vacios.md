# SPEC-TA-039 — Seed de permisos: preservar roles deliberadamente vacíos

## Información general

| Campo | Valor |
|---|---|
| ID | TA-039 |
| Nombre | Corrección de seed de permisos |
| Tarea | T01 — Preservar roles deliberadamente vacíos |
| Sprint | Sprint 2 |
| Épica | EN-003 / Permisos |
| Prioridad / estimación | Alta / 0,5 SP |
| Estado | **Draft** |
| Responsable | Fabricio Aguilar |
| Reviewer | Por asignar (distinto del autor) |
| Rama | `fix/TA-039-seed-roles-vacios` |
| Base | `origin/integration/sprint-01` en `2fc228d` |
| Fecha | 27/10/2026 |
| Origen | Auditoría pre-Sprint 2, hallazgo **S1-06** (HIGH, defecto confirmado) |
| Dependencia | RBAC actual ([SPEC-S1-RBAC](SPEC-S1-RBAC-roles-permisos-configurables.md)) |

## 1. Objetivo

Que ejecutar el seed (`python seed.py`, o la carga de las pruebas) **nunca devuelva
permisos que un administrador retiró**, incluido el caso en que dejó un rol sin
ningún permiso. Al mismo tiempo, una base nueva debe seguir recibiendo la
asignación inicial de la tabla 4.3 de SPEC-S1-RBAC.

## 2. Situación actual (evidencia)

`backend/app/modules/authentication/infrastructure/permission_seed.py`, línea 41:

```python
to_assign = codes if role_id not in roles_with_permissions else codes & new_codes
```

El seed interpreta "el rol no tiene permisos" como "el rol todavía no se
inicializó". Pero RN-06 de SPEC-S1-RBAC permite que un administrador deje un rol
vacío (`PUT /api/roles/{id}/permissions` con `permisos: []`).

**Reproducción (27/10/2026, sobre `2fc228d`).** Se carga el seed, se dejan sin
permisos los del Almacenero y se vuelve a ejecutar el seed. Resultado: el
Almacenero recupera `inventory.view`, `inventory.manage` y `optimization.view`.
La auditoría reprodujo lo mismo con el Operario (de 0 a 8 permisos). La prueba
existente `test_seed_does_not_restore_a_permission_removed_by_the_administrator`
solo retira **un** permiso, por eso no detecta el caso.

**Riesgo.** Un redespliegue o un bootstrap restablece autorizaciones que el
administrador retiró a propósito; por ejemplo, vuelve a habilitar
`optimization.confirm`, que descuenta stock.

Hay además un detalle relacionado en `backend/seed.py`: `crear_roles()` hace
`commit` de los roles **antes** de llamar a `seed_permissions`. Si el seed falla
entre ambos pasos, quedan roles sin permisos en la base.

## 3. Alcance

### Incluye

- La regla para decidir cuándo un rol recibe su asignación inicial completa.
- `seed.py`: crear los roles que falten y su asignación inicial en **una sola
  transacción**.
- Pruebas de regresión con los cinco casos que pide la auditoría.

### Fuera de alcance

- Cambios de esquema o migraciones. Este diseño no los necesita.
- La API de roles, el frontend y RN-05/RN-06/RN-07 (no cambian).
- El catálogo de permisos y la tabla 4.3 (no cambian).
- Ejecuciones concurrentes del seed (`docs/infrastructure/staging.md` ya indica
  que no está diseñado para eso).

## 4. Alternativas evaluadas

| # | Alternativa | Migración | Cambios fuera del seed | Evaluación |
|---|---|---|---|---|
| A | Marca persistente por rol (por ejemplo, `roles.permisos_inicializados`) | Sí | Modelo, migración, backfill | Explícita, pero obliga a tocar la BD compartida. El backfill tampoco sabe si un rol que hoy está vacío lo está a propósito. |
| B | Inicializar **solo** los roles que el seed crea en esa misma ejecución | No | 5 setups de prueba (`conftest.py`, `e2e_server.py`, `orders_support.py`, `clients_support.py`, `test_repository.py`) | Cumple la recomendación de la auditoría, pero obliga a editar fixtures compartidas de otros módulos. |
| C | **Híbrida (recomendada):** un rol recibe su asignación inicial completa si (a) el seed lo crea en esa ejecución, o (b) la base todavía no tiene **ninguna** fila en `rol_permisos` | No | Ninguno | Distingue sin migración y sin tocar fixtures. Ver §5. |

**Por qué (b) no vuelve a caer en el mismo error.** La condición ya no es que *un
rol* esté vacío, sino que *el sistema completo* nunca se haya inicializado. Una
vez que se inicializa, `rol_permisos` no puede volver a quedar vacía desde la
aplicación, porque RN-05 obliga al Administrador a conservar siempre
`roles.view` y `roles.manage`. Por eso, "`rol_permisos` vacía" solo ocurre en una
base nueva, nunca por una decisión de un administrador.

## 5. Reglas

- **R-01 Base nueva.** Si `rol_permisos` no tiene ninguna fila, cada rol de
  ASIGNACION_INICIAL que exista recibe su asignación inicial completa. Es el
  caso de una base recién migrada y de los setups de prueba.
- **R-02 Rol creado por el seed.** Un rol que `seed.py` crea en esa ejecución
  recibe su asignación inicial completa, en la misma transacción en que se crea.
- **R-03 Rol existente.** Un rol que ya existía en una base inicializada **nunca**
  recibe su asignación inicial completa, tenga cero, algunos o todos sus
  permisos.
- **R-04 Permiso nuevo del catálogo.** Un código que se incorpora al catálogo se
  asigna a los roles que lo tienen en ASIGNACION_INICIAL. Es el comportamiento
  actual y se conserva (ver P-02).
- **R-05 Nunca quita.** El seed nunca elimina permisos ni filas.
- **R-06 Atomicidad.** En `seed.py`, la creación de roles, la carga del catálogo y
  la asignación se confirman juntas. Si algo falla, no se guarda nada y una nueva
  ejecución parte del mismo estado.
- **R-07 Idempotencia.** Ejecutar el seed dos o más veces seguidas no cambia nada.

## 6. Diseño técnico

**Capa:** Infrastructure del módulo `authentication` y el script de bootstrap. No
cambia el Domain ni la Presentation.

1. `permission_seed.py`:
   - nueva firma `seed_permissions(db, created_roles: Collection[str] = ())`;
   - `fresh = not assigned` (no hay ninguna fila en `rol_permisos`);
   - `initialize = fresh or role_name in created_roles`;
   - `to_assign = codes if initialize else codes & new_codes`;
   - actualizar el docstring con R-01 a R-07.
2. `seed.py`:
   - `crear_roles()` junta los nombres que agrega, hace `flush` en lugar de
     `commit` y llama a `seed_permissions(db, created_roles=creados)`;
   - `seed_permissions` hace el único `commit`.
3. Las llamadas existentes de las pruebas no cambian: usan R-01.

## 7. Criterios de aceptación

| CA | Criterio |
|---|---|
| CA-01 | Base nueva (roles sin permisos y `rol_permisos` vacía): se carga la asignación completa de la tabla 4.3. |
| CA-02 | Almacenero u Operario vaciados por el administrador siguen vacíos después de 1 y de 2 ejecuciones del seed. |
| CA-03 | Un rol parcialmente configurado no recupera los permisos retirados. |
| CA-04 | Un permiso nuevo del catálogo se asigna según la tabla 4.3 (R-04). |
| CA-05 | En una base ya inicializada, un rol que faltaba y que `seed.py` crea recibe su asignación inicial; los demás roles no cambian. |
| CA-06 | Si la asignación falla, `seed.py` no deja roles creados sin permisos (R-06). |
| CA-07 | Repetir el seed es idempotente. Las suites existentes (backend, frontend y E2E) pasan sin cambiar sus aserciones; sin migraciones. |

## 8. Pruebas previstas

- **Unitarias** (`tests/unit/authentication/test_permission_seed.py`, SQLite como las existentes):
  - CA-01 a CA-05 y CA-07.
  - Primero se agrega la regresión de CA-02 y se demuestra que **falla** con el código actual.
- **`seed.py`** (`tests/unit/authentication/test_seed_script.py`, nuevo): CA-05 y CA-06, con `SessionLocal` apuntando a SQLite y un fallo inyectado en la asignación.
- **Regresión:** la suite completa del backend con PostgreSQL; frontend y E2E por CI.

## 9. Evidencia requerida

`docs/evidence/sprint-02/TA-039/README.md` con:

- la salida en rojo antes de la corrección y en verde después;
- la suite completa;
- la tabla CA → prueba;
- confirmación de que no hay migraciones ni cambios en la API.

## 10. Decisiones y preguntas abiertas

- **P-01:** aprobar la alternativa C (recomendada) frente a A o B.
- **P-02:** ¿un permiso **nuevo** del catálogo debe asignarse también a un rol que
  el administrador dejó vacío? La propuesta es **sí** (R-04): no es un permiso
  retirado, sino uno que no existía, y así lo hace hoy el seed. Si el equipo
  prefiere lo contrario, solo cambia R-04 y CA-04.
- **P-03:** si en algún entorno el Administrador quedó sin permisos por un fallo
  antiguo entre roles y permisos (y `rol_permisos` no está vacía), el seed no lo
  repara. Ese estado viola RN-05 y se trataría aparte, con autorización del equipo.

## Historial de estado

| Fecha | Versión | Estado | Cambio |
|---|---|---|---|
| 27/10/2026 | 0.1 | Draft | Borrador: análisis, alternativas y reglas propuestas para revisión. |
