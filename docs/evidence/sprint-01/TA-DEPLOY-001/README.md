# TA-DEPLOY-001 — Evidencia de Staging

## Identificación

- **PBI:** TA-DEPLOY-001 — Preparación y despliegue controlado de Staging
- **SPEC:** `docs/specs/SPEC-TA-DEPLOY-001-staging.md`
- **Rama:** `feature/TA-DEPLOY-001-staging`
- **Estado de la SPEC:** Draft

## Estado de T01 — Arranque Heroku del monorepo

**IMPLEMENTADA / VALIDACIÓN LOCAL COMPLETA.** La evidencia disponible valida localmente la estructura de arranque desde la raíz, la resolución de dependencias, la declaración de Python 3.11 y el comando equivalente al Procfile. No es una validación de Heroku real.

Esta documentación registra resultados de validaciones ejecutadas y proporcionadas para T01; no se repitieron durante su documentación.

Se registraron estos archivos en la raíz del monorepo:

- `.python-version`, con contenido `3.11`.
- `requirements.txt`, con contenido `-r backend/requirements.txt`.
- `Procfile`, con contenido `web: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`.

El detalle de comandos y resultados está en [test-results/t01-heroku-boot.md](test-results/t01-heroku-boot.md).

## CA-01

**PARCIALMENTE VALIDADO.** La validación local no demuestra detección por Heroku, instalación limpia Linux, uso del `PORT` asignado por Heroku, arranque de un dyno ni registro de SHA desplegado. Por tanto, CA-01 no se declara Cumplido; esos puntos quedan pendientes de T07.

## Alcance de esta evidencia

Este directorio registra únicamente la evidencia disponible de T01. No contiene evidencia de T02–T07. No se ejecutó un despliegue ni una instalación limpia Linux/Heroku para producir este registro.
