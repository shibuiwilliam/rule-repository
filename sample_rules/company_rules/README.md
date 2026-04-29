# YourExampleCompany — Company Rules & Policies

This directory contains the official rules, policies, and standards for **YourExampleCompany**, an IT service consultation firm.

## Document Catalog

| ID | Document | Scope | Owner |
|---|---|---|---|
| POL-001 | [Code of Conduct](01_code_of_conduct.md) | All personnel | People & Culture |
| POL-005 | [Information Security Policy](02_information_security_policy.md) | All systems & data | Information Security Office |
| STD-001 | [Software Development Standards](03_software_development_standards.md) | All engineering | Engineering Excellence Team |
| POL-010 | [Remote Work Policy](04_remote_work_policy.md) | All employees | People & Culture |
| POL-015 | [Expense and Travel Policy](05_expense_and_travel_policy.md) | All business travel | Finance |
| STD-005 | [Client Engagement Guidelines](06_client_engagement_guidelines.md) | All client projects | Delivery Excellence Team |

## Document Conventions

- **MUST** — Mandatory requirement. Violation may result in disciplinary action.
- **MUST NOT** — Prohibition. Violation is a policy breach.
- **SHOULD** — Recommended practice. Expected unless there's a documented justification.
- **MAY** — Optional/permitted behavior. At the individual's discretion.

These align with [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) convention.

## Using with Rule Repository

These documents are designed to be ingested into the Rule Repository using:

```bash
# Import all policies
for doc in sample_rules/company_rules/0*.md; do
  rulerepo-ingest --source claude-md --file "$doc" --scope "company/policies"
done
```

Or upload through the frontend at `/documents` for guided extraction with human review.

## Review Schedule

| Frequency | Documents |
|---|---|
| Quarterly | STD-001 (Software Development Standards) |
| Semi-annual | POL-005 (Information Security), STD-005 (Client Engagement) |
| Annual | POL-001 (Code of Conduct), POL-010 (Remote Work), POL-015 (Expense & Travel) |

## Contact

- **Policy questions**: compliance@yourexamplecompany.com
- **Security concerns**: security@yourexamplecompany.com
- **HR matters**: people@yourexamplecompany.com
