# Database & Data Access Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-003  
**Version:** 2.0  
**Effective Date:** 2025-04-01  
**Owner:** Backend Engineering Team  
**Review Cycle:** Quarterly

---

## 1. Database

- MUST use PostgreSQL 17 as the primary relational database.
- MUST use SQLAlchemy 2.0+ with async support (`sqlalchemy[asyncio]` + `asyncpg`).
- MUST NOT use raw SQL in application code except for performance-critical queries — and those MUST use parameterized queries.
- MUST NOT use SQLite, MySQL, or other databases without architecture review.

## 2. Schema Design

- MUST use UUID primary keys for all tables (server-generated, not client-supplied).
- MUST include `created_at` and `updated_at` timestamps on every table.
- MUST NOT use auto-incrementing integer IDs — they leak ordering information and are enumerable.
- MUST use `TIMESTAMPTZ` (timezone-aware) for all timestamp columns.
- MUST add appropriate indexes for columns used in WHERE, JOIN, and ORDER BY clauses.
- MUST NOT store denormalized data unless justified by measured query performance (document the justification).
- SHOULD normalize to 3NF unless performance requires denormalization.

## 3. Migrations

- MUST use Alembic for all schema changes.
- MUST NOT make manual DDL changes in any environment (including development).
- MUST write backward-compatible migrations: new columns MUST be nullable or have defaults.
- MUST NOT drop columns or tables in the same release that stops using them — wait one release cycle.
- MUST include both `upgrade()` and `downgrade()` functions in every migration.
- MUST test migrations against a copy of production data before deploying.
- SHOULD keep migrations small and focused (one logical change per migration).

## 4. ORM Patterns

- MUST use SQLAlchemy's `Mapped` and `mapped_column` syntax (2.0-style declarative).
- MUST define relationships explicitly with `relationship()` and foreign keys.
- MUST NOT use lazy loading (`lazy="select"`) — use `selectinload()` or `joinedload()` explicitly.
- MUST NOT perform N+1 queries. Use eager loading or batch queries for related objects.
- MUST use `async_sessionmaker` with `expire_on_commit=False` for FastAPI dependency injection.
- MUST scope sessions to request lifecycle — one session per request via dependency injection.

## 5. Query Patterns

- MUST use the repository pattern: data access logic lives in `adapters/` or `repositories/`, not in API handlers.
- MUST NOT write queries in API route handlers directly.
- MUST use parameterized queries for all user-supplied values (never string interpolation).
- MUST paginate all list queries — no unbounded `SELECT *`.
- MUST set explicit `LIMIT` on all queries (default 100, max 1000).
- SHOULD use `EXISTS` subqueries instead of `COUNT(*)` when only checking for presence.
- SHOULD use `SELECT ... FOR UPDATE` when reading data that will be modified in the same transaction.

## 6. Soft Deletes

- MUST use soft deletes for user-facing data: `deleted_at TIMESTAMPTZ NULL`.
- MUST filter soft-deleted records in all default queries.
- MUST NOT hard-delete user data without explicit data retention policy approval.
- SHOULD create a partial index: `CREATE INDEX ... WHERE deleted_at IS NULL` for query performance.

## 7. Transactions

- MUST use explicit transactions for multi-step write operations.
- MUST NOT hold transactions open during external I/O (HTTP calls, file reads).
- MUST handle deadlocks with retry logic (up to 3 retries with exponential backoff).
- SHOULD keep transactions as short as possible — prepare data before opening the transaction.

## 8. Connection Pooling

- MUST configure connection pool: `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`.
- MUST NOT create new database connections per request — use the shared pool.
- MUST monitor pool exhaustion and alert when connections exceed 80% of pool size.

## 9. Data Types for SNS

| Data | PostgreSQL Type | Notes |
|---|---|---|
| User IDs | `UUID` | Server-generated |
| Post content | `TEXT` | Max 5000 characters enforced at app layer |
| Timestamps | `TIMESTAMPTZ` | Always UTC |
| Tags/labels | `JSONB` or `TEXT[]` | JSONB preferred for complex metadata |
| Follower count | `INTEGER` | Denormalized, updated via trigger or background job |
| Media URLs | `TEXT` | S3 presigned URLs, not stored as BLOBs |

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*
