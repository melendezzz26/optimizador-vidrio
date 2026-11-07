"""Reconcile one FF run after stopping/verifying ALL web/calculator processes.

No automatic restart or HTTP recovery: FF has no durable process identity.
--service-stopped is the operator's explicit attestation, not a PID check.
Use only against an authorized database after verifying the maintenance window.
"""
import argparse

from app.modules.optimization.application.run_recovery import RecoverStoppedRun


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('optimization_id', type=int)
    parser.add_argument('--service-stopped', action='store_true', required=True,
                        help='Attest all service/calculator processes have been stopped and verified.')
    args = parser.parse_args()
    if args.optimization_id <= 0:
        parser.error('optimization_id must be positive')
    from app.shared.database.session import SessionLocal
    from app.modules.optimization.infrastructure.run_uow import SqlRunUnitOfWork
    run = RecoverStoppedRun(lambda: SqlRunUnitOfWork(SessionLocal)).execute(
        args.optimization_id, service_stopped=args.service_stopped)
    print(f'{run.optimization_id}: {run.status.value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
