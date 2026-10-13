# SP-005 - Compatibilidad geométrica pre-raster de stock

| Campo | Valor |
|---|---|
| Historia relacionada | HU-008 - Stock compatible |
| Tipo | Decisión técnica de preselección geométrica |
| Estado | Decisión aplicada en la rama HU-008; revisión independiente pendiente |

## Colisión del identificador

El identificador SP-005 aparece en SPEC-TA-013-datos-base.md con el nombre
histórico "Comparación y selección de tipos y espesores de vidrio". Este
informe no reemplaza ni modifica aquella referencia. Documenta la decisión
geométrica que HU-008 y su SPEC denominan SP-005. La colisión queda explícita
hasta que el equipo asigne identificadores canónicos distintos.

## Problema y pregunta

Antes de registrar un pedido, Orders necesita saber si cada pieza tiene al menos
una plancha o retazo elegible cuyas dimensiones puedan admitirla. La consulta
no debe reservar ni cambiar inventario.

Pregunta: ¿qué regla geométrica reproducible puede descartar una pieza que
no cabe individualmente antes de la rasterización?

## Hipótesis y método

La comparación de cajas envolventes alineadas a los ejes, con orientación normal
y rotación ortogonal de 90 grados, sirve como predicado pre-raster por pieza.
Se contrastó el modelo actual de planchas y geometrías de retazos, el validador
heredado de HU-008 y la regla de disponibilidad implementada por HU-014. La
implementación y las pruebas de dominio, repositorio y flujo API en
[La evidencia ejecutable](../evidence/sprint-01/HU-008/README.md) contiene los
resultados reproducibles de esta decisión.

## Decisión: candidato compatible individual

Una pieza tiene candidato compatible si existe al menos una plancha o retazo
que cumpla simultáneamente el tipo de vidrio, el espesor, la disponibilidad y
la regla de caja envolvente de esta sección. El candidato se comprueba por línea
de pieza; cantidad de la línea no se interpreta como unidades a reservar ni
como una prueba de disponibilidad conjunta.

Para una pieza de caja (ancho, alto) y stock de caja (ancho, alto), hay cabida
según esta regla cuando:

    (p.ancho <= s.ancho AND p.alto <= s.alto)
    OR
    (p.ancho <= s.alto AND p.alto <= s.ancho)

Las comparaciones son inclusivas: las dimensiones exactamente iguales caben.
Solo se permite la orientación almacenada y su intercambio de ejes de 90 grados;
no se buscan ángulos arbitrarios.

### Dimensiones de una pieza

- Rectángulo: width_mm por height_mm.
- Circunferencia: diámetro por diámetro (2 * radius_mm).
- Polígono convexo: ancho y alto de su caja mínima calculados desde los extremos
  de vertices_mm.

### Plancha candidata

Una plancha debe tener id_tipo_vidrio y espesor_mm iguales a los de la pieza,
estado = true, cantidad > 0 y dimensiones suficientes según la regla de
rotación. No se modifica su cantidad.

### Retazo candidato

Un retazo debe tener id_tipo_vidrio y espesor_mm iguales a los de la pieza y
estado = true. Su caja se calcula desde la geometría persistida: dimensiones
para rectángulos, diámetro para circunferencias y extremos de vértices para
polígonos convexos. Se aplica la misma comparación inclusiva y rotación de 90
grados. No se asigna cantidad a retazos.

La regla de retazo compara cajas envolventes y es una preselección: por sí sola
no demuestra contención exacta dentro de una silueta curva o poligonal ni una
colocación final. Esa decisión corresponde a la etapa posterior de colocación.
El validador rechaza geometrías persistidas cuyo tipo no reconoce.

## Disponibilidad y HU-014

La regla de HU-014 define una plancha disponible como estado = true,
cantidad > 0 y sin baja manual; un retazo disponible debe tener estado = true
y no tener baja manual. El código HU-014 registra la baja y establece
estado = false en la misma transacción, y rechaza reactivar el recurso cuando
existe una baja. Por ello, este consumidor filtra estado = true (y cantidad
positiva para planchas) sin duplicar una consulta a movimientos.

La restricción depende del invariante de HU-014. Una escritura externa que
cree un movimiento de baja y deje estado = true quedaría fuera del contrato y
no está cubierta por este lector.

## Candidato individual y factibilidad conjunta

La validación garantiza solamente que cada línea de pieza tiene uno o más
candidatos individuales al momento de la consulta. Varias piezas pueden señalar
al mismo stock y la validación no calcula si pueden colocarse todas a la vez.
Tampoco multiplica los candidatos por la cantidad solicitada. La factibilidad
conjunta se evalúa después mediante rasterización y colocación.

## No mutación y fuera de alcance

La comprobación usa una transacción de lectura que termina con rollback. No crea
reservas, no descuenta cantidades, no cambia estados, no registra consumo y no
inicia optimización.

Fuera de alcance: rasterización, empaquetamiento, heurísticas FF/BF/WF, selección
de mejor candidato, reserva, confirmación o consumo de stock.

## Resultado

La regla queda formalizada como un filtro individual basado en cajas envolventes
con giro ortogonal. La prueba unitaria comprueba límites inclusivos, rotación y
rechazo por dimensiones; las pruebas de Inventory verifican elegibilidad y
lectura sin mutación. La API comprueba que un pedido con una pieza sin candidato
no se persiste. La evidencia final debe registrar los resultados concretos de
las ejecuciones; este documento no declara aprobación Verified.
