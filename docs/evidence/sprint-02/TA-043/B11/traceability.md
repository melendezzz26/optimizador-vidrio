# Matriz final de trazabilidad TA-043

Estados: **CUMPLIDO**, **CONDICIONADO**, **PARCIAL** o **PENDIENTE**. Las
pruebas repetidas no se cuentan dos veces.

| ID | Criterio | Prueba/evidencia | Estado | Observación |
|---|---|---|---|---|
| RF-01 | Captura común para seis motores | B05/B06/B09, hashes B10 | CUMPLIDO | Entrada congelada |
| RF-02 | Catálogo e identidades | B01/B03 | CUMPLIDO | v1/v2 separados |
| RF-03 | Estados de seis ejecuciones | B05/B09 | CUMPLIDO | Un worker |
| RF-04 | Parciales, fallos y diagnósticos | B03/B05/B09 | CUMPLIDO | M6 conserva causas |
| RF-05 | Métricas coherentes | B07/B09/B10 | CUMPLIDO | Sin exigir distribuciones iguales |
| RF-06 | Visualización 2D/3D | B07/B09 | CUMPLIDO | Escritorio/móvil |
| RF-07 | Selección elegible | B08/B09 | CUMPLIDO | Manual |
| RF-08 | Delta exclusivo seleccionado | B08/B09 | CUMPLIDO | Sin consumo al seleccionar |
| RF-09 | Recibo e idempotencia | B06/B08/B09 | CUMPLIDO | Reintento sin doble descuento |
| RF-10 | Conflicto y rollback | B08/B09 | CUMPLIDO | Stock/concurrencia |
| RF-11 | Historia v1/FF | B02/B06/B09 | CUMPLIDO | `/runs` conservado |
| RF-12 | Perfiles y acceso cruzado | B01/B06/B07 | CUMPLIDO | Permisos verificados |
| RF-13 | Migración/FK/unicidad | B02/B06/B08 | CUMPLIDO | Downgrade protegido |
| RF-14 | Persistencia sin cardinalidad v2 fija | B01–B06 | CUMPLIDO | Seis métodos |
| RF-15 | Regresión HF | B03/B09 | CUMPLIDO | Guard/fallback |
| RF-16 | Paridad BRF/score | B03/B09 | CUMPLIDO | Desempates preservados |
| RF-17 | Paridad BS-2 | B03/B09/B10 | CUMPLIDO | Ancho 2 y límites |
| RF-18 | Callbacks provisional/final | B03/B07/B09 | CUMPLIDO | M6 diagnosticado |
| RF-19 | Recuperación sin recálculo | B06/B07/B08/B09 | CUMPLIDO | Permisos/identidades |
| RF-20 | Pedidos HU-018 mixtos | SPEC CA-20 | CONDICIONADO | HU-018 fuera de la base |
| RNF-01 | Aislamiento y máscaras | B01/B04/B05 | CUMPLIDO | Cruces rechazados |
| RNF-02 | Cotas reales | B04/B05/B10 | CUMPLIDO | Solo cargas medidas |
| RNF-03 | Cierre antes de admisión | B04/B05/B10 | CUMPLIDO | Limpieza observada |
| RNF-04 | Accesibilidad/móvil | B07/B09 | CUMPLIDO | Evidencia frontend |
| RNF-05 | Determinismo/regresión | B03/B09/B10 | CUMPLIDO | Variación diagnóstica permitida |
| RNF-06 | Trazabilidad y smoke real | B09/B10/B11 | CUMPLIDO | Aprobación formal pendiente |
| SM-01 | Arranque/readiness/login real | B07/B09 | CUMPLIDO | PostgreSQL aislado |
| SM-02 | POST/GET v2 y seis IDs | B06/B09 | CUMPLIDO | Terminal recuperable |
| SM-03 | Estados por ejecución | B05/B09 | CUMPLIDO | Independientes |
| SM-04 | Resultados y capturas UI | B07/B09 | CUMPLIDO | 2D/3D |
| SM-05 | Selección manual y recarga | B08/B09 | CUMPLIDO | Sin elección automática |
| SM-06 | Delta/recibo/idempotencia | B08/B09 | CUMPLIDO | Un solo consumo |
| SM-07 | Inventario intacto antes de confirmar | B08/B09 | CUMPLIDO | Verificado |
| SM-08 | Historia legacy | B02/B06/B09 | CUMPLIDO | v1 y `/runs` |
| SM-09 | Motor fallido y cinco consultables | B05/B09 | CUMPLIDO | Integración/fallo controlado |
| SM-10 | PID, supervisor y limpieza | B05/B09/B10 | CUMPLIDO | Sin huérfanos |

Las 36 filas corresponden a 20 RF, 6 RNF y 10 SM; los 36 CA del SPEC se
trazan uno a uno mediante la relación RF/RNF/SM → CA.

