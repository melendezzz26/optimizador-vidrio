# SPEC TA-018 — Best Fit

Responsable: Andro Quispe. Base técnica actualizada tras cambios integrados en PR #58.
Base 783aac8, reutilizando domain/packing.py sin duplicación.
BestFitOptimizer.optimize ofrece simulación de dominio, como WorstFitOptimizer.

Por cada unidad y nivel de fuente: generar FeasibleCandidate canónico de cada
fuente compatible usando primera orientación y primera posición factibles.
Seleccionar min con tuple:
(remaining_free_cells_after_placement, stock_rank, orientation_rank, row, column).
Los ranks son los del motor POST-PR58, no orden nuevo por ID.
RETAZO es nivel 1; PLANCHA solo se evalúa si no hay candidato retazo.
No optimizar posición/orientación dentro de fuente.

Capacidad libre = suma bit_count(usable & ~blocked) del layout_after existente.
Unidad: celdas raster; considera material interior, margen, ocupación y separación.
Conversión explícita a mm², si se necesita: celdas × resolution_mm².
Resolución común en el problema hace comparable el score.
No usar área bbox, área geométrica ni capacidad previa como sustituto.

Reutilizar FeasibleCandidate y cache del cálculo; selección incremental.
Resultado conserva método BF también después de calculate_metrics.
Simulación no escribe inventario ni confirma pedidos.
HTTP/lifecycle durable permanece con contrato FF vigente, igual que WF integrado.

Aceptación: normal, rotación necesaria, no colocable, desempate, repetición,
prioridad retazo, fallback plancha, capacidad posterior con separación,
regresión FF, métricas y snapshot de BD intacto.

