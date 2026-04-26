"""Project-specific exception hierarchy.

All application errors should inherit from RuleRepoError.
Never raise bare Exception in application code.
"""


class RuleRepoError(Exception):
    """Base exception for all Rule Repository errors."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(RuleRepoError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            code="NOT_FOUND",
            status_code=404,
        )


class ValidationError(RuleRepoError):
    """Raised when input data fails validation beyond Pydantic checks."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422)


class ConflictError(RuleRepoError):
    """Raised when an operation conflicts with existing state."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, code="CONFLICT", status_code=409)


class AuthorizationError(RuleRepoError):
    """Raised when the caller lacks permission for the requested action."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class AuthenticationError(RuleRepoError):
    """Raised when authentication fails or is missing."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401)


class ExternalServiceError(RuleRepoError):
    """Raised when an external service (LLM, DB, search) fails."""

    def __init__(self, service: str, message: str) -> None:
        super().__init__(
            message=f"{service} error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
        )
