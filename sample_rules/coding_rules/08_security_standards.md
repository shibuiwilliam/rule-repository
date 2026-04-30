# Security Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-008
**Version:** 2.5
**Effective Date:** 2025-04-01
**Owner:** Security Team + Backend Engineering Team
**Review Cycle:** Quarterly

---

## 1. Input Validation

- MUST validate all user input at the API boundary using Pydantic models.
- MUST enforce maximum lengths on all string inputs (prevent oversized payloads).
- MUST sanitize HTML in user-generated content to prevent stored XSS.
- MUST validate file uploads: check MIME type, file extension, and file size.
- MUST NOT trust `Content-Type` headers alone — verify file signatures (magic bytes).
- MUST reject requests with unexpected fields (Pydantic `model_config = ConfigDict(extra="forbid")`).

## 2. Output Encoding

- MUST escape user-generated content in all API responses to prevent reflected XSS.
- MUST set `Content-Type: application/json` on all JSON responses.
- MUST set security headers on all responses:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Content-Security-Policy: default-src 'self'`

## 3. SQL Injection Prevention

- MUST use parameterized queries for all database operations.
- MUST NOT concatenate user input into SQL strings, even for `ORDER BY` or `LIMIT` clauses.
- MUST use SQLAlchemy's query builder or ORM — never raw SQL with f-strings.
- MUST validate and allowlist sort column names when accepting client-supplied sort parameters.

## 4. Secrets Management

- MUST NOT hardcode secrets (API keys, passwords, tokens) in source code.
- MUST NOT commit `.env` files to version control.
- MUST store secrets in environment variables or a secrets manager (AWS Secrets Manager, Vault).
- MUST rotate API keys and database passwords at least every 90 days.
- MUST use separate credentials for each environment (dev, staging, production).
- MUST NOT log secrets at any log level.

## 5. Dependencies

- MUST pin all dependency versions in `pyproject.toml` (use exact versions or lock file).
- MUST run `pip-audit` or `safety` in CI to check for known vulnerabilities.
- MUST NOT use dependencies with unpatched critical CVEs (CVSS >= 9.0).
- MUST update dependencies with critical security patches within 48 hours of disclosure.
- SHOULD prefer packages with > 1000 GitHub stars and updates within the last 6 months.

## 6. File Upload Security

- MUST store uploaded files in object storage (S3), not on the application server.
- MUST generate random filenames for stored files — never use the client-supplied filename.
- MUST scan uploaded files for malware before serving them to other users.
- MUST limit file sizes: 10 MB for images, 50 MB for videos.
- MUST NOT serve user-uploaded files from the same domain as the API — use a separate CDN domain.

## 7. Rate Limiting & Abuse Prevention

- MUST rate-limit all endpoints (see ENG-002 §8 for defaults).
- MUST implement CAPTCHA for registration, password reset, and public posting.
- MUST block accounts after 10 consecutive failed login attempts (temporary 15-minute lockout).
- MUST log and alert on brute-force patterns (same IP, many usernames).
- SHOULD implement content-based spam detection for posts and comments.

## 8. Data Privacy

- MUST NOT log personally identifiable information (PII) including: email, phone, IP address, location.
- MUST encrypt PII at rest in the database (use column-level encryption for email, phone).
- MUST provide a data export endpoint for GDPR/privacy compliance.
- MUST provide a data deletion endpoint that removes all user data within 30 days.
- MUST NOT share user data with third-party services without explicit consent.

## 9. CORS

- MUST configure CORS to allow only the frontend domain(s).
- MUST NOT use `Access-Control-Allow-Origin: *` in production.
- MUST limit allowed methods to those actually used.
- MUST NOT expose sensitive headers via `Access-Control-Expose-Headers`.

## 10. OWASP Top 10 Compliance

This project MUST address all OWASP Top 10 risks:

| Risk | Mitigation |
|---|---|
| A01 Broken Access Control | Object-level auth checks on every mutation |
| A02 Cryptographic Failures | bcrypt/argon2 for passwords, TLS everywhere |
| A03 Injection | Parameterized queries, Pydantic validation |
| A04 Insecure Design | Threat modeling during design phase |
| A05 Security Misconfiguration | Secure defaults, no debug mode in production |
| A06 Vulnerable Components | Automated dependency scanning in CI |
| A07 Auth Failures | JWT with short expiry, rate-limited login |
| A08 Software Integrity | Signed Docker images, locked dependencies |
| A09 Logging Failures | Structured logging with security events |
| A10 SSRF | No user-controllable URLs in server-side requests |

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*
