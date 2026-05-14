# Compliance Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Compliance Portal

Navigate to `http://localhost:3000/compliance`. The Compliance shell shows an amber-accented sidebar with five navigation items: Dashboard, Bundles, Audit Packets, Exception Tracking, and Regulatory Feed.

## 2. Dashboard Overview

The compliance dashboard provides a cross-domain view of organizational rule adherence. Key metrics include:

- **Overall compliance rate** across all departments
- **Open exceptions** and their approval status
- **Regulatory feed** showing recent upstream regulation changes
- **Audit packet** readiness status

## 3. Browse Rule Bundles

Navigate to `/compliance/bundles`. Rule bundles group related rules across departments for regulatory or audit purposes. Bundles can span multiple domains (e.g., a "Data Privacy" bundle might include rules from Legal, IT Security, and HR).

## 4. Review Audit Packets

Navigate to `/compliance/audit-packets`. Audit packets are assembled collections of rules, evaluations, and evidence for regulatory review. Each packet includes:

- Rules covered and their health scores
- Evaluation history with verdict distributions
- Hash-chained audit log entries as evidence
- Attestation campaign status

## 5. Track Exceptions

Navigate to `/compliance/exceptions`. View all active rule exceptions requested by agents or users. Each exception shows:

- The rule being excepted
- The requestor and justification
- Duration and expiration
- Approval status

## 6. Monitor Regulatory Feed

Navigate to `/compliance/regulatory`. Track upstream regulation changes from regulatory source feeds (e-Gov, FSA notices). When an upstream norm changes, the system auto-drafts proposals for affected operational rules through the norm lineage chain.

## Next Steps

- Explore the [Engineering walkthrough](engineering.md) for code-focused governance
- Review the [Intelligence Dashboard](../intelligence/dashboard.md) for health and effectiveness metrics
- See [Federation](../architecture/federation.md) for cross-organizational rule composition
