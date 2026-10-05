# TA-003: dominio geométrico de retazos

- Fecha: 2026-10-04.
- SPEC: [API de inventario](../../../specs/SPEC-TA-003-api-inventario.md).
- Rama: `feature/TA-003-api-inventario`.
- Commit base consultado: `e2c0bdb7191104635c12305d51f97512f472f462`.
- Validación sobre cambios sin commit; Python 3.11.9 del entorno `backend/venv`.

## Alcance y decisiones

Solo dominio geométrico y pruebas unitarias. Sin cambios en modelos, migraciones,
autenticación, aplicación, API ni frontend. Sin conexiones remotas.

`calculate_area_mm2` valida las tres geometrías de la SPEC y devuelve `Decimal`
con dos decimales y `ROUND_HALF_UP`. `InvalidGeometryError` deriva de `ValueError`.
Se aceptan `int`, `Decimal` y `float` finitos (convertidos mediante `Decimal(str(value))`);
se rechazan booleanos y cadenas, incluso numéricas. El contexto decimal local
usa precisión calculada a partir de las entradas y una constante PI decimal.

Los polígonos admiten ambos sentidos de recorrido. La validación estricta por
semiplanos, O(n²), rechaza cruces, concavidad, vértices repetidos y colinealidad;
el primer vértice no se repite al final. El área se calcula por la fórmula del
cordón. La positividad se comprueba antes y después de cuantizar a dos decimales
con `ROUND_HALF_UP`: si el resultado es `0.00`, se lanza `InvalidGeometryError`.
Solo se retorna un `Decimal` con exactamente dos decimales en el intervalo
`[0.01, 9999999999999999.99]`, conforme a `NUMERIC(18,2)` y `CHECK area_mm2 > 0`
de NewGlass v1.1. El máximo inclusivo se define en el dominio mediante
`MAX_AREA_MM2 = Decimal("9999999999999999.99")`, sin consultar infraestructura;
si el área cuantizada lo supera se lanza `InvalidGeometryError`. Un área matemática
de `0.005 mm²` produce `0.01` y se acepta. Los campos adicionales se ignoran y `area_mm2`
aportado por el cliente nunca se usa. No se modifica la entrada.

## TDD: pruebas específicas

Desde `backend/`, con `venv/Scripts` al inicio de PATH:

```text
python -m pytest -q tests/unit/inventory/test_geometry.py
```

Primero se creó únicamente el archivo de pruebas. La ejecución inicial del
intérprete fue bloqueada por el sandbox de Windows; se repitió fuera de esa
restricción, sin cambiar las pruebas ni crear aún la implementación:

```text
ModuleNotFoundError: No module named 'app.modules.inventory.domain.geometry'
1 error in 0.22s
```

Después de la implementación inicial, antes de corregir la positividad cuantizada:

```text
147 passed in 0.16s
```

Incluye medidas inválidas, no finitos, estructuras incorrectas, ambos sentidos,
estrella auto-intersectada, precisión de coordenadas grandes, redondeo, contexto
decimal del llamador e independencia del área proporcionada en la entrada.

## Suite completa

Resultado histórico inicial, anterior a la corrección del área cuantizada,
desde `backend/` con el mismo entorno:

```text
python -m pytest -q
343 passed in 77.88s (0:01:17)
```

Son 196 pruebas existentes y 147 nuevas. Las pruebas de integración existentes
usan su fixture de PostgreSQL temporal en `127.0.0.1`; no se usa Supabase.

## Revisión histórica del diff (antes de preparar el índice)

Desde la raíz, `git diff --check` terminó sin salida y con código 0.
La SPEC es un archivo modificado; dominio, pruebas y evidencia siguen sin
seguimiento. Se revisó además cada archivo nuevo mediante
`git diff --no-index --check -- NUL <archivo>`, sin incidencias de whitespace,
y se obtuvo su tamaño con `git diff --no-index --stat -- NUL <archivo>`.
No se prepararon archivos en el índice ni se creó ningún commit.

