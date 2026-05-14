# Security Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Security Portal

Navigate to `http://localhost:3000/security`. The Security shell shows a red-accented sidebar with five navigation items: Dashboard, Classification, Encryption, Eval Harness, and Access Logs.

## 2. Dashboard Overview

The security dashboard provides an overview of IT security and access control compliance:

- **Rule compliance rates** for security-domain rules
- **Classification distribution** across the rule corpus (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED)
- **Access control** status and recent audit events
- **Vulnerability and IaC compliance** metrics

## 3. Manage Classification

Navigate to `/security/classification`. View and manage the classification levels assigned to rules, documents, evaluations, and audit entries. Classification drives Row-Level Security enforcement across all three data stores (PostgreSQL, Elasticsearch, MCP).

## 4. Review Encryption Status

Navigate to `/security/encryption`. Monitor Customer-Managed Encryption Key (CMEK) status for sensitive data. This page shows:

- Encryption key rotation status
- WORM storage mirroring for audit log entries
- PII redaction policy status

## 5. Eval Harness Results

Navigate to `/security/eval-harness`. Review results from the nightly evaluation harness that validates LLM evaluation quality across all 8 domains. The harness runs 90 golden cases and reports precision, recall, and F1 per domain. Quality drops trigger CI gates that block merges.

## 6. Access Logs

Navigate to `/security/access-logs`. Review read-access audit logs for classified data. Every access to CONFIDENTIAL or RESTRICTED data is logged with actor, timestamp, resource, and classification level.

## Next Steps

- Review [Classification and RLS](../adr/003-classification-and-rls.md) for the access control architecture
- Explore the [IT Security domain pack](../architecture/overview.md#domain-packs) for security rules
- See [Compliance-Grade Audit](../architecture/overview.md#compliance-grade-audit) for WORM and hash-chain details
