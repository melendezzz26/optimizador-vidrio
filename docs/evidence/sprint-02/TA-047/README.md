# Evidencia TA-047

Autor y revisor académico: Andro Joseph Quispe Cesias. Sin aprobación de GitHub atribuida.

Base `7556a700496673d00fe41b6036d69d91d0939959`; rama `feature/S2-TA047-preflight-optimizacion`. La auditoría inicial está en `AUDIT-PRELIMINAR.md`.

Pruebas locales con Python del entorno virtual:

| Suite | Resultado |
| --- | --- |
| Preflight y aceptación individual | 14 aprobadas |
| Preparación y contratos | 46 aprobadas |
| Raster y placement | 137 aprobadas |
| Geometría, rotaciones y reglas comunes | 236 aprobadas |
| Pedidos unidad/API | 150 aprobadas, 99 omitidas |
| FF, BF, WF, M4, M5, M6 y TA-027 (unidad) | 190 aprobadas |
| API corrida y límites | 47 aprobadas, 27 omitidas |

Las omisiones corresponden a pruebas dependientes del entorno de base de datos; no equivalen a PASS. Las pruebas de dominio verifican además un ángulo no ortogonal en la grilla de 5°, círculos, polígonos, margen, separación, determinismo y stock sin mutación. El caso válido compara el resultado de First Fit antes y después de preflight; otra prueba comprueba que la aceptación seguida de cálculo llama una vez al motor. La aceptación rechazada no crea corrida ni cambia el pedido.

Medición exploratoria local, una ejecución por escenario, resolución 1 mm y paso 5°; tiempos en ms, no umbrales:

| Caso | Piezas | Fuentes disponibles / examinadas | Orientaciones solicitadas | Preflight | First Fit |
| --- | ---: | ---: | ---: | ---: | ---: |
| Válido | 1 | 1 / 1 | 1 | 0.644 | 0.803 |
| Imposible | 1 | 1 / 1 | 72 | 25.516 | 21.507 |
| Mixto | 3 | 1 / 3 | 74 | 22.202 | 23.504 |

Las fuentes examinadas cuentan consultas por pieza, no fuentes físicas distintas; las orientaciones cuentan llamadas al cache, no necesariamente máscaras únicas. Los resultados no demuestran que preflight sea siempre más rápido; su ventaja es evitar los motores y persistencia cuando falla en el flujo integrado. La medición no comprende comparación multimétodo ni acceso a base de datos.
