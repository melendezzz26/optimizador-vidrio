# TASKS-SP-004 — Heurística M4

| ID | Trabajo | Estado |
|---|---|---|
| SP004-M4-01 | Preservar Filler/DJD y leer evidencia anterior. | Hecha |
| SP004-M4-02 | Auditar el modelo de geometría y demostrar ruta experimental sin modificar producción. | Hecha |
| SP004-M4-03 | Investigar Block Packing, generación/complementariedad, compacidad, rotación y BRF; fijar medida local sin atribuir fórmula no verificada. | Hecha |
| SP004-M4-04 | Actualizar SPEC/PLAN/TASKS y revisión técnica antes de implementar. | Hecha |
| SP004-M4-05 | Documentar intención y crear 3–5 casos de diagnóstico DJD no oficiales. | Hecha |
| SP004-M4-06 | Implementar Pair-Block en `experiments/optimization/block_packing/`. | Hecha |
| SP004-M4-07 | Crear caso discriminante Block con triangulares complementarios y trazabilidad. | Hecha |
| SP004-M4-08 | Crear pruebas de compatibilidad, orientación, separación, identidad, fallback y determinismo. | Hecha |
| SP004-M4-09 | Ejecutar comparaciones FF/BF/WF/Block en SMALL/MEDIUM/COMPLEX/discriminante. | Hecha |
| SP004-M4-10 | Correr matriz DJD ×4 y clasificar A/B/C/D sin volver a tunear dimensiones. | Hecha |
| SP004-M4-11 | Crear notebook `SP004-Block-Packing.ipynb` con outputs locales y figuras. | Hecha |
| SP004-M4-12 | Actualizar evidencia y evaluación comparativa Filler/DJD/Block; recomendar TA-042. | Hecha |
| SP004-M4-13 | Ejecutar pruebas DJD/Block y regresiones FF/BF/WF; verificar CA. | Hecha |
| SP004-M4-14 | Crear commits locales coherentes; detenerse antes de push/PR/merge. | Hecha |

| SP004-M4-15 | Auditar rotaciones v1, oportunidades de 5 grados, literatura de bloques y criterio v2 antes de cambiar codigo. | Hecha |
| SP004-M4-16 | Implementar orientaciones validas cada 5 grados, equivalencias raster exactas, pruning determinista y contadores. | Hecha |
| SP004-M4-17 | Declarar hasta tres casos complementarios v2 sin cambiar dimensiones tras benchmark. | Hecha |
| SP004-M4-18 | Ejecutar FF/BF/WF/Pair-Block v2 en serie sobre oficiales y diagnosticos; clasificar A-E. | Hecha |
| SP004-M4-19 | Probar separacion, rotacion, identidad, pruning, rendimiento y determinismo v2. | Hecha |
| SP004-M4-20 | Actualizar notebook, evidencia y decision GO/NO-GO de Pair-Block/TA-042; cerrar localmente. | Hecha |

| SP004-HF-01 | Investigar hole filling/IFP/backfilling y distinguir método publicado de adaptación raster local. | Hecha; referencias y límites en SPEC/SP-004. |
| SP004-HF-02 | Auditar RasterMask, SheetLayout, colisión, separación, margen, orientación, layouts temporales y stock. | Hecha antes de implementación. |
| SP004-HF-03 | Definir hueco físico y pocket de placement con una regla determinista computable. | Hecha; conectividad 4-conexa. |
| SP004-HF-04 | Congelar hasta cuatro diagnosticos externos a TA-027 antes de comparar metodos. | Hecha; manifiesto y cuatro JSON congelados en e624e60 y 3ac7b97. |
| SP004-HF-05 | Implementar deteccion, mapas en escala de grises y placement experimental aislado. | Hecha; detector raster, mapas SVG y fallback pocket-first. |
| SP004-HF-06 | Probar reglas geometricas, compatibilidad, rotacion, determinismo y no mutacion. | Hecha; suite HF actual: 13 pruebas PASS, incluyendo equivalencia del flood raster acelerado. |
| SP004-HF-07 | Comparar FF/BF/WF/HF solo en los diagnosticos; medir deteccion y placement por separado. | Hecha; cuatro casos, tres repeticiones HF y contadores/tiempos en CSV/JSON. |
| SP004-HF-08 | Resolver VIABLE/NO VIABLE; correr benchmarks oficiales solo tras pasar el criterio. | Hecha; mini-spike VIABLE; benchmarks EXP autorizados por gate y NO-GO TA-042. |
| SP004-HF-09 | Actualizar documentacion/evidencia y crear commits locales; no publicar la rama. | Hecha; cierre local en commits, sin push/PR/merge. |
| SP004-HF-10 | Definir tres pedidos sintéticos realistas y congelar fixtures, intención, hash y commit antes de comparar heurísticas. | Hecha antes de las corridas; HF-REALISTIC-001/002/003, intención congelada y commit `fda6d12`. |
| SP004-HF-11 | Comparar FF/BF/WF/HF serialmente con configuración idéntica y registrar métricas oficiales, contadores, placements y tiempos. | Hecha; CSV y JSON realistas incluyen resultados y detalle de tres repeticiones HF por fixture. |
| SP004-HF-12 | Verificar determinismo y generar figuras solo donde se usaron pockets; actualizar notebook y documentación SP-004. | Hecha; firmas PASS ×3, una figura para 002 y seis para 003; notebook con outputs medidos y reporte NO-GO. |
| SP004-HF-13 | Reejecutar pruebas HF/regresiones, comprobar artefactos y cerrar el hito con commits locales sin publicar. | Hecha; 13 pruebas HF y 145 regresiones PASS; artefactos validados en commits locales. |
