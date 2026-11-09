"""The published CI summary must not include arbitrary failure output."""
import importlib.util
from pathlib import Path


path = Path(__file__).resolve().parents[3] / '.github/scripts/backend_failure_summary.py'
spec = importlib.util.spec_from_file_location('backend_failure_summary', path)
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


def test_summary_reports_failure_location_without_secrets(tmp_path):
    (tmp_path / 'general.xml').write_text('''<testsuites><testsuite tests="3" failures="1" errors="0" skipped="1">
      <testcase classname="tests.test_demo" name="test_capacity[small]"><failure message="AssertionError: TOKEN_PRIVATE">
      tests/api/test_demo.py:42: AssertionError: TOKEN_PRIVATE
      postgresql://user:password@example.invalid/db
      </failure></testcase></testsuite></testsuites>''', encoding='utf-8')
    report = reporter.build_report(tmp_path)
    assert '1 aprobadas, 1 fallidas, 0 errores, 1 omitidas' in report
    assert 'tests.test_demo::test_capacity' in report and '[small]' not in report
    assert 'AssertionError' in report and 'tests/api/test_demo.py:42' in report
    assert 'TOKEN_PRIVATE' not in report and 'password' not in report
    assert 'comparison-runner: no ejecutada' in report


def test_untrusted_test_name_is_not_published(tmp_path):
    (tmp_path / 'general.xml').write_text('''<testsuite tests="1" failures="1" errors="0" skipped="0">
      <testcase classname="test" name="SECRET VALUE"><failure message="oops"/></testcase></testsuite>''', encoding='utf-8')
    assert 'SECRET VALUE' not in reporter.build_report(tmp_path)
