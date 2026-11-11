# Auditoría TA-QA-010

Corte: 2026-11-11. Solo lectura de fuentes y generación documental; sin ejecutar pruebas del producto.

## Ownership
EN-REPO-001 PLAN mantiene estrategia compartida pendiente; MIGRATION en ambos repos conserva evidencia histórica en legado. Se utiliza provisionalmente optimizador-vidrio/integration-02 por instrucción del encargo. No se duplica informe.

## Repositorios y ramas

### optimizador-vidrio

| Rama | SHA |
|---|---|
| backup/pre-separacion-2026-11-10 | 137f2ccd7a542c73e99fd40a792287595cdcd9c8 |
| docs/EN-REPO-001-separacion-repositorios | b8b55ad831c229dfefc321747003da686d8a1a60 |
| docs/EN-UX-001-ui-auditorias | 61aa7193e81f0488021b9a9bcc8cef14dda27d6b |
| docs/EN-UX-002-inspector-piezas | 76682461ef2f93d19f0121a5040020f70b61a52c |
| docs/EN-UX-004-cancelacion-segura | 8c1e89d97a3902da3c175d39a026c24d30bcf753 |
| docs/HU-VENT-001-analisis-plancha-completa | a30641b4af19dd2718fea121f8214ec6808060e4 |
| docs/S2-TA-QA-001-metricas-iso25023 | ea5399adca0810feb72f421f137f50498c8527e0 |
| docs/fix-TA-QA-001-formulas-metricas | f3ac2616754f05cab8fa2e6e194f9e39156dea30 |
| enabler/S2-ENQA001-modelo-calidad-iso25010 | b231010fc405113c21176380437c087f40d7a325 |
| feature/EN-REPO-001-extraccion | 9325e0df6d4dcea206ad7e8b061deb757b9de26b |
| integration-02 | 02bc2ef97411eaf00e56104cc9f82cd983b18fb4 |
| main | 9a890d1b90d381ea1ccf76cc7212f371fc2feb94 |
| qa/TA-QA-002-rendimiento-carga | 820779c4377012a849e0402f1f92a638710705a5 |
| qa/TA-QA-005-usabilidad-accesibilidad | 3bf682056cb4bfe56214d545dd05faf866370cf7 |
| qa/TA-QA-009-seguridad-operacional-corte | 06d2df49e0b24c44073d56f79ca6e6d442bcbbfc |
| test/S2-TA-QA-006-seguridad-permisos | 45578f65fea8665854c09d84245ba1c8ddc320cd |
| test/S2-TA-QA-008-compatibilidad-flexibilidad | 53b5e66ff2436f6d6d7f6f1a624660717e25bfcf |

### newglass-frontend

| Rama | SHA |
|---|---|
| ci/EN-REPO-001-e2e-backend-actual | 382db36cabe158d54dbb17c2c0fa1d737d85942f |
| feat/HU-MAT-001-trazabilidad-material | f1f4311d4df430779dbe34c930f034870a2521da |
| feature/EN-UX-001-resultados-operativos | d2a221a08ced752e8d2d7f845b612ef86815d223 |
| feature/EN-UX-002-inspector-piezas | a030f4842fec34446500f180de06175dddf0fd0e |
| feature/EN-UX-004-cancel-ui | 1dc56ab28df7b3709e84ccfdbb4e5719faf4ad42 |
| fix/CI-pages-use-preinstalled-postgres | 071bcdf088e3bc78e81416801b27f370c081b148 |
| fix/EN-UX-003-engine-identifiers | 8b448bc2569810f657a6781c4d0ea1bbd09ad16e |
| fix/EN-UX-003-historico-sin-mascaras | cbba36fa6d9e2b0f2d508ea9770f7c51001cd776 |
| fix/EN-UX-003-shell-background-language | 401071fe739d08d17230c126a9fc8c82433cc819 |
| fix/EN-UX-004-cancelled-operator-copy | f8d5c332c944d12b9050d9bf4c82f49d0987e28e |
| fix/EN-UX-004-explicit-cancel-success-title | b78211f55061eeeee483effef5679f227893c07e |
| import-history | 106ac88aa79e24c6ad2e97855886a45104a2b7ca |
| main | 1868759b733a5798cf47307d6c1dffbd730e43a0 |
| revert-3-feature/EN-UX-002-inspector-piezas | 852cb1a2bfdadee3dd3359c4ddfbb0b91cdb7c7d |
| test/S2-TA-QA-008-compatibilidad-flexibilidad | 54b852d49840983c724490e56d5b6ade00a807d6 |

### newglass-backend

| Rama | SHA |
|---|---|
| docs/EN-REPO-001-instrucciones-independientes | d20f609a3b9c5e7ce7a21dc57eb51252c8bbb1ad |
| feat/HU-MAT-001-trazabilidad-material | e5138a7aa9305021fb12746fe2fffc7324ff0042 |
| feature/EN-UX-004-cancel-intent | 85d431b0bf9a2b199a58b52a50c8c4058292694c |
| feature/EN-UX-004-cancel-supervisor | 8c328539392492fdb2995bcc7788306f40c4cf66 |
| import-history | c84b624872f9dda67c522a9ff4e69f86932b6a7e |
| main | 2afa9d72cecee74d4c61187ff15c74564e7dde3f |
| test/TA-QA-006-port-security-tests | 8d3e558b01b7d08530bd3cbe0014a00745c4c6c1 |

## Cobertura de búsqueda
Se revisaron los inventarios de docs, SPEC/PLAN/TASKS, evidencia y resultados en integration-02, main frontend/backend y ramas QA-002/005/009, EN-REPO-001, HU-VENT-001 y corrección QA-001. Se consultaron hasta 100 PR por repositorio (el inventario de legado cubre el período de Sprint 2). TA-QA-007 no tiene resultados específicos localizados; no se infiere ausencia de trabajo no publicado. HU-VENT-001 es análisis documental sin baseline de calidad usado en este informe.

## Hallazgos metodológicos
- Matriz: 26 metas conservadas, 19 porcentajes corregidos; PR #120 sin merge.
- Rendimiento: 36 grupos, 108 datos; n=3; p50 recalculado; p95 descartado para MP-03. Se conservan causas individuales, incluido M6/150 con TIME_BUDGET_EXCEEDED que el resumen agrupado no refleja.
- QA-005: PASS de foco/teclado inicializados; completitud de T-OPT-02 no depende de ejecutar selección. Sin datos crudos versionados localizados.
- QA-009: ocho grupos, con subcasos; excepciones de dominio no equivalen a rechazo E2E.
- Credenciales literales en arneses QA-005/009: no se reutilizan ni se copian; acción de saneamiento fuera de esta tarea.
- S2-WF-CARGA atribuye responsable a Aguilar. Melendez se acredita mediante PR #108 y ACADEMIC-800; HU-MAT-001 PR #5 backend es de AndroJQC.
- 564 PASS post-merge es evidencia narrativa en rama histórica no integrada; 554 dispone de JUnit. No sustituir ni sumar.

## Publicación
Rama exclusiva docs/S2-TA-QA-010-informe-cuantitativo-iso. Base integration-02. Draft por aportes pendientes. Reviewer formal solicitado: fabrilar1; revisión final grupal pendiente. Sin merge.
