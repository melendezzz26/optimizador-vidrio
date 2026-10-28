# PLAN-TA-027 — Casos experimentales

Responsable: Andro Quispe. Revisor: Fabricio Melendez Quezada. Fecha: 28/10/2026.
Estado: autorizado para ejecución por el usuario; review pendiente, sin cierre formal.

1. Mantener baseline SP-002; no alterar motor ni comparador TA-021.
2. Usar `experiments/optimization/cases/` y `loader.py`, extensión de la convención experiments/raster.
3. Definir tres JSON pequeños con configuración explícita, piezas y stock congelados.
4. Construir entradas nuevas con preparación productiva; validar configuración y stock con contratos existentes.
5. Probar equivalencia/aislamiento, ejecutar dos veces cada método y revalidar placements con métricas comunes.
6. Guardar matriz, fichas, hashes y resultados de sanidad; no analizar desempeño relativo.
7. Commit/push por hitos; PR conjunto, CI y review melendezzz26. STOP antes de merge.