## TDD: corrección de positividad después de cuantizar

Se sustituyó la prueba que aceptaba `0.00` por seis casos de rechazo para las
tres geometrías (áreas pequeñas y valores inmediatamente inferiores al umbral).
Se añadieron tres casos aceptados: área exacta `0.005` en rectángulo y triángulo,
y circunferencia con radio `0.03990` (frente a `0.03989`, rechazado).
El helper de los casos normales también comprueba positividad y mantiene la
verificación de tipo `Decimal` y exponente `-2`.

Antes de modificar la implementación, desde `backend/`:

```text
python -m pytest -q tests/unit/inventory/test_geometry.py
6 failed, 149 passed in 0.25s
```

Los seis fallos fueron `DID NOT RAISE InvalidGeometryError`: confirmaron que
el dominio aún devolvía `0.00`. La corrección valida el área matemática,
cuantiza con `ROUND_HALF_UP` y rechaza un resultado no positivo antes de retornar.
La SPEC documenta la regla para todas las geometrías.

Después de la corrección, con el mismo comando específico:

```text
155 passed in 0.14s
```

Suite completa de la corrección del límite inferior, desde `backend/`:

```text
python -m pytest -q
351 passed in 83.23s (0:01:23)
```

Son 196 pruebas existentes y 155 del dominio geométrico. La revisión de esa iteración
desde la raíz con `git diff --check` no produce salida (código 0).
`git status --short` muestra:

```text
 M docs/specs/SPEC-TA-003-api-inventario.md
?? backend/app/modules/inventory/domain/exceptions.py
?? backend/app/modules/inventory/domain/geometry.py
?? backend/tests/unit/inventory/
?? docs/evidence/sprint-01/TA-003/
```

`exceptions.py` sigue sin seguimiento desde la iteración inicial; no fue
modificado en esta corrección. No se hizo commit.

## TDD: límite superior del área cuantizada

Se mantuvieron los cinco archivos que ya estaban staged. La corrección agrega
la constante de dominio `MAX_AREA_MM2` y valida el máximo después de cuantizar
con `ROUND_HALF_UP`, conservando el rechazo del resultado `0.00`.

Las nuevas pruebas aceptan el máximo exacto en rectángulo y polígono y el área
`9999999999999999.9949`, que redondea al máximo. Rechazan el área
`9999999999999999.995`, que redondea por encima del máximo, y excesos en las
tres geometrías. El antiguo rectángulo de área enorme pasa a ser un caso de
rechazo; la prueba de precisión conserva su ancho y reduce el alto para obtener
un área válida. Los casos normales comprueban ambos límites y dos decimales.

Antes de modificar el dominio, desde `backend/`, con `venv/Scripts` en PATH:

```text
python -m pytest -q tests/unit/inventory/test_geometry.py
5 failed, 158 passed in 0.28s
```

Los cinco fallos fueron `DID NOT RAISE InvalidGeometryError`, demostrando la
ausencia de validación del límite superior. La SPEC documenta el rango final.

Después de implementar la validación, con el mismo comando específico:

```text
163 passed in 0.17s
```

Suite completa final, desde `backend/`:

```text
python -m pytest -q
359 passed in 77.50s (0:01:17)
```

Son 196 pruebas existentes y 163 del dominio geométrico. Se conservan las
fixtures existentes de PostgreSQL temporal local, sin conexiones remotas.

Desde la raíz se actualizaron únicamente los cinco archivos actuales en el
índice mediante `git add` con sus rutas explícitas. `git diff --cached --check`
terminó sin salida y con código 0. `git status --short`:

```text
A  backend/app/modules/inventory/domain/exceptions.py
A  backend/app/modules/inventory/domain/geometry.py
A  backend/tests/unit/inventory/test_geometry.py
A  docs/evidence/sprint-01/TA-003/geometria-dominio.md
M  docs/specs/SPEC-TA-003-api-inventario.md
```

No se modificó `exceptions.py` en esta corrección ni se creó ningún commit.
