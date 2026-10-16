# S1 — T1: modelos y contratos compartidos

Fecha: 16/10/2026 (Lima). Rama: `feature/S1-optimization-core`.
Alcance autorizado: únicamente T1 del [PLAN Approved](../../../specs/PLAN-S1-optimization-first-fit.md).
No se ejecutó T2 ni se creó preparación, expansión, motor, rotación, proveedor de
stock, streaming, endpoints, migración, persistencia, confirmación o frontend.
No se hizo commit, push, merge ni PR.

## Auditoría y decisión

Se leyeron íntegramente SPEC S1, PLAN S1 y SPEC HU-015, y se inspeccionaron las
cuatro capas actuales de Optimization. El árbol inicial estaba limpio.

- Se conservan `RasterMask`, funciones de `rasterizer.py` (no existe una clase
  Rasterizer), `SheetLayout`, `PlacementCheck`, `RasterizedPiece`, ports/casos de
  uso/adaptador/contratos/guards existentes HU-015. No hay entidad Placement previa.
- Se crea `domain/problem.py`: configuración, unidades, grupos, candidatos,
  problema, placement por composición, resultado y contenedor de métricas futuras.
- Se crea `application/dto.py`: estado/observación y progreso derivado.
- Se crean `presentation/run_schemas.py` y `run_serialization.py`, sin importarlos
  desde el router existente. Reutilizan los schemas geométricos HU-015.
- Se añade una subsección T1 al PLAN con contrato wire completo, matriz de errores,
  precisión Decimal, NDJSON futuro, permisos puente y pendientes cross-branch.
- Se añaden dos suites contractuales y fixtures JSON compartibles con UI.

La composición de placement conserva referencias a unidad/candidato y contorno
orientado/local; no añade identidad a la validación de ocupación de SheetLayout.
La preparación/rotación se implementará en sus tareas correspondientes.

## Contrato compartible con UI

Fuente: [fixtures v1](../../../../backend/tests/api/optimization/fixtures/s1_contract_v1.json),
[schemas](../../../../backend/app/modules/optimization/presentation/run_schemas.py)
y subsección T1 del PLAN. El ejemplo es ilustrativo; no se presenta como cálculo
ni flujo de red observado. Siete eventos del camino exitoso más evento alternativo
de fallo cubren los ocho tipos solicitados.

Inicio solo `order_ids`, configuración efectiva backend sin defaults cliente;
envelope versionado, ocho eventos, placement reconstruible, GET con unidades
colocadas/no colocadas, métricas nullable y confirmabilidad; confirm sin body,
respuesta por pedidos/recursos físicos y conflicto 409. Nuevas medidas Decimal se
serializan como strings. `physical_unit_index` interno mapea a `stock_unit_index`
wire. La geometría canónica conserva la representación numérica de HU-015.

## Validación ejecutada

Directorio: `optimizador-vidrio/backend/`, Python del `venv` existente.

```powershell
& ./venv/Scripts/python.exe -B -m pytest -q tests/optimization tests/unit/optimization tests/api/optimization
```

Resultado final observado: **286 passed, 1 warning in 76.13s**, sin skips ni fallos.
Warning: `StarletteDeprecationWarning` por TestClient/httpx; no se modificaron
dependencias. La regresión incluye `/start`, `/rasterize`, formas soportadas,
validaciones, autorización, serialización, geometría, presupuestos y pruebas
existentes de ausencia de escrituras excluidas. Las fixtures existentes usan
recursos de prueba controlados, incluido PostgreSQL temporal local, sin destinos
remotos. No se ejecutaron pruebas de frontend ni una suite completa del backend.

La primera invocación de Python en sandbox no pudo iniciar el intérprete base
WindowsApps del venv. Las ejecuciones autorizadas fuera del sandbox sí pudieron
iniciarlo; no fue un fallo de pruebas del producto. Validaciones intermedias:
18 pruebas de modelo y después 50 de modelo/contrato pasaron; el resultado final
anterior incluye los casos adicionales y reemplaza esos conteos intermedios.

Se ejecutaron `git diff --check`, `git diff --stat` y `git status --short`.
El diff tracked contiene únicamente el PLAN; los archivos creados permanecen
untracked deliberadamente porque no se preparó ningún commit. Se revisa además
whitespace de archivos nuevos mediante `git diff --no-index --check` contra NUL.

## Compatibilidad y revisión siguiente

Sin incompatibilidades nuevas con HU-015; sus archivos ejecutables y contratos
permanecen intactos, y su regresión focalizada pasa. Continúa el límite conocido
de algunos radios fraccionarios del raster, cubierto por el tratamiento seguro
422 existente; T1 no lo modifica.

Revisar antes de T3: composición de placement, contorno orientado/local y puente
explícito Decimal → raster existente; mantener el mapeo de índices físicos y
strings Decimal acordados con UI. Continúan pendientes el contrato batch
caller-owned de Orders, el mapeo RBAC de rutas nuevas y el mínimo independiente
de área recuperable inexistente en Configuracion. No se inventan acuerdos ni
defaults. Mensaje de integración preparado en el PLAN; no se envió externamente.
