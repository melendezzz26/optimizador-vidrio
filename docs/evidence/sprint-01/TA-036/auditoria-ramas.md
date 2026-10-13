# TA-036 — Auditoría previa de ramas paralelas

Base: `origin/integration/sprint-01` = `b7a0175`; trabajo: `feature/TA-036-saneamiento-funcional`, documental `f6ed987`.
Inspección de referencias disponibles mediante `git log`, `git diff --name-status` y `git show`. Ningún checkout, merge, rebase, cherry-pick ni copia de implementación paralela.

## HU-008 (Luis / Andro)

Tip `46d801e`; commits exclusivos: `24484a4`, `8ea8acd`, `0241365`, `ccfa6a6`, `46d801e`.
Archivos: Inventory `application/ports.py`, `infrastructure/repository.py`, nuevos `domain/services/{__init__.py,stock_compatibility_validator.py}`, test unitario y `SPEC-HU-008-stock-compatible.md`.
Ya ofrece `get_compatible_stock` por tipo/espesor, estado disponible y cantidad positiva; dominio calcula AABB y admite giro de 90°. No conecta la consulta a POST Orders.
TA-036 no incorpora ni duplica este servicio. Orders permanece independiente de stock. Tras integrar, HU-008 debe conservar su consulta como puerto reutilizable desde Optimization, respetar saldo parcial/estado y no convertir el POST en un chequeo de stock.

## TA-005 / TA-006 (Aguilar)

Tip `5c58321`; commits exclusivos: `06b5735`, `78be47c`, `5c58321`.
Añade `optimization/domain/{raster_mask.py,rasterizer.py}`, tres tests de raster y su SPEC.
Ya rasteriza rectángulo, circunferencia y polígono; `rasterize_geometry` consume directamente `geometria.vertices_mm` para polígonos. No sustituir algoritmo ni crear otro rasterizador.
Tras integrar, Aguilar debe conectar la geometría persistida definitiva (incluido retazo), sin longitudes como entrada alternativa, y mantener regresiones de formas distintas con longitudes iguales.

| Rama paralela | Archivos solapados | Contrato afectado | Riesgo de conflicto | Acción posterior |
|---|---|---|---|---|
| `origin/feature/HU-008-stock-compatible` | `backend/app/modules/inventory/application/ports.py`; `backend/app/modules/inventory/infrastructure/repository.py` | Baja parcial, saldo disponible, consulta compatible fuera de POST | Medio: mismo repositorio/puerto, métodos diferentes | Conservar ambos cambios al integrar; consulta reutilizable desde Optimization, solo estado=true y cantidad>0 |
| `origin/feature/TA-005-TA-006-rasterizacion` | Ninguno | `geometria.vertices_mm` canónico | Bajo textual; medio funcional al conectar consumidores | Usar vértices persistidos finales; conservar algoritmo de Aguilar y validar contratos |

La modificación de puerto de baja añade cantidad explícita; la del repositorio se limita al movimiento y orden. No se anticipa resolución del código paralelo.
