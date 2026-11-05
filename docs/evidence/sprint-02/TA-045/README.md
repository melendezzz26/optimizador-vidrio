# TA-045 — Auditoría y validación sobre Sprint 2 integrado

Fecha de trabajo: 2026-11-05 (America/Lima). Rama exclusiva:
`fix/S2-TA045-precision-geometrica`. Base y HEAD inicial:
`2c592296f6ffcc2befc0fef0f05c1024f0d378d4`; árbol inicial limpio.
No se hizo merge, cherry-pick, push, cambio del PR #102 ni acceso a Supabase.

## Causa raíz y contrato comprobado

`placement.distance_in_cells` calculaba `ceil(d/r - 1e-9)`. En la base integrada:

| Distancia mm | Resolución mm/celda | Antes | Después |
|---:|---:|---:|---:|
| 0 | 1 | 0 | 0 |
| 1e-10 | 1 | 0 | 1 |
| 1 | 1 | 1 | 1 |
| 1.0000000001 | 1 | 1 | 2 |
| 0.07 | 0.01 | 7 | 7 |
| 0.070000000001 | 0.01 | 7 | 8 |

Esto contradice SPEC-TA-007 RN-04/05/06: la distancia aplicada nunca debe ser
inferior a la configurada. También fallaban el siguiente float después de 1,
positivos subnormales y divisiones cuyo cociente flotante se vuelve cero.

Regla exacta: para `d >= 0` y `r > 0`, finitos, convertir los números raster
aceptados mediante `Decimal(str(valor))`. Si `d=dn/dd` y `r=rn/rd`, calcular
`n=(dn*rd + dd*rn - 1)//(dd*rn)`. Satisface `n*r >= d` y, si `n>0`,
`(n-1)*r < d`. No depende de la precisión del contexto Decimal. No se aplica
tolerancia, cuantización de coordenadas ni redondeo bancario a estas distancias.
Una entrada float `0.30000000000000004` conserva ese valor decimal; no se infiere
que el emisor quiso decir `0.3`. Los múltiplos decimales exactos sí se conservan.

La API raster mantiene `int`/`float` finitos, excluyendo bool, distancias negativas,
NaN e infinitos. Ahora valida explícitamente resolución positiva y finita con
`PlacementError`, también para distancia cero. `RasterMask` ya exigía esa resolución;
no se amplía el contrato a Decimal en la API raster. La configuración de dominio
mantiene su contrato distinto: Decimal/int, finitos, y resolución positiva.

## Trazabilidad de unidades y semántica física

- `Configuracion`: margen y separación `Numeric(8,2)`; resolución `Numeric(8,3)`.
  `run_uow.configuration()` crea `OptimizationConfig` sin conversión binaria implícita.
- `packing._distance_cells` **ya era exacta** en la base integrada. No se demuestra
  una subestimación en los seis motores a través de esa ruta. El defecto directo
  está en `distance_in_cells`; las pruebas nuevas protegen ambas rutas.
- `_empty_layout` calculaba conteos exactos, los multiplicaba por resolución float
  y los volvía a convertir en `SheetLayout.empty`. Quitar solamente el epsilon
  introduciría sobreestimaciones: `3*float(0.1)=0.30000000000000004` daría 4 celdas.
  Los conteos validados llegan ahora a `_from_cells` sin ese viaje de ida y vuelta.
- Margen: erosión de la máscara interior del material; separación: dilatación de
  la unión ocupada. Vecindad cuadrada/Chebyshev, conservadora también en diagonal.
  No hay kerf independiente en el contrato ni separación exterior adicional.
- Planchas: ancho/alto físicos en mm, contorno rectangular original en stock.
  Retazos: contorno rectangular, circular o polígono convexo original. El raster
  del material admite solo celdas completamente interiores; el de las piezas
  cubre conservadoramente su figura orientada. No se descuentan reservas de las
  dimensiones nominales ni se añaden dos reservas entre piezas.
- `resolution_mm` expresa mm/celda; filas/columnas y posiciones internas son
  celdas. Las coordenadas publicadas son índices por resolución Decimal. La política
  de seis decimales de contornos/rotación y `raster_number` permanece intacta.
