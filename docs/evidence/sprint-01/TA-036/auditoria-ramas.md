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

## Reinspección T06 — 13/10/2026

Se repitieron `git log --oneline --decorate BASE..RAMA` y
`git diff --name-status BASE...RAMA`, con BASE
`origin/integration/sprint-01`, y lectura de código mediante `git show`.
Se comparó el conjunto de archivos con `BASE...HEAD` (`0e67631`). Las
referencias locales conservan los mismos tips y solapamientos de la matriz
anterior. No se hizo fetch: esta auditoría prueba el contenido de las refs
disponibles localmente, no la actualidad del servidor remoto.

- Integración: `b7a0175522f5506c11a7782c3a4f8433dd61b4a6`.
- HU-008: `46d801ed3faacc0f62018584d0d6f8a65900d440`.
- TA-005/TA-006: `5c58321f02c02f693ccb462390a1588952c237bc`.

HU-008 ya filtra `estado=true` y `cantidad>0` para planchas y estado para
retazos. La adaptación posterior debe conservar esa regla y probarla con
saldos después de bajas parciales. Su servicio de dominio usa biblioteca
estándar, sin esquemas HTTP ni ORM de Orders. La conexión desde Optimization
no existe en la rama TA-036: CA-09 se registra PARTIAL, sin importar trabajo
ajeno para completar ese alcance diferido.

El correctivo `0e67631` añadió validación de cantidad al escritor común del
repositorio de inventario. HU-008 deberá conservarla junto con las firmas
actualizadas de movimiento. Esto mantiene el riesgo medio en los mismos dos
archivos; no se simulan ni resuelven conflictos por anticipado.

El rasterizador de Aguilar ya recibe `rasterize_geometry(geometry)` y, para
polígonos, `geometry.vertices_mm`. La integración posterior debe pasar el
resultado final persistido de pedidos/retazos. No se ejecutaron sus tests ni
se integró su código durante T06; no hay archivos solapados.

## Instrucciones posteriores al merge de TA-036

Estas instrucciones se entregan para los responsables; **no se ejecutaron**.
Aplican únicamente después de que TA-036 esté mergeado a
`integration/sprint-01`, en la copia de trabajo de cada compañero.

### Fabricio Aguilar

```powershell
git checkout feature/TA-005-TA-006-rasterizacion
git fetch origin
git merge origin/integration/sprint-01
```

Conservar raster estándar y algoritmo desarrollado. Conectar personalizada a
la geometría final `vertices_mm`, incluidos retazos; no reconstruir desde
longitudes independientes. Resolver únicamente conflictos reales y ejecutar
los tests propios de raster y regresiones geométricas con formas de iguales
lados y distinta disposición.

### Luis I. / Andro Quispe

```powershell
git checkout feature/HU-008-stock-compatible
git fetch origin
git merge origin/integration/sprint-01
```

Conservar `get_compatible_stock`, validador geométrico y DTOs desacoplados.
Mantener estado disponible y saldo positivo: baja parcial 10→9 conserva
elegibilidad; saldo cero y retazo dado de baja la pierden. Conservar las
firmas/validaciones de cantidad de TA-036 al resolver conflictos reales de
`application/ports.py` e `infrastructure/repository.py`. Si se introdujo algún
acoplamiento del POST pedido desde el tip auditado, retirarlo. Preparar el
consumo desde Optimization y repetir POST sin inventario, bajas e historial.
