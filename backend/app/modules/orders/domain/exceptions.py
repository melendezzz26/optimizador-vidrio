class DomainException(Exception):
    pass

class InvalidGeometryException(DomainException):
    pass

class InvalidOrderException(DomainException):
    pass


class NoCompatibleStockException(DomainException):
    def __init__(self, pieces: list[dict[str, str | int]]) -> None:
        super().__init__("Una o m\u00e1s piezas no tienen material compatible disponible.")
        self.pieces = pieces


class OrderNotFoundException(DomainException):
    pass


class OrderStateConflictException(DomainException):
    """The order exists but its current state prevents this mutation."""

    pass
