# Rule Repository

> A software platform for managing, searching, serving, and enforcing natural-language rules — laws, contracts, internal policies, engineering guidelines, and documentation standards — using LLMs and AI agents.

---

## 1. Project Overview

The **Rule Repository** is a system that stores human-authored rules in their original natural-language form and makes them operationally useful: searchable, applicable, and enforceable across business systems and software development environments. Where traditional rule engines require translating human rules into a formal language (and losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs and AI agents to interpret, search, and enforce them at runtime.

This approach is inspired by, and generalizes, the concept of **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea in three directions:

- **Wider scope of rules**: not only AI agent guardrails, but laws, contracts, HR policies, engineering rules, and documentation conventions.
- **Wider scope of consumers**: human users, business systems, IDEs, CI pipelines, and AI agents.
- **Wider scope of time**: pre-flight checks, post-hoc audits, and continuous compliance monitoring.

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository fills a gap that no current category of software addresses cleanly:

- **Document management systems** store the source documents but do not understand the rules inside them.
- **Rule engines (Drools, DMN, OPA)** require formal encoding and lose the original semantics.
- **GRC platforms** track compliance status but do not enforce rules at the point of action.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.

The Rule Repository treats **rules themselves as first-class, versioned, governed assets**, decoupled from any single consumer and reusable across the entire organization.

---

## 3. Goals and Non-Goals

### 3.1 Goals
- Store rules in natural language, with full traceability to their source documents.
- Provide rich search (full-text, vector, category, hybrid, intent-based) over rule corpora.
- Enable runtime evaluation: "given this context and intent, is this action compliant with the relevant rules?"
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Detect conflicts, redundancies, and dead rules across the corpus.
- Make rule provenance, rationale, and revision history first-class.
- Provide ergonomic SDKs so business systems and AI agents can integrate easily.

### 3.2 Non-Goals
- Replacing IAM, RBAC, ABAC, or network-layer access control. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel or compliance officers. The system surfaces issues; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts on behalf of users.

---

## 4. Architecture

The system is composed of three top-level components:

```
┌──────────────────────────────────────────────────────────────┐
│                    Rule Management Server                      │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐   │
│  │ Extraction │  │   Search   │  │  Code-Aware          │   │
│  │  Pipeline  │  │  (FT/Vec/  │  │  Evaluation Engine   │   │
│  │            │  │  Cat/Hyb)  │  │  (LLM-as-Judge)      │   │
│  └────────────┘  └────────────┘  └──────────────────────┘   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐   │
│  │ Discovery  │  │ Rule Store │  │  Intelligence &      │   │
│  │  Engine    │  │ (PG+ES+   │  │  Observability +     │   │
│  │            │  │  Neo4j)   │  │  Feedback Loop       │   │
│  └────────────┘  └────────────┘  └──────────────────────┘   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐   │
│  │ Governance │  │  Gateway   │  │  Context Delivery    │   │
│  │ / RBAC +   │  │  (webhook  │  │  (MCP + Formatter)   │   │
│  │ Federation │  │  enforce)  │  │                      │   │
│  └────────────┘  └────────────┘  └──────────────────────┘   │
│  ┌────────────┐                                              │
│  │ Audit Log  │                                              │
│  │ (hash-     │                                              │
│  │  chained)  │                                              │
│  └────────────┘                                              │
│    REST API │ Intent API │ Evaluate API │ Gateway API        │
└─────────────┼────────────┼──────────────┼────────────────────┘
              │            │              │
  ┌───────────┼────────────┼──────────────┼──────────────┐
  │           │            │              │              │
┌─▼──────┐ ┌─▼──────┐ ┌──▼───────┐ ┌───▼────────┐ ┌──▼──────┐
│  Rule  │ │Agentic │ │   MCP    │ │   CLI      │ │ GitHub  │
│ Client │ │ Client │ │  Server  │ │  Tools     │ │  App    │
│  SDK   │ │  SDK   │ │(agents)  │ │(CI/hooks)  │ │(PR rev) │
└────────┘ └────────┘ └──────────┘ └────────────┘ └─────────┘
    │           │           │             │             │
    ▼           ▼           ▼             ▼             ▼
 Business    HR/Contract  Claude Code   CI pipelines  GitHub
 systems     systems      + any MCP     (GH Actions)  PRs
                          agent
```

### 4.1 Trust and Data Boundaries
- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and judgments they are authorized to see.
- All evaluation calls produce immutable audit records on the server side.

---

## 5. Domain Model

### 5.1 The `Rule` Entity

A rule is the central first-class object. It is **not** a regex or a code expression; it is a structured envelope around a natural-language statement.

| Field | Description |
|---|---|
| `id` | Stable identifier |
| `statement` | The rule text in natural language (the canonical form) |
| `source_refs` | Pointers to the source document, section, and offset |
| `scope` | Who/what the rule applies to (org units, roles, systems, regions) |
| `modality` | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `effective_period` | `valid_from` / `valid_until` |
| `preconditions` | Facts required to evaluate the rule |
| `exceptions` | References to other rules or carve-outs |
| `rationale` | Why the rule exists (purpose, intent) |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `tags` | Free-form taxonomic labels |
| `governance` | Owner, approvers, revision history |
| `embedding` | Vector representation (derived) |

The `statement` is the **source of truth**. Structured fields exist for indexing, filtering, and prioritization — never to override the meaning of the statement.

### 5.2 Rule Relationships

Rules form a graph, not a flat list. Modeling these relationships explicitly is what turns the repository from a list into a **provenance and impact graph**.

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision that replaces a prior version |

### 5.3 Meta-Rules

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy"). Meta-rules are evaluated by the same engine but are scoped to govern the rule corpus itself.

---

## 6. Components

### 6.1 Rule Management Server

The server is the system of record for all rules.

**Capabilities:**
- **Rule CRUD** with revision history and effective-date semantics.
- **Extraction pipeline** that ingests documents (contracts, regulations, policy PDFs) and proposes candidate rules through a multi-stage process: structural parsing → normative-sentence detection → coreference resolution → metadata inference → relationship suggestion → human review.
- **Search APIs**:
  - Full-text search
  - Vector search (semantic similarity)
  - Category/tag search
  - Hybrid search (BM25 + vector reranking)
  - **Context search**: given a body of facts, return applicable rules
  - **Impact search**: given a proposed rule change, return affected rules
- **Intent API**: a natural-language endpoint that classifies the user's intent (`lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`) and routes to the appropriate backend.
- **Evaluation engine**: given context + candidate action + relevant rules, returns a verdict (`ALLOW` / `DENY` / `NEEDS_CONFIRMATION`) with a human-readable reason and a structured **reason graph**.
- **Audit log**: append-only, hash-chained record of all evaluations including inputs, applied rules, model identity, and verdict.
- **Governance**: role-based access (Owner / Approver / Reader) per rule category, revision approval workflow, and effective-date scheduling.

### 6.2 Rule Client (Python SDK)

A thin, ergonomic wrapper over the server APIs.

```python
from rulerepo import RuleClient

client = RuleClient(server_url="...", api_key="...")

# Search
rules = client.search.hybrid("overtime monthly limit", scope="hr/attendance")

# Intent
result = client.intent.ask("What are the rules for refunding orders over $500?")

# CRUD
rule = client.rules.get("rule_abc123")
client.rules.update(rule.id, statement="...", revision_note="...")
```

### 6.3 Agentic Rule Client (Python SDK)

A higher-level client that wraps `RuleClient` and adds AI-agent capabilities for systems that need to **enforce** rules, not merely query them.

**Added capabilities:**
- **Automatic context gathering**: given an event, pull related facts from surrounding systems before evaluation.
- **Two-stage evaluation**: first narrow the rule set by metadata and embeddings, then evaluate the narrow set with a high-quality model.
- **Result caching**: hash-keyed cache, automatically invalidated on rule revision.
- **Reason graphs**: structured DAG of which facts triggered which conditions in which rules.
- **Repair suggestions**: when an action is denied, propose the minimum modification that would make it compliant.
- **Three integration modes**:
  - `preflight` — block actions before they happen (low-latency).
  - `posthoc` — batch audit after the fact (high-accuracy).
  - `sidecar` — observe in parallel without blocking the primary flow.

```python
from rulerepo.agentic import AgenticRuleClient

client = AgenticRuleClient(server_url="...", scope="hr/attendance")

result = client.evaluate(
    context={"employee_id": "E001", "month": "2025-04", "overtime_hours": 50},
    intent="register_overtime",
    mode="preflight",
)

if result.verdict == "DENY":
    print(result.violations)        # which rules were violated
    print(result.reason_graph)      # why
    print(result.suggested_fix)     # how to comply
```

---

### 6.4 Code-Aware Evaluation Engine

The evaluation engine is the core differentiator. It accepts code changes as first-class input, maps them to relevant rules, and returns verdicts with code-specific remediation.

**Pipeline**: Context Assembly → Rule Selection → LLM-as-Judge → Verdict Aggregation

- **Context Assembler**: Accepts unified diffs, file paths, or free-form facts. Parses diffs into structured `FileChange` objects with language detection and function extraction.
- **Rule Selector**: Narrows the corpus to ~5-20 relevant rules via scope/severity/modality/tag filtering, then semantic ranking. Runs in <50ms for the metadata stages.
- **Evaluation Core**: Runs each selected rule against the context using Gemini with structured JSON output. Model selection is tiered by severity: Flash for LOW/MEDIUM, Flash+medium-thinking for HIGH, Pro+high-thinking for CRITICAL.
- **Verdict Aggregator**: Combines per-rule verdicts (any DENY → overall DENY) and builds a fix summary.

**Code-aware features**: understands file paths for scope matching, understands diffs to evaluate only what changed, references specific functions and lines, and returns actionable fix suggestions.

### 6.5 Agent Context Delivery (MCP + Smart Rule Selection)

Exposes the Rule Repository to AI coding agents via the Model Context Protocol (MCP). The key innovation is **active context delivery** — rules reach the agent at the right moment without being asked.

- **MCP Server**: FastMCP server with stdio (for Claude Code) and streamable-http (for remote agents) transports.
- **Tools**: `search_rules`, `evaluate_compliance`, `explain_rule`, `find_conflicts`, `get_rules_for_context` (the key tool).
- **Resources**: `rule://{id}` (single rule), `ruleset://{scope}` (dynamic CLAUDE.md section).
- **Prompts**: `compliance_check`, `rule_summary`, `impact_analysis` (structured agent workflows).
- **Rule Formatter**: Three output formats optimized for LLM context — `instructions` (concise MUST/SHOULD hierarchy), `checklist` (PR review), `detailed` (full metadata).
- **Scope Registry**: In-memory file-glob-to-rule mapping for sub-10ms rule selection.
- **CLAUDE.md Generator**: `scripts/generate_claude_md.py` exports rules as static CLAUDE.md sections for teams not yet on MCP.

### 6.6 Development Workflow Integration

Integration into the places where code is written, reviewed, and merged.

- **GitHub PR Review**: Webhook receiver processes `pull_request` events, runs evaluation, posts structured review comments with per-rule verdicts and fix suggestions.
- **CI Pipeline CLI** (`rulerepo-check`): Runs `git diff` → evaluates → exits 0/1/2. Supports `--format text|json|github-actions` for inline PR annotations.
- **Agent Hooks** (`rulerepo-hook`): `preflight` mode injects applicable rules before edit, `posthoc` mode evaluates changes after edit. Designed for Claude Code hooks.
- **Rule Ingestion** (`rulerepo-ingest`): Imports CLAUDE.md files as rule sources through the extraction pipeline.

### 6.7 Rule Intelligence & Observability

Analytics, health scoring, and automated improvement recommendations.

- **Health Scorer**: Per-rule score (0-100) across 6 dimensions — completeness, clarity, test coverage, freshness, activity, owner engagement.
- **Evaluation Analytics**: Corpus-wide and per-rule metrics from the audit log — fire rate, deny rate, latency, trends.
- **Recommender**: Automated suggestions — retire dormant rules, clarify ambiguous ones, escalate persistent violations, strengthen SHOULD→MUST.
- **Dashboard**: Frontend Intelligence page with summary cards, health table, and recommendation list.

### 6.8 Rule Enforcement Gateway

Event-driven, zero-code rule enforcement via webhooks.

- **Webhook Ingestion**: Receives events from GitHub, Slack, or generic sources at `/api/v1/gateway/ingest/{source}`.
- **Policy Engine**: Matches events to enforcement policies using fnmatch patterns.
- **Event Normalizers**: GitHub (PR, issue events), Slack (message events), Generic (pass-through).
- **Automated Evaluation**: Matched policies trigger the evaluation engine with extracted context.

### 6.9 Automatic Rule Discovery

Solves the cold-start problem: instead of requiring humans to write rules from scratch, the system discovers rules that already exist implicitly in a project's artifacts.

- **Source Analyzers**: CLAUDE.md parser (extracts rules from agent instructions with modality detection and scope inference), linter config parser (converts ruff/eslint/tsconfig/prettier settings into natural-language rules with appropriate modality and severity), and code pattern analyzer (static analysis reveals implicit conventions — e.g., "94% of handlers use Pydantic" becomes a candidate rule).
- **Pattern Detector**: Frequency analysis and deduplication across sources, with confidence scoring. Patterns detected independently from multiple sources receive higher confidence.
- **Candidate Generator**: Gemini-powered refinement of raw patterns into structured rule candidates with statement, modality, severity, scope, and rationale. Uses structured JSON output.
- **Human Review Queue**: All candidates go through an approve/edit/dismiss workflow before becoming active rules. Batch approval is available for high-confidence candidates (>0.9).
- **API**: `POST /api/v1/discover/scan` (trigger scan), `GET /api/v1/discover/candidates` (review candidates), `POST /api/v1/discover/candidates/{id}/approve` (create rule from candidate).
- **MCP Tool**: `discover_rules` — allows any MCP-connected agent to bootstrap rules from a codebase.
- **Frontend**: `/discover` page with source selector, scan progress, and candidate review workflow.

### 6.10 Agent Correction Feedback Loop

Captures human corrections of AI-generated code and converts them into rule improvements, creating a flywheel: more agent usage -> more corrections -> better rules -> fewer corrections.

- **Correction Capture**: Two mechanisms — PR-based (passive: compares evaluated diff with final merged diff to identify human corrections) and agent hook-based (active: detects human edits to files recently modified by an agent).
- **Correction Analyzer**: Classifies each correction as `new_rule` (no matching rule exists — the correction reveals a coverage gap), `improve_existing` (a rule exists but is ambiguous — suggest rewrite), or `adjust_scope` (a rule exists but wasn't delivered to the agent — widen scope/file matching).
- **Candidate Generation**: Gemini drafts a rule (or rewrite) from the correction context, with structured output for statement, modality, severity, and scope.
- **Background Workers**: arq + Redis infrastructure for scheduled health scoring, recommendation generation, correction statistics aggregation, and async analysis.
- **Intelligence Integration**: Correction trends over time, top violated rules (which rules agents break most), coverage gaps (file paths/scopes with unmatched corrections), and rule effectiveness (did corrections decrease after a rule was created?).
- **API**: `POST /api/v1/feedback/corrections` (submit correction), `GET /api/v1/feedback/stats` (correction analytics), approve/dismiss workflow.
- **Frontend**: `/feedback` page for correction review; additions to `/intelligence` with correction trend charts, top violated rules table, and coverage gap heatmap.

### 6.11 Cross-Project Rule Federation

Hierarchical rule composition across organizational boundaries: organization -> team -> project. Rules at higher levels automatically apply to all descendants, with project-level overrides.

- **Hierarchy**: Organization rules apply to all teams and projects. Team rules apply to all projects in the team. Project rules apply only to that project. Each level can override a parent rule (the override replaces, not supplements, the parent rule).
- **Federation Resolver**: Walks the ancestor chain (project -> team -> organization), collects rules from all levels, and applies overrides. The unified rule set feeds into the existing rule selector transparently.
- **Domain Model**: `RuleFederation` (id, name, level, parent_id, default_scope) and `RuleFederationMembership` (rule_id, federation_id, override_parent_rule_id) in PostgreSQL.
- **Evaluation Integration**: `rule_selector` accepts a `federation_id` parameter. When set, rules are resolved through the hierarchy. When absent, behavior is unchanged.
- **MCP Integration**: `get_rules_for_context` accepts an optional `federation` parameter (e.g., `"acme-corp/backend/payments-api"`) for hierarchical rule resolution.
- **Rule Sync**: When an organization-level rule changes, all descendant projects are flagged for re-evaluation and notifications fire.
- **API**: Full CRUD at `/api/v1/federations`, plus `GET /api/v1/federations/{id}/effective-rules` (inherited + own) and `GET /api/v1/federations/{id}/diff/{other_id}` (compare two nodes).
- **Frontend**: `/federations` page with tree view, effective rules per node with inheritance source, override button on inherited rules, and diff view between nodes.

### 6.12 Rule Playground & Testing Framework

Interactive sandbox and regression testing for rules.

- **Playground**: `POST /api/v1/playground/evaluate` accepts a draft rule statement + sample code and returns a verdict without persisting anything — no audit log writes, no cache writes, no rule creation. Pure sandbox for testing rule wording.
- **Per-Rule Test Cases**: Each rule can have test cases (sample input + expected verdict). Test cases can be manually created, auto-generated from historical evaluations, or generated by Gemini from the rule statement.
- **Test Runner**: `POST /api/v1/rules/{id}/test-cases/run` executes all test cases against the rule, compares actual vs expected verdicts, and reports pass/fail.
- **Test Generator**: `POST /api/v1/rules/{id}/test-cases/generate` calls Gemini to auto-create compliant and non-compliant examples.
- **Frontend**: `/playground` page with split-pane layout (rule editor + code editor + result panel). Test Cases tab on rule detail page.

### 6.13 Proactive Alert System

Background workers generate alerts when they detect problems during scheduled analysis.

- **Alert Types**: `dormant_rule` (0 evaluations in 90 days), `high_deny_rate` (>50% deny rate), `health_decline` (score dropped below 40), `conflict_detected` (repeated rule conflicts).
- **Alert Lifecycle**: `active` → `acknowledged` → `resolved`. All alerts have severity (info/warning/critical), title, description, and optional rule reference.
- **Webhook Notifications**: Critical alerts dispatch via `send_webhook()` to the configured `ALERT_WEBHOOK_URL`.
- **API**: `GET /api/v1/alerts`, `POST /api/v1/alerts/{id}/acknowledge`, `POST /api/v1/alerts/{id}/resolve`.

### 6.14 Rule Set Snapshots & Environment Deployment

Versioned snapshots of the rule corpus with environment-based deployment and impact simulation.

- **Snapshots**: Immutable frozen copies of all rules matching a scope filter at a point in time. Stored as JSONB in PostgreSQL. Created via `POST /api/v1/snapshots`.
- **Environment Deployment**: Deploy a snapshot to `production`, `staging`, or `development`. Only one active deployment per environment. Deactivates the previous deployment atomically.
- **Rollback**: Reactivate the previous deployment for an environment via `POST /api/v1/snapshots/{id}/rollback`.
- **Impact Simulation**: Before deploying, `POST /api/v1/snapshots/{id}/simulate` compares the proposed snapshot against the current deployment — shows rules added/removed and risk assessment.
- **Evaluation Integration**: `POST /api/v1/evaluate` accepts an `environment` parameter. When set, evaluation uses only rules from the active snapshot for that environment.
- **MCP Integration**: `evaluate_compliance` tool accepts `environment` parameter.
- **Frontend**: `/snapshots` page with create/deploy/rollback/simulate workflow.

---

## 7. Key Features

### 7.1 Foundational
- Natural-language rule storage with full provenance to source documents.
- Multi-modal search (full-text, vector, category, hybrid).
- Rule lifecycle: draft → review → approved → effective → superseded → retired.
- REST API and Intent API.
- Python SDK (Rule Client) and Agentic SDK.

### 7.2 Differentiating
- **Conflict Detector**: continuously scans for `conflicts_with` candidates across the corpus.
- **Counterexample Generator**: for each rule, generates minimal compliant and non-compliant examples that serve as regression tests.
- **Rule Coverage**: identifies dormant rules (never triggered) and over-triggered rules (likely misaligned with reality) using event logs.
- **Change Impact Simulator**: replays historical events against a proposed rule revision to show what would have changed.
- **Refinement Feedback Loop**: when humans correct a verdict, the system identifies the ambiguous rule wording and proposes rewrites.
- **Polyglot Rules**: maintains semantically equivalent rule pairs across languages (e.g., EN/JA contracts) and continuously verifies their equivalence.
- **Provenance Lineage**: tracks the chain Law → Internal Policy → Department Rule → Contract Clause, so upstream changes propagate downstream.
- **Rule Tutor**: an LLM-powered conversational interface that explains relevant rules to new employees or new project members.
- **Why API**: returns multi-level rationale for any verdict, traversing `rationale` and `source_refs`.
- **Automatic Rule Discovery**: bootstraps rules from CLAUDE.md, linter configs, and code conventions — solves the cold-start problem.
- **Correction Feedback Loop**: learns from human corrections of AI-generated code, turning every fix into a candidate rule.
- **Cross-Project Federation**: org->team->project rule inheritance with overrides, enabling organization-wide governance.
- **Rule Playground**: interactive sandbox for testing rules against sample code before deployment.
- **Proactive Alerts**: background workers detect dormant rules, high deny rates, and health decline — notify via webhooks.
- **Versioned Snapshots**: atomic deployment of rule sets to environments with rollback and impact simulation.

### 7.3 Cross-Cutting
- Immutable audit log with hash-chained integrity.
- Tiered LLM strategy: small/fast models for screening, large/accurate models for high-severity judgments, optional consensus voting for `CRITICAL` rules.
- PII sanitization on inputs and masking on logs.
- RBAC per rule category with Owner / Approver / Reader separation.

---

## 8. Use Cases

### 8.1 HR / Attendance Management
The HR system registers attendance and overtime. The Rule Repository holds the work regulations. The Agentic Rule Client validates each registration in `preflight` mode and alerts on violations (e.g., monthly overtime exceeding the legal limit, missing 36-agreement filing).

### 8.2 Contract Management
The contract management system stores contracts under negotiation. The Rule Repository holds internal procurement rules and prior contract clauses. When a new contract is registered, the Agentic Rule Client checks for contradictions with internal policy and conflicts with prior contracts.

### 8.3 Software Development
The Rule Repository stores the engineering team's coding standards, documentation conventions, and review checklists. CI pipelines use the Rule Client to evaluate pull requests against these rules and post review comments. IDE extensions surface relevant rules as developers write code.

### 8.4 Regulatory Compliance
A financial institution stores regulations (e.g., consumer protection laws) in the repository, with derived internal procedures linked via `derives_from`. When a regulation is amended, the Provenance Lineage and Change Impact Simulator together identify all downstream procedures that need review.

### 8.5 AI-Assisted Development
A team uses Claude Code with the Rule Repository. Rule Discovery bootstraps 50 rules from their existing CLAUDE.md, linter configs, and code conventions in an afternoon. Agents receive applicable rules via MCP and write compliant code from the start. When a human reviews AI-generated code and makes corrections, the Correction Feedback Loop captures the delta, proposes new rules, and the correction rate drops over time. Organization-wide engineering standards are shared across all team repositories via Federation, with project-specific overrides where needed.

---

## 9. Technical Stack (Proposed)

These are starting recommendations, subject to revision during implementation.

| Layer | Recommended Technology |
|---|---|
| Language (server) | Python (FastAPI) or Go |
| Language (clients) | Python (initial), TypeScript (next) |
| Rule store | PostgreSQL with `pgvector` for embeddings, or a dedicated vector DB |
| Full-text search | OpenSearch or PostgreSQL FTS |
| Document storage | S3-compatible object storage |
| LLM access | Pluggable provider layer (Anthropic, OpenAI, Google, self-hosted) |
| Audit log | Append-only table with hash chain; optional WORM storage |
| Task queue | Redis + arq (background workers for health scoring, correction analysis, scheduled jobs) |
| Auth | OIDC / OAuth2 |
| Deployment | Container-native, Kubernetes-ready |

The architecture intentionally avoids hard-coding a single LLM provider. The `Evaluator` interface should accept any model that can perform structured judgment.

---

## 10. Roadmap

The project is structured in four phases, each delivering independent value.

### Phase 1 — Foundation (Storage & Search) [COMPLETE]
- Rule data model and persistence
- Document ingestion and rule extraction pipeline (assisted, human-approved)
- Full-text, vector, category, and hybrid search
- REST API and Intent API
- Rule Client (Python SDK)
- Basic governance (RBAC, revision history)

**Value delivered:** "Our rules are organized and findable."

### Phase 2 — Enforcement (Evaluation & Integration) [COMPLETE]
- Code-Aware Evaluation Engine (§6.4): diff parsing, rule selection, LLM-as-Judge, verdict aggregation
- Agent Context Delivery (§6.5): MCP server, smart rule selection, three output formats
- Development Workflow Integration (§6.6): GitHub PR review, CI CLI, agent hooks, rule ingestion
- Agentic Rule Client with real evaluation via `POST /api/v1/evaluate`
- Rule Enforcement Gateway (§6.8): webhook-driven enforcement with policy engine
- Rule Intelligence (§6.7): health scoring, analytics, recommendations

**Value delivered:** "Our rules are enforced where work happens."

### Phase 3 — Discovery & Learning [COMPLETE]
- Automatic Rule Discovery (§6.9): source analyzers, pattern detection, candidate generation, human review queue, MCP tool
- Agent Correction Feedback Loop (§6.10): correction capture, analyzer, candidate generation, background workers (arq + Redis), intelligence integration
- Cross-Project Rule Federation (§6.11): hierarchical rule composition, federation resolver, evaluation and MCP integration, rule sync

**Value delivered:** "Our rules bootstrap themselves, learn from corrections, and scale across the organization."

### Phase 3.5 — Adoption Acceleration [IMPLEMENTED]
- One-click GitHub repository import: `POST /api/v1/discover/import` fetches CLAUDE.md, linter configs, and code patterns from a GitHub URL → produces candidate rules in seconds
- Automatic PR correction capture: `services/feedback/pr_capture.py` compares evaluated diff vs merged diff to auto-capture human corrections
- Rule impact preview: `services/evaluation/impact_preview.py` replays historical evaluations with modified rule to show blast radius before committing changes
- Conflict resolution transparency: evaluate API now returns `conflict_resolutions[]` showing which rules were overridden and why
- Cache + top violations analytics: intelligence dashboard exposes LLM cache hit rate and most frequently violated rules

**Value delivered:** "Rules bootstrap in minutes, learn from every PR, and update confidently."

### Phase 4 — Testing & Deployment Safety [COMPLETE]
- Rule Playground (§6.12): sandbox evaluation, no-persistence testing
- Per-Rule Test Cases: manual, historical, and Gemini-generated test cases with pass/fail tracking
- Proactive Alerts (§6.13): background workers generate alerts for dormant rules, high deny rates, health decline
- Rule Set Snapshots (§6.14): versioned snapshots, environment deployment, rollback, impact simulation
- Environment-based evaluation: evaluate API and MCP tools accept environment parameter

**Value delivered:** "Rules can be tested before deployment, the system alerts on problems, and rule sets deploy safely."

### Phase 5 — Self-Improving Governance [PLANNED]

#### 5a. Correction-to-Rule Flywheel
- Automatic rule drafting: when 3+ corrections in the same pattern accumulate within 14 days with confidence > 0.8, auto-create a DRAFT rule with linked evidence
- Smart batching: cluster corrections by semantic similarity before drafting (avoid 50 individual draft rules)
- Maintainer routing: auto-notify the scope's rule owner with evidence, confidence score, and approve/edit/dismiss actions
- Effectiveness tracking: measure correction rate before vs after rule activation to prove ROI

#### 5b. Structured Remediation
- Machine-readable `Remediation` objects in evaluation response (type, file, line, action, original, replacement)
- Agents can auto-apply fixes for low-severity rules without human intervention
- `--auto-fix` flag for `rulerepo-check` CLI that applies remediations and re-evaluates
- CI pipelines that self-heal: fix → commit → re-check → pass

#### 5c. Rule Maturity Model
- Three maturity levels: `experimental` → `stable` → `proven`
- Experimental rules (< 30 days) produce NEEDS_CONFIRMATION instead of DENY (shadow mode)
- Auto-promotion based on false positive rate: < 5% → stable, < 1% → proven
- Progressive enforcement: observe → warn → enforce pipeline visible on dashboard

#### 5d. Advanced Intelligence
- Conflict detector (continuous scanning)
- Verdict drift detection (temporal, model, semantic)
- Agent performance dashboard (compliance rate per agent, top violations, trends)
- Webhook subscriptions for rule change notifications
- Weekly governance digest (new drafts, promotions, top violations, pending actions)
- Provenance lineage propagation, polyglot rule sync, Rule Tutor

**Value delivered:** "Our rules improve themselves — every correction teaches the system."

---

## 11. Success Metrics

- **Coverage**: percentage of rules in target source documents successfully extracted and registered.
- **Latency**: p50 / p95 / p99 evaluation latency in `preflight` mode.
- **Accuracy**: human-rated correctness of verdicts on a held-out test set; precision and recall on conflict detection.
- **Adoption**: number of integrated systems and active rules; volume of evaluation requests per day.
- **Governance health**: percentage of rules with complete metadata, current rationale, and active owners.
- **Time-to-comply on regulatory change**: median time between a source-law amendment and the corresponding internal rule revision being approved.

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Always log full evaluation context; require human review on high-severity denials; consensus voting for CRITICAL rules; refinement feedback loop. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity; refinement loop suggests rewrites; require unit tests on each rule. |
| LLM costs scale poorly with rule corpus size | Two-stage evaluation (metadata pre-filter, then LLM); aggressive caching; tiered model selection. |
| Sensitive data leaks through evaluation context | Input sanitization; log masking; tenant isolation; optional fully self-hosted model deployment. |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via `effective_period`; sidecar mode for shadow testing. |
| Over-reliance reduces human judgment | Position the system as decision support, not decision replacement; preserve rationale visibility; require human approval for rule revisions. |
| Conflicts with existing IAM / GRC tools | Position the Rule Repository as a complementary semantic layer; provide integration points rather than competing with baseline controls. |

---

## 13. Glossary

- **Rule**: a natural-language normative statement, plus structured metadata, managed as a first-class object.
- **Statement**: the canonical natural-language text of a rule.
- **Modality**: the strength of the obligation (MUST, MUST_NOT, SHOULD, MAY, INFO).
- **Scope**: the set of subjects, systems, or contexts to which a rule applies.
- **Verdict**: the result of an evaluation (ALLOW, DENY, NEEDS_CONFIRMATION).
- **Reason graph**: a structured DAG explaining which facts triggered which conditions in which rules.
- **Meta-rule**: a rule whose subject is other rules.
- **Provenance lineage**: the chain of derivation from a higher-level source (e.g., a law) down to operational rules and contract clauses.
- **Preflight / Posthoc / Sidecar**: three modes of integration corresponding to before-action, after-action, and parallel-observation enforcement.
- **LLM-as-Judge**: the architectural pattern of using a large language model to evaluate whether an action complies with a natural-language rule.

---

## 14. Open Questions

These will be resolved during early design iterations:

- What is the canonical schema for `scope`? (Free-form tags vs. structured org/role/system/region tuples.)
- How should the system handle rules that depend on external data sources (e.g., a list of approved vendors that changes daily)?
- What is the expected SLO for `preflight` evaluations? This drives model selection and caching strategy.
- Should the audit log be exposed to tenants in raw form, or only as derived reports?
- What is the multi-tenant isolation model? Single-tenant deployments first, or multi-tenant from day one?
- How are deprecated rules archived without losing the ability to re-evaluate historical events?

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes should follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect.*