# API Design Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-002
**Version:** 2.5
**Effective Date:** 2025-04-01
**Owner:** Backend Engineering Team
**Review Cycle:** Quarterly

---

## 1. Framework

- MUST use FastAPI for all HTTP endpoints.
- MUST use Pydantic v2 models for request validation and response serialization.
- MUST NOT use Flask, Django, or other frameworks without architecture review approval.

## 2. URL Structure

- MUST version all APIs: `/api/v1/...`, `/api/v2/...`.
- MUST use plural nouns for resource collections: `/api/v1/users`, `/api/v1/posts`, `/api/v1/comments`.
- MUST use kebab-case for multi-word URL segments: `/api/v1/friend-requests`, not `/api/v1/friendRequests`.
- MUST NOT embed actions in URLs: use `POST /api/v1/posts/{id}/likes` instead of `POST /api/v1/posts/{id}/like-post`.
- MUST use path parameters for resource identity: `/api/v1/users/{user_id}`.
- MUST use query parameters for filtering, sorting, and pagination: `?page=2&page_size=20&sort=-created_at`.

## 3. HTTP Methods

| Method | Use | Idempotent |
|---|---|---|
| GET | Read a resource or collection | Yes |
| POST | Create a resource or trigger an action | No |
| PUT | Full replacement of a resource | Yes |
| PATCH | Partial update of a resource | No |
| DELETE | Remove a resource (soft-delete preferred) | Yes |

- MUST use the correct HTTP method for each operation.
- MUST NOT use GET for operations that modify state.
- MUST NOT use POST for idempotent operations that PUT or PATCH would cover.

## 4. Request Validation

- MUST validate all request bodies with Pydantic models.
- MUST use `Field(...)` with constraints: `min_length`, `max_length`, `ge`, `le`, `pattern`.
- MUST NOT trust client-supplied IDs for authorization — always re-derive from the authenticated user.
- MUST limit request body size: 1 MB for JSON, 10 MB for file uploads (configurable per endpoint).
- MUST validate pagination parameters: `page >= 1`, `1 <= page_size <= 100`.

## 5. Response Format

- MUST return JSON for all API responses.
- MUST use consistent envelope for collections:
  ```json
  { "items": [...], "total": 42, "page": 1, "page_size": 20 }
  ```
- MUST use consistent error format:
  ```json
  { "error": { "code": "NOT_FOUND", "message": "User not found: u-123" } }
  ```
- MUST include `created_at` and `updated_at` timestamps in resource responses (ISO 8601 format).
- MUST NOT expose internal IDs (database row IDs) — use UUIDs or opaque string identifiers.

## 6. Status Codes

| Code | When |
|---|---|
| 200 | Successful read or update |
| 201 | Resource created |
| 204 | Successful delete (no body) |
| 400 | Client error (malformed request) |
| 401 | Authentication required |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (duplicate, state violation) |
| 422 | Validation error (Pydantic) |
| 429 | Rate limited |
| 500 | Internal server error |

- MUST use the correct status code for each response.
- MUST NOT return 200 for error conditions.
- MUST NOT return 500 for client errors.

## 7. Pagination

- MUST implement cursor-based pagination for timelines and feeds (high-volume, real-time data).
- MAY use offset-based pagination for admin or search endpoints.
- MUST default to `page_size=20` and cap at `page_size=100`.
- MUST return `total` count only when the client explicitly requests it (`?include_total=true`) — counting is expensive on large tables.

## 8. Rate Limiting

- MUST implement rate limiting on all public endpoints.
- MUST return `429 Too Many Requests` with `Retry-After` header when limits are exceeded.
- SHOULD use sliding window rate limiting (not fixed window).
- Default limits: 100 requests/minute for authenticated users, 20/minute for unauthenticated.

## 9. Documentation

- MUST document all endpoints with OpenAPI annotations (FastAPI auto-generates from type hints).
- MUST include `summary`, `description`, and `response_model` on every endpoint.
- MUST include example request/response bodies for complex endpoints.
- SHOULD tag endpoints by domain: `users`, `posts`, `comments`, `notifications`, `admin`.

## 10. Deprecation

- MUST NOT remove API endpoints without a deprecation period of at least 3 months.
- MUST mark deprecated endpoints with `Deprecated: true` in OpenAPI spec and return `Sunset` header.
- SHOULD provide migration documentation when deprecating endpoints.

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*
