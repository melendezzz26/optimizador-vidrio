# ADR-001 — Selección de arquitectura de software

- **Estado:** Accepted
- **Fecha:** 2026-10-03
- **Relacionados:** EN-001, SP-006

## Contexto

NewGlass requiere una arquitectura común que permita a cuatro integrantes desarrollar módulos distintos sin concentrar lógica de negocio en routers, componentes de interfaz o acceso a datos.

El sistema incluye frontend web, API backend, persistencia relacional y un motor geométrico/optimización que debe poder probarse independientemente.

## Decisión

NewGlass utilizará:

- arquitectura cliente-servidor de tres niveles;
- frontend React/Vite desplegable independientemente;
- backend FastAPI como una única aplicación desplegable;
- backend organizado como monolito modular;
- Clean Architecture dentro de cada módulo;
- PostgreSQL/Supabase como persistencia relacional.

Los módulos principales son:

- `authentication`;
- `users`;
- `inventory`;
- `orders`;
- `optimization`;
- `results`;
- `configuration`.

Cada módulo backend puede contener:

- `domain/`
- `application/`
- `infrastructure/`
- `presentation/`

La regla principal de dependencia es:

`Presentation -> Application -> Domain`

`Infrastructure` implementa los contratos requeridos por las capas internas.

`Domain` no debe depender de FastAPI, SQLAlchemy ni Supabase.

## Alternativas consideradas

### Monolito sin modularidad

Descartado por el riesgo de aumentar el acoplamiento entre funcionalidades.

### Microservicios

No adoptados para la versión actual debido a la complejidad adicional de despliegue, comunicación, observabilidad y consistencia sin una necesidad demostrada.

### MVC / capas globales

No se adopta como organización principal del backend porque favorecería carpetas globales compartidas entre todos los módulos.

## Consecuencias

### Positivas

- fronteras funcionales explícitas;
- mayor testabilidad;
- menor acoplamiento del dominio;
- evolución progresiva;
- una sola unidad de despliegue.

### Costos

- mayor cantidad de carpetas y contratos;
- requiere disciplina para respetar dependencias;
- la migración del código existente debe realizarse progresivamente.

## Regla de evolución

El código nuevo deberá respetar esta arquitectura.

El código existente se migrará progresivamente cuando sea modificado o mediante tareas de refactorización protegidas por pruebas.

Los cambios arquitectónicos transversales futuros deberán registrarse mediante un nuevo ADR.
