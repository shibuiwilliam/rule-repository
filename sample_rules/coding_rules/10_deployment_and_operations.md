# Deployment & Operations Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-010
**Version:** 1.5
**Effective Date:** 2025-04-01
**Owner:** Backend Engineering Team + DevOps
**Review Cycle:** Quarterly

---

## 1. Containerization

- MUST use multi-stage Docker builds to minimize image size.
- MUST NOT run containers as root in any environment.
- MUST pin base image versions: `python:3.13-slim`, not `python:latest`.
- MUST scan images for vulnerabilities before pushing to the registry.
- MUST keep production images under 200 MB.
- MUST include a `.dockerignore` that excludes tests, docs, and dev configs.

## 2. CI/CD Pipeline

- MUST run the following checks on every PR:
  1. `ruff check .` (linting)
  2. `ruff format --check .` (formatting)
  3. `mypy --strict src/` (type checking)
  4. `pytest` (all tests)
  5. `pip-audit` (dependency vulnerabilities)
- MUST NOT merge PRs with failing CI checks.
- MUST deploy to staging automatically on merge to `main`.
- MUST require manual approval for production deployment.
- MUST deploy to production using blue-green or rolling updates (zero downtime).

## 3. Environment Configuration

- MUST use environment variables for all configuration (12-factor app).
- MUST NOT embed environment-specific values in code or Docker images.
- MUST maintain a `.env.example` file with all required variables (no real secrets).
- MUST use separate credentials for each environment: development, staging, production.
- MUST encrypt secrets in CI/CD pipelines (GitHub Actions secrets, Vault).

## 4. Health Checks

- MUST implement a `/healthz` endpoint that returns 200 if the service is running.
- MUST implement a `/readyz` endpoint that checks all dependencies (database, Redis, external services).
- MUST NOT perform expensive operations in health check endpoints.
- MUST configure container orchestrator (Docker/Kubernetes) to use health checks with:
  - Liveness: `/healthz`, interval 10s, timeout 5s, 3 retries
  - Readiness: `/readyz`, interval 5s, timeout 5s, 3 retries

## 5. Database Migrations in Deployment

- MUST run migrations as a separate step before deploying new application code.
- MUST NOT run migrations inside the application process at startup in production.
- MUST verify migration success before routing traffic to new instances.
- MUST have a rollback plan for every migration (tested `downgrade()` function).
- SHOULD use a migration lock to prevent concurrent migration runs.

## 6. Monitoring

- MUST monitor and alert on:
  - Error rate (> 1% of requests over 5 minutes)
  - Latency (p99 > 2 seconds over 5 minutes)
  - CPU usage (> 80% sustained for 5 minutes)
  - Memory usage (> 85% of limit)
  - Database connection pool exhaustion (> 80% utilized)
  - Disk usage (> 85%)
- MUST use structured JSON logs (see ENG-006) for centralized log aggregation.
- SHOULD use Prometheus + Grafana or Datadog for metrics and dashboards.
- SHOULD implement distributed tracing (OpenTelemetry) for request flow visibility.

## 7. Incident Response

- MUST follow the incident severity classification:

| Severity | Definition | Response Time |
|---|---|---|
| SEV-1 | Service fully down or data breach | 15 minutes |
| SEV-2 | Major feature broken, affecting > 10% users | 1 hour |
| SEV-3 | Minor feature broken, workaround exists | 4 hours |
| SEV-4 | Cosmetic or non-urgent issue | Next business day |

- MUST write a post-incident review (PIR) for all SEV-1 and SEV-2 incidents within 48 hours.
- MUST NOT blame individuals in PIRs — focus on system improvements.
- SHOULD practice incident response procedures quarterly.

## 8. Backup & Recovery

- MUST back up the production database daily with point-in-time recovery enabled.
- MUST retain backups for at least 30 days.
- MUST test backup restoration quarterly.
- MUST document the recovery procedure with expected recovery time objective (RTO) and recovery point objective (RPO).
- Target: RTO < 1 hour, RPO < 15 minutes.

## 9. Scaling

- MUST design all services to be horizontally scalable (stateless application servers).
- MUST NOT store session state on the application server — use Redis or JWT.
- MUST use connection pooling for database connections (not one connection per request).
- SHOULD implement auto-scaling based on CPU and request rate metrics.
- SHOULD use read replicas for read-heavy database workloads.

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*
