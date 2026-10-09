# Evolución de Base de Datos v1.3 — Operación pre-raster

**Proyecto:** NewGlass — Optimizador de corte de vidrio  
**Estado:** Aprobado / Vigente  
**Fecha:** 08/10/2026  
**Revisión anterior relevante:** `d6e7f8a9b0c1` — HU-006 material y espesor por pieza

## 1. Objetivo

Definir la evolución del modelo relacional necesaria para soportar:

- clientes asociados a pedidos;
- gestión de pedidos pre-raster;
- bajas y mermas de inventario con trazabilidad;
- separación entre baja manual y consumo por optimización;
- continuidad del modelo multimaterial por pieza.

Esta evolución no modifica la decisión de que la simulación/rasterización no consume inventario.

## 2. Principios de diseño

- PostgreSQL/Supabase continúa como base de datos central.
- SQLAlchemy continúa como ORM.
- Alembic es obligatorio para cambios estructurales.
- No se realizarán cambios manuales de esquema en Supabase.
- Se evita duplicidad de datos.
- JSONB solo se utiliza donde la forma de los datos es variable, como geometrías.
- Los registros de inventario no se eliminan físicamente desde la aplicación.
- Los cambios deberán ser reversibles o abortar de manera segura cuando una reversión implique pérdida de información.

## 3. Entidad CLIENTE

### 3.1 Propósito

Representar a la persona o empresa que solicita un trabajo de corte.

`CLIENTE` es independiente de `USUARIO`.

### 3.2 Propuesta de campos

| Campo | Tipo propuesto | Regla |
|---|---|---|
| `id_cliente` | INTEGER | PK, NOT NULL |
| `tipo_documento` | VARCHAR | NOT NULL |
| `numero_documento` | VARCHAR | NOT NULL |
| `nombre_razon_social` | VARCHAR | NOT NULL |
| `telefono` | VARCHAR | NULL |
| `estado` | BOOLEAN | NOT NULL, DEFAULT TRUE |
| `fecha_registro` | TIMESTAMPTZ | NOT NULL |

### 3.3 Reglas

- El documento debe ser único cuando la política del tipo de documento lo requiera.
- Un cliente inactivo conserva sus pedidos históricos.
- `CLIENTE` no contiene credenciales ni roles.
- No se crea una relación de herencia o supertipo con `USUARIO` en esta versión.

## 4. Evolución de PEDIDO

La estructura multimaterial se mantiene:

```text
PEDIDO
├── id_pedido
├── fecha_registro
├── estado
├── id_usuario_registro
├── id_cliente
└── PIEZAS
```

Se agrega:

| Campo | Tipo | Regla |
|---|---|---|
| `id_cliente` | INTEGER | FK CLIENTE, NOT NULL para nuevos pedidos |

El pedido conserva:

- `id_usuario_registro`: quién operó NewGlass;
- `id_cliente`: para quién se realiza el trabajo.

## 5. PIEZA

No se revierte la migración HU-006 multimaterial.

Cada `PIEZA` conserva:

- `id_tipo_vidrio`;
- `espesor_mm`;
- `tipo_forma`;
- `cantidad`;
- `dimensiones`;
- `geometria`;
- `area_mm2`.

Las formas admitidas continúan siendo:

- `RECTANGULO`;
- `CIRCUNFERENCIA`;
- `POLIGONO_CONVEXO`.

## 6. Trazabilidad de inventario

### 6.1 Nueva entidad propuesta

Se propone `MOVIMIENTO_INVENTARIO` como registro de eventos operativos sobre planchas y retazos.

| Campo | Tipo propuesto | Regla |
|---|---|---|
| `id_movimiento` | INTEGER | PK |
| `id_plancha` | INTEGER | FK PLANCHA, NULL |
| `id_retazo` | INTEGER | FK RETAZO, NULL |
| `tipo_evento` | VARCHAR | NOT NULL |
| `motivo` | VARCHAR/TEXT | NOT NULL para bajas manuales |
| `observacion` | TEXT | NULL |
| `id_usuario` | INTEGER | FK USUARIO, NOT NULL |
| `fecha` | TIMESTAMPTZ | NOT NULL |
| `id_optimizacion` | INTEGER | FK OPTIMIZACION, NULL |

