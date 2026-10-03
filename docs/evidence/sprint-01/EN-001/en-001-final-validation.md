# EN-001: evidencia de validación integral final

## Identificación y alcance

- Rama: `enabler/EN-001-reestructurar-repositorio`.
- Baseline: `5c172a7`, tag `baseline-pre-reestructuracion-v1`.
- Commit validado antes del cierre documental:
  `a388b8e0a6c8a9749b445d57d4ccdf32a427c797`.
- El working tree comenzó y terminó limpio durante la validación integral.

Esta evidencia recoge los resultados reales de esa validación; no representa
una nueva ejecución de pytest, lint o build durante el cierre documental.
El cierre documental actualiza únicamente los README de rasterización e
infraestructura y añade este documento.

## Estructura y alcance verificados

| Área | Resultado |
|---|---|
| Backend | `backend/app/modules/` contiene `authentication`, `users`, `inventory`, `orders`, `optimization`, `results` y `configuration`, cada uno con `domain`, `application`, `infrastructure` y `presentation`. |
| Shared | `backend/app/shared/` contiene `database`, `security`, `config` y `observability`. |
| Frontend | `frontend/src/features/` reserva las siete funcionalidades anteriores; existe `frontend/src/shared/`. No replica las capas del backend. |
| Pruebas | Existen `backend/tests/unit/`, `api/`, `integration/` y `optimization/`; las pruebas antiguas conservan sus ubicaciones. |
| Experimentos | `experiments/raster/` contiene README, `cases/`, `scripts/` y `results/`, con marcadores versionados. La aplicación no importa desde `experiments/`. |
| Documentación | Existen README raíz, CONTRIBUTING y guías de backend, frontend y docs; están presentes `docs/adr/`, `architecture/`, `database/`, `specs/`, `testing/`, `infrastructure/`, `spikes/`, `ui-ux/` y `evidence/`. |
| Estándares | `.gitignore`, `.editorconfig` y `.gitattributes` verificados; `backend/.env.example` contiene solo las tres variables previstas con valores ficticios. |
| CI | `.github/workflows/ci.yml` declara Pull Requests y push a `main`, con jobs independientes para backend y frontend. |

First Fit, Best Fit y Worst Fit permanecen fuera del alcance de Sprint 1.
La estructura reservada no acredita módulos ni algoritmos implementados.

## Conservación del comportamiento y shared/database

La comparación con el baseline confirmó que `app/database.py` se trasladó a
`app/shared/database/session.py` con contenido idéntico. El paquete exporta
`Base`, `SessionLocal` y `engine`; `app.models` utiliza el mismo objeto `Base`.

No hubo cambios funcionales salvo el traslado autorizado de database y la
actualización de sus imports en `backend/main.py`, `backend/seed.py`,
`backend/app/models.py` y `backend/alembic/env.py`; el comportamiento se conserva.
El código anterior de `core/`, `routers/`, `schemas/` y `services/` permanece
intacto. Login, NuevoPedido y App.jsx no cambiaron. No se alteraron definiciones
ORM ni archivos de migraciones.

`backend/tests/unit/test_database_structure.py` verifica los exports, la
identidad de `Base` y estas diez tablas registradas en `Base.metadata`:

```text
configuraciones
ejecuciones_optimizacion
metricas_ejecucion
pedidos
piezas
planchas
retazos
roles
tipos_vidrio
usuarios
```

La prueba usa un proceso aislado, una URL SQLite en memoria, desactiva la carga
de `.env` y bloquea `Engine.connect` y `Engine.raw_connection`.
No se ejecutó ninguna operación contra PostgreSQL/Supabase, ningún seed ni
`/db-test`. No se ejecutaron migraciones Alembic ni `upgrade`, `downgrade`,
`stamp` o `revision`; no hubo cambios de esquema.

## Validación local: entorno, comandos y resultados observados

Entorno local: Python **3.11.9**, Node **22.16.0** y npm **10.9.2**.

