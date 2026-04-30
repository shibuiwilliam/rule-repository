# Authentication & Authorization Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-004
**Version:** 2.0
**Effective Date:** 2025-04-01
**Owner:** Backend Engineering Team + Security Team
**Review Cycle:** Semi-annual

---

## 1. Authentication

- MUST use JWT (JSON Web Tokens) for API authentication.
- MUST use short-lived access tokens (15 minutes) and long-lived refresh tokens (30 days).
- MUST store refresh tokens in a server-side allowlist (database or Redis) for revocation.
- MUST NOT store JWTs in localStorage — use httpOnly, Secure, SameSite=Strict cookies for web clients.
- MUST validate JWT signature, expiration, and issuer on every request.
- MUST use RS256 (asymmetric) signing for production JWTs. HS256 is acceptable only in development.

## 2. Password Handling

- MUST hash passwords with `bcrypt` (cost factor 12) or `argon2id`.
- MUST NOT store passwords in plain text, reversibly encrypted, or with MD5/SHA-1/SHA-256 alone.
- MUST enforce minimum password length of 8 characters.
- SHOULD check passwords against the HaveIBeenPwned API (k-anonymity method) during registration.
- MUST rate-limit login attempts: max 5 failures per account per 15 minutes.

## 3. Authorization

- MUST check authorization on every state-changing endpoint — never rely on the client to enforce access.
- MUST verify that the authenticated user owns the resource they're modifying (object-level authorization).
- MUST NOT use role checks alone for sensitive operations — always check resource ownership.
- MUST use a centralized authorization middleware or dependency, not scattered `if` checks in handlers.
- MUST log all authorization failures for security monitoring.

## 4. Permission Model

| Role | Can do |
|---|---|
| `user` | Read/write own posts, follow/unfollow, manage own profile |
| `moderator` | All user actions + hide/flag posts, mute users, review reports |
| `admin` | All moderator actions + manage users, change roles, access admin API |

- MUST implement role-based access control (RBAC) with the roles above.
- MUST NOT hardcode role names in business logic — use a roles table or enum.
- SHOULD support fine-grained permissions for admin actions (e.g., `admin:delete_user` vs `admin:view_stats`).

## 5. API Key Authentication

- MUST support API key authentication for server-to-server and bot integrations.
- MUST hash API keys before storage (SHA-256 is sufficient — keys are high-entropy).
- MUST scope API keys to specific permissions (read-only, write, admin).
- MUST allow key revocation without affecting other keys.

## 6. OAuth2 / Social Login

- SHOULD support OAuth2 login with Google, Apple, and GitHub.
- MUST NOT store OAuth2 access tokens — use them only during the login flow.
- MUST link social accounts to existing user accounts when the email matches.
- MUST require email verification before activating accounts created via social login.

## 7. Session Management

- MUST invalidate all sessions when a user changes their password.
- MUST provide a "log out all devices" feature that revokes all refresh tokens.
- MUST expire inactive sessions after 30 days of no activity.
- MUST NOT include sensitive data (email, role) in the JWT payload — only `sub` (user ID) and `exp`.

---

*Last reviewed: 2025-04-01 | Next review: 2025-10-01*
