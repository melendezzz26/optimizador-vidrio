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
