from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from threading import Barrier
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import Cliente
from app.modules.clients.application.dto import CreateClientData
from app.modules.clients.application.use_cases import create_client
from app.modules.clients.domain.client import NewClient
from app.modules.clients.domain.errors import DuplicateClientDocumentError
from app.modules.clients.infrastructure.sqlalchemy_client_repository import SqlAlchemyClientRepository

NEW = NewClient("Vidrios Norte", "TEST", "0001", None, datetime(2026, 10, 9, tzinfo=timezone.utc))


def test_roundtrip_commits_and_returns_detached_data(session_factory):
    with session_factory() as session:
        saved = SqlAlchemyClientRepository(session).add(NEW)
    assert saved.client_id > 0
    assert saved.name == NEW.name and saved.is_active
    assert saved.created_at.utcoffset().total_seconds() == 0
    with session_factory() as session:
        assert SqlAlchemyClientRepository(session).list_clients() == [saved]
        row = session.get(Cliente, saved.client_id)
        assert (row.tipo_documento, row.numero_documento, row.telefono) == ("TEST", "0001", None)


def test_database_duplicate_rolls_back_and_session_can_be_reused(session_factory):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        original = repository.add(NEW)
        with pytest.raises(DuplicateClientDocumentError) as caught:
            repository.add(replace(NEW, name="Duplicado"))
        assert caught.value.__cause__.orig.sqlstate == "23505"
        assert caught.value.__cause__.orig.diag.constraint_name == "uq_clientes_tipo_numero_documento"
        assert repository.list_clients() == [original]
        second = repository.add(replace(NEW, document_number="0002"))
        assert second.client_id != original.client_id


def test_inactive_client_still_reserves_document_and_is_listed(session_factory):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        original = repository.add(NEW)
        session.execute(sa.update(Cliente).where(Cliente.id_cliente == original.client_id).values(estado=False))
        session.commit()
        assert repository.list_clients()[0].is_active is False
        with pytest.raises(DuplicateClientDocumentError):
            repository.add(NEW)


def test_different_type_and_nullable_documents_follow_existing_constraint(session_factory):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        repository.add(NEW)
        repository.add(replace(NEW, document_type="OTHER"))
        for document_type, document_number in [(None, None), ("TEST", None), (None, "0001")]:
            for _ in range(2):
                repository.add(replace(NEW, document_type=document_type, document_number=document_number))
        assert len(repository.list_clients()) == 8


@pytest.mark.parametrize("filters, expected", [
    ({}, ["Vidrios Norte", "Taller Sur", "NORTE pequeño"]),
    ({"document": "0001"}, ["Vidrios Norte"]),
    ({"document": "001"}, []),
    ({"query": "nOrTe"}, ["Vidrios Norte", "NORTE pequeño"]),
    ({"query": "ausente"}, []),
    ({"document": "0001", "query": "sur"}, []),
    ({"document": "0001", "query": "norte"}, ["Vidrios Norte"]),
])
def test_search_and_stable_listing(session_factory, filters, expected):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        for i, name in enumerate(["Vidrios Norte", "Taller Sur", "NORTE pequeño"], start=1):
            repository.add(replace(NEW, name=name, document_number=f"{i:04d}"))
        assert [client.name for client in repository.list_clients(**filters)] == expected


@pytest.mark.parametrize("query", ["%", "_", "/", "\\", "' OR 1=1 --"])
def test_name_search_treats_wildcards_and_sql_as_literal_text(session_factory, query):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        repository.add(NEW)
        special = repository.add(replace(NEW, name=f"Taller {query} Especial", document_number="2"))
        assert repository.list_clients(query=query) == [special]


def test_unrelated_constraint_failure_is_not_a_duplicate(session_factory):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        with pytest.raises(IntegrityError) as caught:
            repository.add(replace(NEW, name=None))
        assert caught.value.orig.sqlstate == "23502"
        assert repository.list_clients() == []
        assert repository.add(NEW).is_active


def test_commit_failure_rolls_back_flushed_client(session_factory):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        with patch.object(session, "commit", side_effect=SQLAlchemyError("synthetic commit failure")):
            with pytest.raises(SQLAlchemyError):
                repository.add(NEW)
        assert repository.list_clients() == []
        assert repository.add(NEW).name == NEW.name


def test_concurrent_creations_cannot_duplicate_document(session_factory):
    barrier = Barrier(2)

    def create():
        with session_factory() as session:
            barrier.wait(timeout=15)
            try:
                create_client(CreateClientData("Concurrente", "TEST", "race"),
                              repository=SqlAlchemyClientRepository(session))
                return "created"
            except DuplicateClientDocumentError:
                return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create(), range(2)))
    assert sorted(results) == ["created", "duplicate"]
    with session_factory() as session:
        assert len(SqlAlchemyClientRepository(session).list_clients(document="race")) == 1


def test_create_does_not_read_after_commit_and_list_uses_one_select(session_factory):
    with session_factory() as session:
        repository = SqlAlchemyClientRepository(session)
        statements = []

        def capture(connection, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        engine = session.get_bind()
        sa.event.listen(engine, "before_cursor_execute", capture)
        try:
            repository.add(NEW)
            assert len(statements) == 1 and statements[0].startswith("INSERT")
            statements.clear()
            repository.list_clients(query="Norte")
            assert len(statements) == 1 and statements[0].startswith("SELECT")
        finally:
            sa.event.remove(engine, "before_cursor_execute", capture)
