# SP-006 — Investigación de M6 con Beam Search acotada

Experimento independiente, en español, con los tres casos oficiales de TA-027 y
los motores FF/BF/WF congelados. La decisión sobre M6 sigue pendiente de Fabricio.
No implementa TA-053 T01/T02. Todos los archivos de esta entrega están aquí;
la aplicación no importa este directorio.

## Abrir en Google Colab (primera vez)

1. Descarga **[SP-006_M6_Beam_Search.ipynb](SP-006_M6_Beam_Search.ipynb)** de esta rama a tu equipo.
2. Entra a [Google Colab](https://colab.research.google.com/), inicia sesión y elige
   **Archivo → Subir cuaderno**. Selecciona el `.ipynb` descargado.
3. En **Entorno de ejecución → Cambiar tipo de entorno de ejecución**, usa Python 3
   con CPU. El cuaderno requiere Python 3.11 o posterior. No necesita GPU.
4. Elige **Entorno de ejecución → Ejecutar todas**. También puedes avanzar con ▶,
   leyendo primero el texto que explica cada celda. Espera a que termine la celda
   anterior; la instalación inicial puede tardar varios minutos.
5. Verás 36 líneas de avance: 3 casos × 6 métodos × 2 repeticiones. Después aparecen
   tablas, figuras, comprobaciones y análisis. Si aparece LIMIT o ERROR, conserva
   ese dato y revisa el motivo; no representa una imposibilidad geométrica.
6. En el panel izquierdo **Archivos**, entra en `sp006_colab` y descarga
   **SP-006_resultados.zip** usando el menú del archivo. Incluye CSV, JSON,
   diferencias por baseline, análisis e imágenes de las 18 combinaciones.
7. Guarda tu copia del notebook y completa sus conclusiones. Los archivos del
   entorno Colab son temporales. La plantilla externa también está disponible en
   [RESULTADOS-SP-006.md](RESULTADOS-SP-006.md).

**Basta subir el `.ipynb`.** Lleva dentro un ZIP verificado que reconstruye código,
fixtures y dependencias. No requiere GitHub privado, Drive, WSL2, credenciales,
base de datos ni servicios de NewGlass. Internet se usa para instalar paquetes
públicos. Un ZIP adicional, `SP-006_M6_Colab.zip`, se genera localmente con el
notebook y sus fuentes; no es necesario para ejecutar Colab.

Para cambiar la distribución mostrada, edita `METODO_PARA_VER = "BS-3"` en la
sección 11 y ejecuta esa celda: admite FF, BF, WF, BS-2, BS-3 y BS-4. Las imágenes
de todos los métodos ya se exportan. Para repetir mediciones de tiempo aumenta
`REPETICIONES` en la sección 6 y ejecuta de nuevo desde allí. Dos repeticiones
sirven como comprobación de determinismo, no como estudio estadístico.

## Procedencia y fidelidad

Referencia verificada el **02/11/2026** mediante `git ls-remote` y `git fetch`:
`origin/integration/sprint-01`, commit **f9cfd4f2644455d616699518948c6660006bdae8**.
Rama de trabajo: `spike/SP-006-m6-beam-search`. La rama local inicial
`chore/p0-functional-sanitization` estaba limpia en `d660ed7` y no se modifica.
La integración local antigua no se usa como referencia; se usa el remoto verificado.

Los fixtures portables se encuentran en
**[vendor/experiments/optimization/cases/](vendor/experiments/optimization/cases/)**.
Son copias byte a byte de:

| Caso | Origen en el repositorio | Unidades | Retazos / planchas físicas |
|---|---|---:|---:|
| SMALL | `experiments/optimization/cases/EXP-SMALL-001.json` | 3 | 1 / 1 |
| MEDIUM | `experiments/optimization/cases/EXP-MEDIUM-001.json` | 9 | 2 / 2 |
| COMPLEX | `experiments/optimization/cases/EXP-COMPLEX-001.json` | 24 | 3 / 4 |

La definición original es [SPEC-TA-027](../../docs/specs/SPEC-TA-027-casos-experimentales.md),
su [PLAN](../../docs/specs/PLAN-TA-027-casos-experimentales.md) y la
[evidencia original](../../docs/evidence/sprint-02/TA-027/README.md).
Los 22 archivos originales copiados, sus rutas y SHA-256 se registran en
[snapshot-manifest.json](snapshot-manifest.json). Incluyen los tres motores,
rasterización, preparación, rotación, métricas, validación de piezas y loader.
Solo se crean `__init__.py` vacíos para aislar los paquetes.

No hay simplificación geométrica: la comparación usa el mismo código puro
congelado. Los resultados son **exploratorios SP-006**, medidos fuera del entorno
productivo. COMPLEX solo tiene fuentes de hasta 22 × 16 mm; no mide escala industrial.
Consulta [METODOLOGIA.md](METODOLOGIA.md) para el algoritmo exacto, las métricas,
reglas, pruebas de equivalencia y faltantes.

## Archivos y responsabilidades

| Archivo o carpeta | Contenido |
|---|---|
| `SP-006_M6_Beam_Search.ipynb` | Cuaderno autosuficiente, explicado y sin salidas precargadas |
| `vendor/` | 22 fuentes/fixtures originales sin cambios y paquetes vacíos |
| `sp006/beam.py` | Algoritmo experimental SP006-BS-v1 |
| `sp006/validation.py`, `checks.py` | Auditoría de placements, integridad y controles portables |
| `sp006/worker.py`, `runner.py` | Aislamiento, mediciones, límites, determinismo y exportación |
| `sp006/plots.py` | Vistas raster y comparaciones gráficas |
| `requirements*.txt` | Dependencias fijadas de ejecución y validación |
| `prepare_snapshot.py`, `build_notebook.py` | Regeneración trazable; Git solo se necesita para recrear el snapshot |
| `validate_notebook.py`, `tests/` | Ejecución limpia y pruebas locales de equivalencia/reglas |
| `METODOLOGIA.md`, `RESULTADOS-SP-006.md` | Método reproducible y plantilla personal |
| `evidence/` | Mediciones locales reales, informe de validación y tres figuras seleccionadas |

`results/`, `.venv/`, ZIP y notebook ejecutado son productos locales ignorados.
La evidencia seleccionada está versionada. No se incluyen datos reales de clientes,
credenciales ni archivos de configuración del backend.

## Reproducir localmente (opcional)

Desde este directorio, con Python 3.11+:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-validation.txt
.venv\Scripts\python build_notebook.py
.venv\Scripts\python -m pytest tests -q
.venv\Scripts\python validate_notebook.py
```

En Linux/Colab, el ejecutable del entorno es `.venv/bin/python`. El notebook no
necesita estos comandos. `validate_notebook.py` copia únicamente el cuaderno a un
directorio de trabajo y ejecuta todas sus celdas con nbclient; guarda las salidas
en `results/` y evidencia seleccionada en `evidence/`. No importa código del backend.
Las nueve pruebas contra el original sí necesitan este checkout local, sin BD.

## Qué observar para decidir

Primero verifica validez, prioridad de retazos, determinismo y ausencia de límites.
Luego compara piezas colocadas, fuentes físicas, aprovechamiento, merma y recuperable.
Finalmente evalúa el tiempo/RSS y si aumentar k cambia lo suficiente para justificarlo.
Los valores de Colab pueden diferir en tiempo y memoria de los locales.
No hay umbral de aceptación de M6 aprobado: completa tu conclusión con evidencia.
La investigación local encuentra ventajas y desventajas según el caso; no declara
un ganador universal ni autoriza la integración posterior.
