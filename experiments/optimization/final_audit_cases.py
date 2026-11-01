"""Small, frozen audit inputs; separate from TA-027's exactly three baselines."""
from copy import deepcopy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('ta027_audit_loader', Path(__file__).with_name('loader.py'))
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


def rectangle(width, height):
    return dict(type='RECTANGULO', width_mm=width, height_mm=height)


def piece(identifier, geometry, quantity=1, glass=1):
    return dict(id_pedido=1, id_pieza=identifier, cantidad=quantity, id_tipo_vidrio=glass,
        espesor_mm=6, tipo_forma=geometry['type'], geometria=geometry)


def stock(identifier, geometry, quantity=1, source='RETAZO', glass=1):
    return dict(material_id=identifier, quantity=quantity, source=source, glass_type_id=glass,
        thickness_mm=6, geometry=geometry)


def case(identifier, pieces, sources, *, resolution=1, margin=0, separation=0):
    return dict(case_id=identifier, schema_version=1, rotation_allowed=True, order_ids=[1],
        config=dict(resolution_mm=resolution, angular_step_deg=5, margin_mm=margin, separation_mm=separation),
        residual_limits=dict(minimum_width_mm=1, minimum_height_mm=1), pieces=pieces, stock=sources)


AUDIT_CASES = {
    'A-coincidence': case('A-coincidence', [piece(1, rectangle(6, 4))],
        [stock(101, rectangle(7, 5)), stock(102, rectangle(10, 7))]),
    'B-source-counterexample': case('B-source-counterexample', [piece(1, rectangle(600, 400))],
        [stock(101, rectangle(1000, 700)), stock(102, rectangle(700, 500))]),
    'C-varied-rectangles': case('C-varied-rectangles',
        [piece(1, rectangle(5, 3), 3), piece(2, rectangle(7, 2), 2), piece(3, rectangle(2, 2), 3),
         piece(4, rectangle(3, 2), glass=2)],
        [stock(101, rectangle(12, 10)), stock(102, rectangle(9, 8)),
         stock(103, rectangle(14, 12), 3, 'PLANCHA'), stock(104, rectangle(2, 3), glass=2)], separation=1),
    'D-asymmetric-triangles': case('D-asymmetric-triangles',
        [piece(1, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [9, 0], [2, 5]]), 2),
         piece(2, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [6, 1], [1, 8]]), 2)],
        [stock(101, rectangle(12, 10)), stock(102, rectangle(10, 12)), stock(103, rectangle(16, 14), 2, 'PLANCHA')],
        resolution=.5, margin=.5, separation=1.25),
    'E-mixed-shapes': case('E-mixed-shapes',
        [piece(1, rectangle(5, 3), 2), piece(2, dict(type='CIRCUNFERENCIA', radius_mm=2), 2),
         piece(3, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [5, 0], [6, 3], [3, 5], [0, 3]]), 2)],
        [stock(101, rectangle(12, 10)), stock(102, dict(type='POLIGONO_CONVEXO', vertices_mm=[[0, 0], [12, 0], [10, 10], [1, 9]])),
         stock(103, rectangle(16, 14), 3, 'PLANCHA')], margin=1, separation=1),
    'WF-15-units-9-sheets': case('WF-15-units-9-sheets', [piece(1, rectangle(1, 1), 15)],
        [stock(201, rectangle(4, 4), 9, 'PLANCHA')]),
    'WF-16-units-10-sheets': case('WF-16-units-10-sheets', [piece(1, rectangle(1, 1), 16)],
        [stock(201, rectangle(4, 4), 10, 'PLANCHA')]),
}


def read_case(identifier):
    if identifier in AUDIT_CASES:
        return deepcopy(AUDIT_CASES[identifier])
    return loader.read_case(identifier)


def build_problem(data):
    return loader.build_problem(deepcopy(data))


CASES = (*AUDIT_CASES, *loader.CASES)
