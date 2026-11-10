# Análisis Funcional, Técnico y Comercial — HU-VENT-001: Venta por Plancha Completa

## 1. Información General y Alcance

| Campo | Valor |
|---|---|
| **Historia de Usuario** | `HU-VENT-001 — Análisis de venta por plancha completa` |
| **Objetivo** | Evaluar la factibilidad comercial, operativa y de arquitectura para una eventual **Versión 2 (v2)** de NewGlass |
| **Restricción de Alcance** | **Solo análisis.** No se implementa ningún módulo de ventas, endpoints ni cambios de base de datos en esta versión |
| **Responsable** | Luis Anthony Ibañez Herrera |
| **Rama** | `docs/HU-VENT-001-analisis-plancha-completa` |
| **Base Auditada** | `integration-02` (`backend/app/models.py`, `backend/app/core/permissions.py`, flujos Orders/Inventory/Optimization y stock real en Supabase Cloud) |

---

## 2. Diferencias Operativas y Comerciales: Piezas Cortadas vs. Plancha Completa

El análisis sobre el negocio vidriero y el modelo actual de NewGlass demuestra que ambas modalidades responden a **lógicas operativas, económicas y físicas completamente distintas**:

| Dimensión | Modalidad Actual: Venta de Piezas Cortadas (A Medida) | Modalidad Evaluada (v2): Venta por Plancha Completa |
|---|---|---|
| **Unidad comercial** | Pieza geométrica específica (`RECTANGULO`, `CIRCUNFERENCIA`, `POLIGONO_CONVEXO`) en mm con cantidad arbitraria. | Lámina comercial estándar íntegra (`id_plancha`), p. ej. `3210 × 2250 mm` o `2240 × 3300 mm`. |
| **Especificación del material** | El cliente solicita `(tipo_vidrio, espesor_mm)`; el motor de optimización elige de qué plancha o retazo obtener la pieza. | El cliente **debe elegir el formato comercial exacto** (`ancho × alto`). Un mismo vidrio coexiste en distintos formatos (ej. en Supabase actual: Espejo 6.0 mm existe en Lote `#1` `3210×2250` y Lote `#3` `2240×3300`). |
| **Proceso en taller** | Complejo: registro de geometría → validación de convexidad → optimización 2D → rasterizado/corte con cuchilla → quiebre y pulido de aristas. | Directo: validación de stock disponible → reserva física → despacho con ventosas/caballetes en almacén **sin pasar por mesa de corte**. |
| **Uso del optimizador** | **Obligatorio** (motores `FF`, `BF`, `WF`, `HF`, `M5`, `M6-BS`). | **Innecesario e incompatible** (si se simulara como pieza de tamaño completo, el margen perimetral vigente `margin_mm > 0` la rechazaría con `MARGEN_INSUFICIENTE`). |
| **Tiempo de ciclo** | Medio / Alto (depende del cómputo de optimización + mano de obra de corte en planta). | Muy bajo (despacho inmediato sujeto únicamente a carga logística). |
| **Estructura de precio** | Área útil cortada + recargo por complejidad geométrica + fracción de merma + mano de obra de corte. | Precio unitario cerrado por lámina comercial (típicamente tarifa mayorista o por $m^2$ bruto sin recargo de corte). |
| **Riesgos físicos** | Altos riesgos de corte (superposición, astillamiento por kerf, estallido en ángulos cóncavos, ver `TA-QA-009`). | Sin riesgo de corte mecánico; riesgo puramente logístico de manipulación y estiba de gran formato. |

---

## 3. Análisis de Propiedad y Gestión de Sobrantes (`Retazos` y `Merma`)

Uno de los puntos más sensibles en el negocio del vidrio es definir **quién asume la pérdida de área útil y quién capitaliza los excedentes**:

### 3.1 En Venta de Piezas Cortadas (Modelo Vigente)
- **Propiedad del sobrante:** **NewGlass (el taller)** conserva físicamente todo el material remanente tras extraer las piezas del cliente.
- **Comportamiento en el sistema:** Al confirmar un corte (`ConfirmRun.execute()`), el dominio ejecuta `calculate_metrics()` contrastando las zonas libres del mapa raster contra `Configuracion.ancho_min_retazo_mm` y `alto_min_retazo_mm`:
  1. Los sobrantes aprovechables se insertan automáticamente en la tabla `retazos` (con `id_ejecucion_origen` y código único) como **activo recuperable del taller**. *(En la base real actual en Supabase existen **6 retazos activos que totalizan $4.36\text{ m}^2$** reutilizables).*
  2. Las tiras frágiles o residuos menores al umbral mínimo se contabilizan como `merma_mm2` y son desechados por el taller (internalizados en el precio del servicio de corte).

