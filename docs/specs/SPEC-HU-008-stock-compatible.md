# SPEC-HU-008 - Stock compatible

| Campo | Valor |
|---|---|
| Estado | Implemented - revisión independiente pendiente; no Verified |
| PBI relacionado | HU-008 - Stock compatible |
| Rama | feature/HU-008-stock-compatible |
| Spike geométrico | [SP-005 - Compatibilidad geométrica pre-raster](../spikes/SP-005-compatibilidad-geometrica-pre-raster.md) |
| Dependencia de disponibilidad | HU-014 - Baja y trazabilidad de inventario |

Cinco commits previos de Luis Anthony Ibañez Herrera se preservaron sin
reescritura. Los commits posteriores y los resultados reproducibles se registran
en docs/evidence/sprint-01/HU-008/.

## 1. Objetivo y alcance

Antes de persistir un pedido nuevo, comprobar que cada pieza solicitada tenga al
menos una plancha o retazo candidato individual de su tipo de vidrio y espesor.
Si una o más piezas no tienen candidato, el POST se rechaza completo, se
identifica cada pieza y no se persiste pedido ni piezas.

La validación es pre-raster, de solo lectura y no reserva ni consume inventario.
No garantiza factibilidad conjunta de las piezas ni cambia el comportamiento de
PUT /api/orders para editar pedidos existentes.

Incluye las geometrías actuales de Orders: RECTANGULO, CIRCUNFERENCIA y
POLIGONO_CONVEXO. La regla geométrica se define en SP-005.

Fuera de alcance: rasterización, colocación conjunta, heurísticas FF/BF/WF,
elección del mejor candidato, reserva, confirmación o consumo.

## 2. Regla de candidato compatible

Una pieza tiene candidato si al menos un recurso satisface tipo de vidrio,
espesor, disponibilidad y cabida individual por caja envolvente. La pieza se
comprueba una vez por línea; el campo cantidad no multiplica recursos ni inicia
una reserva conjunta.

Plancha: mismo id_tipo_vidrio y espesor_mm, estado = true, cantidad > 0 y
dimensiones suficientes en orientación normal o girada 90 grados.

Retazo: mismo id_tipo_vidrio y espesor_mm, estado = true y caja envolvente
derivada de la geometría suficiente en orientación normal o girada 90 grados.
No hay cantidad de retazo.

El ajuste es inclusivo en los bordes. Para cajas (w, h) de pieza y (W, H) de
stock:

    (w <= W AND h <= H) OR (w <= H AND h <= W)

La caja de una circunferencia usa su diámetro en ambos ejes. La caja de un
polígono usa max - min de cada coordenada. Para geometrías no rectangulares de
retazo, comparar envolventes es un filtro pre-raster; no certifica contención
exacta en la silueta ni una colocación final. La limitación está documentada
en SP-005.

### Disponibilidad HU-014

HU-014 registra la baja y fija estado=false atómicamente; también impide
reactivar un recurso con una baja manual. Por eso Inventory excluye material
inactivo y planchas con cantidad cero usando el estado actual del recurso, sin
consultar de nuevo la tabla de movimientos. Esta decisión depende del invariante
transaccional de HU-014; una escritura externa que deje movimiento de baja con
estado=true quedaría fuera del contrato actual.

## 3. Flujo de creación

1. Orders valida el cliente, catálogo, cantidades y geometrías con las reglas
   actuales.
2. El puerto de Orders StockCandidateChecker solicita los índices de piezas sin
   candidato.
3. El adaptador de infraestructura delega a Inventory.StockCompatibilityService
   y a InventoryRepository.get_compatible_stock; no hace una llamada HTTP interna.
4. Inventory agrupa lecturas por pareja de tipo/espesor dentro de
   read_transaction(), calcula cajas y evalúa cada pieza sin considerar su
   cantidad como reserva.
5. Si falta un candidato, Orders lanza NoCompatibleStockException. El endpoint
   devuelve 422 antes de invocar la persistencia de Orders.
6. Si todas las piezas tienen candidato, el flujo existente persiste pedido y
   piezas en una transacción.

El validador de dominio no importa FastAPI ni SQLAlchemy. Application depende del
puerto; el adaptador de Orders Infrastructure conecta ese puerto con el servicio
y repositorio de Inventory. La lectura finaliza con rollback y no escribe
inventario. No se añaden tablas ni migraciones.

## 4. Contrato de error API

El POST conserva el 422 usado por Orders para reglas de negocio. Para falta de
stock devuelve un objeto detail estructurado:

    {
      "detail": {
        "code": "NO_COMPATIBLE_STOCK",
        "message": "Una o más piezas no tienen material compatible disponible.",
        "pieces": [
          {
            "index": 2,
            "reason": "No hay plancha ni retazo disponible del tipo y espesor seleccionados con dimensiones suficientes para esta pieza."
          }
        ]
      }
    }

index es base 1 y corresponde al orden de piezas del POST. No se exponen SQL,
traceback ni datos innecesarios. Los demás errores de 422 mantienen el contrato
vigente.

## 5. Comportamiento frontend

El formulario canónico FormularioPedido conserva cliente y piezas al recibir
NO_COMPATIBLE_STOCK, marca las piezas indicadas y muestra su motivo junto a la
pieza. Si el usuario edita una pieza marcada, retira el mensaje de esa pieza para
que pueda corregir y volver a enviar. El backend es la fuente de verdad y no se
replica una consulta de stock en React.

El modo de edición no usa el chequeo de stock de creación. No se amplió
HU-008 al PUT de pedidos históricos.

## 6. Tareas y criterios de aceptación

| Tarea | Resultado implementado |
|---|---|
| T01 - filtrar por tipo y espesor | get_compatible_stock aplica parejas exactas y disponibilidad; pruebas PostgreSQL cubren tipo, espesor, estado y cantidad. |
| SP-005 T01 - formalizar candidato | Regla de caja envolvente, rotación, disponibilidad, límite individual/conjunto y colisión histórica documentados en el spike geométrico. |
| T02 - planchas | El servicio evalúa cada forma contra planchas candidatas con dimensiones exactas, rotación y rechazo por tamaño. |
| T03 - retazos | El servicio deriva la caja desde rectángulo, círculo o polígono convexo persistido y acepta con un solo candidato individual. |
| T04 - bloquear registro | El POST verifica todas las piezas antes de persistir y devuelve los índices/motivos; el formulario conserva y marca el borrador. |

- CA-01: una pieza con plancha compatible disponible se acepta.
- CA-02: un retazo compatible puede satisfacer la validación individual.
- CA-03: se excluyen materiales inactivos, planchas con cantidad cero y parejas
  incompatibles de tipo/espesor.
- CA-04: si alguna pieza carece de candidato, no se persiste el pedido ni ninguna
  pieza.
- CA-05: API y UI identifican la pieza y muestran un motivo comprensible.
- CA-06: la validación no modifica cantidades ni estados de inventario.

## 7. Pruebas y evidencia

La evidencia ejecutable cubre cajas de geometría, límites exactos, rotación, no
cabida, candidatos de plancha y retazo, filtros reales de Inventory en PostgreSQL,
disponibilidad HU-014, errores de Orders, ausencia de persistencia parcial,
conservación del borrador, E2E de éxito/rechazo, suites completas y Alembic.
Los comandos y sus resultados exactos se registran en
[La evidencia reproducible](../evidence/sprint-01/HU-008/README.md).

Implemented describe el estado de código y validación de esta rama. La SPEC no
pasa a Verified: falta una revisión independiente y el cierre formal del PR.
