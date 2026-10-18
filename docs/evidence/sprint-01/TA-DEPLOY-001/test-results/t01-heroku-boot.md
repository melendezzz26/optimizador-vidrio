# T01 — Arranque Heroku del monorepo

- **Rama:** `feature/TA-DEPLOY-001-staging`
- **Fecha de ejecución:** no especificada en los resultados proporcionados.

Esta nota registra resultados reales proporcionados para T01; no se repitieron durante su documentación.

## Archivos de configuración registrados

En la raíz del monorepo:

| Archivo | Contenido/estado registrado |
|---|---|
| `.python-version` | `3.11` |
| `requirements.txt` | `-r backend/requirements.txt` |
| `Procfile` | `web: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port $PORT` |
| `runtime.txt` | No existe |

## Python local

- **Versión:** Python 3.11.9.

## Resolución de dependencias desde la raíz

**Comando ejecutado:**

```powershell
.\backend\venv\Scripts\python.exe -m pip install --dry-run -r requirements.txt
```

**Resultado:** PASS.

- El archivo raíz resolvió `backend/requirements.txt`.
- Todas las dependencias quedaron satisfechas.
- No se instalaron ni actualizaron paquetes.
- La ejecución usó el venv local de Windows. No demuestra una instalación limpia en Linux ni la detección real del buildpack de Heroku.

## Arranque local equivalente al Procfile

- **Working directory:** `backend`.
- **Comando:** `python -m uvicorn main:app --host 0.0.0.0 --port 8001`.
- El proceso inició correctamente y registró `application startup complete`.
- Uvicorn escuchó en `0.0.0.0:8001`.

**Solicitud:** `GET http://127.0.0.1:8001/`

**Resultado:** HTTP 200.

```json
{"mensaje":"Backend del optimizador de vidrio funcionando"}
```

Este arranque local equivalente no prueba el puerto `$PORT` asignado por Heroku ni el arranque de un dyno.

## Evaluación de CA-01

**PARCIALMENTE VALIDADO.**

Validado localmente:

- estructura de archivos de arranque desde la raíz;
- fuente única de dependencias declarada mediante `requirements.txt` raíz;
- Python 3.11 declarado;
- comando equivalente al Procfile;
- arranque local y respuesta HTTP 200.

Pendiente de T07:

- detección real de la aplicación/dependencias por Heroku;
- instalación limpia en entorno Heroku/Linux;
- uso del `PORT` suministrado por Heroku;
- arranque real del dyno;
- registro del SHA desplegado.

No se declara CA-01 Cumplido ni T01 como validación Heroku real.
