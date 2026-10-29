"""Exception hierarchy for smartposti_tracker."""


class TrackingError(Exception):
    """Base class for all errors raised by this library."""


class AuthError(TrackingError):
    """Fetching the anonymous access token failed."""


class APIError(TrackingError):
    """The tracking API returned an HTTP error or GraphQL errors."""

    def __init__(self, message, status_code=None, errors=None):
        super().__init__(message)
        self.status_code = status_code
        self.errors = errors or []


class ShipmentNotFound(TrackingError):
    """No shipment matches the given tracking code."""

    def __init__(self, code):
        super().__init__(f"shipment not found: {code}")
        self.code = code
