# NewGlass — Optimizador de Corte de Vidrio

NewGlass es un sistema web para gestionar materiales y pedidos y optimizar la
distribución de piezas de vidrio sobre planchas y retazos reutilizables.

## Stack principal

- Frontend: React y Vite.
- Backend: Python y FastAPI, como una única aplicación desplegable.
- Persistencia: PostgreSQL/Supabase, con SQLAlchemy y Alembic.
- Validación: pytest en backend; ESLint y build de Vite en frontend.

## Organización del repositorio

```text
backend/       API y módulos del backend
frontend/      Interfaz web organizada progresivamente por features
docs/          Arquitectura, SPEC, pruebas, decisiones y evidencia
experiments/   Exploración reproducible, incluida rasterización
```

El repositorio está en migración progresiva hacia la
[arquitectura modular aprobada](docs/adr/ADR-001-seleccion-arquitectura.md).
El backend organiza cada módulo en `domain`, `application`, `infrastructure` y
`presentation`. El frontend utiliza `features/` y no replica esas capas.
El código anterior permanece operativo en sus rutas actuales hasta que el
responsable de cada módulo lo migre con pruebas.

## Guías

- [Contribuir y organizar el trabajo](CONTRIBUTING.md).
- [Preparar y ejecutar el backend](backend/README.md).
- [Preparar y ejecutar el frontend](frontend/README.md).
- [Índice de documentación](docs/README.md).
- [Experimentos de rasterización](experiments/raster/README.md).

Durante Sprint 1, la experimentación de optimización se centra en rasterización.
First Fit, Best Fit y Worst Fit quedan fuera del alcance de ese sprint.
