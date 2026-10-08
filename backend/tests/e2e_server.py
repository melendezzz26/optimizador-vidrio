"""Local browser-test server; never reads a shared DATABASE_URL or real users.

Run from backend: python -m tests.e2e_server
Requires the same PostgreSQL binaries as the integration suite.
"""
import os
import json
from pathlib import Path
import secrets
import tempfile
import sys
from datetime import datetime, timezone

import sqlalchemy as sa
import uvicorn

from tests.integration.postgres_support import temporary_postgres, new_database, upgrade, _run

STATE = Path(tempfile.gettempdir()) / "newglass-orders-e2e-8017.json"


def stop():
    """Playwright on Windows terminates Python without running finally blocks."""
    if not STATE.exists():
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    root = Path(state["root"]).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve()
    assert root.name.startswith("newglass-orders-e2e-")
    data = root / "data"
    if (data / "postmaster.pid").exists():
        options = (data / "postmaster.opts").read_text(encoding="utf-8")
        postgres = Path(options.split(' "-D"')[0].strip('" \n'))
        pg_ctl = postgres.with_name("pg_ctl" + postgres.suffix)
        status = _run([pg_ctl, "-D", data, "status"])
        assert status.returncode in (0, 3), status.stderr
        if status.returncode == 0:
            result = _run([pg_ctl, "-D", data, "-m", "fast", "-w", "stop"])
            assert result.returncode == 0, result.stderr
    STATE.unlink()


def main():
    root = Path(tempfile.mkdtemp(prefix="newglass-orders-e2e-"))
    with temporary_postgres(root) as cluster, new_database(cluster) as engine:
        os.environ["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)
        # Only synthetic loopback connection details; useful for manual evidence.
        STATE.write_text(json.dumps({"root": str(root), "database_url": os.environ["DATABASE_URL"]}), encoding="utf-8")
        os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
        os.environ["TOKEN_MINUTOS"] = "480"
        result = upgrade(engine, "head")
        if result.returncode:
            raise RuntimeError(result.stderr)

        from app.shared.security import hash_password

        with engine.begin() as connection:
            connection.execute(sa.text("INSERT INTO roles(id_rol,nombre) VALUES (1,'Operario')"))
            connection.execute(sa.text("""
                INSERT INTO usuarios(dni,nombres,apellidos,usuario,password_hash,id_rol,fecha_creacion)
                VALUES ('70000001','Operario','Prueba','O70000001',:password,1,:now)
            """), {"password": hash_password("Orders-test-2026!"), "now": datetime.now(timezone.utc)})
            connection.execute(sa.text("INSERT INTO tipos_vidrio(id_tipo_vidrio,nombre,estado) VALUES (7,'Material de prueba',true)"))
            connection.execute(sa.text("INSERT INTO tipos_vidrio_espesores VALUES (7,5.5),(7,6)"))

        for command in ("heads", "current"):
            result = _run([sys.executable, "-m", "alembic", command], env=os.environ)
            print(f"python -m alembic {command}\n{result.stdout}{result.stderr}", flush=True)
            if result.returncode:
                raise RuntimeError("Alembic inspection failed")
        print("Synthetic local database: " + os.environ["DATABASE_URL"], flush=True)
        uvicorn.run("main:app", host="127.0.0.1", port=8017, log_level="warning")


if __name__ == "__main__":
    stop() if "--stop" in sys.argv else main()
