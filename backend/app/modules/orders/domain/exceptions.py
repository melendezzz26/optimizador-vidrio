class DomainException(Exception):
    pass

class InvalidGeometryException(DomainException):
    pass

class InvalidOrderException(DomainException):
    pass


class OrderNotFoundException(DomainException):
    pass


class OrderStateConflictException(DomainException):
    """The order exists but its current state prevents this mutation."""

    pass
