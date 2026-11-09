# Prueba de capacidad HTTP: 600–800 piezas

Rama de prueba: `test/resource-profile-800`. Base auditada:
`b964b2bca3fb67739a6f7fe05d2a0dd69ce2766b` (`integration-02`).
El despliegue de prueba está autorizado por el propietario; esta rama no debe
integrarse hasta revisar las mediciones del despliegue.

## Cambios

- El diagnóstico persistido identifica el exceso de RSS del servidor, del total
  supervisado y un fallo de asignación del trabajador por separado. Incluye picos,
  límites, despacho e inicio real. Se emiten logs JSON `comparison_resource_*`
  sin credenciales, geometría ni información del cliente.
- Una interrupción global no presenta a un motor pendiente como ejecutado.
- Cada trabajador transmite la máscara del material al declararla y reutiliza
  una referencia validada mientras siga siendo la misma. Ambos extremos mantienen
  una sola entrada; el caché no crece con las piezas ni cruza ejecuciones.
- Un evento se decodifica una vez. El supervisor y la proyección HTTP reutilizan
  el hecho ya validado; las máscaras del navegador mantienen el contrato público.
- Las lecturas de ventanas/manifiestos y las escrituras de referencias visuales
  verifican pertenencia y supervisión sin decodificar los seis resultados.
- Se detectan límites de cgroup v1/v2 y sus padres accesibles. El preflight del
  comparador secuencial descuenta la memoria del servidor ya incluida en el
  presupuesto agregado; el comparador v1 conserva su reserva original.
- Los overrides son explícitos, acotados y deben dejar al menos 64 MiB o el 10 %
  de la capacidad del contenedor fuera del presupuesto agregado. Sin overrides
  permanecen los límites originales. No se cambian algoritmos, tiempos, M6 nativo,
  admisión de 800 piezas, confirmación ni movimientos de inventario.

## Medición reproducible

Desde `backend`, con dependencias y binarios PostgreSQL locales:

```bash
export NEWGLASS_REQUIRE_POSTGRES=1
export NEWGLASS_TEST_PG_BIN=/usr/lib/postgresql/16/bin
python -B -m scripts.profile_comparison_http --units 800 --output /tmp/http-800.json
```

El script crea un clúster PostgreSQL y un servidor uvicorn propios de loopback.
Envía un pedido por el endpoint real, consume sus eventos, consulta los seis
resultados persistidos y libera sin confirmar. Registra inventario antes/después,
referencias físicas únicas, despacho, cierre de trabajadores, RSS y tiempos.
No acepta URL de base/API remota ni usa `.env`. El endpoint de cierre del fixture
se agrega únicamente al ejecutar este script, nunca al iniciar `main:app`.

La carga contiene dos grupos de vidrio de 6 mm, tres figuras repetidas por grupo
(rectángulo 120×80, círculo r=40 y paralelogramo convexo), dos planchas 2440×3300
por grupo, resolución 1 mm, paso 5°, margen/separación 0. Prueba unidades físicas,
no 800 geometrías distintas. No reproduce toda la base ni la CPU de Heroku.

La [comparación exploratoria en Actions](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/42521005911)
completó los seis motores en ambos códigos para los tres tamaños. Los picos RSS
del proceso web estuvieron en torno a 202–225 MiB con los cambios y 206–225 MiB
en la base. **No demuestra una reducción sustancial del pico de RAM** ni reproduce
el corte de Heroku. Las corridas usaron máquinas distintas, una muestra por caso;
los tiempos no constituyen un SLA ni una medición estadística. La primera versión
exploratoria del fixture no conservó el informe de cierre/inventario al recibir
SIGTERM; el fixture actual pide un cierre normal y exige esa evidencia.

## Perfil experimental para Basic 512 MiB

