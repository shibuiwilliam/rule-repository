# Legal Persona Guide

## Overview

The Legal persona provides a contract- and regulation-centric view of the Rule Repository, focused on clause compliance, jurisdictional requirements, and document review workflows.

## Getting Started

1. Navigate to the Legal dashboard at `/legal`
2. Your default view shows the Contract Review Queue
3. Use the sidebar to access the clause library, jurisdiction search, rules, and intelligence

## Key Workflows

### Reviewing a Contract
- Upload a contract document (PDF, text, or markdown) via the Contract Review Queue
- The system extracts clauses, identifies normative statements, and evaluates them against applicable rules
- Submit contract sections via `POST /api/v1/submissions` with `kind: "document_artifact"`

### Managing the Clause Library
- Browse and search reusable clause templates organized by jurisdiction and contract type
- Tag clauses with jurisdictions, contract categories, and regulatory references
- Link related clauses using the rule graph (e.g., `refines`, `overrides`, `conflicts_with`)

### Jurisdiction Search
- Filter rules by jurisdiction using structured scope attributes
- Compare requirements across jurisdictions to identify gaps or conflicts

### Discovering Rules from Legal Documents
- Upload legal source documents (statutes, regulations, internal policies)
- The extraction pipeline identifies normative sentences and suggests candidate rules
- Domain-specific analyzers handle Japanese legal structure (conditions/items/numbers) and other jurisdiction formats

### Using the Playground
- Test rules against sample contract sections or legal document excerpts
- The playground defaults to document section mode for the Legal persona

## Vocabulary
- **Rule** = Legal requirement, contractual obligation, or compliance standard
- **Violation** = Clause or document section that fails to meet a requirement
- **Evaluation** = Contract or document review against applicable rules
- **Subject** = Document artifact (contract section, policy excerpt, regulatory filing)

## Templates
- `legal-contracts-jp` -- Japanese contract compliance (NDA, anti-social-forces clause, governing law, etc.)
- `legal-contracts-en-us` -- US contract compliance (limitation of liability, indemnification, etc.)

## Implementation Status

- **Route group**: `(legal)`
- **Pages**: Dashboard + 4 sub-pages
- **Integration level**: Partially integrated
- **Notable sub-pages**: clauses, lineage, redlines, contracts/review/[id]
