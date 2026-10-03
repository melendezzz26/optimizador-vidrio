# Experimentos de NewGlass

Este directorio contiene exploración reproducible separada del código de la
aplicación. La aplicación nunca importa directamente desde `experiments/`.
Una solución validada se incorpora después a su módulo, con pruebas propias.

La estructura reservada para rasterización es:

```text
raster/
    cases/      Entradas reproducibles
    scripts/    Código de experimentación
    results/    Resultados generados
```

First Fit, Best Fit y Worst Fit están fuera del alcance de Sprint 1.
Esta estructura no implementa algoritmos ni declara experimentos ejecutados.

Consultar la [guía de rasterización](raster/README.md). Las conclusiones se
documentan en [docs/spikes/](../docs/spikes/README.md), y la evidencia seleccionada
en `docs/evidence/sprint-01/<ID>/`.
