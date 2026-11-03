# HF-REALISTIC-INTENT

## Congelacion previa

Estos son perfiles sinteticos y plausibles de pedidos pequenos de corte de vidrio para mobiliario, vitrinas y piezas decorativas. No representan pedidos reales de clientes ni se construyeron a partir de placements de Hole Filling. Las cantidades, rangos de tamanos, material, espesor y stock se definieron antes de ejecutar FF, BF, WF o HF.

Los casos se congelaron antes de comparar resultados y no seran modificados posteriormente para favorecer una heuristica. Los hashes SHA-256 siguientes identifican exactamente los bytes de cada fixture; el commit local de congelacion se registra en la traza del benchmark.

| Fixture | Unidades | Justificacion de pedido | Retazo / plancha (mm) | SHA-256 |
|---|---:|---|---|---|
| HF-REALISTIC-001 | 15 | Tres circulos medianos (diametros 120, 150 y 180 mm), dos paneles rectangulares y diez piezas pequenas para un conjunto de vitrinas o modulos de exhibicion. | 300x220 / 420x320 | ed1daf63a76becb6023a36dd7e3b5e51a17e93c63130b9108d3c050de1c8837f |
| HF-REALISTIC-002 | 18 | Ocho triangulos de varios tamanos, cinco poligonos convexos y cinco piezas pequenas; representa un lote decorativo con infills triangulares y elementos de remate. | 320x220 / 450x330 | 67a92893b6956a6c8ea0853edeff35567346bdb6406ea249477645a8dec95c9f |
| HF-REALISTIC-003 | 20 | Cuatro paneles rectangulares, cuatro circulos, seis poligonos convexos y seis piezas pequenas; es el pedido de perfiles mas heterogeneos. | 360x240 / 520x400 | 212b1641a3441afa989a11212d207db06d8929189caf3f2a610e46130e0308d6 |

## Configuracion comun

- Material 1, vidrio de 6 mm; todas las piezas y stocks son compatibles dentro de cada pedido.
- Raster de 1 mm; grilla angular del motor de 5 grados (0, 5, ..., 355); margen 5 mm y separacion 3 mm.
- Un retazo y una plancha rectangular por caso. La busqueda vigente prioriza retazo y luego plancha.
- Cada geometria del JSON es una unidad solicitada; no hay semillas ni placements precargados.
- Las orientaciones no se limitan a giros cardinales. Los perfiles se fijaron por tipo de trabajo y rango dimensional, sin medir encaje con una configuracion futura de pocket.

## Regla de clasificacion congelada

Se aplicaran las categorias A-E solicitadas. E tiene precedencia cuando el runtime HF supera 10 veces el baseline mas rapido, conservando el umbral de costo ya usado para el mini-spike. Sin E, C requiere mejora funcional sin deterioro en una metrica primaria; D identifica un resultado funcional peor; B indica uso de pocket y cambio de patron con metricas empatadas; A indica ausencia de uso de pocket o patron equivalente. El tiempo no integra la firma de determinismo.