### 6.2 Regla de fuente

Un movimiento debe referir exactamente a una fuente:

- una `PLANCHA`, o
- un `RETAZO`.

No ambas simultáneamente.

### 6.3 Tipos de evento iniciales

| Evento | Uso |
|---|---|
| `BAJA_ROTURA` | Material roto físicamente |
| `BAJA_MERMA` | Material que dejó de ser utilizable |
| `BAJA_ERROR_REGISTRO` | Alta inválida o duplicada que debe quedar fuera de operación |
| `BAJA_RETIRO` | Retiro administrativo |
| `CONSUMO_OPTIMIZACION` | Reservado para la confirmación futura de una solución |

Los nombres finales deberán quedar definidos en la SPEC correspondiente antes de implementar la migración.

## 7. Disponibilidad operativa

Una baja manual:

- no elimina el registro;
- lo excluye de las consultas normales de stock disponible;
- conserva el historial del motivo, usuario y fecha.

Los listados podrán permitir filtros de:

- disponibles;
- dados de baja;
- consumidos, cuando corresponda;
- todos.

La representación exacta de disponibilidad en `PLANCHA` y `RETAZO` deberá definirse antes de implementar para no sobrecargar un único booleano `estado` con significados diferentes.

## 8. Consumo por optimización

La simulación y rasterización no modifican inventario.

El consumo se realizará únicamente al confirmar una solución válida y deberá conservar la relación con la ejecución/optimización correspondiente.

Por tanto:

```text
baja manual ≠ consumo por optimización
```

## 9. Migración propuesta

La migración que implemente esta evolución deberá ser descendiente de:

```text
d6e7f8a9b0c1
```

Secuencia esperada:

1. crear `clientes`;
2. definir índices y restricciones de identificación;
3. agregar `pedidos.id_cliente`;
4. aplicar una estrategia explícita para pedidos históricos;
5. establecer `NOT NULL` cuando los datos históricos estén resueltos;
6. crear `movimientos_inventario`;
7. agregar sus FK y restricciones XOR;
8. actualizar modelos ORM;
9. actualizar repositorios/casos de uso;
10. ejecutar pruebas de migración y regresión.

## 10. Pedidos históricos

No se inventarán clientes automáticamente durante la migración.

Antes de aplicar la migración al entorno compartido se deberá decidir explícitamente cómo tratar cualquier pedido histórico existente sin cliente.

Alternativas válidas a revisar:

- asociar manualmente un cliente real;
- utilizar un registro técnico de migración aprobado por el equipo;
- abortar la migración hasta resolver los datos.

La decisión deberá quedar documentada antes de ejecutar la migración en Supabase.

## 11. Pruebas requeridas

La evolución deberá cubrir al menos:

- upgrade desde `d6e7f8a9b0c1`;
- downgrade seguro;
- FK `PEDIDO → CLIENTE`;
- documento de cliente duplicado;
- cliente inactivo con historial conservado;
- baja de plancha;
- baja de retazo;
- motivo obligatorio;
- XOR plancha/retazo;
- registro no eliminado físicamente;
- consultas de stock que excluyan bajas;
- rollback ante error;
- regresión completa del backend.

## 12. Impacto sobre módulos

### Orders

- cliente obligatorio;
- búsqueda/filtros por cliente;
- edición de pedido `PENDIENTE`;
- validación de stock antes del registro.

### Inventory

- baja lógica;
- historial;
- retazo poligonal;
- stock compatible.

### Optimization

No se modifica todavía el inventario durante simulación/rasterización.

### Results

La confirmación futura utilizará trazabilidad de consumo.

## 13. Decisión final

La evolución v1.3 extiende el modelo sin reemplazar el contrato multimaterial HU-006. CLIENTE queda separado de USUARIO y la trazabilidad de inventario se modela de forma explícita para preservar historial y permitir una futura integración segura con la confirmación de optimización.
