# Rule Repository

The Rule Repository is a platform for managing, searching, serving, and enforcing natural-language rules. It stores rules written in plain language --- laws, contracts, internal policies, engineering guidelines, documentation standards --- and makes them operationally useful through LLM-assisted interpretation.

Where traditional rule engines require translating human rules into formal logic (losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs to interpret, search, and enforce them at runtime.

## Key Capabilities

- **Store rules** as natural-language statements with full provenance to source documents, revision history, and governance metadata.
- **Search 5 ways**: full-text (BM25), semantic (vector), category/tag, hybrid (BM25 + vector), and context-based (given facts, find applicable rules).
- **Extract rules from documents**: upload PDFs, text, or markdown files and run an LLM-powered extraction pipeline that proposes candidate rules for human review.
- **Evaluate compliance**: submit code diffs, file changes, or free-form facts and receive per-rule verdicts (ALLOW / DENY / NEEDS_CONFIRMATION) with fix suggestions.
- **Deliver rules to AI agents**: expose the rule corpus to coding agents and other AI systems via an MCP server and formatted rule context.
- **Enforce via webhooks**: receive events from GitHub, Slack, or any webhook source, match them to enforcement policies, and run automated evaluation.
- **Discover rules automatically**: scan project artifacts (CLAUDE.md, linter configs, code patterns) to identify implicit rules and propose them as candidates for human review.
- **Learn from corrections**: capture developer feedback on evaluation results and use it to create new rules, refine existing ones, and reduce false positives over time.
- **Organize by project**: rules belong to projects; a project selector filters rules, evaluations, and search across the UI and API.
- **Federate across teams**: compose rules hierarchically (organization, team, project) with inheritance and overrides so each team gets the right rule set.
- **Observe rule health**: track per-rule health scores, evaluation analytics, and automated improvement recommendations across the corpus.
- **Rule Playground**: sandbox-test rule statements against sample code without audit trails or caching, and manage per-rule test cases (manual, historical, and Gemini-generated).
- **Proactive Alerts**: receive automated notifications when rules become dormant, exhibit high deny rates, decline in health, or conflict with other rules.
- **Versioned Snapshots**: capture immutable snapshots of the rule corpus, deploy them to environments (production, staging, development), simulate impact, and roll back.

## Get Started

See the [Quick Start](getting-started/quick-start.md) guide to have the full stack running locally in under five minutes.
