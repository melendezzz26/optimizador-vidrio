# Guía de desarrollo de NewGlass

## Flujo de trabajo

`PBI/HU -> SPEC -> implementación -> pruebas -> evidencia -> PR`

1. Identificar el PBI/HU y el alcance acordado.
2. Crear o actualizar la SPEC en `docs/specs/`, usando
   [SPEC-TEMPLATE.md](docs/specs/SPEC-TEMPLATE.md).
3. Implementar en el módulo o feature correspondiente.
4. Ejecutar las pruebas y comprobaciones pertinentes.
5. Guardar evidencia reproducible en `docs/evidence/sprint-01/<ID>/`.
6. Abrir un PR que relacione el trabajo con su SPEC, validación y evidencia.

Los responsables se acuerdan por trabajo y se registran en su SPEC o herramienta
de planificación. Las asignaciones de un sprint no son reglas permanentes de
la arquitectura.

## Backend: monolito modular

El código nuevo se organiza en
`backend/app/modules/<modulo>/{domain,application,infrastructure,presentation}`.
Los módulos disponibles son `authentication`, `users`, `inventory`, `orders`,
`optimization`, `results` y `configuration`.

| Capa | Responsabilidad |
|---|---|
| `domain` | Entidades, reglas e invariantes propias del módulo. |
| `application` | Casos de uso, coordinación y contratos requeridos para ejecutarlos. |
| `infrastructure` | Adaptadores concretos de persistencia, archivos y servicios externos. |
| `presentation` | Routers, contratos HTTP y traducción de entradas, resultados y errores. |

La regla de dependencias es `Presentation -> Application -> Domain`.
`Infrastructure` implementa contratos internos; las capas internas no importan
sus implementaciones concretas. `Domain` no depende de FastAPI, SQLAlchemy ni
Supabase. Evitar imports entre implementaciones internas de módulos diferentes.

`backend/app/shared/` contiene únicamente capacidades realmente transversales:
configuración, infraestructura común de base de datos, seguridad reutilizable
y observabilidad. Una carpeta reservada no necesita implementaciones anticipadas.
No colocar allí casos de uso, endpoints, entidades o repositorios específicos,
usuarios temporales ni algoritmos exclusivos de un módulo.

La decisión completa está en el
[ADR-001](docs/adr/ADR-001-seleccion-arquitectura.md).

## Frontend: organización por funcionalidades

La funcionalidad nueva se ubica en `frontend/src/features/<feature>/`.
Se reservan los mismos nombres funcionales que en backend, pero no se replican
sus capas Clean Architecture. Componentes, hooks, estado y acceso a API se
organizan dentro de cada feature cuando sean necesarios.

`frontend/src/shared/` se reserva para componentes y utilidades reutilizables
por varias features, sin lógica específica de una funcionalidad.
No crear implementaciones de ejemplo solo para llenar carpetas.

## Pruebas y validación

Elegir la ubicación según el propósito de la prueba:

- `backend/tests/unit/`: unidades aisladas; organizar por módulo cuando sea útil.
- `backend/tests/api/`: contratos HTTP, validación de entradas y respuestas.
- `backend/tests/integration/`: interacción entre componentes y adaptadores con
  recursos de prueba controlados, nunca la base remota compartida por defecto.
- `backend/tests/optimization/`: casos geométricos y de rasterización del código
  incorporado al módulo Optimization; evitar duplicarlos en otra categoría.

Las pruebas existentes mantienen sus ubicaciones. Las convenciones y comandos
están en [docs/testing/README.md](docs/testing/README.md). La preparación local
se explica en los README de [backend](backend/README.md) y
[frontend](frontend/README.md).

## SPEC, evidencia y experimentos

- SPEC: `docs/specs/SPEC-<ID>-<tema>.md`.
- Evidencia: `docs/evidence/sprint-01/<ID>/`, con comandos, contexto y resultados reales.
- Investigación: `docs/spikes/` para preguntas, hipótesis y conclusiones sustentadas.
- Experimentos raster: `experiments/raster/`; entradas en `cases/`, exploración
  en `scripts/` y resultados generados en `results/`.

La aplicación nunca importa directamente código de `experiments/`. Una solución
validada se incorpora después al módulo correspondiente, con sus propias pruebas.
First Fit, Best Fit y Worst Fit están fuera del alcance de Sprint 1.
Una carpeta vacía reservada no representa trabajo implementado ni evidencia.

## Convivencia temporal con el código anterior

El código anterior permanece donde está hasta que el responsable de su módulo
lo migre con pruebas y revise sus consumidores. Esto incluye `app/core/` y
`app/models.py`, así como `frontend/src/pages/NuevoPedido.jsx`. El inicio de
sesión ya se migró a `app/modules/authentication/`, `app/shared/security/` y
`frontend/src/features/authentication/` (HU-001).

Las tareas estructurales no cambian sus imports, endpoints, contratos ni lógica
de negocio, ni trasladan estos archivos a una carpeta `legacy/`. El bloque
`shared/database` ya cerrado conserva su implementación y documentación.

Antes de un PR, revisar el diff completo y `git diff --check`. Incluir únicamente
archivos del alcance; no añadir `.env`, entornos virtuales ni salidas generadas.
La preparación de esta fase no requiere ejecutar seed ni migraciones Alembic.
