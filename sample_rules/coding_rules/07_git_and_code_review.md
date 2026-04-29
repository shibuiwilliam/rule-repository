# Git & Code Review Standards

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-007  
**Version:** 2.0  
**Effective Date:** 2025-04-01  
**Owner:** Backend Engineering Team  
**Review Cycle:** Semi-annual

---

## 1. Branching Strategy

- MUST use trunk-based development: short-lived feature branches off `main`.
- MUST name branches: `feat/<description>`, `fix/<description>`, `chore/<description>`.
- MUST NOT commit directly to `main` — all changes through pull requests.
- MUST delete feature branches after merge.
- SHOULD keep branches under 3 days old. Long-lived branches accumulate merge conflicts.

## 2. Commit Messages

- MUST use Conventional Commits format: `type(scope): description`.
- MUST use one of: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`.
- MUST write the description in imperative mood: "add timeline endpoint", not "added" or "adds".
- MUST keep the first line under 72 characters.
- SHOULD include a body for non-trivial changes explaining *why*, not just *what*.
- MUST NOT include ticket/issue numbers in the commit message body — link them in the PR description.

## 3. Pull Requests

- MUST have at least one approval from a peer reviewer before merging.
- MUST have two approvals for changes touching authentication, authorization, or payment code.
- MUST pass all CI checks (tests, lint, type check) before merge is allowed.
- MUST include in the PR description:
  - **What**: summary of changes
  - **Why**: motivation or link to issue
  - **How to test**: manual testing steps or test commands
  - **Screenshots**: for UI-affecting changes (if applicable)
- MUST NOT exceed 400 lines of changed code per PR. Split larger changes into stacked PRs.
- MUST NOT approve your own pull request.
- SHOULD respond to PR review requests within 4 business hours.

## 4. Code Review Checklist

Reviewers MUST check:
- [ ] Does the code do what the PR description says?
- [ ] Are there tests for the new behavior?
- [ ] Are error cases handled?
- [ ] Is the code readable without the PR description as context?
- [ ] Are there any N+1 query issues?
- [ ] Are there any security concerns (input validation, auth checks)?
- [ ] Are log messages structured and at the right level?

## 5. Merge Strategy

- MUST use "Squash and Merge" for feature branches (one clean commit on main).
- MUST NOT use "Merge Commit" or "Rebase and Merge" — squash keeps history clean.
- MUST NOT force-push to shared branches or `main`.
- SHOULD rebase on `main` before merging to avoid unnecessary merge conflicts.

## 6. Hotfixes

- MUST create hotfix branches from `main`: `hotfix/<description>`.
- MUST get at least one reviewer approval, even for urgent fixes.
- MAY bypass the normal PR process only for critical production incidents (SEV-1), with post-incident review.

## 7. Protected Files

- MUST require CODEOWNERS approval for changes to:
  - `alembic/` (database migrations)
  - `core/auth.py` (authentication logic)
  - `core/config.py` (application configuration)
  - `docker-compose.yml` and `Dockerfile`
  - CI/CD pipeline configuration

---

*Last reviewed: 2025-04-01 | Next review: 2025-10-01*
