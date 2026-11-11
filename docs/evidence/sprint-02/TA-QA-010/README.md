# TA-QA-010 — Evidencia documental

[Informe](../../../quality/TA-QA-010-informe-cuantitativo-ISO-NewGlass.md). Corte 2026-11-11. No se volvieron a ejecutar pruebas, benchmarks ni capturas.

- metricas-consolidadas.json/csv: 26 filas, fórmulas/metas de PR #120 y evaluación conservadora.
- rendimiento-fuente.json: copia exacta semántica del JSON de Luis; referencia E05 en fuentes.json.
- rendimiento-consolidado.json/csv: p50 por rango más cercano, máximos, RSS de proceso y estados por repetición.
- compatibilidad-consolidada.json: 72 casos agrupados por proyecto, ver E03.
- checks-fuentes.json: checks consultados por SHA, sin convertirlos en MM-04.
- resumen.json: estados y subtotal con resultado.
- AUDITORIA.md: ownership, ramas y limitaciones de fuentes.
- generar_graficos.py: generación reproducible de siete PNG a partir de estos JSON; requiere Python, matplotlib y numpy. Ejecutar `python generar_graficos.py` desde esta carpeta. No prueba el producto.

No hay datos personales de usuarios, credenciales ni rutas locales en los archivos nuevos. Los documentos de origen conservan sus propios límites; el informe no copia sus credenciales ni cuentas. Word y capturas de Notion permanecen fuera de Git. Las imágenes PNG versionadas son únicamente los siete gráficos generados de datos consolidados.

CA-01/02/03 preparados. CA-04: acciones listas; revisión del equipo pendiente.

Validación documental: 26 métricas, 108 registros de carga, siete PNG y 21 enlaces relativos comprobados. Las 17 fuentes GitHub respondieron HTTP 200. Las dos páginas oficiales ISO devolvieron 403 al método HEAD automatizado, pero se consultaron mediante navegación web; no se consideran enlaces inexistentes. Ver `validacion-documental.json` y `validacion-enlaces.json`.

El DOCX se comprobó como contenedor OOXML íntegro, con tablas, las 26 métricas y 13 imágenes incrustadas (siete gráficos y seis evidencias existentes). No se realizó renderizado de páginas con Microsoft Word o LibreOffice en esta validación.
