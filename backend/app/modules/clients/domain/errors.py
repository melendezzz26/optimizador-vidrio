"""Errores del contrato de clientes."""


class InvalidClientDataError(ValueError):
    pass


class DuplicateClientDocumentError(Exception):
    pass
