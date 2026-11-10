"""Arnés de Pruebas de Seguridad Operacional del Corte (TA-QA-009).

Ejecución con conexiones 100% REALES:
- Autenticación contra FastAPI y Supabase PostgreSQL real.
- Consulta real de planchas activas y clientes en producción/staging.
- Inyección de patrones de corte inválidos para verificar rechazo al 100%.
"""
from decimal import Decimal
import json
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Asegurar que backend/ está en sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main
from app.modules.optimization.domain.rasterizer import rasterize_geometry, rasterize_material
from app.modules.optimization.domain.placement import PlacementError, PlacementIssue, SheetLayout
from app.modules.optimization.domain.problem import (
    MaterialGroup,
    MaterialSource,
    OptimizationConfig,
    OptimizationProblem,
    OptimizationResult,
    PieceUnit,
    Placement,
    StockCandidate,
)
from app.modules.optimization.domain.confirmation import consumption_groups
from app.modules.optimization.application.resource_policy import HU015_RASTER_BUDGET
from app.modules.optimization.application.errors import RasterBudgetExceeded


RESULTS_OUT = Path(r"C:\Users\liban\Desktop\rework-vidrio\Notion\TA-QA-009\safety_results.json")


def run_safety_suite():
    print("=========================================================================")
    print("      TA-QA-009 — SUITE DE SEGURIDAD OPERACIONAL DEL CORTE (REALES)      ")
    print("=========================================================================\n")

    report = {
        "suite": "TA-QA-009 Seguridad Operacional del Corte",
        "real_database": "Supabase Cloud PostgreSQL",
        "cases": [],
        "summary": {"total": 0, "rejected_safely": 0, "escapes": 0, "rejection_rate_pct": 0.0},
    }

    with TestClient(main.app) as client:
        # 1. Autenticación real y consulta de stock real en Supabase
        print("[1/3] Autenticando usuario real (A74000010) y consultando stock real en Supabase...")
        login_res = client.post("/api/auth/login", json={"username": "A74000010", "password": "Admin1234!"})
        assert login_res.status_code == 200, f"Fallo en login real: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        planchas_res = client.get("/api/inventory/planchas", headers=headers)
        assert planchas_res.status_code == 200
        planchas = [p for p in planchas_res.json() if p["estado"] is True and p["cantidad"] > 0]
        assert len(planchas) > 0, "No se encontraron planchas activas reales en Supabase."
        real_plancha = planchas[0]

        clientes_res = client.get("/api/clients", headers=headers)
        assert clientes_res.status_code == 200
        real_client = clientes_res.json()[0]

        print(f"   ✔ Usuario autenticado: A74000010")
        print(f"   ✔ Plancha real consultada (ID #{real_plancha['id_plancha']}): "
              f"{real_plancha['ancho_mm']} x {real_plancha['alto_mm']} mm (Espesor {real_plancha['espesor_mm']} mm)")
        print(f"   ✔ Cliente real consultado (ID #{real_client['id_cliente']}): {real_client['nombre_razon_social']}\n")

        report["real_plancha_used"] = {
            "id_plancha": real_plancha["id_plancha"],
            "ancho_mm": float(real_plancha["ancho_mm"]),
            "alto_mm": float(real_plancha["alto_mm"]),
            "espesor_mm": float(real_plancha["espesor_mm"]),
        }

        resolution_mm = 5.0
        material_geom = {
            "type": "RECTANGULO",
            "width_mm": float(real_plancha["ancho_mm"]),
            "height_mm": float(real_plancha["alto_mm"]),
        }
        material_mask = rasterize_material(material_geom, resolution_mm=resolution_mm)
        piece_geom = {"type": "RECTANGULO", "width_mm": 400.0, "height_mm": 400.0}
        piece_mask = rasterize_geometry(piece_geom, resolution_mm=resolution_mm)

        print("[2/3] Ejecutando inyección de patrones de corte inválidos...\n")

        # ------------------------------------------------------------------
        # CP-SEC-01: Superposición (OVERLAP)
        # ------------------------------------------------------------------
        layout = SheetLayout.empty(material_mask, margin_mm=15.0, separation_mm=10.0)
        # Colocar primera pieza en una zona válida (margen = 3 celdas -> fila 3, col 3)
        layout = layout.place(piece_mask, 3, 3)
        overlap_check = layout.check(piece_mask, 5, 5)
        rejected_overlap = False
        try:
            layout.place(piece_mask, 5, 5)
        except PlacementError as exc:
            rejected_overlap = True
            err_msg = str(exc)
        assert not overlap_check.is_valid and overlap_check.issue == PlacementIssue.OVERLAP and rejected_overlap
        print(f"  [CP-SEC-01] Superposición -> RECHAZADO ({overlap_check.issue.value}): {err_msg}")
        report["cases"].append({
            "id": "CP-SEC-01",
            "riesgo": "R-01 Colisión de cuchilla / doble rayado",
            "codigo_rechazo": overlap_check.issue.value,
            "detalle": err_msg,
            "rechazado": True,
        })

        # ------------------------------------------------------------------
        # CP-SEC-02: Invasión de margen perimetral (MARGIN)
        # ------------------------------------------------------------------
        layout_m = SheetLayout.empty(material_mask, margin_mm=15.0, separation_mm=10.0)
        margin_check = layout_m.check(piece_mask, 0, 0)
        rejected_margin = False
        try:
            layout_m.place(piece_mask, 0, 0)
        except PlacementError as exc:
            rejected_margin = True
            err_msg_m = str(exc)
        assert not margin_check.is_valid and margin_check.issue == PlacementIssue.MARGIN and rejected_margin
        print(f"  [CP-SEC-02] Invasión margen -> RECHAZADO ({margin_check.issue.value}): {err_msg_m}")
        report["cases"].append({
            "id": "CP-SEC-02",
            "riesgo": "R-02 Desportillamiento perimetral por tensión",
            "codigo_rechazo": margin_check.issue.value,
            "detalle": err_msg_m,
            "rechazado": True,
        })

        # ------------------------------------------------------------------
        # CP-SEC-03: Separación inferior al kerf (SEPARATION)
        # ------------------------------------------------------------------
        # piece_mask tiene 80 columnas (400/5). Colocada en col 3 ocupa cols 3..82.
        # Con separación de 10 mm (2 celdas), cols 83 y 84 están bloqueadas. Colocar en col 84 choca con separación.
        sep_check = layout.check(piece_mask, 3, 84)
        rejected_sep = False
        try:
            layout.place(piece_mask, 3, 84)
        except PlacementError as exc:
            rejected_sep = True
            err_msg_s = str(exc)
        assert not sep_check.is_valid and sep_check.issue == PlacementIssue.SEPARATION and rejected_sep
        print(f"  [CP-SEC-03] Separación insuficiente -> RECHAZADO ({sep_check.issue.value}): {err_msg_s}")
        report["cases"].append({
            "id": "CP-SEC-03",
            "riesgo": "R-03 Colapso de puente intermedio y astillamiento",
            "codigo_rechazo": sep_check.issue.value,
            "detalle": err_msg_s,
            "rechazado": True,
        })

        # ------------------------------------------------------------------
        # CP-SEC-04: Pieza fuera de límites (OUT_OF_BOUNDS)
        # ------------------------------------------------------------------
        oversized_geom = {
            "type": "RECTANGULO",
            "width_mm": float(real_plancha["ancho_mm"]) + 500.0,
            "height_mm": float(real_plancha["alto_mm"]) + 500.0,
        }
        oversized_mask = rasterize_geometry(oversized_geom, resolution_mm=resolution_mm)
        oob_check = layout_m.check(oversized_mask, 0, 0)
        rejected_oob = False
        try:
            layout_m.place(oversized_mask, 0, 0)
        except PlacementError as exc:
            rejected_oob = True
            err_msg_o = str(exc)
        assert not oob_check.is_valid and oob_check.issue == PlacementIssue.OUT_OF_BOUNDS and rejected_oob
        print(f"  [CP-SEC-04] Pieza fuera de límites -> RECHAZADO ({oob_check.issue.value}): {err_msg_o}")
        report["cases"].append({
            "id": "CP-SEC-04",
            "riesgo": "R-04 Corte al vacío e impacto contra mesa CNC",
            "codigo_rechazo": oob_check.issue.value,
            "detalle": err_msg_o,
            "rechazado": True,
        })

        # ------------------------------------------------------------------
        # CP-SEC-05: Polígono cóncavo y autointersecante vía POST /api/orders REAL
        # ------------------------------------------------------------------
        concave_payload = {
            "id_cliente": real_client["id_cliente"],
            "piezas": [{
                "id_tipo_vidrio": real_plancha["id_tipo_vidrio"],
                "espesor_mm": float(real_plancha["espesor_mm"]),
                "tipo_forma": "POLIGONO_CONVEXO",
                "cantidad": 1,
                "vertices_mm": [[0, 0], [200, 0], [200, 100], [100, 100], [100, 200], [0, 200]],  # Forma L cóncava
            }],
        }
        res_concave = client.post("/api/orders", headers=headers, json=concave_payload)
        assert res_concave.status_code == 422, f"Se esperaba HTTP 422 pero llegó {res_concave.status_code}"

        self_intersect_payload = {
            "id_cliente": real_client["id_cliente"],
            "piezas": [{
                "id_tipo_vidrio": real_plancha["id_tipo_vidrio"],
                "espesor_mm": float(real_plancha["espesor_mm"]),
                "tipo_forma": "POLIGONO_CONVEXO",
                "cantidad": 1,
                "vertices_mm": [[0, 0], [100, 100], [100, 0], [0, 100]],  # Moño / Autointersección
            }],
        }
        res_intersect = client.post("/api/orders", headers=headers, json=self_intersect_payload)
        assert res_intersect.status_code == 422, f"Se esperaba HTTP 422 pero llegó {res_intersect.status_code}"
        msg_concave = res_concave.json().get("detail", str(res_concave.json()))
        print(f"  [CP-SEC-05] Geometría cóncava y cruce HTTP -> RECHAZADO (HTTP 422): {msg_concave}")
        report["cases"].append({
            "id": "CP-SEC-05",
            "riesgo": "R-05 Estallido incontrolado en vértices cóncavos",
            "codigo_rechazo": "HTTP 422 Unprocessable Entity",
            "detalle": f"Cóncavo: {msg_concave} | Autointersección: HTTP 422",
            "rechazado": True,
        })

        # ------------------------------------------------------------------
        # CP-SEC-06: Confirmación incompleta e incompatibilidad de espesores
        # ------------------------------------------------------------------
        thick_decimal = Decimal(str(real_plancha["espesor_mm"]))
        glass_id = int(real_plancha["id_tipo_vidrio"])

        unit = PieceUnit(
            order_id=999,
            piece_id=1,
            unit_index=1,
            glass_type_id=glass_id,
            thickness_mm=thick_decimal,
            geometry={"type": "RECTANGULO", "width_mm": 100, "height_mm": 100},
            area_mm2=Decimal("10000"),
        )
        stock = StockCandidate(
            source=MaterialSource.SHEET,
            material_id=real_plancha["id_plancha"],
            physical_unit_index=1,
            glass_type_id=glass_id,
            thickness_mm=thick_decimal,
            geometry=material_geom,
            area_mm2=Decimal(str(real_plancha["ancho_mm"])) * Decimal(str(real_plancha["alto_mm"])),
        )
        group = MaterialGroup(
            glass_type_id=glass_id,
            thickness_mm=thick_decimal,
            units=(unit,),
            stock_candidates=(stock,),
        )
        cfg = OptimizationConfig(resolution_mm=Decimal("5"), margin_mm=Decimal("10"), separation_mm=Decimal("5"))
        prob = OptimizationProblem(order_ids=(999,), groups=(group,), config=cfg)

        incomplete_result = OptimizationResult(
            problem=prob,
            placements=(),
            metrics=None,
        )
        rejected_inc = False
        try:
            consumption_groups(incomplete_result)
        except ValueError as exc:
            rejected_inc = True
            err_msg_inc = str(exc)

        # Adicionalmente verificar rechazo por incompatibilidad de espesor/material
        wrong_stock = StockCandidate(
            source=MaterialSource.SHEET,
            material_id=9999,
            physical_unit_index=1,
            glass_type_id=glass_id,
            thickness_mm=thick_decimal + Decimal("2.0"),
            geometry=material_geom,
            area_mm2=Decimal("1000000"),
        )
        rejected_mat = False
        try:
            Placement(
                piece=unit,
                stock=wrong_stock,
                x_mm=Decimal("0"),
                y_mm=Decimal("0"),
                rotation_deg=Decimal("0"),
                geometry=unit.geometry,
            )
        except ValueError as exc:
            rejected_mat = True
            err_msg_mat = str(exc)

        assert rejected_inc and rejected_mat
        print(f"  [CP-SEC-06] Confirmación incompleta y cruce material -> RECHAZADO: {err_msg_inc} / {err_msg_mat}")
        report["cases"].append({
            "id": "CP-SEC-06",
            "riesgo": "R-06 Corte incompleto / mezcla de espesor incompatible",
            "codigo_rechazo": "NOT_CONFIRMABLE / MATERIAL_MISMATCH",
            "detalle": f"{err_msg_inc} | {err_msg_mat}",
            "rechazado": True,
        })

        # ------------------------------------------------------------------
        # CP-SEC-07: Colisión de identidad de retazo único
        # ------------------------------------------------------------------
        rejected_rem = False
        try:
            StockCandidate(
                source=MaterialSource.REMNANT,
                material_id=77,
                physical_unit_index=2,  # Index distinto de 1 prohibido para retazos físicos únicos
                glass_type_id=glass_id,
                thickness_mm=thick_decimal,
                geometry={"type": "RECTANGULO", "width_mm": 500, "height_mm": 500},
                area_mm2=Decimal("250000"),
            )
        except ValueError as exc:
            rejected_rem = True
            err_msg_rem = str(exc)
        assert rejected_rem
        print(f"  [CP-SEC-07] Doble asignación de retazo -> RECHAZADO (ValueError): {err_msg_rem}")
        report["cases"].append({
            "id": "CP-SEC-07",
            "riesgo": "R-07 Doble corte sobre retazo único agotado",
            "codigo_rechazo": "REMNANT_COLLISION / ValueError",
            "detalle": err_msg_rem,
            "rechazado": True,
        })

        # ------------------------------------------------------------------
        # CP-SEC-08: Control de Presupuesto Raster Anti-Bloqueo (OOM)
        # ------------------------------------------------------------------
        oversized_budget_geom = {"type": "RECTANGULO", "width_mm": 3000, "height_mm": 3000}
        rejected_budget = False
        try:
            HU015_RASTER_BUDGET.check(oversized_budget_geom, 0.5)  # 6000x6000 = 36M celdas > 1M
        except RasterBudgetExceeded as exc:
            rejected_budget = True
            err_msg_b = str(exc)
        assert rejected_budget
        print(f"  [CP-SEC-08] Presupuesto raster excedido -> RECHAZADO (RasterBudgetExceeded): {err_msg_b}\n")
        report["cases"].append({
            "id": "CP-SEC-08",
            "riesgo": "R-09 Agotamiento de memoria / congelamiento en turno",
            "codigo_rechazo": "RasterBudgetExceeded / HTTP 422",
            "detalle": err_msg_b,
            "rechazado": True,
        })

    total = len(report["cases"])
    rejected = sum(1 for c in report["cases"] if c["rechazado"])
    report["summary"] = {
        "total": total,
        "rejected_safely": rejected,
        "escapes": total - rejected,
        "rejection_rate_pct": round((rejected / total) * 100.0, 2),
    }

    RESULTS_OUT.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[3/3] Resumen Final de Seguridad Operacional:")
    print(f"   • Casos problemáticos evaluados : {total}")
    print(f"   • Casos rechazados a tiempo     : {rejected}")
    print(f"   • Fugas operacionales           : {total - rejected}")
    print(f"   • Tasa de Rechazo Seguro        : {report['summary']['rejection_rate_pct']}%")
    print(f"\n✔ Reporte JSON guardado en: {RESULTS_OUT}")


if __name__ == "__main__":
    run_safety_suite()
