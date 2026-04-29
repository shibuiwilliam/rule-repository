# YourExampleSoftware — Coding Rules & Engineering Standards

**Project:** YourExampleSoftware — a social networking service (SNS) web backend  
**Language:** Python 3.13 (FastAPI)  
**Team:** Backend Engineering Team

## Document Catalog

| ID | Document | Scope | Audience |
|---|---|---|---|
| ENG-001 | [Python Style Guide](01_python_style_guide.md) | All Python code | All developers |
| ENG-002 | [API Design Standards](02_api_design_standards.md) | REST API endpoints | Backend developers |
| ENG-003 | [Database & Data Access](03_database_and_data_access.md) | PostgreSQL, ORM, migrations | Backend developers |
| ENG-004 | [Authentication & Authorization](04_auth_and_authorization.md) | Auth flows, JWT, permissions | All developers |
| ENG-005 | [Testing Standards](05_testing_standards.md) | Unit, integration, E2E tests | All developers |
| ENG-006 | [Error Handling & Logging](06_error_handling_and_logging.md) | Exceptions, logging, monitoring | All developers |
| ENG-007 | [Git & Code Review](07_git_and_code_review.md) | Branching, commits, PR process | All developers |
| ENG-008 | [Security Standards](08_security_standards.md) | Input validation, secrets, OWASP | All developers |
| ENG-009 | [Performance & Scalability](09_performance_and_scalability.md) | Caching, queries, async patterns | Senior developers |
| ENG-010 | [Deployment & Operations](10_deployment_and_operations.md) | CI/CD, Docker, monitoring | DevOps, senior devs |

## Modality Conventions

- **MUST** — Mandatory. CI will enforce or code review will reject.
- **MUST NOT** — Prohibited. Violation is a blocking issue.
- **SHOULD** — Strongly recommended. Deviation requires a comment explaining why.
- **MAY** — Optional. Use your judgment.

## Using with Rule Repository

```bash
for doc in sample_rules/coding_rules/0*.md; do
  rulerepo-ingest --source claude-md --file "$doc" --scope "engineering/python"
done
```

Or drag and drop all 10 files onto the Documents page for guided extraction.
