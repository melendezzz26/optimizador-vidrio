"""Entradas T00 para unidades, stock, vértices y rejillas; sin datos reales.

Autor: Fabricio Melendez Quezada. Revisor asignado: Andro Quispe.
No sustituyen los casos congelados TA-027 ni representan el triple peor caso.
"""
import math

RESOURCE_CASES = ("T00-UNITS-150", "T00-STOCK-50", "T00-VERTICES-128", "T00-GRID-4M")


def read_resource_case(case_id):
    if case_id not in RESOURCE_CASES:
        raise ValueError("Caso de recursos desconocido.")
    geometry = dict(type="RECTANGULO", width_mm=2, height_mm=2)
    stock = dict(type="RECTANGULO", width_mm=20, height_mm=20)
    quantity, stock_quantity = 1, 1
    if case_id == "T00-UNITS-150":
        quantity, stock_quantity = 150, 50
    elif case_id == "T00-STOCK-50":
        quantity, stock_quantity = 12, 50
    elif case_id == "T00-VERTICES-128":
        geometry = dict(type="POLIGONO_CONVEXO", vertices_mm=[
            [round(6 * math.cos(i * math.tau / 128), 6),
             round(6 * math.sin(i * math.tau / 128), 6)] for i in range(128)])
        quantity, stock_quantity = 8, 3
        stock = dict(type="RECTANGULO", width_mm=30, height_mm=30)
    elif case_id == "T00-GRID-4M":
        geometry = dict(type="RECTANGULO", width_mm=1990, height_mm=1990)
        stock = dict(type="RECTANGULO", width_mm=2000, height_mm=2000)
    return dict(case_id=case_id, schema_version=1, rotation_allowed=True, order_ids=[1],
        config=dict(resolution_mm=1, angular_step_deg=5, margin_mm=0, separation_mm=0),
        residual_limits=dict(minimum_width_mm=1, minimum_height_mm=1),
        pieces=[dict(id_pedido=1, id_pieza=1, cantidad=quantity, id_tipo_vidrio=1,
                     espesor_mm=6, tipo_forma=geometry["type"], geometria=geometry)],
        stock=[dict(material_id=1, quantity=stock_quantity, source="PLANCHA",
                    glass_type_id=1, thickness_mm=6, geometry=stock)])
