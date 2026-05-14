# Marketing Persona Walkthrough

> Time: ~15 minutes. Prerequisites: `make up && make seed` completed.

## 1. Access the Marketing Portal

Navigate to `http://localhost:3000/marketing`. The Marketing shell shows a purple-accented sidebar with five navigation items: Dashboard, Creative Review, Ad Compliance, Brand Rules, and Campaign Audit.

## 2. Dashboard Overview

The marketing dashboard shows compliance metrics for creative and communication content:

- **KPIs**: total rules, pending reviews, compliance rate
- **Verdict distribution** across recent evaluations
- **Compliance by content type** (ad copy, press releases, social media)
- **Recent creative reviews** with inline details

## 3. Submit Creative for Review

Navigate to `/marketing/creative-reviews`. Submit creative content (ad copy, promotional materials, social media posts) for compliance review. The system evaluates content against applicable communication and marketing rules, checking for:

- Brand guideline adherence
- Regulatory compliance (PMDA, FIEA guidance)
- Channel-specific rules (social vs. press release)
- Recipient-aware context (internal vs. external vs. customer)

## 4. Browse Brand Guidelines

Navigate to `/marketing/guidelines`. View marketing-specific rules with keyword search and severity filters. Rules cover brand standards, advertising compliance, and communication policies.

## 5. Review Creative Details

Click on any creative review to see `/marketing/creatives/review/[id]`. The detail view shows:

- The submitted content
- Per-rule verdicts with confidence scores
- Suggested text rewrites with diff preview
- Remediation actions

## Next Steps

- Explore the [MCP Server](../integrations/mcp.md) for agent-based content review
- See the `evaluate_communication` MCP tool for programmatic review
- Review [Communication domain pack rules](../architecture/overview.md#domain-packs) for available policies