El Dashboard confirmó Basic en `newglass-api-staging`. La RAM de ese tipo es
512 MB según la [tabla oficial](https://www.heroku.com/dynos/configure/).
Los overrides de la rama de prueba son:

| Variable | MiB |
|---|---:|
| `NEWGLASS_COMPARISON_SUPERVISOR_MIB` | 280 |
| `NEWGLASS_COMPARISON_WORKER_MIB` | 128 |
| `NEWGLASS_COMPARISON_AGGREGATE_MIB` | 448 |
| `NEWGLASS_DYNO_MEMORY_MIB` | 512 |

La reserva de auxiliares (16 MiB) está incluida en el agregado. El trabajador
conserva un límite de espacio virtual, distinto de RSS. El perfil redistribuye
capacidad hacia el servidor; el pico virtual observado del trabajador fue
aproximadamente 43 MiB. La cuota explícita del dyno solo puede reducir la capacidad
detectada: no permite saltarse un cgroup más restrictivo.

El workflow `Resource profile HTTP 600-800` prueba este perfil con
`--require-complete`: falla si no obtiene seis resultados completos, inventario
intacto, unidades sin duplicar y cierre verificado. Esto limita el proceso de
comparación, pero el runner de Actions no simula físicamente un dyno de 512 MiB.
La verificación final debe repetirse en Heroku, también con pedidos consecutivos.

La [corrida con presupuestos Basic](https://github.com/melendezzz26/optimizador-vidrio/actions/runs/42521552208)
aprobó el gate estricto para los tres lotes: los seis motores comenzaron y
completaron, se consultaron 12 600 colocaciones únicas en total, el inventario
antes/después coincidió y todos los procesos quedaron cerrados. Ningún callback
visual reportó errores. Una muestra por tamaño:

| Unidades | Resultados completos | Pared HTTP s | Pico RSS web MiB | Pico agregado supervisado MiB |
|---:|---:|---:|---:|---:|
| 600 | 6/6 | 111.984 | 204.090 | 244.652 |
| 700 | 6/6 | 141.807 | 213.457 | 254.266 |
| 800 | 6/6 | 177.577 | 220.387 | 267.109 |

El pico virtual del trabajador fue 41.3–43.2 MiB. Estos resultados validan los
presupuestos internos con esa carga; no acreditan todavía la ejecución en Heroku.

## Geometrías grandes a 1 mm, primera revisión

La revisión de [TA-016](specs/SPEC-TA-016-rotacion-compartida.md) y
[TA-037](specs/SPEC-TA-037-control-carga-optimizador.md) limita las bases en
admisión y reemplaza orientaciones durante la búsqueda. En local, ambos casos
pasaron la nueva admisión a 1 mm y 5°, con margen y separación de 0 mm.
Cada motor se ejecutó mediante su adaptador en un proceso local independiente.

| Caso | Motores completos | Causa de los resultados pendientes |
|---|---|---|
| #61 reconstruido, 247 unidades | FF, BF, WF y HF | M5 llegó a 120 s. M6-BS llegó a su límite de tiempo con 237 colocadas. |
| Primeras 800 unidades del CSV de auditoría, 40 planchas y 2 retazos sintéticos compatibles | 0 de 6 | FF, BF, WF, HF y M5 llegaron a 120 s. M6-BS alcanzó el límite de estado de 32 MiB con 99 colocadas. |

La contabilidad raster se mantuvo dentro de 64 MiB en esas ejecuciones.
La medición es del adaptador local, sin HTTP ni PostgreSQL. El segundo caso
comprueba la admisión y distingue los límites restantes de búsqueda. El
criterio de completar 800 unidades grandes en staging sigue pendiente.

## Geometrías grandes a 1 mm, segunda revisión

Con las mejoras exactas de búsqueda y memoria, M5 completó las 247 unidades
del #61 reconstruido en 94.37 s y M6 en 51.03 s con el plazo anterior.
Diez casos pequeños por los seis motores conservaron huellas idénticas de
colocaciones, contornos, fuentes, giros, métricas y retazos frente a `e77d6f9`.

Prueba de capacidad local con las primeras 800 unidades válidas del CSV,
40 planchas compatibles (25 de 2440 × 3300 mm y 15 de 3300 × 2140 mm) y dos
retazos (2440 × 373 mm y 440 × 904 mm). Resolución 1 mm, paso 5°, margen y
separación 0 mm. Cada adaptador se ejecutó en un proceso con un límite duro
de espacio virtual de 128 MiB y tiempo ampliado. Las métricas revalidaron
cada colocación contra el raster; se verificaron las 800 identidades únicas
por resultado.

| Motor | Colocadas | Pared s | Pico RSS MiB | Planchas |
|---|---:|---:|---:|---:|
| FF | 800 | 183.42 | 83.68 | 29 |
| BF | 800 | 280.17 | 83.32 | 30 |
| WF | 800 | 261.59 | 82.34 | 29 |
| HF | 800 | 181.64 | 83.66 | 29 |
| M5 | 800 | 460.97 | 84.36 | 29 |
| M6-BS | 800 | 303.75 | 88.17 | 31 |

Las huellas distinguen cinco distribuciones. HF usó su comportamiento de
respaldo por pieza y coincidió con FF. M6 completó de forma nativa con 494 667
sondeos, un pico de estado de 30 097 084 bytes y ancho de haz 2. Estos tiempos
suman cerca de 28 min para la secuencia. Excluyen HTTP, observación visual,
PostgreSQL y variaciones de CPU de Heroku.

Para la prueba desplegada, el perfil v2 de la rama permite 600 s por método
a partir de 200 unidades. Los pedidos pequeños conservan el plazo habitual.
El watchdog y el proceso usan el mismo presupuesto congelado para la
comparación. La medición de memoria no cambia el tamaño de las piezas ni las
existencias que exige la solución.

## Despliegue y vuelta atrás

Publicar manualmente `test/resource-profile-800` en la aplicación staging
existente. El `Procfile` de esta rama fija el perfil de memoria y de tiempo
en el proceso web sin modificar Config Vars. No cambiar plan, base,
secretos, número de dynos ni automatic deploy. Pages admite temporalmente esta
rama y publica solo después de backend, frontend y E2E del workflow de despliegue.
No ejecutar confirmación de corte durante las pruebas de capacidad.

Para volver al comportamiento previo: desplegar `integration-02`, cuyo `Procfile`
no contiene esos overrides. No se requieren migraciones ni restauración de inventario.
Revisar antes los resultados de prueba retenidos y que no quede una comparación
con supervisor activo.
