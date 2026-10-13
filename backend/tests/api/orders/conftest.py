from tests.integration.postgres_support import isolated_postgres  # noqa: F401
from tests.orders_support import orders_database, session_factory  # noqa: F401

import pytest


@pytest.fixture(autouse=True)
def inventory_reads_use_the_temporary_database(session_factory):
    from main import app
    from app.modules.orders.presentation.dependencies import get_inventory_session_factory

    original = app.dependency_overrides.get(get_inventory_session_factory)
    app.dependency_overrides[get_inventory_session_factory] = lambda: session_factory
    try:
        yield
    finally:
        if original is None:
            app.dependency_overrides.pop(get_inventory_session_factory, None)
        else:
            app.dependency_overrides[get_inventory_session_factory] = original
