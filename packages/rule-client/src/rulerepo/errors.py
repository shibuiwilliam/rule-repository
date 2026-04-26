"""SDK-specific exceptions, mapped from HTTP status codes."""


class RuleRepoError(Exception):
    """Base exception for the Rule Repository SDK."""

    def __init__(self, message: str, status_code: int = 0, code: str = "") -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(RuleRepoError):
    """The requested resource was not found (404)."""

    pass


class ValidationError(RuleRepoError):
    """The request failed validation (422)."""

    pass


class AuthenticationError(RuleRepoError):
    """Authentication failed (401)."""

    pass


class AuthorizationError(RuleRepoError):
    """Insufficient permissions (403)."""

    pass


class ServerError(RuleRepoError):
    """The server returned an unexpected error (5xx)."""

    pass


def raise_for_status(status_code: int, body: dict) -> None:
    """Raise an appropriate SDK exception based on HTTP status code.

    Args:
        status_code: HTTP response status code.
        body: Response body parsed as dict.

    Raises:
        NotFoundError: For 404 responses.
        ValidationError: For 422 responses.
        AuthenticationError: For 401 responses.
        AuthorizationError: For 403 responses.
        ServerError: For 5xx responses.
        RuleRepoError: For other non-2xx responses.
    """
    if 200 <= status_code < 300:
        return

    error = body.get("error", {})
    message = error.get("message", f"HTTP {status_code}")
    code = error.get("code", "")

    match status_code:
        case 404:
            raise NotFoundError(message, status_code, code)
        case 422:
            raise ValidationError(message, status_code, code)
        case 401:
            raise AuthenticationError(message, status_code, code)
        case 403:
            raise AuthorizationError(message, status_code, code)
        case s if s >= 500:
            raise ServerError(message, status_code, code)
        case _:
            raise RuleRepoError(message, status_code, code)
