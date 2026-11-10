# SPEC-ACADEMIC-800 — Comparación independiente de seis métodos, hasta 800 unidades

Estado: implementación para revisión. Solicitud: Fabricio, 08/11/2026.
Base: integration-02, 1277c742de2dc347fab49060b74726c03e8f4341.

## Objetivo y alcance

Evaluar FF, BF, WF, HF, M5 y M6 por separado sobre la misma solicitud e
inventario congelados. Admitir lotes de 600, 700 y 800 unidades físicas;
cantidad no equivale a 800 geometrías grandes distintas. Mantener las reglas
de material/espesor, rasterización, giros, márgenes y separación.

## Reglas

- M6 nunca completa su resultado con FF/BF u otro motor. Al agotar recursos
  devuelve exclusivamente la última frontera nativa completa y su causa.
- La búsqueda BS-2 mantiene dos estados y evalúa hasta doce sucesores por
  padre. Las propuestas recorren orientaciones y fuentes de forma determinista;
  fuentes vacías con el mismo layout se consideran simétricas. Se priorizan
  los giros ortogonales y después los demás giros configurados; cada
  fuente/orientación propone su primera posición factible. Sigue siendo
  una búsqueda acotada: no promete optimalidad ni cobertura de cualquier lote.
- La puntuación acotada prioriza cobertura y área colocada, cantidad y área
  de material usado, y menor envolvente ocupada; el desempate es determinista.
  Es una variante declarada de M6: no calcula el mayor rectángulo residual
  para cada candidato. Las métricas finales sí conservan su cálculo exacto.
- El presupuesto nativo de M6 es 110 s dentro de los 120 s del cálculo,
  con frontera de 2, 60 000 expansiones, 1 000 000 sondeos y 32 MiB de estado.
  Estos límites no sustituyen la cota de 256 MiB del proceso.
- La enumeración exhaustiva anterior se conserva como opción explícita de
  reproducción (`candidate_limit=None, positions_per_orientation=2`),
  con su puntuación residual anterior y sin respaldo cruzado. La política aplicada se registra.
- L-03 pasa de 300 a 800 unidades; 801 se rechaza antes de expandir cantidades.
  Permanecen los límites de geometrías/raster, stock y concurrencia.
- Los contratos de orden visual y sus consumidores admiten 800 referencias.
  Los eventos de comparación tienen una cota finita de 128 KiB; el flujo
  visual individual conserva su cota de 64 KiB.
- No se modifican datos remotos, inventario, roles ni configuraciones de corte.

## Capacidad con geometrías comerciales a 1 mm

- El recorrido exacto de posiciones puede saltar filas descartadas únicamente
  mientras las restricciones que prueban la imposibilidad sigan idénticas.
  La primera fila y columna factibles, el orden de giros y fuentes y los
  desempates siguen siendo los de cada método.
- Un cálculo puede reutilizar una consulta exacta para la misma máscara y el
  mismo layout inmutable. La memoria de consultas es acotada y sus referencias
  son débiles. M6 conserva el conteo lógico de sondeos y M5 calcula los scores
  de retazo cuando hay al menos dos fuentes en uso que compiten. El conteo
  exacto de celdas puede descartar una máscara que exceda el espacio libre.
- El cálculo de retazo máximo recorre los tramos libres de cada fila y conserva
  el histograma y los desempates de área, posición, ancho y alto.
- Los layouts inmutables pueden compartir enteros de filas con contenido
  idéntico. La separación, el margen y los bits ocupados se conservan.
  El recorrido compartido reserva filas ocupadas, filas de separación si
  se crean y filas de margen si no comparten la máscara del material. Las
  máscaras de material se contabilizan en la caché raster de TA-016.
  M6 contabiliza el grafo real por identidad y conserva sus dos alternativas
  y sus límites de estado, sondeos y tiempo.
- Comparar colocaciones, contornos, fuentes, giros, métricas y retazos en casos
  pequeños antes y después de cada ajuste. Medir también el pedido #61 y las
  800 unidades del CSV de auditoría con stock suficiente a 1 mm y 5°.

### Presupuesto de cálculo para pedidos grandes

- El runner v2 puede activar un plazo explícito con
  `NEWGLASS_COMPARISON_LARGE_SECONDS` para comparaciones de 200 unidades o más.
  Se usa el mismo plazo por método y un único trabajador secuencial. El umbral
  incluye la carga comercial reducida a 247 unidades. Los pedidos menores y
  los despliegues sin la variable conservan 120 s por método y 900 s globales.
- El plazo configurado se limita a 900 s por método. El total reserva además
  el arranque y la parada por motor. M6 usa el 90% del plazo para su búsqueda,
  con un mínimo de 110 s, y conserva su millón de sondeos y la cota de estado
  de 32 MiB. El resto del plazo permite calcular métricas y enviar el resultado.
- Se conservan la cuadrícula, el paso angular, los criterios de cada motor,
  el orden de desempate y los límites de memoria del perfil. El watchdog
  aplica el presupuesto elegido a partir de la entrada congelada. La
  persistencia y el cierre verificado siguen usando el flujo existente.

## Criterios de aceptación y evidencia

1. Pruebas de límites: 600/700/800 aceptadas; 801 rechazada en backend y UI.
2. Ningún agotamiento nativo de M6 se reinterpreta como COMPLETED/NO_FIT ni
   llama a First Fit. La confirmación de parciales sigue bloqueada.
3. Benchmark reproducible de 600/700/800 unidades mixtas, a 1 mm y 5°, con
   los seis adaptadores reales; registrar cobertura, causa, tiempo y memoria.
   No presentar un límite de admisión como garantía de completar todo lote.
4. Revalidar las colocaciones con el validador raster y calcular métricas.
5. Regresiones geométricas, de contratos, ejecución y límites pertinentes.

Sin migración de BD. Los resultados históricos con respaldo siguen siendo
legibles y conservan su identificación; no se reescriben como búsqueda pura.
El despliegue queda separado de la implementación y de las mediciones locales.