### 3.2 En Venta por Plancha Completa (Modalidad v2)
- **Propiedad del sobrante:** **El cliente** adquiere y se lleva el **100% de la superficie bruta** de la lámina intacta. Cualquier corte o desperdicio que el cliente genere posteriormente en su obra o taller es asumido y conservado exclusivamente por él.
- **Comportamiento en el sistema:** Para NewGlass **no existe ejecución de optimización**, por lo tanto:
  - **Retazos generados en BD:** **0** (nunca se crea un registro en `retazos` porque no hay `id_ejecucion_origen`).
  - **Merma operativa en taller:** **0 mm²**.
  - **Impacto contable/operativo:** El margen unitario por $m^2$ suele ser menor que en corte a medida, pero se compensa con rotación rápida de inventario y cero generación de desperdicio ni horas-hombre de corte.

> **Caso borde detectado (Maquila con devolución de sobrantes):** Si un cliente comprara una plancha completa pero exigiera que NewGlass realice los cortes y *además* le entregue todos los retazos resultantes, no debe tratarse como venta por plancha completa sino como un pedido cortado con cláusula especial de retiro total de sobrantes (fuera del alcance estándar de v2).

---

## 4. Impacto Técnico Requerido por Módulo (Auditoría sobre Arquitectura Real)