- Se preservan los atajos existentes de margen que vacía el layout y separación
  saturada, así como todos los límites de ejecución, memoria y rasterización.

## Comparación con la rama histórica

Referencia auditada: `recovery-audit/TA-045`, HEAD
`948e1fea8d17b772d33151a678de5703f0b7fa64`, ancestro común
`7556a700496673d00fe41b6036d69d91d0939959`.

`f98c72fe0f9749eab01a853518e54e6eff9caa71` contiene la corrección válida: techo
racional de las representaciones decimales, constructor por conteos y eliminación
del viaje por floats en packing. Los dos archivos productivos de la base integrada
coincidían con sus versiones anteriores a ese fix; la adaptación no exige cambiar
los motores. Se recuperó únicamente esa lógica, con validación explícita adicional
de resolución y regresiones más amplias.

`948e1fe` solo agrega documentación/evidencia histórica. No se importó como bloque:
su base y sus resultados no son evidencia nueva y describían TA-043 pendiente.
Las pruebas antiguas tenían 20 casos y denominaban M4/M6 a HF/M6-BS. Las actuales
usan el catálogo integrado, añaden propiedades racionales y de límites, precisión
fraccionaria, inviabilidad, retazos, rotaciones y adaptadores/snapshots v3.
No se restauraron declaraciones obsoletas sobre API/UI ni trabajo de TA-047/TA-049.

## Archivos y efecto por motor

Producción: `placement.py` y `packing.py` en
`backend/app/modules/optimization/domain/`. Pruebas: `tests/optimization/test_placement.py`
y `tests/unit/optimization/test_ta045_separation.py`. Documentación: SPEC-TA-045,
una precisión del texto en SPEC-HU-015 y esta evidencia con sus salidas.

Archivos documentales: `docs/specs/SPEC-TA-045-separacion-corte.md`,
`docs/specs/SPEC-HU-015-interfaz-rasterizacion.md` y este `README.md`.
Salidas bajo `docs/evidence/sprint-02/TA-045/test-results/`: `backend-main.txt`,
`comparison-calculation.txt`, `comparison-supervision-v2.txt`, `sequential-runner.txt`,
`comparison-runner.txt`, `frontend-lint.txt`, `e2e.txt` y `validation-runtime.json`.
Este último acredita exit 0 incluso para lint, que no produce texto cuando pasa.
Se eliminaron únicamente espacios finales de la salida E2E para `git diff --check`.

| Motor | Ruta de geometría | Efecto |
|---|---|---|
| FF | pack → _empty_layout → SheetLayout | Conteos exactos, misma búsqueda |
| BF | pack + selector BF | Misma geometría, mismo score/selector |
| WF | pack + selector WF | Misma geometría, mismo score/selector |
| HF | packing y validación de alternativas | Mismos límites y decisiones HF |
| M5 | pack + Best Residual Fit | Misma puntuación y geometría |
| M6-BS | _empty_layout + búsqueda propia | Ancho 2 y límites intactos |

La suite nueva contiene 106 casos: 10 de lógica compartida y 16 por cada motor
(96 en total): adyacencia en plancha/retazo, casos viables/inviables, ajuste exacto
fraccionario sin reserva doble/exterior, retazos de tres geometrías y adaptador con
snapshot. Además hay 97 casos de placement, incluidos oráculos racionales de
conservación mínima y monotonía. Se validan las celdas independientemente del
layout y se reproducen las colocaciones por la API oficial. Rotación de 90° forzada
por una fuente estrecha; rotación de 5° con cajas superpuestas y máscaras separadas.

## Ejecuciones y resultados

Entorno: Python 3.11.9, pytest 9.1.1, Linux/WSL, PostgreSQL 18 local efímero.
`PYTHON_DOTENV_DISABLED=1`, `NEWGLASS_REQUIRE_POSTGRES=1`,
`NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/18/bin`. Ninguna conexión remota.

Las versiones de `backend/requirements.txt` se verificaron contra el runtime.
Faltaban openpyxl 3.1.5, et-xmlfile 2.0.0 y python-multipart 0.0.20; se instalaron
solo en `backend/.venv/ta045-deps`, ignorado por Git. Los dos primeros intentos de
suite amplia terminaron con 24 y 21 errores de recolección, respectivamente; no
son PASS. No se modificó requirements ni el entorno compartido.

