# Riesgos e incidencias finales

| Riesgo/incidencia | Estado | Acción requerida |
|---|---|---|
| RF-20/HU-018 no pertenece a TA-043 | Condicionado | Integrar HU-018 en una fase autorizada y repetir CA-20 |
| Heroku no ofrece necesariamente procfs/prctl/RLIMIT_AS/spawn | Abierto | Validar plataforma objetivo antes de desplegar |
| Capacidad de 150 unidades no medida | Abierto | Medir solo con presupuesto aprobado |
| Cargas generales >12 unidades no acreditadas | Abierto | Definir y medir perfiles SMALL/MEDIUM/COMPLEX adicionales |
| Resúmenes B10 y última corrida JSON tienen tiempos globales distintos | Observación documental | Tratar `B10/measurements.json` como medición cruda de la última corrida y reconciliar cifras antes del PR |
| Recuperación ambigua requiere intervención controlada | Conocido | Runbook operativo y bloqueo conservador |
| Primer ST-INT fue 3/4 por radio.check | Cerrado como incidencia E2E | Conservar antecedente; no tratar como estabilidad estadística |
| Una instancia/proceso web | Restricción | No habilitar escala horizontal sin rediseño/revisión |
| SPEC/PLAN siguen Draft | Pendiente formal | Revisión y aprobación de Fabricio |

No se detectó defecto crítico que justifique modificar producción durante B11.
