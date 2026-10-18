# Corte comercial de Sprint 1

Evidencia puntual del cierre P0 del 17 de octubre de 2026. No reemplaza ni
regenera las evidencias históricas de Sprint 1.

- [Informe, límites y reproducción](../../../reviews/S1-commercial-cut-hardening.md).
- [Benchmark](benchmark.json): tiempo, memoria de máscaras, heap máximo,
  memoria retenida tras tres repeticiones y máximo del proceso.
- [Escenario real por API local](scenario.json): 8/8, configuración, posiciones,
  métricas, confirmación, stock 10 → 9 y origen del retazo; escritorio y móvil.
- [Distribución 2D](chromium-desktop-2d.png), [cámara XYZ](chromium-desktop-3d.png),
  [retazo y origen](chromium-desktop-remnant.png), [retazo en móvil](chromium-mobile-remnant.png).

Datos sintéticos sobre PostgreSQL temporal aislado. El equivalente a #64 usa
ocho rectángulos de 600 × 800 mm; no se extrajo geometría ni se modificó el pedido
#64 de Supabase. Los JSON no contienen tokens ni credenciales. Los logs completos
permanecen fuera del repositorio.
