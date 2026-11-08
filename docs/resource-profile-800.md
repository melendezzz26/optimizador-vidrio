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

## Despliegue y vuelta atrás

Publicar manualmente `test/resource-profile-800` en la aplicación staging
existente. El `Procfile` de esta rama fija únicamente esas cuatro variables
públicas en el proceso web; no requiere revelar ni modificar Config Vars. No cambiar plan, base,
secretos, número de dynos ni automatic deploy. Pages admite temporalmente esta
rama y publica solo después de backend, frontend y E2E del workflow de despliegue.
No ejecutar confirmación de corte durante las pruebas de capacidad.

Para volver al comportamiento previo: desplegar `integration-02`, cuyo `Procfile`
no contiene esos overrides. No se requieren migraciones ni restauración de inventario.
Revisar antes los resultados de prueba retenidos y que no quede una comparación
con supervisor activo.
