# Finalización del comparador Sprint 2

Base: `2402142`, rama `feat/S2-finalizacion-comparador`.
Alcance autorizado: M6-01, M6-02, benchmarks, trazabilidad y UX; luego suites
integrales y preparación local de PR #102. Sin cambios de BD, Supabase, push,
merge ni despliegue. Se conservan SPEC TA-043/053, contratos v1/v2, ADR-001,
CONTRIBUTING y gate TA-040.

## M6-01

Contar por identidad el grafo vivo de estados, máscaras de material, filas,
placements, trazas y scores. Reservar antes de construir sucesores memoria para
dos layouts (incluido el suspendido en el generador), validación, dilatación,
puntuación, ordenamiento y contabilidad. La caché raster conserva su límite
independiente. No eliminar fuentes ni reemplazar la última frontera hasta
completar el nivel. `state_bytes_peak` registra reservas admitidas;
`state_bytes_bound` incluye la reserva que eventualmente detuvo la búsqueda.

Aceptación: una/ocho planchas grandes pueden iniciar búsqueda; fuentes realmente
excesivas se rechazan antes de rasterizar; un corte conserva la frontera anterior;
la paridad de fixtures TA-053 se mantiene y todas las reservas admitidas caben
en 32 MiB. Regresiones en `test_beam_memory.py` y suites TA-053 existentes.

## Fases siguientes

- M6-02: última posición exacta por bits, checkpoints y límites sin cambios;
  equivalencia exhaustiva y paridad de trazas/geometrías/métricas.
- Benchmarks sintéticos: registrar cobertura, fuentes, métricas, recursos y origen
  de terminación. Un parcial nunca cuenta como seis resultados completos.
- Trazabilidad/UX: reutilizar contratos existentes, distinguir fuentes propuestas,
  recuperables potenciales y recibo de inventario confirmado; historial accesible
  e idempotencia automática, sin ejecutar motores al consultar resultados.
- Cierre: suites CI separadas, frontend, TA-040, revisión de diff y secretos.

La medición sintética no certifica el pedido real #69.

## Validación local final (2026-11-06)

Código validado: `fd9653d`. Backend: 3257 aprobadas (3183 principal y 8/26/26/14
en procesos aislados del CI), sin omisiones, con PostgreSQL 18 temporal. Incluye
TA-045/047/049. Frontend: 213 unitarias y 598 de componentes (58 archivos);
lint/build correctos. TA-040: PASS 148/148 (B02 2 y restante 146), sin omisiones,
escritorio/móvil, servidores y clústeres nuevos por fase. El caso nuevo reproduce
ocho fuentes físicas, revisión móvil con teclado, cancelación sin consumo y
confirmación de ocho unidades con un único movimiento por la cantidad correcta.

Sin cambios de modelos, migraciones o dependencias. `git diff --check` y revisión
de secretos correctos; salidas/capturas fuera de Git. Persisten los avisos previos
de Starlette/httpx y tamaño de bundle. Mediciones y protocolo #69 en
`docs/comparison-performance.md`. Solo commits locales; publicación, checks
remotos y salida de Draft del PR #102 pendientes de autorización/revisión.