La inspección directa del modelo relacional ([`backend/app/models.py`](file:///C:/Users/liban/Desktop/rework-vidrio/optimizador-vidrio/backend/app/models.py)), las reglas de dominio y los permisos RBAC ([`backend/app/core/permissions.py`](file:///C:/Users/liban/Desktop/rework-vidrio/optimizador-vidrio/backend/app/core/permissions.py)) revela que **la v1 está diseñada 100% alrededor del flujo de corte** y requeriría las siguientes adaptaciones estructurales para soportar venta de plancha completa en v2:

### 4.1 Módulo de Pedidos (`pedidos`, `piezas` y UI de Registro)
- **Separación de modalidad en `Pedido`:** Hoy la tabla `pedidos` no tiene columna `tipo_pedido` y su restricción SQL `ck_pedidos_estado` solo admite `('PENDIENTE', 'EN_OPTIMIZACION', 'OPTIMIZADO', 'CONFIRMADO', 'CANCELADO')`. Se requeriría agregar `tipo_pedido` (`'CORTE_A_MEDIDA'` vs. `'PLANCHA_COMPLETA'`) y nuevos estados logísticos (`'RESERVADO'`, `'DESPACHADO'` / `'ENTREGADO'`).
- **Desacople de la tabla `piezas`:** Actualmente `Pieza` exige obligatoriamente `tipo_forma IN ('RECTANGULO', 'CIRCUNFERENCIA', 'POLIGONO_CONVEXO')`, `geometria`, `area_mm2` y referencia solo `(id_tipo_vidrio, espesor_mm)`. Para vender plancha completa no hay que definir figuras geométricas; se necesita una nueva tabla o detalle **`detalle_pedido_plancha`** con llave foránea directa a **`planchas.id_plancha`** y `cantidad` para distinguir formatos exactos (ej. Lote `#1` `3210×2250` vs. Lote `#3` `2240×3300`).
- **Interfaz Frontend (`FormularioPedido.jsx`):** Incorporar un selector de modalidad que oculte las dimensiones geométricas/editor de polígonos cuando se seleccione *"Plancha completa"* y muestre en su lugar un selector de lotes disponibles en almacén con validación en vivo de stock suficiente.

### 4.2 Módulo de Inventario (`planchas`, `movimientos_inventario`, Trazabilidad)
- **Extensión de eventos en `MovimientoInventario`:** Actualmente el `CheckConstraint` `ck_movimientos_inventario_tipo_evento` restringe los eventos exclusivamente a `'BAJA_ROTURA', 'BAJA_MERMA', 'BAJA_ERROR_REGISTRO', 'BAJA_RETIRO', 'CONSUMO_OPTIMIZACION'`.
  - *Riesgo de usar parche actual:* Registrar una venta usando `BAJA_RETIRO` (mediante `WriteoffDialog`) distorsionaría las auditorías de merma y pérdidas de almacén.
  - *Cambio requerido:* Migración Alembic ampliando los eventos permitidos con **`'VENTA_PLANCHA_COMPLETA'`** (desvinculado de `id_optimizacion` y vinculado a `id_pedido`).
- **Mecanismo de Reserva y Concurrencia (`SELECT FOR UPDATE`):** A diferencia del corte a medida (que solo descuenta stock al final cuando el operario confirma en `ConfirmRun`), la venta de una plancha entera exige **reservar o descontar la unidad desde el registro/aprobación del pedido** (`cantidad_disponible` vs `cantidad_reservada`). Sin esto, el optimizador podría asignar la misma lámina a otro pedido concurrente produciendo sobreventa.
- **Atributos económicos (Inexistentes en v1):** Ni `Plancha` ni `TipoVidrio` poseen columnas de `costo_compra`, `precio_venta_unit`, `moneda` ni descuentos por volumen. Si la v2 busca un módulo de ventas real (facturación/cotización), exigirá modelar listas de precios y reglas fiscales.

### 4.3 Módulo de Optimización (`pendingOrdersSource.js`, `stock_adapter.py`, `Optimizacion`)
- **Exclusión obligatoria de cola de pedidos pendientes:** Actualmente [`pendingOrdersSource.js`](file:///C:/Users/liban/Desktop/rework-vidrio/optimizador-vidrio/frontend/src/features/optimization/pendingOrdersSource.js) consulta automáticamente todos los pedidos con `estado='PENDIENTE'` cada 15 segundos para mostrarlos en el área de optimización. Tanto el endpoint backend `/api/orders` como el adaptador de optimización deben **filtrar y excluir** cualquier pedido de modalidad `PLANCHA_COMPLETA` para evitar que entre a cálculo innecesariamente o sufra rechazo geométrico por márgenes.
- **Lectura segura de stock libre:** `InventoryStockAdapter` deberá consultar únicamente stock no comprometido en ventas directas pendientes de despacho.

### 4.4 Seguridad y Control de Acceso (RBAC)
- En [`permissions.py`](file:///C:/Users/liban/Desktop/rework-vidrio/optimizador-vidrio/backend/app/core/permissions.py) existen 13 códigos agrupados en `users`, `roles`, `inventory`, `orders` y `optimization`. Para v2 se recomienda introducir permisos específicos (ej. `sales.view`, `sales.create` o `orders.direct_sheet`) y evaluar un nuevo rol comercial (`Vendedor` / `Mostrador`) que pueda registrar ventas de plancha sin otorgarle permiso `inventory.manage` (que hoy permite dar de baja o alterar stock arbitrariamente).

---

## 5. Evaluación de Alternativas y Recomendación Estratégica para el Equipo

| Alternativa | Descripción | Pros | Contras / Riesgos |
|---|---|---|---|
| **A. Incorporar ahora en v1** | Modificar base de datos, pedidos, inventario y optimización antes de cerrar la versión actual. | Cobertura inmediata de despacho directo en un solo sistema. | **Alto riesgo de regresión.** Obliga a migrar restricciones SQL críticas (`pedidos`, `movimientos_inventario`), mezcla responsabilidades de optimización industrial con ventas/facturación aún no definidas y retrasa el despliegue estable de v1. |
| **B. Descartar definitivamente** | Limitar NewGlass de por vida solo a piezas cortadas. | Cero esfuerzo adicional de desarrollo. | Pérdida de oportunidad comercial: en vidrierías reales la venta por plancha cerrada a contratistas y sub-distribuidores mueve gran volumen de inventario con cero merma. |
| **C. Postergar para v2 desacoplada** *(Recomendada)* | Cerrar v1 consolidando corte a medida, e iniciar la v2 con diseño propio de Despacho Directo / Ventas. | Protege la estabilidad de v1; permite definir precios/facturación y reserva de stock de forma limpia; evita parches peligrosos como abusar de `BAJA_RETIRO`. | Requiere que temporalmente las salidas de planchas completas sigan gestionándose en contabilidad/caja externa o registro controlado de almacén hasta v2. |

### Veredicto Oficial Recomendado: **POSTERGAR PARA VERSIÓN 2 (v2)**

Se recomienda formalmente al equipo **POSTERGAR** la implementación de la venta por plancha completa para el ciclo de **Versión 2**, descartando cualquier adaptación improvisada sobre los módulos actuales de v1.

#### Condiciones Habilitantes ("Checklist Go/No-Go") antes de implementar en v2:
1. **Definición de alcance financiero:** Confirmar si v2 gestionará solo despacho físico de láminas (control de stock) o un módulo comercial completo (cotizador, precios por formato, comprobantes y descuentos).
2. **Reserva atómica de stock:** Diseñar `cantidad_reservada` en `planchas` y bloqueo transaccional entre ventas directas y confirmaciones del optimizador.
3. **Aislamiento de flujo:** Garantizar por diseño en base de datos y API que una venta de plancha completa **nunca** entre al módulo de optimización de corte ni genere registros ficticios en `retazos`.
