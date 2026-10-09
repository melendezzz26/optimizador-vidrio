# ADR-002 — Operación pre-rasterización

**Proyecto:** NewGlass — Optimizador de corte de vidrio  
**Estado:** Aprobado / Vigente  
**Fecha:** 08/10/2026  
**Alcance:** Sprint 1 — Base funcional pre-rasterización

## 1. Contexto

La convergencia de HU-006 y HU-007 dejó implementado el backend multimaterial, pero la revisión funcional evidenció necesidades adicionales antes de iniciar la rasterización:

- asociación del pedido a un cliente;
- gestión de pedidos basada en listado;
- edición de pedidos solo mientras estén en estado `PENDIENTE`;
- validación obligatoria de stock antes de registrar un pedido;
- consideración de planchas y retazos como fuentes de material compatibles;
- trazabilidad de bajas, merma y retiro de material;
- reutilización del editor poligonal;
- experiencia visual coherente entre Users, Inventory y Orders;
- despliegue funcional previo a la implementación de rasterización.

Estas decisiones afectan datos, interfaz, contratos entre módulos y flujo de trabajo, por lo que se registran como una decisión transversal.

## 2. Decisiones

### 2.1 Cliente separado de Usuario

`CLIENTE` será una entidad independiente de `USUARIO`.

- `USUARIO` representa al personal interno que accede a NewGlass y posee credenciales y rol.
- `CLIENTE` representa a la persona o empresa que solicita el trabajo.
- `PEDIDO` deberá conservar tanto el cliente como el usuario que realizó el registro.

No se crea una superentidad `PERSONA` o `TERCERO` en esta etapa. Si aparecen proveedores u otros actores externos, esta decisión podrá evolucionar posteriormente.

### 2.2 Gestión de pedidos

Orders abrirá inicialmente una pantalla de gestión/listado, no el formulario de creación.

La gestión incluirá:

- búsqueda;
- filtros por cliente, estado y fecha;
- visualización de detalle;
- creación de nuevo pedido;
- edición únicamente para pedidos `PENDIENTE`.

Estados no editables:

- `EN_OPTIMIZACION`;
- `OPTIMIZADO`;
- `CONFIRMADO`;
- `CANCELADO`.

### 2.3 Material y espesor por pieza

Se mantiene la decisión multimaterial ya implementada:

- `id_tipo_vidrio` y `espesor_mm` pertenecen a `PIEZA`;
- un mismo pedido puede contener piezas con distintas combinaciones de material y espesor;
- las formas admitidas son `RECTANGULO`, `CIRCUNFERENCIA` y `POLIGONO_CONVEXO`.

### 2.4 Validación obligatoria de stock antes del registro

Un pedido no podrá registrarse si alguna pieza no posee al menos una fuente de material candidata disponible.

La validación debe considerar, según corresponda:

- tipo de vidrio;
- espesor;
- disponibilidad;
- cantidad disponible en planchas;
- dimensiones;
- geometría del retazo;
- compatibilidad geométrica individual.

La validación pre-raster **no reserva ni consume stock**.

### 2.5 Límite de la validación pre-raster

La validación anterior al registro garantiza que cada pieza tenga al menos una fuente candidata.

No garantiza que todas las piezas puedan colocarse simultáneamente sobre el stock disponible. Esa factibilidad conjunta se evaluará posteriormente mediante rasterización y colocación.

### 2.6 Retazos como fuente de stock

Los retazos registrados y disponibles pueden participar como candidatos de material si cumplen las reglas de compatibilidad de la pieza.

La prioridad definitiva entre planchas y retazos no se resuelve en esta fase; pertenece al flujo posterior de optimización.

### 2.7 Baja lógica y trazabilidad de inventario

Las acciones de eliminación visibles en la interfaz no realizarán `DELETE` físico sobre planchas o retazos.

Una baja deberá conservar:

- material afectado;
- tipo de evento;
- motivo;
- observación, cuando corresponda;
- usuario responsable;
- fecha.

Se distinguirán al menos:

- rotura;
- merma/daño;
- error de registro;
- retiro administrativo;
- consumo por optimización.

El consumo por optimización no se modelará como una baja manual.

### 2.8 Editor poligonal reutilizable

La lógica desarrollada para HU-007 se reutilizará en Orders e Inventory.

En Orders:

- el editor solo aparecerá al seleccionar `POLIGONO_CONVEXO`;
- se abrirá como flujo contextual/modal;
- al agregar o actualizar la pieza, el editor se cerrará.

En Inventory:

- el mismo editor permitirá registrar o editar retazos poligonales;
- no se mantendrá un segundo editor independiente.

### 2.9 Patrón UI común

Users, Inventory y Orders seguirán un patrón común:

1. listado/gestión como vista inicial;
2. búsqueda y filtros;
3. formulario abierto solo mediante una acción `Nuevo` o `Editar`;
4. estados de `loading`, `empty`, `error`, `success`, `warning`, `disabled` y confirmación;
5. componentes reutilizables y accesibles.

### 2.10 Despliegue funcional antes de rasterización

Antes de implementar TA-005/TA-006 deberá existir un despliegue funcional de:

- Authentication;
- Users;
- Inventory;
- Clientes;
- Orders;
- validación pre-raster de stock.

El despliegue deberá superar un smoke/E2E reproducible.

### 2.11 Rasterización y heurísticas

La rasterización se mantiene dentro de Sprint 1.

La interfaz raster deberá cubrir:

- selección de pedido;
- recuperación de piezas;
- ejecución/configuración permitida;
- visualización de geometría original frente a máscara raster;
- estados de error y resultado.

`First Fit`, `Best Fit` y `Worst Fit` permanecen en Sprint 2.

## 3. Alternativas descartadas

- Crear `PERSONA`/`TERCERO` desde ahora: complejidad no justificada.
- Permitir editar pedidos después de `PENDIENTE`: riesgo de invalidar resultados ya generados.
- Eliminar físicamente planchas o retazos: pérdida de trazabilidad.
- Duplicar el editor poligonal entre Orders e Inventory.
- Iniciar rasterización antes de contar con un flujo funcional desplegado.

## 4. Consecuencias

Esta decisión requiere:

- evolución del modelo de datos;
- nuevas migraciones Alembic;
- actualización de Orders, Inventory y Users;
- nuevos contratos de consulta y edición;
- pruebas de integración y E2E;
- despliegue funcional pre-raster;
- actualización de documentación y evidencias.

## 5. Relación con backlog

Esta decisión se implementará principalmente mediante:

- HU-003 — Gestión de usuarios;
- HU-005 — Gestión de retazos;
- HU-006 — Registrar pedido;
- HU-008 — Stock compatible;
- HU-012 — Gestión de clientes;
- HU-013 — Gestión de pedidos;
- HU-014 — Baja y trazabilidad de inventario;
- HU-015 — Interfaz de rasterización;
- TA-033 — Editor poligonal reutilizable;
- TA-034 — Patrón de gestión y feedback compartido;
- TA-035 — Despliegue funcional pre-raster.

## 6. Decisión final

La base funcional pre-rasterización deberá quedar integrada, desplegada y verificada antes de continuar con la rasterización del Sprint 1. Las heurísticas FF/BF/WF continúan reservadas para Sprint 2.
