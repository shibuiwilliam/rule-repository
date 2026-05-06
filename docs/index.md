# Rule Repository

The Rule Repository is a platform for managing, searching, serving, and enforcing natural-language rules. It stores rules written in plain language --- laws, contracts, internal policies, engineering guidelines, documentation standards --- and makes them operationally useful through LLM-assisted interpretation.

Where traditional rule engines require translating human rules into formal logic (losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs to interpret, search, enforce, and **improve** them at runtime.

## Key Capabilities

- **Store rules** as natural-language statements with document context, preconditions, exceptions, following/violation examples, provenance, revision history, governance metadata, and maturity level.
- **Progressive enforcement**: new rules start in **shadow mode** (experimental) --- they observe but don't block. Rules auto-promote to stable and proven based on accuracy. Teams add rules fearlessly.
- **Search 5 ways**: full-text (BM25), semantic (vector), category/tag, hybrid (BM25 + vector), and context-based (given facts, find applicable rules). Documents also support full-text, semantic, and hybrid search.
- **Extract rules from documents**: upload PDFs, text, or markdown files and run an LLM-powered extraction pipeline that captures rule context, preconditions, exceptions, and following/violation examples from the source document.
- **Evaluate compliance with full context**: submit code diffs, file changes, or free-form facts. The LLM evaluator receives the rule's rationale, context, preconditions, exceptions, and examples to produce accurate per-rule verdicts with **structured remediations**.
- **Deliver rules to AI agents**: expose the rule corpus via MCP server (12 tools), session context API (`GET /rules/context?files=...`), and CLI hooks. File-aware scope resolution matches rules to the files being edited.
- **Rule templates**: 5 pre-built rule sets (57 rules) for Python/FastAPI, TypeScript/React, security (OWASP), API design, and testing. Import in one API call.
- **Enforce via webhooks**: receive events from GitHub, Slack, or any webhook source, match them to enforcement policies, and run automated evaluation.
- **Discover rules automatically**: scan project artifacts (CLAUDE.md, linter configs, policy documents, code patterns) to identify implicit rules.
- **Self-improving flywheel**: capture human corrections, cluster similar patterns, auto-draft rule proposals via Gemini, and approve with one click. Every correction teaches the system.
- **Governance proposals**: propose rule changes (create, amend, retire, merge, split, override) through a collaborative workflow with multi-approver voting, threaded comments, conflict analysis, and impact preview.
- **Autonomous agent governance**: each AI agent gets a profile with trust levels, personalized rule delivery (mastered rules suppressed, weak areas boosted), verdict challenge/negotiation, and multi-agent governance sessions.
- **Rule marketplace**: publish versioned rule packages, subscribe across teams, and detect composition conflicts when combining packages.
- **Two-tier activity review**: rough triage across all rules followed by detailed LLM evaluation of relevant rules.
- **Compliance dashboard**: the home page shows agent compliance rate with 7-day trend, rules by status, top violated rules, recent corrections, and pending actions --- all in one view.
- **Organize by project**: rules belong to projects; a project selector filters everything across the UI and API. Search has its own project dropdown with an "All Projects" option.
- **Federate across teams**: compose rules hierarchically (organization, team, project) with inheritance and overrides. Add/remove rules and view effective rule sets in the tree view.
- **Observe rule health**: track per-rule health scores (6 dimensions), evaluation analytics, maturity distribution, and automated improvement recommendations.
- **Track agent performance**: per-agent compliance rates, violation trends, targeted rule delivery that boosts rules an agent historically breaks.
- **Rule Playground**: sandbox-test rules against code snippets or real-world scenarios (narrative + structured facts) without audit trails or caching.
- **Rule effectiveness scores**: per-rule precision, prevention rate, and agent adoption metrics. Proves ROI.
- **Weekly governance digest**: automated Monday report with compliance trends, top violations, and pending actions. Delivered via webhook.
- **Team comparison**: cross-project compliance comparison for multi-team organizations.
- **Proactive Alerts**: automated notifications for dormant rules, high deny rates, health decline, and conflicts. Six background workers run daily maintenance.
- **Versioned Snapshots**: capture immutable snapshots, deploy to environments (production, staging, development), simulate impact, and roll back.

## Get Started

See the [Quick Start](getting-started/quick-start.md) guide to have the full stack running locally in under five minutes.
