# ADR 004: Contract Clause Engine

**Status:** Accepted

**Date:** 2026-05-08

## Context

Legal teams need to evaluate contract drafts against organizational standards at the clause level, not just the document level. A contract may be overall acceptable but contain individual clauses that violate policy (e.g., unlimited liability, foreign governing law, data export provisions).

## Decision

We implement a Contract Clause Engine as a specialized evaluation path:

1. **Clause extraction** via `adapters/contract_parser.py` -- parses DOCX/PDF/text contracts into structured clause units with type classification (15 clause types)
2. **Clause comparison** via `adapters/contract_compare.py` -- semantic diff between two contracts at the clause level
3. **Clause-level evaluation** -- each clause is evaluated independently against applicable rules
4. **Clause aggregation** via `services/evaluation/clause_aggregator.py` -- clause-level verdicts collapse to a contract-level verdict

Four evaluation modes are supported:
- **Self-conformance** -- contract vs. organization's standard clauses
- **Cross-contract** -- two contracts compared against each other
- **Regulatory compliance** -- clauses vs. regulatory requirements
- **Risk scoring** -- quantified risk assessment per clause

All remediations from the contract engine are marked `auto_applicable=false` -- contract changes are never applied automatically.

## Consequences

- The legal plugin owns the clause extraction prompts and evaluation templates
- Clause-level evaluation produces more LLM calls but better precision
- The standard clause library becomes a first-class organizational asset
