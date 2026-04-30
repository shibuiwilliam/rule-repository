# Performance & Scalability Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-009
**Version:** 1.5
**Effective Date:** 2025-04-01
**Owner:** Backend Engineering Team
**Review Cycle:** Quarterly

---

## 1. Response Time Targets

| Endpoint Type | p50 | p95 | p99 |
|---|---|---|---|
| Read (GET) | < 50ms | < 200ms | < 500ms |
| Write (POST/PATCH) | < 100ms | < 500ms | < 1s |
| Timeline/Feed | < 100ms | < 300ms | < 800ms |
| Search | < 200ms | < 1s | < 2s |
| File upload | < 500ms | < 2s | < 5s |

- MUST meet p95 targets for all endpoints.
- MUST alert when p99 exceeds targets for more than 5 consecutive minutes.

## 2. Async Patterns

- MUST use `async`/`await` for all I/O operations (database, HTTP, file system).
- MUST NOT use synchronous blocking calls (`time.sleep`, synchronous HTTP) in async handlers.
- MUST NOT use `asyncio.run()` inside request handlers — the event loop is already running.
- MUST use `asyncio.gather()` for concurrent independent I/O operations.
- SHOULD use background tasks (FastAPI `BackgroundTasks` or arq) for operations that don't need to complete before responding.

## 3. Caching

- MUST cache frequently read, rarely changed data: user profiles, follower counts, site configuration.
- MUST use Redis for application-level caching.
- MUST set TTL on all cache entries — no indefinite caching.
- MUST invalidate cache on write operations for the same resource.
- MUST NOT cache user-specific data in shared caches without proper key isolation.
- SHOULD use cache-aside pattern: check cache → miss → query DB → populate cache → return.

| Data | TTL | Invalidation |
|---|---|---|
| User profile | 5 minutes | On profile update |
| Post content | 10 minutes | On post edit/delete |
| Follower count | 1 minute | On follow/unfollow |
| Timeline | 30 seconds | On new post in followed users |
| Site config | 1 hour | On admin change |

## 4. Database Performance

- MUST use `EXPLAIN ANALYZE` on all queries that run in production before merging.
- MUST NOT use `SELECT *` — explicitly list required columns.
- MUST add database indexes for any query that exceeds 10ms in `EXPLAIN`.
- MUST NOT perform full table scans on tables exceeding 100K rows.
- MUST use connection pooling (see ENG-003 §8).
- SHOULD use read replicas for read-heavy endpoints (timelines, search).
- SHOULD use materialized views for complex aggregations (trending posts, top users).

## 5. Pagination

- MUST implement cursor-based pagination for timelines and feeds.
- MUST NOT use OFFSET-based pagination for high-volume data (performance degrades linearly).
- MUST NOT return more than 100 items per page.
- SHOULD return a `next_cursor` token in the response for the client to fetch the next page.

## 6. Background Processing

- MUST use a task queue (arq + Redis) for operations exceeding 500ms.
- MUST NOT perform these operations synchronously in request handlers:
  - Sending emails or push notifications
  - Image/video processing
  - Feed fan-out (distributing posts to follower timelines)
  - Analytics event recording
  - External API calls that are not latency-critical

## 7. Media Handling

- MUST NOT serve media files through the application server — use a CDN.
- MUST generate presigned S3 URLs for direct client uploads (bypass the server for large files).
- MUST generate thumbnail sizes at upload time, not on-demand.
- MUST limit image dimensions: max 4096x4096 pixels.
- SHOULD use WebP format for image thumbnails (smaller size, better quality).

## 8. Load Testing

- MUST run load tests before major releases simulating 10x current peak traffic.
- MUST test under sustained load (30 minutes minimum) to detect memory leaks and connection pool exhaustion.
- SHOULD use k6 or Locust for load testing.
- SHOULD maintain a load test suite in the repository.

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*
