"""Diagnóstico local sin DB ni credenciales; no sustituye una comparación real."""
from dataclasses import asdict
import argparse
import json
import platform
import sys

from app.modules.optimization.application.comparison_limits import DEFAULT_COMPARISON_BUDGET
from app.modules.optimization.application.errors import RunError
from app.modules.optimization.infrastructure.comparison_runner import ComparisonProcessRunner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=('comparison-v1','comparison-v2'),default='comparison-v1')
    profile=parser.parse_args().profile
    service=ComparisonProcessRunner()
    if profile=='comparison-v2':
        from app.modules.optimization.infrastructure.sequential_runner import SequentialProcessRunner
        service=SequentialProcessRunner()
    report = {
        "python": platform.python_version(),
        "platform": sys.platform,
        "budget": asdict(DEFAULT_COMPARISON_BUDGET),
        "profile": profile,
    }
    try:
        service.preflight()
    except RunError as error:
        report.update(available=False, code=error.code, message=error.message)
        if error.__cause__ is not None:
            report["reason"] = type(error.__cause__).__name__
        status = 1
    else:
        report.update(available=True)
        status = 0
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
