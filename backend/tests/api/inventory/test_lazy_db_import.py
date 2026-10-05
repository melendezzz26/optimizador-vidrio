import subprocess
import sys

def test_main_does_not_import_database():
    code = (
        "import sys\n"
        "import main\n"
        "if 'app.shared.database' in sys.modules:\n"
        "    sys.exit(1)\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Error: Database fue importado o hubo un error: {result.stderr} {result.stdout}"
    assert "OK" in result.stdout
