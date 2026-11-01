from uvicorn import Config
from uvicorn.supervisors.watchfilesreload import FileFilter

from scripts.dev_server import server_options


def test_reload_watches_source_and_excludes_nested_validation_scripts(tmp_path):
    for name in ("app", ".venv/validation/nested", "venv/lib", "tests", "scripts", "alembic/versions"):
        (tmp_path / name).mkdir(parents=True)
    options = server_options(tmp_path, reload=True)
    options.pop("app_dir")  # uvicorn.run handles this before constructing Config.
    filter = FileFilter(Config(**options))
    assert filter(tmp_path / "main.py")
    assert filter(tmp_path / "app/module.py")
    for path in (".venv/validation/nested/export.py", "venv/lib/library.py", "tests/test_case.py",
                 "scripts/temporary.py", "alembic/versions/revision.py", "seed.py"):
        assert not filter(tmp_path / path), path


def test_stable_server_does_not_enable_reload_or_extra_workers():
    options = server_options()
    assert options["reload"] is False and "workers" not in options
    assert "reload_dirs" not in options
