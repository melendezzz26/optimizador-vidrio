"""Map the confirmation DTO to the unchanged T1 wire contract."""
from .run_schemas import ConfirmResponseV1


def stock_reference(stock):
    return dict(material_source=stock.source, material_id=stock.material_id, stock_unit_index=stock.physical_unit_index)


def confirmation_response(result):
    return ConfirmResponseV1(schema_version=1, id_optimizacion=result.optimization_id, confirmed=True,
        orders=[dict(id_pedido=i, estado="CONFIRMADO") for i in result.order_ids],
        materials_consumed=[stock_reference(s) for s in result.materials_consumed],
        remnants_created=[dict(id_retazo=r.remnant_id, source=stock_reference(r.source), x_mm=r.x_mm, y_mm=r.y_mm,
                               geometria=dict(r.geometry), area_mm2=r.area_mm2) for r in result.remnants_created])
