# T05 — Build para GitHub Pages

12/10/2026. Base: `d27fc4d`. SPEC Reviewed releída antes de T05.
Node `22.23.2`, npm `10.9.8`; dependencias existentes, sin actualización.

## Implementación

Modo `staging`, `base=/optimizador-vidrio/`, API HTTPS explícita sin fallback
local en ese bundle. El modo normal conserva desarrollo. `build:staging` y
`check:staging` son comandos separados y obligatorios para el artefacto Pages.
No se introdujo React Router: se retiró el bypass por pathname y el editor
sigue integrado en el formulario de pedidos (Agregar pieza → Polígono convexo).

## Ejecuciones reales desde frontend/

| Comando/check | Resultado |
|---|---|
| `npm run test:unit` | 101 pass, 0 fail, 0 skipped, 182.134 ms |
| `npm run test:component` | 20 archivos, 206 tests passed, 54.10 s |
| `npm run lint` | Código 0, sin diagnósticos |
| `npm run build` | Código 0, 1941 módulos, 1.25 s |
| `VITE_API_URL=https://api.example.test` + `npm run build:staging` | Código 0, 1941 módulos, 523 ms |
| `npm run check:staging` | PASS: assets HTML con base correcta/presentes; textos del bundle sin localhost, DSN, nombres de secretos ni patrones de tokens privados |
| Builds negativos reales, con API vacía/HTTP/localhost | Tres rechazos esperados por validación VITE_API_URL; harness código 0 |
| Inspección CSS | Imagen pública fondoLogin e imagen importada fondo-vidrio con prefijo Pages |

La URL `.test` es sintética y pública; solo se incorporó al build local ignorado,
no como valor por defecto ni configuración de producción. No se hicieron
solicitudes a ella. Build inspeccionado: `index-DuoycA_y.js`,
`index-DgESzcDg.css`. No hubo warnings ni skips en estas suites frontend.

La prueba de componente recorre App → Nuevo pedido → Agregar pieza → editor
y cierre manteniendo `/optimizador-vidrio/`; usa APIs/autenticación simuladas.
No afirma smoke de navegador contra Pages real ni persistencia de borradores
al recargar. No se publicó Pages ni se modificó el backend o workflows.

CA-09/10/11: aporte local validado; origen real y artefacto publicado pendientes.
CA-17: navegación local validada; carga/recarga Pages real pendiente de T07.
`git diff --check` y check staged se exigen antes del commit T05.