También se interrumpió una ejecución sobre el montaje Windows después de registrar
fallos parciales, sin declararla aprobada ni alterar límites. La validación completa
se repitió en una copia privada del mismo checkout dentro del filesystem Linux.
Los hashes de ambos archivos productivos y ambas pruebas modificadas se comparan
antes de ejecutar; el manifiesto conserva esos hashes y los códigos de salida.

| Ejecución | Resultado |
|---|---|
| Regresiones definitivas con placement/packing de la base cargados solo en memoria | 35 failed, 168 passed (fallos esperados, prueba del defecto) |
| Placement + TA-045 corregidas | 203 passed, 0 failed, 0 skipped |
| Backend principal, exclusiones de CI | 3091 passed, 0 failed, 0 skipped; 1 aviso Starlette/httpx |
| Comparación calculation aislada | 8 passed, 0 failed, 0 skipped |
| Comparación supervision v2 aislada | 26 passed, 0 failed, 0 skipped |
| Sequential runner aislado | 26 passed, 0 failed, 0 skipped |
| Comparison runner aislado | 14 passed, 0 failed, 0 skipped |
| E2E focalizado, comparación salvo B02 | 16 passed (8 desktop + 8 mobile), 0 failed, 0 skipped, 0 flaky |
| Lint frontend en copia temporal | PASS, exit 0 |
| Compilación Python e indentación | PASS, 4 archivos con compileall y tabnanny |
| git diff --check | PASS, también requerido sobre el índice antes de commit |

Total backend no solapado: **3165 passed, 0 failed, 0 skipped**. Las 203 pruebas
focalizadas están incluidas en ese total y no se vuelven a sumar. Incluye los seis
motores, raster/rotación/contratos, comparación v1/v2, API, persistencia y confirmación
real sobre PostgreSQL efímero. No se ejecutaron unitarias/build de frontend: no hay
cambios de código frontend. El aviso Starlette/httpx no altera el resultado y no
se introducen dependencias nuevas para silenciarlo.

Comandos focalizados, desde backend:

```bash
python -m pytest tests/optimization/test_placement.py tests/unit/optimization/test_ta045_separation.py -q --tb=short
```

Backend conserva las cinco selecciones y fronteras de aislamiento de
`.github/workflows/ci.yml`: suite principal con sus cuatro `--ignore`, y cada
archivo excluido en un proceso nuevo. Se añaden `-x --tb=short` para diagnóstico,
sin omitir casos si la ejecución termina aprobada. Las salidas y los comandos
efectivos se guardan en [test-results](test-results/).

Selección E2E equivalente, desde frontend con Python/Node/PostgreSQL locales:

```bash
PLAYWRIGHT_CHANNEL=chromium npx playwright test optimization-comparison.spec.js --grep-invert 'TA-043 B02 smoke'
```

La copia temporal usa configuración derivada de la original, con caché Vite local
y reporter JSON/lista. Se excluye el smoke B02 de downgrade/upgrade porque exige
su propia fase con base vacía. No se desactiva ni sustituye el gate global: esta
ejecución se declara exclusivamente focalizada. Se usan las dos variantes desktop/mobile.
El error sintético de persistencia FF en la salida es intencional: el escenario
comprueba el fallo de FF y la confirmación única de BF. Ambos proyectos pasan ese
caso. El manifiesto registra limpieza del servidor con exit 0; la copia privada
se eliminó al finalizar, sin seguir sus symlinks a dependencias.

## Riesgos y criterio de integración

La corrección geométrica queda validada por las ejecuciones anteriores. Se recomienda
integrarla en `recovery/sprint-02` después de ejecutar y aprobar el E2E global completo
en sus dos fases: una selección focalizada no lo certifica. No se hizo push ni
se modificó el PR #102 o las ramas protegidas. No se declara la totalidad histórica
de TA-045/T03 verificada ni aprobación formal de revisión.
La métrica cuadrada y la reserva adicional propia de la discretización permanecen;
esta corrección no certifica el espacio continuo ni el rendimiento de toda orden.
Las configuraciones almacenadas tienen menor escala que las entradas extremas de
regresión; esos casos protegen el contrato reutilizable, no describen valores comerciales.
