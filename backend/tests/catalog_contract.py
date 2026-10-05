"""Expectativas SP-005 de pruebas; producción consulta el catálogo persistido."""

from decimal import Decimal


EXPECTED_CATALOG = {
    name: tuple(Decimal(value) for value in values.split())
    for name, values in {
        "Incoloro": "3 4 5.5 6 8 10 12",
        "Bronce": "4 5.5 6 8 10",
        "Gris": "4 5.5 6 8 10",
        "Catedral": "3 3.5 5",
        "Reflejante": "4 5.5 6 8",
        "Espejo": "2 3 4 6",
    }.items()
}
