# Sales Persona Guide

## Overview

The Sales persona provides a deal- and pricing-centric view of the Rule Repository, focused on discount approval, pricing compliance, and deal review workflows.

## Getting Started

1. Navigate to the Sales dashboard at `/sales`
2. Your default view shows the Deal and Discount Review Queue
3. Use the sidebar to access pricing policies, deal history, rules, and intelligence

## Key Workflows

### Reviewing Deals and Discounts
- Review pending deal approvals in the Deal and Discount Review Queue
- Submit deal proposals via `POST /api/v1/submissions` with `kind: "business_event"`
- Computational rules automatically check discount percentages against authorized limits

### Pricing Compliance
- Enforce pricing floors, discount caps, and resale price maintenance rules
- Flag deals that violate antitrust or fair pricing regulations
- Submit pricing decisions via `POST /api/v1/submissions` with `kind: "decision_request"`

### Deal Approval Workflow
- Route deals through the appropriate approval chain based on discount level and deal size
- Track approval history and audit trail for each deal
- Alerts surface when deals approach or exceed discount thresholds

### Discovering Rules from Sales Policies
- Upload sales policy documents (pricing guidelines, discount authorization matrices, channel policies)
- The extraction pipeline identifies normative statements and pricing metadata
- Review and approve discovered rule candidates

### Using the Playground
- Test rules against sample deal proposals or pricing scenarios
- The playground defaults to business event form mode for the Sales persona

## Vocabulary
- **Rule** = Pricing policy, discount limit, or sales compliance standard
- **Violation** = Deal or pricing decision that fails to meet a policy
- **Evaluation** = Deal review against applicable pricing and sales rules
- **Subject** = Business event (deal proposal, discount request) or decision request (pricing approval)

## Templates
- `sales-pricing-jp` -- Japanese pricing compliance (discount limits, resale price maintenance)
