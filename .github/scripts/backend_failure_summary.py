"""Create a deliberately restricted CI report from local pytest JUnit files."""
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

PHASES = ('general', 'comparison-calculation', 'comparison-supervision', 'sequential-runner', 'comparison-runner')
SAFE_NAME = re.compile(r'^[A-Za-z0-9_./:\[\]-]{1,200}$')
EXCEPTION = re.compile(r'\b(AssertionError|TimeoutError|RuntimeError|ValueError|TypeError|KeyError|ImportError|ModuleNotFoundError|OperationalError|IntegrityError|ProgrammingError|WorkersNotStopped|Failed|Error)\b')
LOCATION = re.compile(r'\b(tests/[A-Za-z0-9_./-]+\.py):(\d+)')
HTTP_ASSERTION = re.compile(r'\bassert (\d{3}) == (\d{3})\b')


def build_report(directory):
    lines = ['## Diagnóstico seguro de backend', '']
    for phase in PHASES:
        path = directory / (phase + '.xml')
        if not path.exists():
            lines.append(f'- {phase}: no ejecutada o sin informe.')
            continue
        try:
            root = ElementTree.parse(path).getroot()
            suites = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
            counts = {key: sum(int(s.get(key, '0')) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
            passed = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
            lines.append(f"- {phase}: {passed} aprobadas, {counts['failures']} fallidas, {counts['errors']} errores, {counts['skipped']} omitidas.")
            for case in root.iter('testcase'):
                failure = case.find('failure')
                if failure is None:
                    failure = case.find('error')
                if failure is None:
                    continue
                # Parametrized values can contain credentials or request data.
                name = case.get('classname', '') + '::' + case.get('name', '').split('[', 1)[0]
                name = name if SAFE_NAME.fullmatch(name) else '[nombre omitido]'
                text = (failure.get('message') or '') + '\n' + (failure.text or '')
                kind = EXCEPTION.search(text)
                locations = list(dict.fromkeys(f'{m.group(1)}:{m.group(2)}' for m in LOCATION.finditer(text)))[:5]
                comparison = HTTP_ASSERTION.search(text)
                safe_assertion = f'; HTTP observado {comparison.group(1)}, esperado {comparison.group(2)}' if comparison else ''
                lines.append(f"  - {name}: {kind.group(1) if kind else 'fallo sin tipo reconocido'}; ubicaciones: {', '.join(locations) if locations else 'no disponibles'}{safe_assertion}.")
        except (ElementTree.ParseError, OSError, ValueError):
            lines.append(f'- {phase}: informe ilegible.')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(build_report(Path(sys.argv[1])), encoding='utf-8')
