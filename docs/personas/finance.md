# Finance Persona Guide

## Overview

The Finance persona provides a transaction- and expense-centric view of the Rule Repository, focused on expense approval, procurement compliance, and financial control enforcement.

## Getting Started

1. Navigate to the Finance dashboard at `/finance`
2. Your default view shows the Transaction Approval Queue
3. Use the sidebar to access expense review, procurement policies, rules, and intelligence

## Key Workflows

### Reviewing Transactions for Compliance
- Review pending transactions in the Transaction Approval Queue
- Submit transactions via `POST /api/v1/submissions` with `kind: "transaction"`
- Computational rules automatically check amounts against thresholds (e.g., entertainment limits, receipt requirements)

### Expense Review
- Evaluate expense reports against policy limits using deterministic evaluation for numeric checks
- Flag expenses that exceed thresholds or lack required documentation
- Alerts surface when spending patterns indicate potential policy violations

### Procurement Compliance
- Enforce Subcontracting Act compliance and three-quote requirements
- Track vendor relationships and contract terms against procurement policies
- Submit procurement decisions via `POST /api/v1/submissions` with `kind: "transaction"`

### Discovering Rules from Finance Policies
- Upload finance policy documents (expense policies, procurement guidelines, regulatory requirements)
- The extraction pipeline identifies normative statements and financial metadata
- Review and approve discovered rule candidates

### Using the Playground
- Test rules against sample transactions or expense submissions
- The playground defaults to transaction form mode for the Finance persona

## Vocabulary
- **Rule** = Financial policy, expense limit, or procurement requirement
- **Violation** = Transaction or expense that fails to meet a policy
- **Evaluation** = Transaction review against applicable financial controls
- **Subject** = Transaction (expense report, purchase order, payment request)

## Templates
- `finance-expense-jp` -- Japanese expense compliance (entertainment limits, receipt thresholds, computational rules)
- `finance-procurement` -- Procurement compliance (Subcontracting Act, three-quote rule)
