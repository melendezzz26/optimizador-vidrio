# TA-013: catálogo persistido

Implementación y validación local del 5 de octubre de 2026, rama `feature/TA-013-datos-base`.

La migración manual `1c8754481a08` carga los seis tipos y 28 combinaciones definidos en la [SPEC](../../../specs/SPEC-TA-013-datos-base.md). `TipoVidrioEspesor` representa `tipos_vidrio_espesores`, con PK `(id_tipo_vidrio, espesor_mm)`, FK al tipo y CHECK positivo. La precisión es `NUMERIC(4,1)`, igual que en los tres consumidores.

El repositorio devuelve los espesores persistidos en una tupla de `Decimal`, ordenados ascendentemente. La consulta de todos los tipos utiliza una consulta de tipos y otra de pares, sin una consulta adicional por cada tipo. No hay listas globales de espesores en el servicio ni en la presentación.

`GlassCatalog` y `validate_tipo_espesor` son contratos públicos de Application reutilizables por Pedidos. El llamador controla la transacción. Se comprueban tipo existente, actividad cuando corresponde, espesor finito positivo y pertenencia al catálogo. El PATCH usa la pareja efectiva de datos nuevos y actuales. Si no cambia la pareja, se permiten otros cambios en material de tipo inactivo.

Un tipo creado manualmente carece de espesores hasta que se registren pares; no recibe una lista predeterminada. La administración de esos pares queda fuera de este alcance.

Pruebas: `tests/unit/inventory/test_catalog.py` cubre las seis combinaciones válidas/inválidas solicitadas, creación y PATCH de ambos materiales, errores sin escrituras, cambios del catálogo, actividad y valores numéricos inválidos. `tests/integration/inventory/test_catalog.py` verifica los seis tipos y cada uno de los 28 pares en PostgreSQL, la repetición de la carga sin duplicados y las restricciones de unicidad y positividad. Los resultados están en [pruebas-ta013.md](pruebas-ta013.md).
