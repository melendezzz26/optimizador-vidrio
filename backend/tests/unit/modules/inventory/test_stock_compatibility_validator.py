import pytest
from decimal import Decimal
from app.modules.inventory.domain.services.stock_compatibility_validator import (
    StockCompatibilityValidator,
    BoundingBox
)

def test_bounding_box_rectangulo():
    piece = {"tipo_forma": "RECTANGULO", "dimensiones": {"width_mm": 1200, "height_mm": 700}}
    box = StockCompatibilityValidator.calculate_bounding_box(piece)
    
    assert box.width_mm == Decimal("1200.0")
    assert box.height_mm == Decimal("700.0")

def test_bounding_box_circunferencia():
    piece = {"tipo_forma": "CIRCUNFERENCIA", "dimensiones": {"radius_mm": 350}}
    box = StockCompatibilityValidator.calculate_bounding_box(piece)
    
    # El diámetro debe ser 700
    assert box.width_mm == Decimal("700.0")
    assert box.height_mm == Decimal("700.0")

def test_bounding_box_poligono_convexo():
    # Vértices de un polígono irregular
    piece = {
        "tipo_forma": "POLIGONO_CONVEXO",
        "dimensiones": {"vertices_mm": [[100, 200], [500, 200], [400, 800], [200, 750]]}
    }
    box = StockCompatibilityValidator.calculate_bounding_box(piece)
    
    # max(x) - min(x) = 500 - 100 = 400
    # max(y) - min(y) = 800 - 200 = 600
    assert box.width_mm == Decimal("400.0")
    assert box.height_mm == Decimal("600.0")

def test_poligono_invalido_lanza_excepcion():
    piece = {
        "tipo_forma": "POLIGONO_CONVEXO",
        "dimensiones": {"vertices_mm": [[0, 0], [100, 0]]} # Solo 2 vértices
    }
    with pytest.raises(ValueError, match="contener al menos 3 vértices"):
        StockCompatibilityValidator.calculate_bounding_box(piece)

def test_fits_geometrically_orientacion_natural():
    box = BoundingBox(width_mm=Decimal("1200"), height_mm=Decimal("700"))
    
    # Stock de 2500x1800
    fits = StockCompatibilityValidator.fits_geometrically(
        box, stock_width_mm=Decimal("2500"), stock_height_mm=Decimal("1800")
    )
    assert fits is True


def test_fits_geometrically_dimensiones_exactas():
    box = BoundingBox(width_mm=Decimal("800"), height_mm=Decimal("600"))

    assert StockCompatibilityValidator.fits_geometrically(
        box, stock_width_mm=Decimal("800"), stock_height_mm=Decimal("600")
    ) is True

def test_fits_geometrically_con_rotacion_90_grados():
    box = BoundingBox(width_mm=Decimal("550"), height_mm=Decimal("750"))
    
    # Stock de 800x600. En natural no cabe (750 > 600), pero rotada sí (550 <= 600 y 750 <= 800).
    fits = StockCompatibilityValidator.fits_geometrically(
        box, stock_width_mm=Decimal("800"), stock_height_mm=Decimal("600")
    )
    assert fits is True

def test_fits_geometrically_no_cabe():
    box = BoundingBox(width_mm=Decimal("900"), height_mm=Decimal("700"))
    
    # Stock de 800x600. No cabe de ninguna forma.
    fits = StockCompatibilityValidator.fits_geometrically(
        box, stock_width_mm=Decimal("800"), stock_height_mm=Decimal("600")
    )
    assert fits is False
