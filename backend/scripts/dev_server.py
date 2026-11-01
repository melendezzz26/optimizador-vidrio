"""WSL/Linux development server; reload watches application source only."""
import argparse
from pathlib import Path


def server_options(backend=None, *, reload=False, port=8000):
    root = Path(backend or Path(__file__).resolve().parents[1]).resolve()
    options = dict(app="main:app", app_dir=str(root), host="127.0.0.1", port=port, reload=reload)
    if reload:
        # Uvicorn recognizes existing absolute directories as excluded trees.
        # Nonexistent absolute glob patterns are rejected by pathlib on 3.11.
        options.update(reload_dirs=[str(root)], reload_excludes=[
            str(root / name) for name in (".venv", "venv", "tests", "scripts", "alembic", ".pytest_cache")
            if (root / name).is_dir()
        ] + ["seed.py"])
    return options


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    import uvicorn
    uvicorn.run(**server_options(reload=args.reload, port=args.port))


if __name__ == "__main__":
    main()
