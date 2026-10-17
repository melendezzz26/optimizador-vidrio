# Evidencia de implementación y validación

Organizar la evidencia de Sprint 1 en `sprint-01/<ID>/`, donde `<ID>` identifica
el PBI, HU, enabler o spike correspondiente.

Cada evidencia debe registrar, cuando corresponda:

- Objetivo y enlace a la SPEC o investigación.
- Rama y commit realmente consultados; indicar si había cambios sin commit.
- Comando y directorio de ejecución.
- Entradas, parámetros y versiones necesarias para reproducir el resultado.
- Resultado observado y limitaciones, sin fechas, métricas ni hashes inventados.

Conservar únicamente los artefactos pequeños necesarios para sustentar el
resultado. Las salidas exploratorias completas de rasterización pertenecen a
`experiments/raster/results/` hasta seleccionar qué evidencia conservar.
No incluir credenciales ni datos sensibles en capturas o logs.

El cierre integrado de Sprint 1 tiene un
[índice canónico UI/First Fit](sprint-01/S1-OPT-UI/README.md),
[resultados finales reproducibles](sprint-01/S1-OPTIMIZATION-FIRST-FIT/integration/final/README.md)
y [auditoría de consolidación](../reviews/S1-evidence-consolidation.md).
Las salidas históricas se distinguen de los resultados posteriores a Orders.

El [cierre P0 de corte comercial](sprint-01/S1-COMMERCIAL-CUT/README.md) conserva
evidencia puntual posterior: 8/8 a 1 mm, benchmark, vistas y origen del retazo.

El directorio `sprint-01/EN-001/` contiene la evidencia existente del traslado de
database. `sprint-01/SP-001-raster/` solo está reservado mediante `.gitkeep`:
no representa un experimento ejecutado ni un resultado aprobado.