| Directorio | Comando ejecutado | Resultado |
|---|---|---|
| `backend/` | `./venv/Scripts/python.exe -m pytest -q` | `20 passed in 4.73s` |
| `frontend/` | `npm.cmd run lint` | Código de salida 0, sin errores. |
| `frontend/` | `npm.cmd run build` | Código de salida 0; 1892 módulos; Vite reportó 927 ms. |
| Raíz | `git diff --check` | Correcto, sin salida; código 0. |
| Raíz | `git diff --cached --check` | Correcto, sin salida; código 0. |
| Raíz | `git diff baseline-pre-reestructuracion-v1 HEAD --check` | Sin errores. |
| Raíz | `git grep -n -F 'app.database' -- '*.py'` | Cero referencias; código 1 esperado por ausencia de coincidencias. |
| Raíz | `git status --short` | Sin salida al inicio y al final de la validación integral. |

Se usaron el intérprete del venv y `npm.cmd` desde PowerShell. Las 20 pruebas
corresponden a 10 de autenticación, 7 de permisos y 3 de estructura de database.

- Se comprobaron **43 enlaces Markdown locales**, sin destinos ausentes.
- Se realizaron **13 verificaciones de exclusión**, todas correctas, mediante
  `git check-ignore --no-index --quiet <ruta>` sobre rutas de comprobación, sin
  crear archivos: `.env`, `.env.local`, `.env.example`, `venv/`, `.venv/`,
  `frontend/dist/`, `frontend/node_modules/`, resultados raster directos y
  anidados, `results/.gitkeep`, `cases/`, `scripts/` y evidencia documental.
- Los entornos locales y resultados generados quedan ignorados; `.env.example`,
  `results/.gitkeep`, entradas, scripts y evidencia permanecen versionables.
- No había archivos versionados que coincidieran con reglas de exclusión ni
  archivos funcionales modificados sin commit.

Durante la revisión se detectaron dos notas desactualizadas de fase 1:
la exclusión de resultados en `experiments/raster/README.md` y la configuración
de CI en `docs/infrastructure/README.md`. Se corrigen en este cierre documental,
sin modificar código, configuración ni estructura.

## Validación remota de GitHub Actions

La existencia y configuración del workflow se verificaron estáticamente:
Python 3.11 con pytest; Node 22 con `npm ci`, lint y build; sin secretos,
BD externa, migraciones ni deployment.

El workflow CI se ejecutó en GitHub Actions mediante el Pull Request #8,
**EN-001: reestructurar repositorio y establecer base arquitectónica**:

- Job `backend`: finalizó correctamente.
- Job `frontend`: finalizó correctamente.
- Después de completar los checks, el Pull Request mostró el estado
  **Ready to merge**.

Estos resultados remotos son posteriores y distintos de las validaciones
locales registradas arriba. No se dispone de duración de los jobs, ID interno
de ejecución, URL ni timestamps; no se atribuyen al runner las métricas locales.

## Pendientes fuera de EN-001

- Migración funcional de los módulos por sus responsables.
- Integración de HU-003 y usuarios persistentes.
- Alineación del modelo de datos.
- Divergencia Alembic `c4e8a1f2b3d5` frente a `9b9f04eb67f6`: el estado remoto
  fue reportado, no consultado durante la validación. Git identifica la primera
  revisión en `origin/feature/HU-003-gestion-usuarios`; corresponde resolverla
  durante esa integración.
- Experimentación raster.
- Pruebas funcionales frontend; lint y build no sustituyen pruebas de interfaz.

## Criterio de cierre técnico

EN-001 cumple la preparación estructural y las validaciones locales previstas.
Este cierre documental corrige las dos notas pendientes y registra la evidencia
sin ampliar el alcance funcional. La validación remota reportada del PR #8
confirma ambos jobs de CI correctos y el estado **Ready to merge** tras los checks.
