"""ST-INC-02: migrate ONLY the private PostgreSQL started by the E2E harness."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import sqlalchemy as sa

from tests.e2e_server import STATE
from tests.integration.postgres_support import upgrade, schema_snapshot
from tests.integration.test_s1_rbac_migration import downgrade
from tests.comparison_history import history_bytes, revision

PREVIOUS = "s2cmp01a1b2c"
CURRENT = "s2cmp02d4e6f8"


def main():
    state = json.loads(STATE.read_text())
    root = Path(state["root"]).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve()
    assert root.name.startswith("newglass-orders-e2e-") and (root / "data/postmaster.pid").exists()
    url = sa.engine.make_url(state["database_url"])
    assert url.host == "127.0.0.1" and url.username == "r1_test" and url.database.startswith("r1_")
    engine = sa.create_engine(url)
    try:
        if "--prepare" in sys.argv:
            result = downgrade(engine, PREVIOUS)
            assert result.returncode == 0, result.stderr
            assert revision(engine) == PREVIOUS
            print(json.dumps({"prepared_revision": PREVIOUS, "isolated": True}))
            return
        assert revision(engine) == PREVIOUS
        before = history_bytes(engine)
        assert all(json.loads(before[t]) for t in ("optimizaciones", "ejecuciones_optimizacion", "metricas_ejecucion"))
        checks_before = schema_snapshot(engine, ["ejecuciones_optimizacion"])
        result = upgrade(engine, CURRENT)
        assert result.returncode == 0, result.stderr
        after = history_bytes(engine)
        assert before == after and revision(engine) == CURRENT
        digest = lambda values: {t: hashlib.sha256(v.encode()).hexdigest() for t, v in values.items()}
        print(json.dumps(dict(result="PASS", previous_revision=PREVIOUS, new_revision=CURRENT,
            rows={t: len(json.loads(v)) for t, v in before.items()}, before_sha256=digest(before),
            after_sha256=digest(after), constraints_before=checks_before,
            constraints_after=schema_snapshot(engine, ["ejecuciones_optimizacion"])), default=str))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
