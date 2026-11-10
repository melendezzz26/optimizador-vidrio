# TA-QA-001 ? Matriz de m?tricas de calidad

Responsable: Andro Joseph Quispe Cesias. **Pendiente de validaci?n final con el modelo de calidad consolidado por Fabricio Aguilar Chavez.** No se encontr? modelo QA consolidado en la documentaci?n de la base auditada. IDs y responsables del backlog proceden del encargo y requieren cotejo con Notion.

[ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) y [ISO/IEC 25023:2016](https://www.iso.org/standard/35747.html) son marcos de referencia de ediciones distintas. Las f?rmulas son propuestas operativas, no transcripciones normativas. ISO 25023 no fija umbrales universales; todas las metas son propuestas del proyecto. No se afirma certificaci?n, conformidad ni acreditaci?n. Subcaracter?sticas orientativas pendientes de validaci?n.

Usabilidad/accesibilidad del backlog se relaciona con Interaction capability; compatibilidad/flexibilidad con Compatibility y Flexibility; seguridad operacional con Safety, distinta de ciberseguridad. Trazabilidad es indicador operativo, no caracter?stica ISO independiente. Seguridad de la informaci?n no est? evaluada.

Estados: DEFINIDA = ficha creada; BASELINE DISPONIBLE = datos comparables verificados; PENDIENTE DE MEDICI?N = ejecuci?n programada; MEDIDA = resultado registrado; VALIDADA = resultado revisado. Todas las filas est?n DEFINIDAS, pendientes de medici?n espec?fica. Baseline significa registrar el valor sin PASS/FAIL cuantitativo hasta acordar umbral. Denominador cero significa no evaluable, nunca PASS.

| ID | Caracter?stica | Subcaracter?stica orientativa | M?trica y objetivo | F?rmula | Unidad | Procedimiento | Herramienta y ambiente | Meta | Justificaci?n | Evidencia esperada | Tarea | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MF-01 | Funcional | Correcci?n | Medir Casos correctos | PASS / ejecutados ? 100 | % | F | pytest / local Linux | 100% cr?ticos | Requisitos indispensables | Registro MF-01 | TA-QA-003 | DEFINIDA |
| MF-02 | Funcional | Correcci?n | Medir Validez geom?trica | patrones v?lidos / generados ? 100 | % | G | pytest / local Linux | 100% cr?ticos | Un patr?n inv?lido causa cortes incorrectos | Registro MF-02 | TA-QA-003 | DEFINIDA |
| MF-03 | Funcional | Correcci?n | Medir Pol?tica de FF BF WF M4 M5 M6 | casos de pol?tica correctos / evaluados ? 100 | % | H | pytest / local Linux | 100% controlados | Cada motor debe cumplir su pol?tica | Registro MF-03 | TA-QA-003 | DEFINIDA |
| MP-01 | Desempe?o | Tiempo | Medir Latencia | fin menos inicio | ms | P | benchmark y procfs / Linux | Baseline | Depende del ambiente | Registro MP-01 | TA-QA-002 | DEFINIDA |
| MP-02 | Desempe?o | Tiempo | Medir p50 | valor ordenado en posici?n ceil(0,50 ? n) | ms | P | benchmark y procfs / Linux | Baseline | Depende del ambiente | Registro MP-02 | TA-QA-002 | DEFINIDA |
| MP-03 | Desempe?o | Tiempo | Medir p95 | valor ordenado en posici?n ceil(0,95 ? n), n ? 100 | ms | P | benchmark y procfs / Linux | Baseline | Muestra insuficiente si n menor de 100 | Registro MP-03 | TA-QA-002 | DEFINIDA |
| MP-04 | Desempe?o | Recursos | Medir Pico RSS | m?ximo de sumas de RSS sincronizadas de proceso y descendientes | MiB | P | benchmark y procfs / Linux | Baseline | Depende del ambiente | Registro MP-04 | TA-QA-002 | DEFINIDA |
| MP-05 | Fiabilidad | Continuidad | Medir Ejecuciones completas | completas v?lidas / iniciadas ? 100 | % | P | benchmark y procfs / Linux | Baseline | Depende de plazo y carga | Registro MP-05 | TA-QA-002 | DEFINIDA |
| MP-06 | Desempe?o | Capacidad | Medir Capacidad observada | mayor escala con todas las repeticiones completas y v?lidas | piezas | P | benchmark y procfs / Linux | Baseline | No implica m?ximo universal | Registro MP-06 | TA-QA-002 | DEFINIDA |
| MU-01 | Interacci?n | Operabilidad | Medir Tareas completadas | completadas / intentadas ? 100 | % | U | navegador y cron?metro / local | Baseline | Depende de muestra | Registro MU-01 | TA-QA-005 | DEFINIDA |
| MU-02 | Interacci?n | Operabilidad | Medir Tiempo por tarea | fin menos inicio por intento | s | U | navegador y cron?metro / local | Baseline | Depende de muestra | Registro MU-02 | TA-QA-005 | DEFINIDA |
| MU-03 | Interacci?n | Errores | Medir Tasa de errores | intentos con error / intentos ? 100 | % | U | navegador y cron?metro / local | Baseline | Definir cat?logo antes de medir | Registro MU-03 | TA-QA-005 | DEFINIDA |
| MU-04 | Interacci?n | Accesibilidad | Medir Navegaci?n por teclado | pasos accesibles / pasos evaluados ? 100 | % | U | navegador y cron?metro / local | 100% cr?ticos | Acceso sin rat?n a tareas cr?ticas | Registro MU-04 | TA-QA-005 | DEFINIDA |
| MU-05 | Interacci?n | Accesibilidad | Medir Foco correcto | transiciones correctas / transiciones evaluadas ? 100 | % | U | navegador y cron?metro / local | 100% cr?ticas | Foco visible y predecible | Registro MU-05 | TA-QA-005 | DEFINIDA |
| MC-01 | Compatibilidad | Coexistencia | Medir Navegadores | combinaciones exitosas / evaluadas ? 100 | % | C | Playwright y DevTools / local | 100% acordadas | Evitar fallos en entornos objetivo | Registro MC-01 | TA-QA-008 | DEFINIDA |
| MC-02 | Flexibilidad | Adaptabilidad | Medir Responsive | pantallas sin p?rdida / pantallas evaluadas ? 100 | % | C | Playwright y DevTools / local | 100% cr?ticas | Mantener controles accesibles | Registro MC-02 | TA-QA-008 | DEFINIDA |
| MC-03 | Flexibilidad | Adaptabilidad | Medir Flujos por viewport | flujos exitosos / flujos evaluados ? 100 | % | C | Playwright y DevTools / local | 100% cr?ticos | Conservar tareas esenciales | Registro MC-03 | TA-QA-008 | DEFINIDA |
| MM-01 | Mantenibilidad | Testabilidad | Medir Cobertura | l?neas ejecutadas / l?neas medibles ? 100 | % | M | pytest y Actions / CI Ubuntu | Baseline | No hay umbral acordado | Registro MM-01 | TA-QA-007 | DEFINIDA |
| MM-02 | Mantenibilidad | Modularidad | Medir Duplicaci?n | l?neas duplicadas / l?neas analizadas ? 100 | % | M | pytest y Actions / CI Ubuntu | Baseline | Herramienta pendiente | Registro MM-02 | TA-QA-007 | DEFINIDA |
| MM-03 | Mantenibilidad | Analizabilidad | Medir Complejidad | complejidad ciclom?tica por funci?n | n?mero | M | pytest y Actions / CI Ubuntu | Baseline | Herramienta pendiente | Registro MM-03 | TA-QA-007 | DEFINIDA |
| MM-04 | Mantenibilidad | Testabilidad | Medir CI | ejecuciones exitosas / terminadas ? 100 | % | M | pytest y Actions / CI Ubuntu | Baseline | No hay umbral acordado | Registro MM-04 | TA-QA-007 | DEFINIDA |
| MS-01 | Seguridad operacional | Restricci?n | Medir Rechazo de inv?lidos | inv?lidos rechazados / inv?lidos evaluados ? 100 | % | S | pytest / local Linux | 100% | Cada inv?lido debe rechazarse | Registro MS-01 | TA-QA-009 | DEFINIDA |
| MS-02 | Seguridad operacional | Restricci?n | Medir Falsa aceptaci?n | inv?lidos aceptados / inv?lidos evaluados ? 100 | % | S | pytest / local Linux | 0% | Una aceptaci?n inv?lida supone riesgo | Registro MS-02 | TA-QA-009 | DEFINIDA |
| MS-03 | Seguridad operacional | Restricci?n | Medir Margen y separaci?n | patrones que cumplen ambos / evaluados ? 100 | % | S | pytest / local Linux | 100% | Respetar restricciones de corte | Registro MS-03 | TA-QA-009 | DEFINIDA |
| MT-01 | Operativa | Trazabilidad | Medir Material identificable | materiales con c?digo visible / utilizados ? 100 | % | T | navegador y PostgreSQL temporal / local | 100% | Cada material debe identificarse | Registro MT-01 | HU-MAT-001 | DEFINIDA |
| MT-02 | Operativa | Trazabilidad | Medir Origen pieza sobrante | relaciones trazables / evaluadas ? 100 | % | T | navegador y PostgreSQL temporal / local | 100% | Reconstruir cada relaci?n | Registro MT-02 | HU-MAT-001 | DEFINIDA |

## Protocolos

Antes de medir: versionar dataset, or?culo, c?digo, configuraci?n, sistema, responsable y comando exacto. Registrar datos crudos, numerador, denominador, exclusiones, fecha y resultados por caso. Una repetici?n por caso y configuraci?n para pruebas deterministas; repetir fallos para diagn?stico sin borrar resultados. Si faltan fixtures, instrumentos o umbrales, reportar pendiente. No usar producci?n. Para metas num?ricas, PASS si se satisface la meta con todos los casos cr?ticos previstos ejecutados; si no, FAIL. Sin umbral, informar valor y no evaluar PASS/FAIL.

- F: con base temporal y casos cr?ticos versionados ejecutar desde backend la suite de [testing](../testing/README.md), una vez; capturar PASS, FAIL y omitidos. Calcular MF-01. Los casos deben tener or?culo independiente.
- G: versionar patrones y dimensiones de fuente, margen, separaci?n y rotaci?n; desde backend ejecutar `python -m pytest -q tests/optimization` como indica [TA-007](../specs/SPEC-TA-007-validacion-geometrica.md). Comprobar cada patr?n sin solapamiento, dentro de fuente y con margen, separaci?n y rotaci?n permitidos; registrar resultados. Si falta cobertura, completar casos en TA-QA-003 antes de medir.
- H: definir casos y empates con selecci?n esperada para FF, BF, WF, M4, M5 y M6; TA-QA-003 debe versionar y ejecutar sus pruebas pytest concretas una vez por motor y registrar selecci?n y pol?tica. No exigir que un m?todo sea siempre superior. Sin or?culo o prueba, pendiente.
- P: Linux aislado; registrar CPU, RAM, l?mites, concurrencia, semilla y datos para 10, 25, 50, 100, 150 y 200 piezas. Ejecutar al menos 100 repeticiones por escala para p95; registrar inicio, fin, validez, plazo, estado y RSS de proceso y descendientes con muestras sincronizadas. Usar benchmark existente en `experiments/optimization/benchmark_capacity.py`; TA-QA-002 debe fijar comando y adaptar captura si no proporciona esos datos. Registrar intervalo de muestreo; RSS agregado no es tracemalloc ni RAM total. Una ejecuci?n completa es v?lida y termina dentro del plazo acordado previamente. Capacidad es solo la mayor escala observada que cumple la regla.
- U: versionar guion y datos de prueba para crear e importar pedido, gestionar inventario, optimizar y confirmar resultado. TA-QA-005 fija participantes, muestra y cat?logo de errores; al menos un intento por escenario y participante. Registrar cron?metro, ?xito, errores, pasos de teclado y transiciones de foco visibles y predecibles. Conservar observaciones anonimizadas.
- C: acordar versiones y dimensiones; candidatos Chrome y Edge desktop, Chrome viewport m?vil y tablet. Ejecutar `npm run test:e2e` en frontend y completar manualmente con DevTools para cada flujo cr?tico y combinaci?n, una vez. Registrar resultados y capturas reales. Emulaci?n no equivale a dispositivo f?sico; no se declara soporte Firefox.
- M: registrar commit y exclusiones; ejecutar pytest conforme a testing README. Cobertura requiere herramienta y configuraci?n verificables; duplicaci?n y complejidad requieren seleccionar herramienta reproducible en TA-QA-007. Para CI registrar estados y URL de ejecuciones terminadas del mismo workflow y rama en ventana fijada antes de medir; excluir canceladas y pendientes con conteo. Una captura por revisi?n.
- S: versionar casos inv?lidos etiquetados por or?culo independiente para solapamiento, salida de fuente, margen y separaci?n; ejecutar `python -m pytest -q tests/optimization` desde backend y pruebas adicionales de rechazo real que TA-QA-009 defina, una vez por caso; registrar aceptaci?n, rechazo y restricciones. Si no se prueba el punto de aceptaci?n, pendiente.
- T: PostgreSQL temporal con pedidos, materiales, piezas y sobrantes conocidos; una ejecuci?n por relaci?n. Cotejar c?digos visibles y v?nculos de origen, pieza y sobrante en interfaz y consultas de solo lectura documentadas por HU-MAT-001; registrar IDs y datos semilla. Si falta funcionalidad o consulta, pendiente.

## Trazabilidad

| M?tricas | Tarea productora | Responsable indicado |
|---|---|---|
| Definici?n de todas | TA-QA-001 | Andro |
| MP-01 a MP-06 | TA-QA-002 | Melendez / Luis |
| MF-01 a MF-03 | TA-QA-003 | Andro / Melendez |
| MU-01 a MU-05 | TA-QA-005 | Luis |
| MM-01 a MM-04 | TA-QA-007 | Melendez |
| MC-01 a MC-03 | TA-QA-008 | Andro |
| MS-01 a MS-03 | TA-QA-009 | Melendez / Luis |
| MT-01 y MT-02 | HU-MAT-001 | Andro / Melendez |
| Consolidaci?n | TA-QA-010 | Todo el equipo |

Antecedentes: [TA-044 capacidad](../specs/SPEC-TA-044-pruebas-capacidad-estres.md), [evidencia TA-044](../evidence/sprint-02/TA-044/capacity_benchmark_results.json), [TA-007 geom?trica](../specs/SPEC-TA-007-validacion-geometrica.md). Local funcional Windows/WSL cuando aplique; supervisor y motores en Linux; CI en GitHub Actions Ubuntu. Staging no es necesario para estas propuestas.
