# TA-QA-003 - Smoke post-merge

PR #112 mergeado por fabrilar1 a integration-02 el 2026-11-10 04:31:12 UTC. Merge y HEAD comprobado: f46d96db9f5ca6071445bae5f884908aed734ff4. GitHub no muestra una review formal en la lista consultada; no se atribuye aprobacion.

En Windows, Python 3.13.17 y pytest 9.1.1, desde el HEAD integrado se repitieron los dos comandos de la evidencia original: bateria dirigida 50 passed in 0.96s; regresion relacionada 564 passed in 9.24s. El valor previo fue 554: entre ambas ejecuciones se integro el PR #109, que incorporo pruebas adicionales en archivos incluidos en la regresion. No se modifican los resultados previos.

CI post-merge: backend, frontend, E2E y Pages PASS en [workflow](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/42756377362). Las 26/26 comprobaciones de validez se limitan a los patrones seleccionados, con cajas envolventes conservadoras para el caso mixto. M6 demuestra exploracion acotada y reproducibilidad, no toda su funcion de puntuacion. La rama local y remota de TA-QA-003 se elimino tras verificaciones; el checkout aislado se reutiliza para TA-QA-008.
