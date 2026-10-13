# SPEC-TA-005-TA-006 — Rasterización de piezas estándar y personalizadas

Estado: Implemented
PBI relacionado: TA-005 T01 (rasterización estándar) y TA-006 T01 (rasterización personalizada) · EN-004
Responsable: Fabricio A.
Dependencias: SP-001 (resolución 5 mm), spike de costo de rasterización (regla conservadora), HU-007 T02/T03 (formato y convexidad de vertices_mm)

## 1. Objetivo

Convertir cada pieza del pedido (rectángulo, circunferencia o polígono convexo) en una máscara raster
binaria, reproducible y conservadora, a la resolución configurada, para que la validación geométrica
(TA-007) y la integración de instancia (TA-008) trabajen sobre celdas en lugar de geometría continua.

## 2. Alcance

Incluye:
- Clase de dominio `RasterMask` (máscara binaria inmutable).
- Rasterización de `POLIGONO_CONVEXO` (TA-006), `RECTANGULO` y `CIRCUNFERENCIA` (TA-005).
- Punto de entrada que recibe la `geometria` tal como la persiste el módulo de pedidos.
- Pruebas unitarias y script de evidencia en `experiments/raster/`.

Fuera de alcance:
- Rotación de piezas (TA-016 / SP-003).
- Límites, superposición, separación y margen (TA-007).
- Construcción de la instancia completa con stock (TA-008).
- API, base de datos, migraciones y frontend: no hay cambios.

## 3. Actor y precondiciones

- Actor: el motor de optimización (código del backend); no hay interacción directa del usuario.
- Precondiciones: la geometría ya fue validada por el módulo de pedidos (medidas positivas y finitas;
  polígono cerrado y convexo según HU-007 T03).

## 4. Entradas / datos

| Campo | Unidad | Formato | Regla |
|---|---|---|---|
| `geometria.type` | — | `RECTANGULO` · `CIRCUNFERENCIA` · `POLIGONO_CONVEXO` | Igual que en `orders` |
| `width_mm`, `height_mm` | mm | número | > 0 y finito |
| `radius_mm` | mm | número | > 0 y finito |
| `vertices_mm` | mm | lista de pares `[x, y]`, sin repetir el primero al final | ≥ 3 vértices; puede tener coordenadas negativas; Y crece hacia abajo (HU-007 T02) |
| `resolution_mm` | mm por celda | número | > 0 y finito; valor por defecto 5 mm (SP-001) |

## 5. Reglas de negocio

- **RN-01 Regla conservadora:** una celda se marca ocupada si la figura cubre un área positiva de ella.
  Tocar solo el borde o una esquina de la celda no la ocupa. Así ninguna parte de la pieza queda fuera de la máscara.
- **RN-02 Origen:** la caja envolvente de la figura se traslada a (0, 0). La fila 0 corresponde a la Y mínima
  y la columna 0 a la X mínima, con Y hacia abajo como en `vertices_mm`.
- **RN-03 Tamaño:** la máscara mide `ceil(ancho / resolución)` columnas por `ceil(alto / resolución)` filas.
- **RN-04 Coma flotante:** las coordenadas se redondean a 0.000001 mm antes de rasterizar.
- **RN-05 Determinismo:** la misma entrada produce siempre la misma máscara. El sentido de recorrido
  (horario o antihorario) y la traslación del polígono no cambian el resultado.
- **RN-06 Dominio puro:** el código no importa FastAPI, SQLAlchemy ni librerías externas, y no modifica la entrada.
- **RN-07 Piezas delgadas:** una pieza más delgada que una celda ocupa al menos una fila o columna completa;
  el error de área crece (spike: tira de 30 mm a 20 mm → 33 %). La resolución no debe superar la dimensión mínima de las piezas.

## 6. Flujo principal

1. El motor recibe la `geometria` de una pieza y la resolución.
2. Se elige el rasterizador según `geometria.type`.
3. Se normalizan las coordenadas (RN-02, RN-04).
4. Se recorre la figura fila por fila y se calcula el tramo de columnas ocupadas (RN-01).
5. Se devuelve una `RasterMask` inmutable.

## 7. Flujos alternativos / errores

