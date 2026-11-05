# TA-043 / B09 — Validación integral

**Estado: COMPLETADO para B09.** ST-INT pasó en escritorio y móvil sobre el
runtime aislado autorizado. SPEC/PLAN permanecen Draft; B10 y B11 no se inician.

[SPEC](../../../../specs/SPEC-TA-043-integracion-seis-motores.md) ·
[PLAN](../../../../specs/PLAN-TA-043-integracion-seis-motores.md) ·
[validación](validation.json) · [smoke integral](smoke/execution.txt)

## Matriz breve de cobertura

| Criterio | Prueba existente/eje B09 | Evidencia | Brecha |
|---|---|---|---|
| Catálogo, seis motores, hash/configuración común | B01–B07 + ST-INT | B07 seis resultados y diagnósticos | Ninguna dentro de B09 |
| Métricas, geometría, 2D/3D y máscaras | B03/B07 + ST-INT | Capturas y `b07-six-engine-ui.json` | Capacidad cuantitativa queda para B10 |
| Selección sin consumo y confirmación exclusiva | B08 + ST-INT | `b08-confirmation.json` desktop/mobile | Ninguna dentro de B09 |
| Idempotencia, concurrencia, conflictos y rollback | B08 backend/API | XML B08 y pruebas de integración | No se duplica en navegador |
| Fallos de motor, IPC, límites, recuperación y observadores | B04–B06/B08 | XML y validaciones B04–B08 | No se afirma que sean pasos UI |
| v1, `/runs`, historia y legacy | B01/B06/B07 + ST-INT | `b07-history-v1-legacy.json` | Ninguna dentro de B09 |
| Procesos, supervisor y limpieza | ST-INT | `cleanup.json`, `processes_after: []` | RSS/capacidad final: B10 |
| RF-20 / HU-018 | Condicionado | No integrado en esta base | Pendiente real, no PASS |

## ST-INT ejecutado

Comando reproducible desde PowerShell externo:

```powershell
wsl.exe -e bash -lc 'cd /mnt/c/Users/fabri/Documents/TALLER\ INTEGRADOR\ I/optimizador-vidrio/backend && /home/fabri/.cache/newglass-validation.SXhCMM/backend/.venv/wsl/bin/python -m tests.optimization_b01_smoke --block B09 --runtime-root /home/fabri/.cache/newglass-validation.SXhCMM'
```

Resultado final: **4/4 PASS**, un worker de Playwright, 54.5 s:

- Chromium escritorio: B07 seis motores/vistas/v1/legacy y B08 selección/
  confirmación.
- Chromium móvil: los mismos dos recorridos.
- PostgreSQL privado, FastAPI real, Vite real, usuario autenticado y motores
  productivos.
- Configuración geométrica real de 5°.
- Inventario intacto antes de seleccionar; confirmación con un movimiento y
  recibo idempotente por escenario.
- Recarga y recuperación sin segundo POST de comparación.
- `processes_before: []`, `processes_after: []`,
  `temporary_copy_removed: true`.

Los estados de las seis ejecuciones fueron `COMPLETADA/COMPLETE`, con
`supervisor_stopped: true`. M6-BS conservó sus estadísticas de búsqueda y HF
sus estadísticas de pocket/fallback. Las capturas, requests y snapshots están
en `smoke/chromium-desktop/` y `smoke/chromium-mobile/`.

## Regresiones ejecutadas

- Backend portable: 641 pruebas de optimización, 590 de inventario/shared y
  113 de ejecución de motores: PASS.
- Frontend: 561/561 componentes PASS; el test v1 que agotó 5 s en la ejecución
  agrupada pasó 8/8 al repetirse aislado con timeout de 15 s.
- ESLint, build Vite y `compileall`: PASS.
- Confirmación B08 focalizada: 20/20 PASS; las dos pruebas API que arrancan el
  supervisor real devuelven el bloqueo esperado `RESOURCE_UNAVAILABLE` en
  Windows y están acreditadas PASS en los XML WSL2 de B08.
- La suite API histórica ejecutada en Windows tuvo 79 PASS y 24 bloqueos por el
  mismo requisito Linux; no se contabiliza como defecto funcional.

Los conteos históricos no se suman de nuevo: B08 acredita 183 casos backend
distintos y 54 frontend distintos en sus XML.

## Intento fallido y corrección

El primer ST-INT obtuvo 3/4: B07 escritorio/móvil y B08 móvil pasaron; B08
escritorio falló en `radio.check()` porque el control no cambió de estado.
No hubo confirmación ni consumo parcial. El B08 aislado posterior pasó y el
ST-INT repetido pasó 4/4. Se conserva el resultado final y la incidencia en
`smoke/execution.txt` de la ejecución aprobada; no se modificó producción ni se
relajaron aserciones.

## Límites y pendientes reales

No se ejecutó RF-20/HU-018 porque no está integrado en esta base. Las mediciones
de capacidad final (RSS agregado, margen y propuesta de despliegue) pertenecen a
B10. No se declaran como PASS en B09.
