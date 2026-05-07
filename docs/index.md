# Rule Repository

The Rule Repository is a platform for managing, searching, serving, and enforcing natural-language rules. It stores rules written in plain language -- laws, contracts, internal policies, engineering guidelines, documentation standards -- and makes them operationally useful through LLM-assisted interpretation.

Where traditional rule engines require translating human rules into formal logic (losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs to interpret, search, enforce, and **improve** them at runtime.

## Key Capabilities

- **Store rules** as natural-language statements with document context, preconditions, exceptions, following/violation examples, provenance, revision history, governance metadata, and maturity level.
- **Multi-domain coverage**: 13 pre-built rule templates (181+ rules) spanning HR/labor law, contracts, expenses, anti-corruption, data privacy, advertising compliance, Python/FastAPI, TypeScript/React, security (OWASP), API design, testing, documentation, and NDA review.
- **Progressive enforcement**: new rules start in **shadow mode** (experimental) -- they observe but don't block. Rules auto-promote to stable and proven based on accuracy. Teams add rules fearlessly.
- **Search 8+ ways**: full-text (BM25), semantic (vector), category/tag, hybrid (BM25 + vector), context-based (given facts, find applicable rules), temporal, citation, subject-aware, and conflict-aware. Documents also support full-text, semantic, and hybrid search.
- **Extract rules from documents**: upload PDFs, text, or markdown files and run an LLM-powered extraction pipeline that captures rule context, preconditions, exceptions, and following/violation examples from the source document. Contract-specific pipeline segments clauses and classifies them.
- **Evaluate compliance with full context**: submit code diffs, file changes, or free-form facts. The LLM evaluator receives the rule's rationale, context, preconditions, exceptions, and examples to produce accurate per-rule verdicts with **structured remediations**. Batched evaluation sends all rules in a single LLM call.
- **Two-tier activity review**: rough triage across all rules followed by detailed LLM evaluation of relevant rules, separating noise from signal.
- **Deliver rules to AI agents**: expose the rule corpus via MCP server (12 tools), session context API (`GET /rules/context?files=...`), and CLI hooks. File-aware scope resolution matches rules to the files being edited.
- **Enforce via webhooks**: receive events from GitHub, Slack, Teams, Email, or any webhook source, match them to enforcement policies, and run automated evaluation.
- **Discover rules automatically**: scan project artifacts (CLAUDE.md, linter configs, policy documents, code patterns) and business sources (Confluence, Notion, e-Gov, EUR-Lex) to identify implicit rules. One-click GitHub import fetches and analyzes repository files.
- **Self-improving flywheel**: capture human corrections, cluster similar patterns, auto-draft rule proposals via Gemini, and approve with one click. Every correction teaches the system.
- **Governance proposals**: propose rule changes (create, amend, retire, merge, split, override) through a collaborative workflow with multi-approver voting, threaded comments, conflict analysis, and impact preview.
- **Autonomous agent governance**: each AI agent gets a profile with trust levels, personalized rule delivery (mastered rules suppressed, weak areas boosted), verdict challenge/negotiation, and multi-agent governance sessions.
- **Compliance dashboard**: the home page shows compliance rate with 7-day trend, rules by status, top violated rules (with effectiveness scores), recent corrections, critical alert banners, and pending actions -- all in one view.
- **Organize by project**: rules belong to projects; a project selector filters everything across the UI and API.
- **Federate across teams**: compose rules hierarchically (organization, team, project) with inheritance and overrides.
- **Observe rule health**: track per-rule health scores, evaluation analytics, maturity distribution, and automated improvement recommendations.
- **Track agent performance**: per-agent compliance rates, violation trends, trust level progression, and targeted rule delivery that boosts rules an agent historically breaks.
- **Rule Playground**: sandbox-test rules against code snippets or real-world scenarios (narrative + structured facts) without audit trails or caching. LLM-powered test case generation.
- **Rule effectiveness scores**: per-rule precision, prevention rate, and agent adoption metrics. Color-coded quality dots on the rules list.
- **Weekly governance digest**: automated Monday report with compliance trends, top violations, most effective rules, declining rules, and pending actions. Delivered via webhook.
- **Team comparison**: cross-project compliance comparison for multi-team organizations.
- **Proactive alerts**: automated notifications for dormant rules, high deny rates, health decline, verdict drift, and effectiveness decline. Six background workers (arq + Redis) run daily maintenance.
- **Versioned snapshots**: capture immutable snapshots, deploy to environments (production, staging, development), simulate impact, and roll back.
- **Conversational tutor**: ask questions about rules in natural language and get LLM-powered explanations and guidance.
- **Persona-aware UI**: sidebar navigation adapts to role (All / Compliance / Engineering / AI Operator), showing the most relevant pages for each workflow.

## Get Started

See the [Quick Start](getting-started/quick-start.md) guide to have the full stack running locally in under five minutes.
