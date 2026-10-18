from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.modules.clients.application.dto import CreateClientData
from app.modules.clients.application.ports import ClientRepository
from app.modules.clients.application.use_cases import create_client, list_clients
from app.modules.clients.domain.client import Client
from app.modules.clients.domain.errors import DuplicateClientDocumentError, InvalidClientDataError

NOW = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)


@pytest.fixture
def repository():
    return Mock(spec=ClientRepository)


def test_create_normalizes_outer_spaces_and_uses_server_clock(repository):
    repository.add.return_value = Client(7, "Vidrios  Norte", "TEST", "0001", "+51 123", True, NOW)
    result = create_client(
        CreateClientData("  Vidrios  Norte ", " TEST ", " 0001 ", " +51 123 "),
        repository=repository, now=lambda: NOW,
    )
    saved = repository.add.call_args.args[0]
    assert (saved.name, saved.document_type, saved.document_number, saved.phone) == (
        "Vidrios  Norte", "TEST", "0001", "+51 123",
    )
    assert saved.created_at == NOW
    assert result.client_id == 7 and result.is_active


@pytest.mark.parametrize("name", ["", " ", "\t\n", None, 42, True, "Nulo\0"])
def test_invalid_name_never_reaches_persistence(repository, name):
    with pytest.raises(InvalidClientDataError, match="nombre_razon_social"):
        create_client(CreateClientData(name), repository=repository)
    repository.add.assert_not_called()


@pytest.mark.parametrize("value", [None, "", " \t "])
def test_empty_optional_values_become_null(repository, value):
    create_client(CreateClientData("Cliente", value, value, value), repository=repository)
    saved = repository.add.call_args.args[0]
    assert (saved.document_type, saved.document_number, saved.phone) == (None, None, None)


@pytest.mark.parametrize("field", ["document_type", "document_number", "phone"])
@pytest.mark.parametrize("value", [42, False, "bad\0"])
def test_invalid_optional_text_is_rejected(repository, field, value):
    with pytest.raises(InvalidClientDataError):
        create_client(CreateClientData("Cliente", **{field: value}), repository=repository)
    repository.add.assert_not_called()


def test_document_has_no_catalog_length_or_pair_requirement(repository):
    for document_type, document_number in [("TIPO-LIBRE", None), (None, "X"), ("X", "A" * 40)]:
        create_client(CreateClientData("Cliente", document_type, document_number), repository=repository)
        saved = repository.add.call_args.args[0]
        assert (saved.document_type, saved.document_number) == (document_type, document_number)


def test_duplicate_from_database_is_propagated(repository):
    repository.add.side_effect = DuplicateClientDocumentError()
    with pytest.raises(DuplicateClientDocumentError):
        create_client(CreateClientData("Cliente", "TEST", "1"), repository=repository)


def test_clock_is_converted_to_utc(repository):
    local = NOW.astimezone(timezone(timedelta(hours=-8)))
    create_client(CreateClientData("Cliente"), repository=repository, now=lambda: local)
    assert repository.add.call_args.args[0].created_at == NOW
    assert repository.add.call_args.args[0].created_at.tzinfo is timezone.utc


def test_naive_clock_is_not_persisted(repository):
    with pytest.raises(ValueError, match="zona horaria"):
        create_client(CreateClientData("Cliente"), repository=repository, now=lambda: NOW.replace(tzinfo=None))
    repository.add.assert_not_called()


@pytest.mark.parametrize("filters, expected", [
    ({}, {"document": None, "query": None}),
    ({"document": " 001 "}, {"document": "001", "query": None}),
    ({"query": " Norte "}, {"document": None, "query": "Norte"}),
    ({"document": "001", "query": "Norte"}, {"document": "001", "query": "Norte"}),
])
def test_list_and_search_return_repository_results(repository, filters, expected):
    repository.list_clients.return_value = [Client(1, "Norte", None, "001", None, False, NOW)]
    assert list_clients(repository=repository, **filters) == repository.list_clients.return_value
    repository.list_clients.assert_called_once_with(**expected)


@pytest.mark.parametrize("field", ["document", "query"])
@pytest.mark.parametrize("value", ["", " \t", "bad\0", 123])
def test_invalid_search_does_not_list_every_client(repository, field, value):
    with pytest.raises(InvalidClientDataError):
        list_clients(repository=repository, **{field: value})
    repository.list_clients.assert_not_called()
