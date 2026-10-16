# Auditoría previa — confirmación backend

Base: f4dd5a5fcd574037e055873d75bafcf15cdbf771, core local=remoto, limpio.
Alembic: única s1opt02b4c6d. No se necesita esquema nuevo.

| Aspecto | Modelo / comportamiento real |
|---|---|
| PLANCHA disponible | cantidad INTEGER >=0, estado booleano; dimensiones NUMERIC(10,2), espesor NUMERIC(4,1), pareja material/espesor FK. cantidad0 implica inactiva en el service actual. |
| RETAZO | fila física unitaria; estado booleano activo/inactivo; no campo consumed. Código único VARCHAR40, geometria JSONB, area_mm2 NUMERIC(18,2)>0, tipo/espesor FK, id_ejecucion_origen FK nullable. |
| Movimiento | recurso XOR plancha/retazo; CONSUMO_OPTIMIZACION ya admitido; id_optimizacion e id_usuario FK, fecha TIMESTAMPTZ, motivo no vacío, observacion opcional, cantidad_afectada positiva para escrituras nuevas, retazo cantidad1. NULL solo historia. |
| Constraints movimiento | FK de recurso/actor/corrida; índices recurso/fecha/ID; unicidad parcial SOLO bajas manuales de retazo, NO consumos. La garantía de consumo requiere lock de fila y relectura del ledger bajo ese lock. |
| Tiempo/versiones | fecha_registro de recursos, fecha de movimiento; no updated_at ni version de stock. Configuracion sí versionada; no se inventan versiones de recurso. |
| Geometría | Inventory domain.geometry.calculate_area_mm2 valida rectángulo/círculo/polígono convexo; HALF_UP a0.01, rango NUMERIC18,2, área positiva después de cuantizar. Geometría JSON numérica, no Decimal string dentro del contorno heredado. |
| Mínimos | ancho_min_retazo_mm y alto_min_retazo_mm en configuración efectiva/snapshot. No mínimo independiente de área definido; se conserva ese pendiente y NO se agrega. |

InventoryService/Repository abren su propia transacción: NO se invocan desde la
confirmación. Optimization tendrá adaptador caller-owned en el UoW existente.
Las ediciones/bajas Inventory ya usan locks por recurso. La regla actual que
impide reactivación en Inventory cubre bajas manuales: confirmación verificará
además movimientos CONSUMO_OPTIMIZACION para que una reactivación no permita
consumir dos veces un retazo. No se modifica la funcionalidad general Inventory.

SPEC RN15–18/CA20–26 y PLAN §12/T10–11 fijan: patrón persistido sin recalcular FF,
locks corrida→pedidos ASC→planchas ASC→retazos ASC, commit único y repetición409.
T1 ya define POST /runs/{id}/confirm SIN body, ConfirmResponseV1 y
ALREADY_CONFIRMED/STOCK_CONFLICT/STATE_CONFLICT409, NOT_CONFIRMABLE422.
La corrida conserva COMPLETADA; confirmed derivado de recibo durable de confirmación
en JSONB existente, sin columna nueva. Consumos/recibo/N pedidos comparten commit.

Existe algoritmo residual seguro: domain/metrics.py, stack monótono sobre celdas
interiores libres, margen/separación y check raster repetido. Ya se verificaron
las512 máscaras3×3 y material irregular. Se reproducen/validan SOLO sus propuestas
persistidas, sin ejecutar First Fit ni buscar placements alternativos. Creación
reutiliza el validador y precisión Inventory; geometría no persistible se omite,
registrando razón técnica y ajustando área recuperable/merma a lo materializado.
Eso no introduce un umbral de área configurable. Mínimos ancho/alto son los de
la configuración efectiva congelada para el run.

HU008 observada solo lectura: a0a2dd2. Su validador usa AABB/0–90 y bloqueo Orders;
NO se reutiliza para aprobar geometría ni confirmar. Útil solo como antecedente
material/espesor y catálogo. No merge/cherry-pick.
UI observada 4a3c9c1; no integrada ni editada.
Orders avanzó a5641bc6 (editor UI y serialización existente en repositorio);
observado, no integrado ni editado. Integration sigue c4c5e5c.
