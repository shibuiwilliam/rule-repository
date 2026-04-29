# Software Development Standards

**YourExampleCompany** — IT Service Consultation

**Document ID:** STD-001  
**Version:** 4.0  
**Effective Date:** 2025-03-01  
**Owner:** Engineering Excellence Team  
**Approved by:** CTO, VP of Engineering  
**Review Cycle:** Quarterly

---

## 1. Purpose

This document defines the engineering standards that all consultants and developers at YourExampleCompany must follow when delivering software for clients. These standards ensure consistency, quality, and security across all engagements.

---

## 2. Scope

Applies to all software development activities performed by YourExampleCompany personnel, including:
- New application development
- System integration and migration
- Code review and advisory services
- Maintenance and support contracts
- Internal tool development

---

## 3. Code Quality Standards

### 3.1 General
- MUST write self-documenting code with clear, intention-revealing names.
- MUST keep functions under 50 lines of executable code.
- MUST keep cyclomatic complexity under 10 per function.
- SHOULD keep files under 300 lines of code.
- MUST NOT commit dead code, commented-out code blocks, or TODO comments without a linked issue.

### 3.2 Documentation
- MUST include a README.md in every repository with: purpose, setup instructions, architecture overview, and contact information.
- MUST write docstrings/comments for all public APIs, interfaces, and complex business logic.
- SHOULD use Google-style docstrings for Python and JSDoc for TypeScript/JavaScript.
- MUST NOT rely on institutional knowledge — document design decisions in ADRs (Architecture Decision Records).

### 3.3 Type Safety
- MUST use type annotations on all public function signatures (Python: type hints, TypeScript: strict mode).
- MUST enable strict type checking in all new projects (mypy --strict for Python, "strict": true for TypeScript).
- MUST NOT use `any` type in TypeScript without a justification comment.
- SHOULD prefer composition over inheritance for complex type hierarchies.

---

## 4. Version Control

### 4.1 Git Practices
- MUST use Git for all source code management.
- MUST write commit messages following Conventional Commits format: `type(scope): description`.
- MUST NOT commit directly to `main` or `master` branches — all changes through pull requests.
- MUST NOT force-push to shared branches.
- SHOULD keep commits atomic — one logical change per commit.
- MUST NOT commit secrets, credentials, API keys, or environment-specific configuration to repositories.

### 4.2 Branching Strategy
- MUST follow trunk-based development or GitHub Flow (feature branches from main).
- MUST name feature branches as: `feat/description`, `fix/description`, `chore/description`.
- MUST delete feature branches after merge.
- SHOULD keep feature branches short-lived (< 3 days where possible).

### 4.3 Pull Requests
- MUST have at least one peer review approval before merging.
- MUST include a clear description of changes, motivation, and testing performed.
- MUST pass all CI checks (linting, testing, type checking) before merge.
- SHOULD keep pull requests under 400 lines of changed code.
- MUST NOT approve your own pull request.

---

## 5. Testing Standards

### 5.1 Coverage Requirements
- MUST maintain minimum 80% code coverage for all new code.
- MUST write unit tests for all business logic functions.
- MUST write integration tests for all API endpoints.
- SHOULD write end-to-end tests for critical user workflows.
- MUST NOT merge code that reduces existing test coverage by more than 2%.

### 5.2 Test Quality
- MUST follow the Arrange-Act-Assert pattern for unit tests.
- MUST use descriptive test names that describe the expected behavior.
- MUST NOT write tests that depend on execution order or external state.
- MUST mock external services in unit tests — never call real APIs.
- SHOULD prefer test fixtures over test data generated at runtime.

### 5.3 CI/CD Pipeline
- MUST configure automated testing on every pull request.
- MUST fail the build on any test failure, lint error, or type error.
- MUST run security scanning (SAST) on every PR.
- SHOULD run dependency vulnerability scanning weekly.

---

## 6. Security in Development

### 6.1 Secure Coding
- MUST validate all user input at system boundaries.
- MUST use parameterized queries — never string concatenation for SQL.
- MUST sanitize output to prevent XSS in web applications.
- MUST NOT log personally identifiable information (PII) in application logs.
- MUST NOT hardcode secrets or credentials in source code.
- MUST use environment variables or secret management tools for configuration.

### 6.2 Dependencies
- MUST pin dependency versions in production deployments.
- MUST review dependency licenses before adding new packages.
- MUST NOT use dependencies with known critical vulnerabilities (CVSS >= 9.0).
- SHOULD prefer well-maintained packages with active communities (> 100 GitHub stars, updated within 6 months).
- MUST update dependencies with critical security patches within 48 hours.

### 6.3 API Security
- MUST implement authentication on all non-public API endpoints.
- MUST use HTTPS for all API communications.
- MUST implement rate limiting on public-facing APIs.
- MUST validate and sanitize all request inputs.
- SHOULD implement request/response logging for audit purposes (excluding sensitive fields).

---

## 7. Architecture Standards

### 7.1 Design Principles
- MUST follow SOLID principles for object-oriented design.
- MUST separate concerns into distinct layers (API, business logic, data access).
- MUST NOT create circular dependencies between modules.
- SHOULD prefer composition over inheritance.
- SHOULD design for horizontal scalability from the start.

### 7.2 API Design
- MUST use RESTful conventions for HTTP APIs (proper methods, status codes, resource naming).
- MUST version APIs (URL path versioning preferred: `/api/v1/...`).
- MUST return structured error responses with error codes and human-readable messages.
- MUST document all APIs with OpenAPI/Swagger specifications.
- SHOULD implement pagination for list endpoints returning > 20 items.

### 7.3 Database
- MUST use migrations for all schema changes — never manual DDL in production.
- MUST NOT store business logic in database triggers or stored procedures.
- MUST add indexes for columns used in WHERE clauses and JOINs.
- SHOULD normalize to 3NF unless denormalization is justified by performance requirements.

---

## 8. Deployment Standards

### 8.1 Infrastructure as Code
- MUST define infrastructure using IaC tools (Terraform, Pulumi, or CloudFormation).
- MUST NOT make manual changes to production infrastructure.
- MUST store IaC definitions in version control.
- MUST use separate environments: development, staging, production.

### 8.2 Containerization
- MUST use multi-stage Docker builds to minimize image size.
- MUST NOT run containers as root in production.
- MUST scan container images for vulnerabilities before deployment.
- MUST pin base image versions (not `latest` tag).

### 8.3 Monitoring and Observability
- MUST implement health check endpoints for all services.
- MUST configure structured logging (JSON format) for all applications.
- MUST set up alerting for service availability and error rates.
- SHOULD implement distributed tracing for microservice architectures.
- MUST NOT log sensitive data (passwords, tokens, PII) in any log level.

---

## 9. Client Delivery Standards

### 9.1 Handover Requirements
- MUST deliver complete documentation (README, architecture diagrams, runbooks) with every engagement.
- MUST conduct a handover session with the client's team before project completion.
- MUST ensure all code is in a client-accessible repository.
- MUST provide a post-engagement support period of at least 2 weeks.

### 9.2 Code Ownership
- MUST transfer full intellectual property rights to the client unless otherwise contracted.
- MUST NOT reuse client-specific code in other engagements without written permission.
- MAY reuse general-purpose utilities and patterns (without client-specific business logic).

---

## 10. Exceptions

Exceptions to these standards must be:
- Documented with justification
- Approved by the Engineering Excellence Team
- Reviewed at the next quarterly standards review
- Time-limited (maximum 6 months)

---

*Last reviewed: 2025-03-01 | Next review: 2025-06-01*
