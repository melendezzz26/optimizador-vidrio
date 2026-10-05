# TA-013: consulta API del catálogo

Se conserva `GET /api/inventory/tipos-vidrio` y su router. `TipoVidrioResponse` agrega `espesores_mm`; el repositorio obtiene los valores desde `tipos_vidrio_espesores`. La conversión de Decimal a número JSON se limita a Presentation.

Ejemplo de objeto devuelto (el ID depende de los datos existentes):

```json
{
  "id_tipo_vidrio": 1,
  "nombre": "Incoloro",
  "descripcion": "Vidrio plano de uso general.",
  "estado": true,
  "espesores_mm": [3, 4, 5.5, 6, 8, 10, 12]
}
```

La respuesta es una lista. Los espesores de cada objeto están ordenados ascendentemente; el orden de los tipos no forma parte del contrato. Los tipos inactivos conservan `estado: false`. Un tipo sin combinaciones devuelve una lista vacía.

`tests/api/inventory/test_inventory_api.py` verifica el campo mediante el servicio falso existente. `tests/integration/inventory/test_catalog.py` recorre el router y schemas reales con un servicio conectado exclusivamente al PostgreSQL temporal:

- GET devuelve HTTP 200 y las seis listas exactas.
- Crear plancha Incoloro + 12 funciona; cambiar solo su tipo a Espejo devuelve 422.
- Crear retazo Catedral + 3.5 funciona; cambiar solo su espesor a 4 devuelve 422; cambiar ambos a Espejo + 2 funciona.
- La persistencia y Application comprueban también las variantes PATCH solo tipo, solo espesor y ambos para planchas y retazos.

No se agregó otro endpoint ni una lista de espesores en el router/schema. La integración HTTP usa TestClient y restaura las dependencias al terminar. Resultados: [pruebas-ta013.md](pruebas-ta013.md).
