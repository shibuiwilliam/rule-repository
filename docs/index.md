# Rule Repository

The Rule Repository is a cross-organizational platform for managing, searching, serving, and enforcing natural-language rules. It stores rules written in plain language -- laws, contracts, internal policies, engineering guidelines, documentation standards -- and makes them operationally useful through LLM-assisted interpretation.

Where traditional rule engines require translating human rules into formal logic (losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs to interpret, search, enforce, and **improve** them at runtime.

## Key Capabilities

- **Store rules** as natural-language statements with document context, preconditions, exceptions, following/violation examples, provenance, revision history, governance metadata, classification level, and maturity level.
- **Multi-domain coverage**: 31 pre-built rule templates (300+ rules) spanning HR/labor law, contracts, expenses, anti-corruption, data privacy, advertising compliance, Python/FastAPI, TypeScript/React, security (OWASP/IaC), API design, testing, documentation, meta-governance, NDA review, finance (invoices, journal entries, POs, revenue recognition), access control, sales pricing, and more.
- **Subject polymorphism**: eight subject kinds (`CODE_DIFF`, `CLAUSE_SET`, `EVENT`, `TRANSACTION`, `CREATIVE`, `DECISION`, `IDENTITY`, `DOCUMENT`) allow the same evaluation pipeline to handle code diffs, contract clauses, HR events, financial transactions, and more. Adding a new domain means writing one adapter.
- **Department-aware governance**: rules belong to departments (Legal, HR, Finance, Sales, Marketing, IT, Operations, R&D, Executive). Proposals, intelligence digests, and notifications route through department resolvers to reach the right owners, approvers, and audiences.
- **Classification-based access control**: every rule, document, evaluation, and audit entry carries a classification (`PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`). PostgreSQL Row-Level Security, Elasticsearch document-level security, and MCP clearance enforcement ensure data boundaries.
- **Progressive enforcement**: new rules start in **shadow mode** (experimental) -- they observe but don't block. Rules auto-promote to stable and proven based on accuracy. Teams add rules fearlessly.
- **Search 8+ ways**: full-text (BM25), semantic (vector), category/tag, hybrid (BM25 + vector), context-based (given facts, find applicable rules), temporal, citation, subject-aware, and conflict-aware. Documents also support full-text, semantic, and hybrid search. All searches enforce classification filters.
- **Extract rules from documents**: upload PDFs, text, or markdown files and run an LLM-powered extraction pipeline that captures rule context, preconditions, exceptions, and following/violation examples from the source document. Contract-specific pipeline segments clauses and classifies them.
- **Evaluate compliance with full context**: submit code diffs, file changes, business events, or free-form facts. The LLM evaluator receives the rule's rationale, context, preconditions, exceptions, and examples to produce accurate per-rule verdicts with **structured remediations**. Batched evaluation sends all rules in a single LLM call.
- **Two-tier activity review**: rough triage across all rules followed by detailed LLM evaluation of relevant rules, separating noise from signal.
- **Deliver rules to AI agents**: expose the rule corpus via MCP server (24 tools including domain-specific retrieval and evaluation), session context API (`GET /rules/context?files=...`), and CLI hooks. File-aware scope resolution matches rules to the files being edited.
- **Enforce via webhooks**: receive events from GitHub, Slack, Teams, Email, or any webhook source, match them to enforcement policies, and run automated evaluation.
- **Discover rules automatically**: scan project artifacts (CLAUDE.md, linter configs, policy documents, code patterns) to identify implicit rules. One-click GitHub import fetches and analyzes repository files.
- **Self-improving flywheel**: capture human corrections, cluster similar patterns, auto-draft rule proposals via Gemini, and approve with one click. Every correction teaches the system.
- **Governance proposals**: propose rule changes (create, amend, retire, merge, split, override) through a collaborative workflow with multi-approver voting, threaded comments, conflict analysis, and impact preview.
- **Autonomous agent governance**: each AI agent gets a profile with trust levels, personalized rule delivery (mastered rules suppressed, weak areas boosted), and verdict challenge/negotiation.
- **Compliance dashboard**: the home page shows compliance rate with 7-day trend, rules by status, top violated rules (with effectiveness scores), recent corrections, critical alert banners, and pending actions -- all scoped to the user's department(s).
- **Organize by project**: rules belong to projects; a project selector filters everything across the UI and API.
- **Federate across teams**: compose rules hierarchically (organization, team, project) with inheritance and overrides.
- **Observe rule health**: track per-rule health scores, evaluation analytics, maturity distribution, and automated improvement recommendations.
- **Track agent performance**: per-agent compliance rates, violation trends, trust level progression, and targeted rule delivery that boosts rules an agent historically breaks.
- **Rule Playground**: sandbox-test rules against code snippets or real-world scenarios (narrative + structured facts) without audit trails or caching. LLM-powered test case generation and counterexample creation.
- **Rule effectiveness scores**: per-rule precision, prevention rate, and agent adoption metrics. Color-coded quality dots on the rules list.
- **Weekly governance digest**: automated Monday report with compliance trends, top violations, most effective rules, declining rules, and pending actions. Delivered via webhook.
- **Team comparison**: cross-project compliance comparison for multi-team organizations.
- **Proactive alerts**: automated notifications for dormant rules, high deny rates, health decline, verdict drift, effectiveness decline, and conflicts. Background workers (arq + Redis) run daily maintenance.
- **Versioned snapshots**: capture immutable snapshots, deploy to environments (production, staging, development), simulate impact, and roll back.
- **Conversational tutor**: ask questions about rules in natural language and get LLM-powered explanations and guidance.
- **Persona-aware UI**: 9 persona portals (Engineering, Legal, HR, Finance, Sales, Compliance, Security, Marketing, Admin) with dedicated dashboards, navigation, and `PersonaSwitcher` for cross-portal navigation.
- **Multilingual**: English and Japanese UI via `next-intl`.
- **Compliance-grade audit**: append-only, hash-chained audit log with WORM storage mirroring, transparency log anchoring (Sigstore Rekor), PII redaction, legal hold, and regulator export formats (J-SOX, SOX, FSA, GDPR).
- **8 domain modules**: engineering, legal, HR, finance, IT security, sales, communications, and governance -- each with its own evaluators, context assemblers, discovery analyzers, and evaluation prompts.
- **Tier 1 infrastructure**: run the full platform with Postgres only (no Elasticsearch, Neo4j, or Redis required). Postgres FTS, adjacency tables, and in-process scheduling provide graceful fallbacks.
- **Pluggable LLM providers**: Gemini (default), Anthropic Claude, OpenAI, Azure OpenAI, Bedrock, and self-hosted. LLM router with fallback chain and circuit breaker. Per-tenant provider overrides.
- **Eval harness**: 90 golden cases across 8 domains validate LLM evaluation quality. Nightly regression with CI gates that block merges on quality drops.
- **Safety**: prompt injection defense (20 patterns, 31 tests), mandatory PII scrubbing middleware, pre-ingest secrets/PII scanner.
- **Risk register**: map rules to organizational risks. Track coverage gaps and risk exposure.
- **Attestation campaigns**: require periodic human attestation of rule compliance. Track campaign status and responses.
- **Regulatory source feeds**: track regulation amendments (e-Gov, FSA). Auto-draft proposals when upstream regulations change.
- **Confidence calibration**: conformal prediction for high-stakes scopes. Multi-judge consensus for CRITICAL evaluations.
- **Verdict drift detection**: weekly replay of canary inputs detects unexpected LLM behavior changes.
- **Polyglot rules**: rules can have translations in multiple locales with consistency verification.
- **Surface abstraction**: 7 evaluation surfaces (code, contract, document, human_action, message, transaction, generic) normalize different input types into a common pipeline. Adding a new surface means implementing one adapter.
- **Domain Packs**: 9 bundled rule packs with scopes, UI routes, prompts, analyzers, and sample data per domain (code, contract, HR attendance, expense, communication, legal, sales, IT security, governance). Loaded at startup by `DomainPackLoader`, controlled by `ENABLED_PACKS` env var.
- **Hybrid evaluation**: rules with `kind=computational` and structured `constraints` are evaluated deterministically before the LLM. Numeric thresholds (expense caps, overtime limits), date comparisons, and enum checks run without LLM calls — only ambiguous cases fall through.
- **Structured scope**: multi-axis scope with `domain`, `org_unit`, `subject_type` dimensions plus ad-hoc attributes (jurisdiction, role, confidentiality). Enables precise cross-organizational rule matching like "US managers' expense policy".
- **Feature flags**: comprehensive flag system (see [FEATURES.md](../FEATURES.md)) controlling infrastructure tiers, cross-org features, opt-in features, and frozen features. All flags verified for graceful degradation.
- **Norm lineage**: trace rule derivation chains from source laws/regulations down to operational rules (and vice versa). Background propagation of upstream norm amendments.
- **Contract review CLI**: `rulerepo-review-contract` evaluates contracts from the command line against organizational clause rules.
- **Action check CLI**: `rulerepo-check-action` evaluates human actions (overtime registration, leave requests) against applicable rules.

## Get Started

See the [Quick Start](getting-started/quick-start.md) guide to have the full stack running locally in under five minutes.
