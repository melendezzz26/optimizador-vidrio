# T5 de sesión — rotación discreta y cache raster

Base: `20f92380def5c179739fb8eaaa8e9a06435d5f49`. Rama exclusiva core.
Equivale a T3 histórica del PLAN. Avanza CA-08/09/12/18, conserva HU-015.
Archivos: `domain/rotation.py`, `tests/unit/optimization/test_rotation.py`, PLAN,
esta evidencia y logs. Ninguna modificación de RasterMask/Rasterizer/SheetLayout.

## Puente numérico y geometría

Secuencia por múltiplos Decimal: 0..menor que 360; paso obligatorio (0,360], sin
default. NULL/float/NaN/infinito rechazados. Normalización al intervalo [0,360).
Rotación de geometría, nunca interpolación de bitmap. Giros de 90 exactos; otros
usan sin/cos float con conversión explícita tras centrar coordenadas, y se normaliza
la caja al origen. Cambiar pivote y trasladar la caja no cambia el contorno local.
Se aplican los 6 decimales mm de RN-04 TA-005/006, no una nueva precisión comercial.
Se devuelve precisamente el contorno orientado redondeado que entra al raster;
la geometría original de PieceUnit queda intacta. Posiciones/ángulos/resolución y
áreas del contrato conservan Decimal.

Resolución/ángulo convertidos a float requieren round-trip Decimal(str(float))
exacto; no se permite perder dígitos ni underflow. Coordenadas aritméticas tienen
presupuesto explícito de conversión <=1e-12 mm antes de RN-04 (redondeo <=0.5e-6 mm).
Esto no promete geometría continua exacta por debajo de RN-04. No se cambia el
comportamiento HU-015. Configuración/contorno fuera de rango o raster rechazado
falla con error, no con una máscara inventada ni NO_FIT falso. Se conserva el
límite conocido de algunos radios fraccionarios del raster existente.

Presupuestos técnicos: 1M celdas/máscara, eje 2440 y 128 vértices (mismos límites
HU-015), 10000 orientaciones máximas por secuencia; rechazar excesos no selecciona
otro paso silenciosamente. Sin promesa de óptimo angular continuo.

## Cache y reutilización

Cache local a corrida: geometría normalizada/fingerprint, resolución Decimal,
ángulo normalizado. Máscaras son inmutables; OrientedUnit conserva asociación con
unidad y Orientation conserva ángulo y contorno. Círculos preparan solo ángulo 0,
incluso si cambia el paso. Otros descartan orientaciones solo tras comparar
filas completas y columnas de máscaras: nunca por igualdad AABB. Se conserva el
primer ángulo de cada equivalencia raster, conforme §8 del PLAN. Cache de material
independiente usa rasterize_material interior, no raster de pieza conservador.

## Pruebas y resultado

Desde backend, `source /workspace/.setup/runtime.sh`:

```bash
python -m pytest -q tests/unit/optimization/test_rotation.py
python -m pytest -q tests/optimization tests/unit/optimization tests/api/optimization tests/integration/optimization
```

**25 passed** focalizadas; **348 passed, 1 warning** regresión, sin skips/fallos.
Logs [focalizadas](logs/t5-focused.txt), [regresión](logs/t5-regression.txt).
Se cubren 90/45/5/360 y paso no divisor, máscara/contorno de polígono trasladado,
rectángulos/cuadrados/círculos, muestras interiores de todas las orientaciones
5°, cache hit entre unidades distintas y separación por geometría/resolución/ángulo,
material irregular interior, precisión, límites y RN-04. HU-015 íntegramente verde;
diff-check correcto antes del commit. SPEC Reviewed y PLAN Approved conservados.

## Equipo y riesgos

[Refs observados](logs/t5-team.txt) iguales a T4; sin integración. Orders payload
por pieza en dd10ec0; UI sigue fixtures (casing/nombres/Decimal requieren adapter
v1 futuro); RBAC dinámico no duplicado; HU-008 histórico. Ver detalle en T3.
Cache se limita a corrida; no persistencia, estados, streaming ni frontend.
