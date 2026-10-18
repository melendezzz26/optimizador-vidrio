class DomainException(Exception):
    pass

class InvalidGeometryException(DomainException):
    pass

class InvalidOrderException(DomainException):
    pass


class OrderNotFoundException(DomainException):
    pass
