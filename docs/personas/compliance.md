# Compliance Persona Guide

## Overview

The Compliance persona provides a cross-domain, organization-wide view of the Rule Repository, focused on regulatory compliance monitoring, audit log access, conflict detection, and change impact analysis across all business domains.

## Getting Started

1. Navigate to the Compliance dashboard at `/compliance`
2. Your default view shows the Cross-Domain Compliance Summary
3. Use the sidebar to access audit logs, conflict alerts, regulatory tracking, rules, and intelligence

## Key Workflows

### Cross-Domain Compliance Monitoring
- View compliance status across all domains (engineering, legal, HR, finance, sales, communication) from a single dashboard
- Filter by domain, severity, time period, and organizational unit
- Track compliance trends and identify emerging risk areas

### Audit Log Access
- Browse the append-only, hash-chained audit log for full traceability
- Filter audit entries by domain, subject type, rule, verdict, and time range
- Export audit data for external reporting and regulatory submissions
- Every evaluation records: which rules were applied, deterministic results, LLM results, and final aggregated verdicts

### Conflict Alert Management
- Review detected conflicts between rules across domains and jurisdictions
- Investigate `conflicts_with` relationships in the rule graph
- Prioritize resolution based on severity and affected scope
- Track conflict resolution status and history

### Regulatory Change Impact Analysis
- Assess how new or changed regulations affect existing rules across the organization
- Use the rule graph to trace dependencies (`depends_on`, `derives_from`, `refines`) from affected rules
- Generate impact reports showing which rules, domains, and organizational units are affected

### Managing All Subject Types
- The Compliance persona can submit and review all subject types:
  - `code_change` -- engineering code compliance
  - `document_artifact` -- contract and policy review
  - `business_event` -- employee events, deal proposals
  - `transaction` -- financial transactions and expenses
  - `communication` -- marketing and external communications
  - `decision_request` -- approval and pricing decisions

### Using the Playground
- Test rules from any domain against any subject type
- The playground provides an input-mode switcher for all subject kinds

## Vocabulary
- **Rule** = Any organizational standard, regulation, or policy across all domains
- **Violation** = Any non-compliance finding regardless of domain
- **Evaluation** = Compliance assessment of any subject against applicable rules
- **Subject** = Any evaluable item (code change, document, event, transaction, communication, decision)

## Templates
All domain templates are accessible from the Compliance persona:
- `legal-contracts-jp` -- Japanese contract compliance
- `legal-contracts-en-us` -- US contract compliance
- `hr-attendance-jp` -- Japanese attendance and overtime compliance
- `hr-conduct` -- Workplace conduct standards
- `finance-expense-jp` -- Japanese expense compliance
- `finance-procurement` -- Procurement compliance
- `sales-pricing-jp` -- Japanese pricing compliance
- `communication-marketing-jp` -- Japanese marketing compliance (Act against Unjustifiable Premiums and Misleading Representations, Pharmaceutical and Medical Device Act)

## Implementation Status

- **Route group**: `(compliance)`
- **Pages**: Dashboard + 4 sub-pages
- **Integration level**: Partially integrated (mostly static data)
- **Notable sub-pages**: bundles, exceptions, audit-packets, regulatory
