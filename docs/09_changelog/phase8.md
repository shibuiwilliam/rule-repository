# Phase 8 — Domain Engines and Discovery: Changelog

> Running record of Phase 8 changes, ordered by merge date.
> Phase 7 (Enterprise Ground) is COMPLETE. Phase 8 builds on Subject Polymorphism, Department/Capacity, and Classification foundations.

---

## 2026-05-08 — Phase 8 Initial Implementation

### Stream A — Contract Clause Engine (DONE)

- **ADR 0004** (`development/adr/0004-contract-clause-engine.md`): Accepted. Documents parser, comparator, aggregator, evaluation modes, and API design.
- **`adapters/contract_parser.py`**: Parses contracts from DOCX (via python-docx), PDF (via Gemini Files API), and plain text. Delegates to clause segmenter and classifier.
- **`adapters/contract_compare.py`**: Semantic clause-level diffing with embedding-based matching and similarity scoring.
- **`services/evaluation/clause_aggregator.py`**: Aggregates clause-by-clause verdicts to contract-level verdict. DENY on any MUST/MUST_NOT clause propagates to contract level.
- **Prompt templates**: `services/evaluation/prompts/clause_set/` — `evaluate_clause.txt`, `compare_clauses.txt`, `risk_score_clause.txt`.
- **`api/v1/contract.py`**: `POST /api/v1/evaluate/contract` endpoint with `review_type` parameter (self_conformance, cross_contract, regulatory_compliance, risk_scoring).
- **Unit tests**: `test_contract_parser.py`, `test_contract_compare.py`, `test_clause_aggregator.py`.

### Stream B — Event Engine Temporal Modes (DONE)

- **ADR 0005** (`development/adr/0005-event-engine-temporal-modes.md`): Accepted. Documents single/sequence/calendar modes.
- **`domain/event_sequence.py`**: `EventEvaluationMode` enum, `EventRecord`, `EventWindow`, `CalendarContext`, `SequenceContext` domain types.
- **Prompt templates**: `services/evaluation/prompts/event/` — `evaluate_sequence.txt`, `evaluate_calendar.txt`.
- **`api/v1/event.py`**: `POST /api/v1/evaluate/event` endpoint with `evaluation_mode` parameter.
- **Unit tests**: `test_event_sequence.py`.

### Stream C — Document Discovery (Partial)

- **`services/discovery/connectors/base.py`**: `DocumentSource` and `IncrementalSource` protocols for multi-source discovery.
- **`services/discovery/analyzers/contract_corpus.py`**: Clusters historical contracts by semantic similarity, extracts de facto standard clauses, drafts candidate rules.
- **`services/discovery/connectors/sharepoint.py`**: SharePoint document source connector.
- **`services/discovery/connectors/google_drive.py`**: Google Drive document source connector.
- **`services/discovery/sources/contract_docx.py`**: Upgraded to full `DocumentSource` implementation with clause extraction.
- **Unit tests**: `test_document_discovery.py`.

### Stream D — Domain-Aware UX (Partial)

- **Route groups**: `app/(legal)/`, `app/(hr)/`, `app/(finance)/`, `app/(marketing)/` with dedicated shell layouts (`LegalShell`, `HrShell`, `FinanceShell`, `MarketingShell`).
- **`/contracts/review/[id]`**: Clause-by-clause verdict view with standard-clause overlay for Legal persona.
- **`/events/[id]`**: Event submission view with applicable rules, evaluation modes, and verdict display for HR persona.
- **`/transactions/[id]`**: Transaction compliance review page placeholder for Finance persona.
- **`/creatives/review/[id]`**: Creative compliance review page placeholder for Marketing persona.

### Remaining Phase 8 Work

- B6: HR system adapter stubs (Workday, SmartHR, freee HR)
- C2: Regulation PDF source upgrade
- C5: Regulation feed (e-Gov API / FSA notices) with `derives_from` linkage
- C8: Confluence and Notion connector upgrades
- C9: Incremental polling worker for regulation feeds
- D4: Department-aware home dashboard
- D5: No-code rule editor wizard
- D6: Intent-first search on home page
- D7: `pnpm lint` and `pnpm typecheck` verification
