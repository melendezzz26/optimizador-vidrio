# TA-QA-001 - Matriz de metricas de calidad

Responsable: Andro Joseph Quispe Cesias. **Pendiente de validacion final con el modelo de calidad consolidado por Fabricio Aguilar Chavez.** No se encontro modelo QA consolidado en la documentacion de la base auditada. IDs y responsables del backlog proceden del encargo y requieren cotejo con Notion.

[ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) y [ISO/IEC 25023:2016](https://www.iso.org/standard/35747.html) son marcos de referencia de ediciones distintas. Las formulas son propuestas operativas, no transcripciones normativas. ISO 25023 no fija umbrales universales; todas las metas son propuestas del proyecto. No se afirma certificacion, conformidad ni acreditacion. Subcaracteristicas orientativas pendientes de validacion.

Usabilidad/accesibilidad del backlog se relaciona con Interaction capability; compatibilidad/flexibilidad con Compatibility y Flexibility; seguridad operacional con Safety, distinta de ciberseguridad. Trazabilidad es indicador operativo, no caracteristica ISO independiente. Seguridad de la informacion no esta evaluada.

Estados: DEFINIDA = ficha creada; BASELINE DISPONIBLE = datos comparables verificados; PENDIENTE DE MEDICION = ejecucion programada; MEDIDA = resultado registrado; VALIDADA = resultado revisado. Todas las filas estan DEFINIDAS, pendientes de medicion especifica. Baseline significa registrar el valor sin PASS/FAIL cuantitativo hasta acordar umbral. Denominador cero significa no evaluable, nunca PASS.

| ID | Caracteristica | Subcaracteristica orientativa | Metrica y objetivo | Formula | Unidad | Procedimiento | Herramienta y ambiente | Meta | Justificacion | Evidencia esperada | Tarea | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MF-01 | Funcional | Correccion | Medir Casos correctos | PASS / ejecutados * 100 | % | F | pytest / local Linux | 100% criticos | Requisitos indispensables | Registro MF-01 | TA-QA-003 | DEFINIDA |
| MF-02 | Funcional | Correccion | Medir Validez geometrica | patrones validos / generados * 100 | % | G | pytest / local Linux | 100% criticos | Un patron invalido causa cortes incorrectos | Registro MF-02 | TA-QA-003 | DEFINIDA |
| MF-03 | Funcional | Correccion | Medir Politica de FF BF WF M4 M5 M6 | casos de politica correctos / evaluados * 100 | % | H | pytest / local Linux | 100% controlados | Cada motor debe cumplir su politica | Registro MF-03 | TA-QA-003 | DEFINIDA |
| MP-01 | Desempeno | Tiempo | Medir Latencia | fin menos inicio | ms | P | benchmark y procfs / Linux | Baseline | Depende del ambiente | Registro MP-01 | TA-QA-002 | DEFINIDA |
| MP-02 | Desempeno | Tiempo | Medir p50 | valor ordenado en posicion ceil(0,50 * n) | ms | P | benchmark y procfs / Linux | Baseline | Depende del ambiente | Registro MP-02 | TA-QA-002 | DEFINIDA |
| MP-03 | Desempeno | Tiempo | Medir p95 | valor ordenado en posicion ceil(0,95 * n), n >= 100 | ms | P | benchmark y procfs / Linux | Baseline | Muestra insuficiente si n menor de 100 | Registro MP-03 | TA-QA-002 | DEFINIDA |
| MP-04 | Desempeno | Recursos | Medir Pico RSS | maximo de sumas de RSS sincronizadas de proceso y descendientes | MiB | P | benchmark y procfs / Linux | Baseline | Depende del ambiente | Registro MP-04 | TA-QA-002 | DEFINIDA |
| MP-05 | Fiabilidad | Continuidad | Medir Ejecuciones completas | completas validas / iniciadas * 100 | % | P | benchmark y procfs / Linux | Baseline | Depende de plazo y carga | Registro MP-05 | TA-QA-002 | DEFINIDA |
| MP-06 | Desempeno | Capacidad | Medir Capacidad observada | mayor escala con todas las repeticiones completas y validas | piezas | P | benchmark y procfs / Linux | Baseline | No implica maximo universal | Registro MP-06 | TA-QA-002 | DEFINIDA |
| MU-01 | Interaccion | Operabilidad | Medir Tareas completadas | completadas / intentadas * 100 | % | U | navegador y cronometro / local | Baseline | Depende de muestra | Registro MU-01 | TA-QA-005 | DEFINIDA |
| MU-02 | Interaccion | Operabilidad | Medir Tiempo por tarea | fin menos inicio por intento | s | U | navegador y cronometro / local | Baseline | Depende de muestra | Registro MU-02 | TA-QA-005 | DEFINIDA |
| MU-03 | Interaccion | Errores | Medir Tasa de errores | intentos con error / intentos * 100 | % | U | navegador y cronometro / local | Baseline | Definir catalogo antes de medir | Registro MU-03 | TA-QA-005 | DEFINIDA |
| MU-04 | Interaccion | Accesibilidad | Medir Navegacion por teclado | pasos accesibles / pasos evaluados * 100 | % | U | navegador y cronometro / local | 100% criticos | Acceso sin raton a tareas criticas | Registro MU-04 | TA-QA-005 | DEFINIDA |
| MU-05 | Interaccion | Accesibilidad | Medir Foco correcto | transiciones correctas / transiciones evaluadas * 100 | % | U | navegador y cronometro / local | 100% criticas | Foco visible y predecible | Registro MU-05 | TA-QA-005 | DEFINIDA |
| MC-01 | Compatibilidad | Coexistencia | Medir Navegadores | combinaciones exitosas / evaluadas * 100 | % | C | Playwright y DevTools / local | 100% acordadas | Evitar fallos en entornos objetivo | Registro MC-01 | TA-QA-008 | DEFINIDA |
| MC-02 | Flexibilidad | Adaptabilidad | Medir Responsive | pantallas sin perdida / pantallas evaluadas * 100 | % | C | Playwright y DevTools / local | 100% criticas | Mantener controles accesibles | Registro MC-02 | TA-QA-008 | DEFINIDA |
| MC-03 | Flexibilidad | Adaptabilidad | Medir Flujos por viewport | flujos exitosos / flujos evaluados * 100 | % | C | Playwright y DevTools / local | 100% criticos | Conservar tareas esenciales | Registro MC-03 | TA-QA-008 | DEFINIDA |
| MM-01 | Mantenibilidad | Testabilidad | Medir Cobertura | lineas ejecutadas / lineas medibles * 100 | % | M | pytest y Actions / CI Ubuntu | Baseline | No hay umbral acordado | Registro MM-01 | TA-QA-007 | DEFINIDA |
| MM-02 | Mantenibilidad | Modularidad | Medir Duplicacion | lineas duplicadas / lineas analizadas * 100 | % | M | pytest y Actions / CI Ubuntu | Baseline | Herramienta pendiente | Registro MM-02 | TA-QA-007 | DEFINIDA |
| MM-03 | Mantenibilidad | Analizabilidad | Medir Complejidad | complejidad ciclomatica por funcion | numero | M | pytest y Actions / CI Ubuntu | Baseline | Herramienta pendiente | Registro MM-03 | TA-QA-007 | DEFINIDA |
| MM-04 | Mantenibilidad | Testabilidad | Medir CI | ejecuciones exitosas / terminadas * 100 | % | M | pytest y Actions / CI Ubuntu | Baseline | No hay umbral acordado | Registro MM-04 | TA-QA-007 | DEFINIDA |
| MS-01 | Seguridad operacional | Restriccion | Medir Rechazo de invalidos | invalidos rechazados / invalidos evaluados * 100 | % | S | pytest / local Linux | 100% | Cada invalido debe rechazarse | Registro MS-01 | TA-QA-009 | DEFINIDA |
| MS-02 | Seguridad operacional | Restriccion | Medir Falsa aceptacion | invalidos aceptados / invalidos evaluados * 100 | % | S | pytest / local Linux | 0% | Una aceptacion invalida supone riesgo | Registro MS-02 | TA-QA-009 | DEFINIDA |
| MS-03 | Seguridad operacional | Restriccion | Medir Margen y separacion | patrones que cumplen ambos / evaluados * 100 | % | S | pytest / local Linux | 100% | Respetar restricciones de corte | Registro MS-03 | TA-QA-009 | DEFINIDA |
| MT-01 | Operativa | Trazabilidad | Medir Material identificable | materiales con codigo visible / utilizados * 100 | % | T | navegador y PostgreSQL temporal / local | 100% | Cada material debe identificarse | Registro MT-01 | HU-MAT-001 | DEFINIDA |
| MT-02 | Operativa | Trazabilidad | Medir Origen pieza sobrante | relaciones trazables / evaluadas * 100 | % | T | navegador y PostgreSQL temporal / local | 100% | Reconstruir cada relacion | Registro MT-02 | HU-MAT-001 | DEFINIDA |

## Protocolos

Antes de medir: versionar dataset, oraculo, codigo, configuracion, sistema, responsable y comando exacto. Registrar datos crudos, numerador, denominador, exclusiones, fecha y resultados por caso. Una repeticion por caso y configuracion para pruebas deterministas; repetir fallos para diagnostico sin borrar resultados. Si faltan fixtures, instrumentos o umbrales, reportar pendiente. No usar produccion. Para metas numericas, PASS si se satisface la meta con todos los casos criticos previstos ejecutados; si no, FAIL. Sin umbral, informar valor y no evaluar PASS/FAIL.

- F: con base temporal y casos criticos versionados ejecutar desde backend la suite de [testing](../testing/README.md), una vez; capturar PASS, FAIL y omitidos. Calcular MF-01. Los casos deben tener oraculo independiente.
- G: versionar patrones y dimensiones de fuente, margen, separacion y rotacion; desde backend ejecutar `python -m pytest -q tests/optimization` como indica [TA-007](../specs/SPEC-TA-007-validacion-geometrica.md). Comprobar cada patron sin solapamiento, dentro de fuente y con margen, separacion y rotacion permitidos; registrar resultados. Si falta cobertura, completar casos en TA-QA-003 antes de medir.
- H: definir casos y empates con seleccion esperada para FF, BF, WF, M4, M5 y M6; TA-QA-003 debe versionar y ejecutar sus pruebas pytest concretas una vez por motor y registrar seleccion y politica. No exigir que un metodo sea siempre superior. Sin oraculo o prueba, pendiente.
- P: Linux aislado; registrar CPU, RAM, limites, concurrencia, semilla y datos para 10, 25, 50, 100, 150 y 200 piezas. Ejecutar al menos 100 repeticiones por escala para p95; registrar inicio, fin, validez, plazo, estado y RSS de proceso y descendientes con muestras sincronizadas. Como punto de partida existe `backend/scripts/benchmark_load_engines.py` en esta base; TA-QA-002 debe definir los datasets y comando, y adaptar la captura si el script no proporciona los datos requeridos. Registrar intervalo de muestreo; RSS agregado no es tracemalloc ni RAM total. Una ejecucion completa es valida y termina dentro del plazo acordado previamente. Capacidad es solo la mayor escala observada que cumple la regla.
- U: versionar guion y datos de prueba para crear e importar pedido, gestionar inventario, optimizar y confirmar resultado. TA-QA-005 fija participantes, muestra y catalogo de errores; al menos un intento por escenario y participante. Registrar cronometro, exito, errores, pasos de teclado y transiciones de foco visibles y predecibles. Conservar observaciones anonimizadas.
- C: acordar versiones y dimensiones; candidatos Chrome y Edge desktop, Chrome viewport movil y tablet. Ejecutar `npm run test:e2e` en frontend y completar manualmente con DevTools para cada flujo critico y combinacion, una vez. Registrar resultados y capturas reales. Emulacion no equivale a dispositivo fisico; no se declara soporte Firefox.
- M: registrar commit y exclusiones; ejecutar pytest conforme a testing README. Cobertura requiere herramienta y configuracion verificables; duplicacion y complejidad requieren seleccionar herramienta reproducible en TA-QA-007. Para CI registrar estados y URL de ejecuciones terminadas del mismo workflow y rama en ventana fijada antes de medir; excluir canceladas y pendientes con conteo. Una captura por revision.
- S: versionar casos invalidos etiquetados por oraculo independiente para solapamiento, salida de fuente, margen y separacion; ejecutar `python -m pytest -q tests/optimization` desde backend y pruebas adicionales de rechazo real que TA-QA-009 defina, una vez por caso; registrar aceptacion, rechazo y restricciones. Si no se prueba el punto de aceptacion, pendiente.
- T: PostgreSQL temporal con pedidos, materiales, piezas y sobrantes conocidos; una ejecucion por relacion. Cotejar codigos visibles y vinculos de origen, pieza y sobrante en interfaz y consultas de solo lectura documentadas por HU-MAT-001; registrar IDs y datos semilla. Si falta funcionalidad o consulta, pendiente.

## Trazabilidad

| Metricas | Tarea productora | Responsable indicado |
|---|---|---|
| Definicion de todas | TA-QA-001 | Andro |
| MP-01 a MP-06 | TA-QA-002 | Melendez / Luis |
| MF-01 a MF-03 | TA-QA-003 | Andro / Melendez |
| MU-01 a MU-05 | TA-QA-005 | Luis |
| MM-01 a MM-04 | TA-QA-007 | Melendez |
| MC-01 a MC-03 | TA-QA-008 | Andro |
| MS-01 a MS-03 | TA-QA-009 | Melendez / Luis |
| MT-01 y MT-02 | HU-MAT-001 | Andro / Melendez |
| Consolidacion | TA-QA-010 | Todo el equipo |

Antecedentes: [TA-007 geometrica](../specs/SPEC-TA-007-validacion-geometrica.md). TA-044 se consulto en la base historica `integration/sprint-01`, pero sus archivos no estan en `integration-02` y no constituyen baseline comparable aqui. Local funcional Windows/WSL cuando aplique; supervisor y motores en Linux; CI en GitHub Actions Ubuntu. Staging no es necesario para estas propuestas.
