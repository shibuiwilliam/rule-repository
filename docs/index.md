# Rule Repository

The Rule Repository is a platform for managing, searching, serving, and enforcing natural-language rules. It stores rules written in plain language --- laws, contracts, internal policies, engineering guidelines, documentation standards --- and makes them operationally useful through LLM-assisted interpretation.

Where traditional rule engines require translating human rules into formal logic (losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs to interpret, search, enforce, and **improve** them at runtime.

## Key Capabilities

- **Store rules** as natural-language statements with full provenance to source documents, revision history, governance metadata, and maturity level.
- **Progressive enforcement**: new rules start in **shadow mode** (experimental) --- they observe but don't block. Rules auto-promote to stable and proven based on accuracy. Teams add rules fearlessly.
- **Search 5 ways**: full-text (BM25), semantic (vector), category/tag, hybrid (BM25 + vector), and context-based (given facts, find applicable rules).
- **Extract rules from documents**: upload PDFs, text, or markdown files and run an LLM-powered extraction pipeline that proposes candidate rules for human review. Bulk extraction runs in parallel.
- **Evaluate compliance with auto-remediation**: submit code diffs, file changes, or free-form facts and receive per-rule verdicts (ALLOW / DENY / NEEDS_CONFIRMATION) with **structured remediations** --- machine-readable fix objects that agents can apply automatically.
- **Deliver rules to AI agents**: expose the rule corpus to coding agents and other AI systems via an MCP server with 6 tools.
- **Enforce via webhooks**: receive events from GitHub, Slack, or any webhook source, match them to enforcement policies, and run automated evaluation.
- **Discover rules automatically**: scan project artifacts (CLAUDE.md, linter configs, policy documents, code patterns) to identify implicit rules.
- **Self-improving flywheel**: capture human corrections, cluster similar patterns, auto-draft rule proposals via Gemini, and approve with one click. Every correction teaches the system.
- **Compliance dashboard**: the home page shows agent compliance rate with 7-day trend, rules by status, top violated rules, recent corrections, and pending actions --- all in one view.
- **Organize by project**: rules belong to projects; a project selector filters everything across the UI and API. Search has its own project dropdown with an "All Projects" option.
- **Federate across teams**: compose rules hierarchically (organization, team, project) with inheritance and overrides. Add/remove rules and view effective rule sets in the tree view.
- **Observe rule health**: track per-rule health scores (6 dimensions), evaluation analytics, maturity distribution, and automated improvement recommendations.
- **Track agent performance**: per-agent compliance rates, violation trends, targeted rule delivery that boosts rules an agent historically breaks.
- **Rule Playground**: sandbox-test rules against code snippets or real-world scenarios (narrative + structured facts) without audit trails or caching.
- **Proactive Alerts**: automated notifications for dormant rules, high deny rates, health decline, and conflicts. Five background workers run daily maintenance.
- **Versioned Snapshots**: capture immutable snapshots, deploy to environments (production, staging, development), simulate impact, and roll back.

## Get Started

See the [Quick Start](getting-started/quick-start.md) guide to have the full stack running locally in under five minutes.
