# Error Handling & Logging Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-006
**Version:** 2.0
**Effective Date:** 2025-04-01
**Owner:** Backend Engineering Team
**Review Cycle:** Quarterly

---

## 1. Exception Hierarchy

- MUST define a project-specific exception hierarchy rooted at `AppError`.
- MUST NOT raise bare `Exception`, `ValueError`, or `RuntimeError` from application code.
- MUST map exceptions to HTTP status codes via a centralized exception handler.

```python
class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"

class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"

class AuthenticationError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"

class AuthorizationError(AppError):
    status_code = 403
    code = "FORBIDDEN"

class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"

class RateLimitError(AppError):
    status_code = 429
    code = "RATE_LIMITED"
```

## 2. Exception Usage

- MUST raise `NotFoundError` when a requested resource doesn't exist — not return `None` and let the caller crash.
- MUST raise `AuthorizationError` when the user lacks permission — not `NotFoundError` (don't leak resource existence).
- MUST NOT catch exceptions silently (`except: pass`). At minimum, log the error.
- MUST NOT use exceptions for control flow in normal execution paths.
- SHOULD catch the most specific exception type possible.
- SHOULD include context in exception messages: `NotFoundError(f"Post not found: {post_id}")`.

## 3. Logging

- MUST use `structlog` with JSON output for all application logging.
- MUST NOT use `print()` anywhere in application code.
- MUST NOT use the standard library `logging` directly — use the structlog wrapper.
- MUST include request ID in all log entries (via middleware context).
- MUST log at the appropriate level:

| Level | When |
|---|---|
| `debug` | Detailed diagnostic information (disabled in production) |
| `info` | Normal operations: request handled, user action completed |
| `warning` | Unexpected but recoverable: retry succeeded, deprecated API called |
| `error` | Operation failed: unhandled exception, external service down |

## 4. What to Log

- MUST log all authentication failures with IP address and user agent.
- MUST log all authorization failures with user ID and requested resource.
- MUST log all API responses with status code, latency, and endpoint.
- MUST log all external service calls with latency and success/failure.
- MUST NOT log passwords, tokens, session IDs, or API keys at any level.
- MUST NOT log personally identifiable information (PII) in plain text — use hashed identifiers or redact.
- MUST NOT log full request/response bodies at `info` level — only at `debug`.

## 5. Structured Log Format

- MUST use key-value pairs, not string formatting:
  ```python
  # CORRECT
  logger.info("post_created", user_id=uid, post_id=pid, latency_ms=42)

  # WRONG
  logger.info(f"User {uid} created post {pid} in 42ms")
  ```
- MUST use consistent key names across the codebase:
  - `user_id`, `post_id`, `comment_id` — resource identifiers
  - `latency_ms` — operation timing
  - `error` — error message string
  - `error_type` — exception class name
  - `status_code` — HTTP response code

## 6. Error Responses

- MUST return structured JSON error responses:
  ```json
  { "error": { "code": "NOT_FOUND", "message": "Post not found: p-123" } }
  ```
- MUST NOT expose stack traces, internal file paths, or database errors to clients.
- MUST include a correlation ID in error responses for debugging: `"request_id": "abc-123"`.
- SHOULD include a `detail` field for validation errors with field-level messages.

## 7. Monitoring Alerts

- MUST alert on error rate exceeding 1% of requests over a 5-minute window.
- MUST alert on p99 latency exceeding 2 seconds.
- MUST alert on unhandled exceptions (500 status codes).
- SHOULD alert on unusual patterns: sudden spike in 401/403 responses, new error types.

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*