- Resolución, medida o coordenada no positiva o no finita → `RasterizationError` con mensaje en español.
- Polígono con menos de 3 vértices o vértices mal formados → `RasterizationError`.
- `type` desconocido → `RasterizationError`.
- `RasterizationError` deriva de `ValueError`; el dominio no expone detalles técnicos al cliente.

## 8. Criterios de aceptación

| CA | Criterio |
|---|---|
| CA-01 | Un rectángulo de 800 × 600 mm a 5 mm genera 160 × 120 celdas y exactamente 19 200 ocupadas. |
| CA-02 | Un rectángulo cuyas medidas no son múltiplo de la resolución se cubre por exceso (802 mm → 161 columnas). |
| CA-03 | Una circunferencia de radio 500 mm a 5 mm genera 200 × 200 celdas, con error de área entre 0 % y 1.5 %. |
| CA-04 | Un polígono convexo válido genera una máscara binaria cuyo error de área está entre 0 % y 1.5 % a 5 mm (hexágono de prueba). |
| CA-05 | Ningún punto interior de la figura cae en una celda libre (regla conservadora), comprobado con una malla de puntos. |
| CA-06 | Trasladar el polígono o invertir su sentido de recorrido produce la misma máscara. |
| CA-07 | El punto de entrada acepta las tres `geometria` que persiste el módulo de pedidos. |
| CA-08 | Entradas inválidas lanzan `RasterizationError`. |
| CA-09 | La máscara expone resolución, filas, columnas, consulta de celda, cantidad de celdas ocupadas y área en mm², para ser consumida por TA-007. |

## 9. Impacto técnico

- Módulos: `backend/app/modules/optimization/domain/` (`raster_mask.py`, `rasterizer.py`).
- API: no aplica.
- BD / migración: no aplica.
- UI: no aplica.
- Experimentos: `experiments/raster/scripts/` (script de evidencia; resultados no versionados).

## 10. Pruebas previstas

- `backend/tests/optimization/test_raster_mask.py`: construcción, consultas e inmutabilidad de la máscara.
- `backend/tests/optimization/test_rasterizer.py`: CA-01 a CA-08.
- Comando: `python -m pytest -q tests/optimization`.

## 11. Evidencias requeridas

- Salida de pytest.
- Tabla de área real frente a área rasterizada por figura y resolución.
- Representación visual de las máscaras (texto o imagen).
- Ubicación: `docs/evidence/sprint-01/TA-005-TA-006/`.

## 12. Decisiones / notas

- **Representación:** cada fila de la máscara se guarda como un entero de Python usado como mapa de bits (spike: entre 40 y 55 veces menos memoria que una lista de listas). Permite que TA-007 detecte superposición con una operación AND por fila.
- **Sin dependencias nuevas:** solo biblioteca estándar; agregar NumPy u otra librería requeriría ADR.
- **D-01 (decisión del responsable, a validar en el PR):** el sistema solo tiene dos formas estándar (`RECTANGULO` y `CIRCUNFERENCIA`, HU-006 T03). El criterio "al menos otra forma estándar" de TA-005 se cubre con el polígono convexo de TA-006, que comparte rasterizador.
- **D-02 (decisión del responsable, a validar con TA-007):** la máscara expone `rows` (bits por fila), `columns`, `row_count`, `resolution_mm`, `is_occupied`, `occupied_cells` y `area_mm2`. Si TA-007 necesita algo adicional, se agrega sin romper este contrato.
- **D-03:** la resolución se recibe como parámetro; su lectura desde la configuración versionada queda para RN-001.

## 13. Estado de implementación

| Tarea | Estado | Evidencia |
|---|---|---|
| TA-006 T01 — Polígono convexo | Implemented | docs/evidence/sprint-01/TA-005-TA-006/ |
| TA-005 T01 — Rectángulo y circunferencia | Implemented | docs/evidence/sprint-01/TA-005-TA-006/ |

- La SPEC no pasó por revisión antes de implementar porque el equipo no estaba disponible; D-01 y D-02 se validan en la revisión del PR.
- El backlog indica no iniciar hasta completar TA-035 T02 (smoke de staging). Se avanzó con el paso de validación de stock
  bloqueado por HU-008, que no está implementada; la rasterización no depende de HU-008 (se integran recién en TA-008).
- Pasa a **Verified** cuando un reviewer distinto del autor apruebe el PR.