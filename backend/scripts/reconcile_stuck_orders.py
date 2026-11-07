"""Reconcilia pedidos atascados en EN_OPTIMIZACION (cierre de observaciones S2, F6).

Por defecto es un DRY-RUN: solo lee e informa. Con --apply devuelve a PENDIENTE
solo los casos A (sin optimización vinculada) y B (todas sus optimizaciones
terminales, sin consumo ni confirmación). C, D y E solo se informan.

Uso, desde backend\\ (o en Heroku: cd backend && ...):
    python -m scripts.reconcile_stuck_orders                   # dry-run
    python -m scripts.reconcile_stuck_orders --report -        # dry-run + JSON por stdout
    python -m scripts.reconcile_stuck_orders --apply --report -
    python -m scripts.reconcile_stuck_orders --order 8 --order 9

Usa los repositorios de la aplicación (sin SQL manual) y la base configurada en
el entorno. No imprime ni lee secretos. Acordado por el equipo para Staging.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
import sys

from app.modules.optimization.application.order_reconciliation import RECOVERABLE, ReconcileStuckOrders


def build_report(entries, *, apply):
    rows = [{**asdict(entry), "case": entry.case.value} for entry in entries]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if apply else "dry-run",
        "summary": {
            "stuck_orders": len(entries),
            "recoverable": sum(entry.case in RECOVERABLE for entry in entries),
            "changed": sum(entry.applied for entry in entries),
            "by_case": {case: sum(entry.case.value == case for entry in entries) for case in "ABCDE"},
        },
        "entries": rows,
    }


def print_table(entries, *, apply, out):
    print(f"Modo: {'APPLY (escribe)' if apply else 'DRY-RUN (no escribe)'}", file=out)
    print(f"{'Pedido':>7}  Caso  {'Antes':<16} {'Después':<16} Aplicado  Optimizaciones / motivo", file=out)
    for entry in entries:
        linked = ", ".join(f"#{link.optimization_id} {link.status}" for link in entry.optimizations) or "ninguna"
        print(f"{entry.order_id:>7}  {entry.case.value:<4}  {entry.before:<16} {entry.after:<16} "
              f"{'sí' if entry.applied else 'no':<8}  {linked} — {entry.reason}", file=out)
    print(f"Total: {len(entries)} pedidos en EN_OPTIMIZACION; "
          f"{sum(entry.applied for entry in entries)} cambiados.", file=out)


def main(argv=None, *, unit_of_work=None, out=sys.stdout):
    parser = argparse.ArgumentParser(description="Reconcilia pedidos atascados en EN_OPTIMIZACION (dry-run por defecto).")
    parser.add_argument("--apply", action="store_true", help="Escribe los cambios de los casos A y B.")
    parser.add_argument("--order", type=int, action="append", dest="orders",
                        help="Limita a este pedido; se puede repetir.")
    parser.add_argument("--report", help="Ruta del informe JSON; '-' lo imprime por la salida estándar.")
    args = parser.parse_args(argv)
    if args.orders and any(order <= 0 for order in args.orders):
        parser.error("--order debe ser un entero positivo")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if unit_of_work is None:
        from app.shared.database.session import SessionLocal
        from app.modules.optimization.infrastructure.order_reconciliation_repository import SqlStuckOrdersUnitOfWork
        unit_of_work = lambda: SqlStuckOrdersUnitOfWork(SessionLocal)  # noqa: E731
    entries = ReconcileStuckOrders(unit_of_work).execute(apply=args.apply, order_ids=args.orders)
    print_table(entries, apply=args.apply, out=out)
    if args.report:
        data = json.dumps(build_report(entries, apply=args.apply), ensure_ascii=False, indent=2)
        if args.report == "-":
            print(data, file=out)
        else:
            with open(args.report, "w", encoding="utf-8") as report:
                report.write(data + "\n")
            print(f"Informe JSON: {args.report}", file=out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
