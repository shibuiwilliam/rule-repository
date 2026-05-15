# Marketing Persona Guide

## Overview

The Marketing persona provides a communications- and creative-centric view of the Rule Repository, focused on advertising compliance, creative review workflows, and marketing guideline enforcement.

## Getting Started

1. Navigate to the Marketing dashboard at `/marketing`
2. Your default view shows the Creative Review Queue
3. Use the sidebar to access creative reviews, guidelines, and marketing rules

## Key Workflows

### Reviewing Creative Assets
- Review marketing materials for regulatory and brand compliance
- Submit creative assets via `POST /api/v1/submissions` with `kind: "communication"`
- Evaluate against advertising regulations (e.g., Act against Unjustifiable Premiums and Misleading Representations, Pharmaceutical and Medical Device Act)

### Managing Marketing Guidelines
- Browse and search marketing guidelines organized by channel and regulation type
- Maintain brand and regulatory compliance standards

### Creative Review Workflow
- Route creative assets through the review and approval process
- Track review history and compliance status for each creative

## Vocabulary
- **Rule** = Marketing guideline, advertising regulation, or brand standard
- **Violation** = Creative asset or communication that fails to meet a guideline or regulation
- **Evaluation** = Creative review against applicable marketing rules
- **Subject** = Communication (advertisement, marketing copy, creative asset)

## Templates
- `communication-marketing-jp` -- Japanese marketing compliance (Act against Unjustifiable Premiums and Misleading Representations, Pharmaceutical and Medical Device Act)

## Implementation Status

- **Route group**: `(marketing)`
- **Pages**: Dashboard + 3 sub-pages
- **Integration level**: Partially integrated
- **Notable sub-pages**: creative-reviews, guidelines, creatives/review/[id]
