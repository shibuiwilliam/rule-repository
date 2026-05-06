# Rule Repository

> A domain-agnostic platform for managing, searching, evaluating, and enforcing natural-language rules — laws, regulations, contracts, internal policies, engineering guidelines, communication standards, and documentation conventions — using LLMs and AI agents.

This document is the canonical specification for the Rule Repository project. It supersedes prior versions and incorporates the structural improvements identified in `IMPROVEMENT.md`. Every section uses an explicit implementation-status marker (`[IMPLEMENTED]`, `[PARTIAL]`, `[PLANNED]`, `[DEPRECATED]`) so readers can distinguish what exists from what is intended.

---

## 1. Project Overview

The Rule Repository is a system that stores human-authored rules in their original natural-language form and makes them operationally useful: searchable, applicable, and enforceable across the full breadth of organizational activity. Where traditional rule engines require translating human rules into a formal language (and lose nuance in the process), the Rule Repository keeps the rule as written and uses LLMs to interpret, search, and enforce them at runtime.

The system is **deliberately domain-agnostic**. The same engine evaluates code changes against engineering rules, contract drafts against procurement policy, employee timesheets against labor law, chat messages against information-handling rules, and document edits against editorial standards. Domain-specific concerns are isolated behind `EvaluationDomainAdapter` interfaces (§4.3) so the core stays uniform.

This approach is inspired by, and generalizes, the concept of **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea in three directions:

- **Wider scope of rules**: not only AI-agent guardrails, but laws, contracts, HR policies, engineering rules, communication norms, and documentation conventions.
- **Wider scope of consumers**: human users, business systems, IDEs, CI pipelines, AI agents, and webhook-driven gateways.
- **Wider scope of time**: pre-flight checks, post-hoc audits, continuous compliance monitoring, and **temporal re-evaluation** ("what was compliant on 2025-04-01 with the rules then in force?").

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository fills a gap that no existing category of software addresses cleanly:

- **Document management systems** store the source documents but do not understand the rules inside them.
- **Rule engines** (Drools, DMN, OPA) require formal encoding and lose the original semantics.
- **GRC platforms** track compliance status but do not enforce rules at the point of action.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.
- **Code review automation** (linters, custom checkers) handles engineering rules but cannot evaluate contract drafts, HR events, or chat messages against the same governance fabric.

The Rule Repository treats **rules themselves as first-class, versioned, governed, multi-tenant assets**, decoupled from any single consumer and reusable across the entire organization.

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Store rules in natural language, with full traceability to their source documents.
- Support multiple evaluation domains uniformly: code, business events, document changes, communication, regulatory text.
- Provide rich search (full-text, vector, category, hybrid, intent-based, temporal, citation, subject-aware, conflict-aware) over rule corpora.
- Enable runtime evaluation: "given this context and intent, is this action compliant with the relevant rules?"
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Support temporal evaluation: re-evaluate historical events using the rule version that was effective at the event time.
- Detect conflicts, redundancies, and dead rules across the corpus continuously, not on demand.
- Make rule provenance, rationale, and revision history first-class — including derivation chains from upstream regulations.
- Provide multi-tenant isolation suitable for production use.
- Provide ergonomic SDKs and a unified CLI so business systems and AI agents can integrate easily.
- Treat the system itself as a meta-rule subject: changes to the system follow the same governance flow as changes to user rules.

### 3.2 Non-Goals

- Replacing IAM, RBAC, ABAC, or network-layer access control. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel or compliance officers. The system surfaces issues; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts on behalf of users.
- Producing deterministic verdicts. Verdicts are LLM-as-Judge outputs and carry uncertainty; the system is designed to make that uncertainty visible and bounded, not to eliminate it.

---

## 4. Architecture

### 4.1 Trust and Data Boundaries

- The server is the only component that holds the canonical rule corpus.
- Each tenant's data is logically isolated at the database, search, and graph layers (§9).
- Clients receive only the rules and judgments they are authorized to see.
- All evaluation calls produce immutable, hash-chained audit records on the server side.
- LLM calls receive PII-tokenized inputs by default; sensitivity-restricted rules use a different provider (self-hosted by default).

### 4.2 Top-Level Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Rule Management Server                               │
│                                                                                │
│  Domain Adapters     Search (8)       Evaluation Engine     Intelligence     │
│  ─ code              FT/Vec/Hybrid    Context Assembler     Health Scoring    │
│  ─ business_event    Category         Rule Selector         Effectiveness     │
│  ─ document_diff     Document         Batch Evaluator       Drift Monitor     │
│  ─ communication     By-source        Verdict Aggregator    Cost Ledger       │
│  ─ documentation     Temporal         Consensus (CRITICAL)  Weekly Digest     │
│                      Citation         Idempotency Cache                       │
│                      Subject-aware                                            │
│                      Conflict-aware                                           │
│                                                                                │
│  Discovery           Federation       Snapshots             Marketplace      │
│  CLAUDE.md /         Org→Team→        Versioned             Internal pkg      │
│  linter / code /     Project          Environments          publish/sub       │
│  patterns +          Override         Rollback              Conflict detect   │
│  Confluence /        Distinct from    Bulk Impact                              │
│  Notion / regulatory Provenance       Preview                                  │
│  feeds               graph                                                     │
│                                                                                │
│  Proposals           Agent            Provenance Lineage    Conflict Scanner  │
│  Multi-approver      Governance       Law→Policy→Rule       Continuous         │
│  workflow            Trust levels     Chain (Why API)       (daily)            │
│  Voting              Personalized                                              │
│  Comments            rules                                                     │
│                                                                                │
│  Counterexample      Polyglot         Rule Tutor            Playground         │
│  Generator           Rules            Conversational        Sandbox            │
│  Per-rule            EN/JA pairs      explainer             Test cases         │
│  test cases          Equivalence                            Test runner        │
│                      verifier                                                  │
│                                                                                │
│  ┌─────────────┐ ┌──────────────┐ ┌───────┐ ┌──────────┐ ┌──────────────┐    │
│  │ PostgreSQL  │ │Elasticsearch │ │ Neo4j │ │  Redis   │ │  Audit Log   │    │
│  │ (truth)     │ │ (search)     │ │(graph)│ │  (jobs)  │ │ (chained)    │    │
│  └─────────────┘ └──────────────┘ └───────┘ └──────────┘ └──────────────┘    │
│                                                                                │
│   REST API │ Intent API │ Evaluate API │ Gateway API │ MCP │ Why API          │
└────────────┼────────────┼──────────────┼─────────────┼──────┼──────────────────┘
             │            │              │             │      │
   ┌─────────┼────────────┼──────────────┼─────────────┼──────┼───────────────┐
   │         │            │              │             │      │               │
┌──▼─────┐┌──▼─────┐ ┌────▼─────┐ ┌─────▼────┐ ┌──────▼──┐ ┌─▼────────┐ ┌───▼───┐
│ Rule   ││Agentic │ │   MCP    │ │   CLI    │ │  GitHub │ │ Gateway  │ │arq-   │
│ Client ││ Client │ │  Server  │ │ rulerepo │ │   App   │ │(webhooks)│ │worker │
│  SDK   ││  SDK   │ │(agents)  │ │(unified) │ │ (PR rev)│ │          │ │(cron) │
└────────┘└────────┘ └──────────┘ └──────────┘ └─────────┘ └──────────┘ └───────┘
    │         │           │            │            │           │           │
    ▼         ▼           ▼            ▼            ▼           ▼           ▼
 Business  HR /        Claude Code   CI / IDE /   GitHub      Slack /     Daily /
 systems   contract    + any MCP     dev hooks    PRs         Teams /     hourly
           systems     agent                                  Email       jobs
```

### 4.3 Evaluation Domain Adapters [IMPLEMENTED]

The evaluation pipeline is structured around **domain adapters**. Each adapter knows how to:

1. Parse a domain-specific input into a uniform `EvaluationContext`.
2. Resolve scopes from domain-specific signals (file paths for code, contract type for documents, channel sensitivity for communication, employee role for business events).
3. Provide domain-specific prompt fragments to the LLM judge.

The orchestrator (`services/evaluation/service.py`) is domain-agnostic. The request specifies a `domain` discriminator; the orchestrator dispatches to the matching adapter.

Adapters:

- `code` — software diffs, file changes, language-aware scope. **[IMPLEMENTED]** (`EvaluationDomainAdapter` Protocol defined in `adapters/base.py`; `CodeAdapter` in `adapters/code/`; existing flat evaluation logic remains for backwards compatibility).
- `business_event` — structured facts about HR, finance, procurement, or other business actions. **[IMPLEMENTED]**
- `document_diff` — clause-level diffs of contracts, policies, regulations. **[IMPLEMENTED]**
- `communication` — chat messages, emails, comments, PR review threads. **[IMPLEMENTED]**
- `documentation` — markdown / reStructuredText / asciidoc edits, glossary alignment, link validity. **[IMPLEMENTED]**

Each adapter shares the same downstream pipeline: `RuleSelector → BatchEvaluator → VerdictAggregator → AuditLog`.

### 4.4 Persistence Layout

| Store | Purpose | Source of truth? |
|---|---|---|
| PostgreSQL | Rules, revisions, evaluations, audit log, governance, agent profiles, snapshots, proposals, packages | Yes — all other stores are derived |
| Elasticsearch | Indexed rules and documents for multi-modal search | No |
| Neo4j | Rule relationship graph (provenance, override, conflict, dependency) and federation hierarchy | No (derived from Postgres `rule_relationships` and `federation_membership` tables) |
| Redis | Job queue (arq), idempotency cache, evaluation cache | No (ephemeral) |
| Object storage (S3-compatible) | Source documents (PDFs, large markdown), archived evaluations, audit-log WORM tier | Yes for source documents; derived for archives |

If derived stores disagree with Postgres, Postgres wins. Reconciler scripts rebuild derived stores from Postgres.

---

## 5. Domain Model

### 5.1 The `Rule` Entity [IMPLEMENTED, EXTENSIONS PLANNED]

A rule is the central first-class object. It is **not** a regex or a code expression; it is a structured envelope around a natural-language statement.

| Field | Description | Status |
|---|---|---|
| `id` | Stable identifier | IMPLEMENTED |
| `tenant_id` | Tenant ownership for multi-tenant isolation | IMPLEMENTED |
| `statement` | The rule text in natural language (the canonical form) | IMPLEMENTED |
| `source_refs` | Pointers to the source document, section, and offset | IMPLEMENTED |
| `scope` | Tag-style scope (e.g. `engineering/python`, `hr/attendance`) | IMPLEMENTED |
| `applicable_to` | Structured `SubjectFilter` list (employment type, role, location, contract type, etc.) | IMPLEMENTED |
| `modality` | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) | IMPLEMENTED |
| `effective_period` | `valid_from` / `valid_until` | IMPLEMENTED |
| `preconditions` | Facts required to evaluate the rule | IMPLEMENTED |
| `exceptions` | References to other rules or carve-outs | IMPLEMENTED |
| `rationale` | Why the rule exists (purpose, intent) | IMPLEMENTED |
| `context` | Surrounding source-document text and section hierarchy | IMPLEMENTED |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL | IMPLEMENTED |
| `regulatory_severity` | None / Guidance / Fine / Criminal (independent of operational severity) | IMPLEMENTED |
| `sensitivity` | PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED (drives LLM provider routing and log retention) | IMPLEMENTED |
| `tags` | Free-form taxonomic labels | IMPLEMENTED |
| `governance` | Owner, approvers, revision history, review cycle | IMPLEMENTED |
| `maturity_level` | EXPERIMENTAL / STABLE / PROVEN | IMPLEMENTED |
| `embedding` | Vector representation (derived) | IMPLEMENTED |
| `equivalence_id` | Group identifier for polyglot equivalent rules | IMPLEMENTED |
| `following_examples` | Compliant examples (for testing and prompt grounding) | IMPLEMENTED |
| `violation_examples` | Non-compliant examples | IMPLEMENTED |

The `statement` is the **source of truth**. Structured fields exist for indexing, filtering, and prioritization — never to override the meaning of the statement.

### 5.2 Subject Scope [IMPLEMENTED]

For non-code domains, scopes need structured matching against subjects of business actions:

```python
@dataclass(frozen=True)
class Subject:
    organization_unit: str | None = None     # "engineering/backend"
    role: str | None = None                  # "manager", "individual_contributor"
    employment_type: str | None = None       # "regular", "contract", "intern"
    location: str | None = None              # ISO country/region: "JP-Tokyo"
    seniority_level: int | None = None
    department: str | None = None
```

A `SubjectFilter` is a partial Subject; all non-None fields must match. Rules carry `applicable_to: list[SubjectFilter]`. The `business_event` adapter constructs a `Subject` from the incoming event and includes only rules whose `applicable_to` matches.

### 5.3 Contract Scope [IMPLEMENTED]

```python
@dataclass(frozen=True)
class ContractScope:
    contract_type: ContractType | None = None  # NDA / MSA / SOW / DPA / LEASE / SALES
    governing_law: str | None = None
    counterparty_country: str | None = None
    party_role: PartyRole | None = None        # disclosing / receiving / both
    language: str | None = None                # BCP-47
    transaction_volume_jpy: int | None = None
```

The `document_diff` adapter classifies the contract on ingestion and uses `ContractScope` for rule selection.

### 5.4 Rule Relationships [IMPLEMENTED]

Rules form a graph, not a flat list. Modeling these relationships explicitly is what turns the repository from a list into a **provenance and impact graph**.

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision that replaces a prior version |

`derives_from` carries an edge property `basis_type` (`law` / `regulation` / `internal_policy` / `department_rule` / `contract_template`) so the provenance graph can be queried separately from the federation graph (§5.6).

### 5.5 Meta-Rules [IMPLEMENTED for storage; PLANNED for active enforcement]

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy", "Every new HIGH-severity rule must have at least one counterexample"). Meta-rules are evaluated by the same engine but are scoped to govern the rule corpus itself. They are the basis for the system's self-governing properties (§7.4).

### 5.6 Federation Hierarchy [IMPLEMENTED]

`organization → team → project` hierarchical rule composition. Rules at higher levels apply to all descendants; descendants can override.

The federation graph is **distinct from the provenance graph** in Neo4j: federation edges are `(:Federation)-[:CONTAINS]->(:Rule)`, provenance edges are `(:Rule)-[:DERIVES_FROM {basis_type: ...}]->(:Rule)`. Mixing them was a design error in earlier iterations and is now explicitly prevented.

### 5.7 Verdict and Reason Graph [IMPLEMENTED]

A verdict is one of `ALLOW`, `DENY`, `NEEDS_CONFIRMATION`. Each per-rule verdict carries:

- `confidence` (LLM-reported)
- `reasoning` (natural-language explanation)
- `remediations` (structured `Remediation` list with `auto_applicable` flag)
- `provider` and `provider_fallback` (which LLM produced the verdict)

The **reason graph** is the structured DAG explaining which facts in the input triggered which conditions in which rules, including conflict-resolution decisions when overrides applied.

---

## 6. Components

### 6.1 Rule Management Server [IMPLEMENTED]

The server is the system of record for all rules.

**Capabilities**:

- **Rule CRUD** with revision history and effective-date semantics.
- **Extraction pipeline**: documents → candidate rules through structural parsing → normative-sentence detection → coreference resolution → metadata inference → relationship suggestion → human review.
- **Search APIs** (8 modes — see §6.7).
- **Intent API**: classifies natural-language queries (`lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`, `propose_rule`) and routes to the appropriate handler.
- **Evaluation engine** with domain adapters (§4.3, §6.4).
- **Audit log**: append-only, hash-chained, with chain-verification tooling and `/api/v1/audit` inspection API.
- **Governance**: role-based access (Owner / Approver / Reader) per rule category, revision approval workflow, effective-date scheduling, annual review cron.

### 6.2 Rule Client (Python SDK) [IMPLEMENTED]

A thin, ergonomic wrapper over the server APIs.

```python
from rulerepo import RuleClient

async with RuleClient(server_url="...", api_key="...") as client:
    rules = await client.search.hybrid(
        "overtime monthly limit",
        scope="hr/attendance",
    )
    result = await client.intent.ask(
        "What are the rules for refunding orders over $500?",
    )
    rule = await client.rules.get("rule_abc123")
    await client.rules.update(
        rule.id,
        statement="...",
        revision_note="...",
    )
```

### 6.3 Agentic Rule Client (Python SDK) [IMPLEMENTED]

A higher-level client that wraps `RuleClient` and adds AI-agent capabilities for systems that need to **enforce** rules.

**Added capabilities**:

- Automatic context gathering from surrounding systems.
- Two-stage evaluation: metadata pre-filter, then high-quality LLM judge.
- Result caching with hash-keyed invalidation.
- Reason graphs returned as structured DAGs.
- Repair suggestions: minimal compliant modification.
- Three integration modes: `preflight` (block), `posthoc` (audit), `sidecar` (observe).

```python
from rulerepo.agentic import AgenticRuleClient

async with AgenticRuleClient(server_url="...", scope="hr/attendance") as client:
    result = await client.evaluate(
        domain="business_event",
        context={
            "event_type": "register_overtime",
            "employee_id": "E001",
            "month": "2025-04",
            "hours": 50,
        },
        intent="register",
        mode="preflight",
    )

    if result.verdict == "DENY":
        print(result.violations)
        print(result.reason_graph)
        print(result.suggested_fix)
```

### 6.4 Domain-Aware Evaluation Engine [IMPLEMENTED]

The evaluation engine accepts inputs through domain adapters (§4.3) and runs them through a uniform pipeline:

**Pipeline**: Domain Adapter Parse → Context Assembly → Rule Selection → LLM-as-Judge (Batch) → Conflict Aggregation → Verdict Aggregation → Persistence → Audit.

- **Context Assembler**: normalizes adapter outputs into `EvaluationContext`.
- **Rule Selector**: narrows the corpus to ~5–20 relevant rules via scope/severity/modality/tag filtering, plus semantic ranking and per-agent boosts (rules an agent has historically violated rank higher).
- **Batch Evaluator**: sends all selected rules to Gemini in a single call (5–20× fewer API calls); falls back to per-rule if the batch fails or exceeds the token budget.
- **Consensus** [IMPLEMENTED]: for `severity=CRITICAL` rules with `DENY` verdict, a second independent call confirms; mismatches return `NEEDS_CONFIRMATION`.
- **Verdict Aggregator**: combines per-rule verdicts (any `DENY` → overall `DENY` unless overridden by a more specific rule via Neo4j override resolution).
- **Persistence**: one row per rule per evaluation in the `evaluations` table for analytics; one row in the audit log per overall evaluation for compliance.
- **Idempotency** [IMPLEMENTED]: `Idempotency-Key` header deduplicates retries within 24 hours.

### 6.5 Agent Context Delivery (MCP) [IMPLEMENTED]

Exposes the Rule Repository to AI coding agents via the Model Context Protocol. **Active context delivery** — rules reach the agent at the right moment without being asked.

- **MCP Server**: FastMCP with stdio (Claude Code) and streamable-http (remote agents).
- **Tools**: `search_rules`, `evaluate_compliance`, `explain_rule`, `find_conflicts`, `get_rules_for_context`, `register_agent`, `get_personalized_rules`, `challenge_verdict`, `request_exception`, `create_proposal`, `get_proposal_status`, `discover_rules`.
- **Resources**: `rule://{id}` (single rule), `ruleset://{scope}` (dynamic CLAUDE.md section).
- **Prompts**: `compliance_check`, `rule_summary`, `impact_analysis`.
- **Rule Formatter**: three output formats — `instructions` (concise MUST/SHOULD), `checklist` (PR review), `detailed` (full metadata).
- **Scope Registry**: file-glob-to-rule mapping for sub-10ms rule selection.
- **Session Context API**: `GET /api/v1/rules/context?files=...&format=instructions` for agent on-demand fetch.
- **CLAUDE.md Generator**: `rulerepo context` exports rules as static CLAUDE.md sections for environments without MCP.

### 6.6 Development Workflow Integration [IMPLEMENTED]

- **GitHub PR Review**: webhook receiver, structured review comments with per-rule verdicts and fix suggestions.
- **CI Pipeline CLI** (`rulerepo check`): runs `git diff` → evaluates → exits 0/1/2/3 (3 = LLM unavailable). Supports `--format text|json|github-actions`.
- **Agent Hooks** (`rulerepo hook`): `preflight` injects rules before edit; `posthoc` evaluates after edit; `task-start` [PLANNED] injects rules at task initiation.
- **Rule Ingestion** (`rulerepo ingest`): imports CLAUDE.md and other sources through the extraction pipeline.

### 6.7 Search [PARTIAL]

Eight search modes, all tenant-scoped and project-filtered:

| Mode | Description | Status |
|---|---|---|
| Full-text | BM25 over statements, rationale, context | IMPLEMENTED |
| Vector | Cosine similarity over embeddings | IMPLEMENTED |
| Hybrid | BM25 + kNN reranking | IMPLEMENTED |
| Category / by-source / documents | Tag, source-document, and document-content search | IMPLEMENTED |
| Context | Given facts, return applicable rules | IMPLEMENTED |
| Temporal | Rules effective at a given timestamp | IMPLEMENTED |
| Citation | Rules referencing a particular external source | IMPLEMENTED |
| Subject-aware | Rules applicable to a specific Subject / ContractScope | IMPLEMENTED |
| Conflict-aware | Rules conflicting with a given rule | IMPLEMENTED |
| Effectiveness-bounded | Rules above/below an effectiveness threshold | PLANNED |

### 6.8 Rule Intelligence and Observability [IMPLEMENTED, EXTENSIONS PLANNED]

- **Health Scorer**: per-rule score (0–100) across completeness, clarity, test coverage, freshness, activity, owner engagement.
- **Effectiveness Score**: precision (40%) + prevention rate (35%) + agent adoption (25%).
- **Evaluation Analytics**: corpus-wide and per-rule metrics (fire rate, deny rate, latency, cost, trends).
- **Recommender**: automated suggestions — retire dormant rules, clarify ambiguous, escalate persistent violations, strengthen SHOULD→MUST.
- **Verdict Drift Monitor** [IMPLEMENTED]: statistical monitor on verdict distribution per rule over rolling windows; alerts on significant deviation.
- **Cost Ledger** [IMPLEMENTED]: per-evaluation token and cost tracking; per-rule, per-project, per-tenant aggregations.
- **Weekly Digest**: compliance trends, top violations, attention-needed, declining rules, sent via webhook (Slack, email).

### 6.9 Rule Enforcement Gateway [IMPLEMENTED]

Event-driven, zero-code rule enforcement via webhooks. Sources include GitHub, Slack, Teams, Email, and generic webhooks. Each source has a normalizer that produces a uniform event shape consumed by the policy engine, which matches events to enforcement policies and triggers evaluation.

### 6.10 Automatic Rule Discovery [IMPLEMENTED, EXTENSIONS PLANNED]

Bootstraps rules from existing artifacts.

**Built-in source analyzers**:

- CLAUDE.md parser
- Linter config parser (ruff, eslint, tsconfig, prettier)
- Code pattern analyzer (frequency-based pattern mining)
- GitHub URL importer (one-click)

**External source connectors** [PARTIAL]:

- Confluence, Notion — **[IMPLEMENTED]**
- e-Gov (Japan), EUR-Lex (EU) — **[IMPLEMENTED]**
- Google Drive, SharePoint, DocuSign — **[PLANNED]**
- Federal Register (US) — **[PLANNED]**

All candidates pass through a human-review queue. Bulk approval available for confidence > 0.9.

### 6.11 Agent Correction Feedback Loop [IMPLEMENTED]

Captures human corrections of AI-generated code/content and converts them into rule improvements: more agent usage → more corrections → better rules → fewer corrections.

- **Correction Capture**: PR-based (passive) and agent-hook-based (active).
- **Correction Analyzer**: classifies as `new_rule`, `improve_existing`, or `adjust_scope`.
- **Auto-Drafter**: clusters similar corrections (cosine similarity > 0.8, ≥3 corrections, avg confidence > 0.8); Gemini drafts a structured rule proposal; approval one-click; new rule starts in `experimental` (shadow mode).

### 6.12 Cross-Project Rule Federation [IMPLEMENTED]

Hierarchical rule composition: organization → team → project. Rules at higher levels apply to all descendants; descendants can override individual rules.

The Federation Resolver walks the ancestor chain and applies overrides. The unified rule set feeds into the rule selector transparently.

**Interaction with Snapshots** [PLANNED documentation, current behavior to be specified]: snapshot capture freezes the federation resolution at creation time. Subsequent parent-rule changes do not retroactively alter deployed snapshots; instead, an alert flags the stale snapshot and a Proposal can be opened to re-snapshot.

### 6.13 Rule Playground & Testing Framework [IMPLEMENTED]

- **Playground**: sandbox evaluation of draft rules without persistence.
- **Per-Rule Test Cases**: manual, historical, or Gemini-generated.
- **Test Runner**: executes test suite per rule, reports pass/fail.
- **Counterexample Generator** [IMPLEMENTED]: on rule create / update, Gemini generates one minimal compliant and one minimal violating example, persisted as test cases.
- **Dependency-Aware Testing** [PLANNED]: editing rule X enqueues tests for X and for rules in `depends_on(X) ∪ overridden_by(X) ∪ conflicts_with(X)`.

### 6.14 Proactive Alert System [IMPLEMENTED]

Background workers generate alerts during scheduled analysis.

**Alert types**: dormant_rule, high_deny_rate, health_decline, conflict_detected, effectiveness_decline, regulatory_change_detected [PLANNED], stale_snapshot [PLANNED], verdict_drift [IMPLEMENTED].

Lifecycle: active → acknowledged → resolved. Critical alerts dispatch via webhook.

### 6.15 Rule Set Snapshots & Environment Deployment [IMPLEMENTED]

Versioned snapshots of the rule corpus with environment-based deployment, rollback, and impact simulation.

**Bulk Impact Preview** [IMPLEMENTED]: simulate multiple simultaneous rule changes (federation overhaul, multi-rule proposals).

### 6.16 Collaborative Governance — Proposals [IMPLEMENTED]

Rule change proposals (create / amend / retire / merge / split / override) with:

- Multi-approver voting
- Threaded comments with inline suggestions
- Automated conflict analysis
- Impact preview before enactment
- Notification routing to affected scope owners

### 6.17 Autonomous Agent Governance [IMPLEMENTED, AUTOMATIC PROMOTION GATED]

Each AI agent has a profile with trust levels (`untrusted` → `limited` → `standard` → `elevated` → `autonomous`). The system delivers personalized rules — suppressing rules the agent has mastered, weighting rules the agent has historically violated.

**Auto-promotion of trust** is gated behind `AGENT_TRUST_PROMOTION_ENABLED=false` by default. Until adversarial scenarios are evaluated, promotion requires human approval.

### 6.18 Rule Marketplace [DEPRECATED — Removed]

~~Teams within a tenant publish versioned rule packages and subscribe to packages from other teams. Composition conflict detection catches clashes when multiple packages combine.~~

**Marketplace was removed** (commit `8fc7e6c`). All models, services, routers, and schemas have been deleted. Re-introduction is deferred until package signing, license metadata, quality certification, and feature interaction semantics (Snapshot × Marketplace, Marketplace × Maturity) are designed.

### 6.19 Continuous Conflict Detector [IMPLEMENTED]

Daily worker scans the corpus for `conflicts_with` candidates:

1. Pairs are pre-filtered by embedding similarity > 0.7 OR scope overlap.
2. Each candidate pair is evaluated by Gemini ("Could a single context simultaneously violate one rule and be required by the other? Cite a minimal example.").
3. Detected conflicts add a `CONFLICTS_WITH` edge to Neo4j and auto-create a `resolve_conflict` Proposal assigned to both rules' owners.

### 6.20 Provenance Lineage and Why API [IMPLEMENTED]

Tracks the chain Law → Cabinet Order → Ministerial Order → Internal Policy → Department Rule → Contract Clause. Distinct from the federation graph.

`GET /api/v1/rules/{id}/why?depth=N` returns multi-level rationale traversing `rationale`, the `derives_from` chain, related external citations, and revision history.

**Regulatory feed integration** complements provenance: when an upstream regulation changes, all rules with `derives_from` pointing to it receive a `regulatory_change_detected` alert and an auto-drafted review proposal.

### 6.21 Polyglot Rules [IMPLEMENTED]

Maintains rule pairs (e.g., EN/JA, EN/ZH) with a shared `equivalence_id`. A daily worker re-validates semantic equivalence via Gemini after either side changes; divergence triggers a `polyglot_drift` alert.

### 6.22 Rule Tutor [IMPLEMENTED]

Conversational page (`/tutor`) backed by the Intent API and the MCP `explain_rule` tool. Supports onboarding new employees and contributors by walking them through applicable rules in dialogue, with examples from `following_examples` and `violation_examples`.

---

## 7. Cross-Cutting Concerns

### 7.1 Multi-Tenancy [IMPLEMENTED]

All major models gain a `tenant_id` foreign key. Postgres Row-Level Security enforces isolation at the database layer. Elasticsearch uses `routing=tenant_{id}` per shard. Neo4j uses one database per tenant (Neo4j 5 multi-database). API keys map to `(tenant_id, agent_id, role)`; authentication middleware sets the request-scoped tenant context.

### 7.2 PII and Sensitivity [IMPLEMENTED]

A PII tokenizer replaces detected PII (emails, phone numbers, government IDs, named entities) with stable placeholders (`[PERSON_1]`, `[EMAIL_1]`) before transmission to LLMs. The reverse-mapping dict is encrypted at rest.

The `sensitivity` field on rules drives:

- LLM provider routing: `RESTRICTED` rules use only allowed providers (self-hosted by default).
- Log retention: `RESTRICTED` rules' evaluation logs purge after 90 days.
- Display masking on the frontend.

### 7.3 Observability [IMPLEMENTED]

OpenTelemetry instrumentation on FastAPI, SQLAlchemy, Elasticsearch, Neo4j, Gemini, and the worker queue. Spans cover the full evaluation pipeline. Metrics exposed via Prometheus on `/metrics`. Cost ledger persisted on `EvaluationRecordModel`.

### 7.4 Self-Governance via Meta-Rules [PLANNED]

The Rule Repository governs itself with meta-rules registered in its own corpus:

- "Every LLM call producing a verdict must log model ID and prompt version."
- "Every new HIGH-severity rule must have at least one counterexample test case."
- "Every CRITICAL rule must use consensus voting."
- "Every rule package published to the marketplace must be signed."

Changes to the system follow the Proposal flow; deployments use Snapshots; effectiveness is tracked. This is the most credible dogfooding path imaginable and is required for the system to be considered production-mature.

### 7.5 LLM Provider Abstraction [IMPLEMENTED]

The `LLMProvider` Protocol is defined in `adapters/llm/base.py`. Implementations exist for Gemini (`adapters/gemini/`), Anthropic (`adapters/llm/anthropic.py`), OpenAI (`adapters/llm/openai.py`), and self-hosted vLLM/Ollama (`adapters/llm/local.py`). Routing in `core/llm.py` selects provider based on `(rule.sensitivity, rule.severity, tenant.allowed_providers)`.

### 7.6 LLM Failure Handling [PLANNED]

Circuit breaker on Gemini calls. When the breaker is open:

- `evaluate` returns `Verdict.UNKNOWN_LLM_DOWN`.
- CI hooks exit with code 3 (distinct from 0/1/2): "human review required, system unavailable".
- Multi-provider fallback when configured: the next-priority provider takes over; verdicts carry `provider_fallback: true`.

### 7.7 Data Retention [PLANNED]

| Data | Retention | Storage |
|---|---|---|
| Hot evaluations | 30 days | Postgres |
| Warm evaluations | 30 days–1 year | Postgres aggregation table + S3 Parquet |
| Cold evaluations | 1 year+ | S3 Parquet only, queried via DuckDB |
| Audit log | 7 years (configurable) | Postgres + S3 WORM tier |
| Corrections | 2 years | Postgres |
| Embeddings | Regenerated every 90 days | Elasticsearch |

### 7.8 Audit Log Integrity [IMPLEMENTED]

Append-only with hash chain. `scripts/verify_audit_chain.py` walks the chain and asserts integrity; CI runs nightly. `GET /api/v1/audit` API exposes audit records to authorized users with filtering and CSV export. The `/audit` frontend page is **[PLANNED]**.

### 7.9 Idempotency [IMPLEMENTED]

`POST /api/v1/evaluate` accepts an `Idempotency-Key` header. Implementation stores `(tenant_id, idempotency_key, request_hash) → evaluation_id` in Redis with 24-hour TTL.

---

## 8. Use Cases

### 8.1 HR / Attendance Management [target domain: business_event]

The HR system registers attendance and overtime. The Rule Repository holds the work regulations. The Agentic Rule Client validates each registration in `preflight` mode and alerts on violations (monthly overtime exceeding the legal limit, missing 36-agreement filing, prohibited late-night assignments for protected categories). Subject scopes match by employment type, location, and seniority.

### 8.2 Contract Management [target domain: document_diff]

The contract management system stores contracts under negotiation. The Rule Repository holds internal procurement rules and prior contract clauses. When a counterparty draft is uploaded:

1. The clause segmenter breaks it into article/section/paragraph units.
2. The clause classifier identifies clause types (NDA, payment terms, IP, liability).
3. The clause-diff evaluator compares against internal standards.
4. The cross-contract conflict checker compares against past contracts.
5. The playbook compliance check verifies negotiation playbook adherence.

### 8.3 Software Development [target domain: code]

The Rule Repository stores engineering coding standards, documentation conventions, and review checklists. CI pipelines use `rulerepo check` to evaluate pull requests and post review comments. IDE extensions surface relevant rules via MCP. The Correction Flywheel continuously improves the rule set based on human edits.

### 8.4 Regulatory Compliance [target domain: business_event + document_diff]

A financial institution stores regulations in the repository, with derived internal procedures linked via `derives_from`. Regulatory feed connectors monitor upstream amendments. When a regulation changes, the Provenance Lineage and Bulk Impact Simulator together identify all downstream procedures that need review and auto-draft revision proposals.

### 8.5 AI-Assisted Development [cross-domain]

A team uses Claude Code with the Rule Repository. Rule Discovery bootstraps 50 rules in an afternoon. Agents receive applicable rules via MCP and write compliant content from the start. Human corrections feed the flywheel. Federation shares organization-wide standards across all team repositories with project-specific overrides.

### 8.6 Internal Communication Governance [target domain: communication]

Slack/Teams/Email gateways forward messages through the communication adapter. Rules detect:

- API keys or credentials pasted in chat.
- Confidential information shared with external channels.
- NDA-bound topics in non-NDA-compliant audiences.
- Soft warnings on harassment-leaning language.
- Required-disclosure prompts in regulated channels.

### 8.7 Documentation Quality [target domain: documentation]

Pull-request changes to documentation pass through the documentation adapter. Rules check:

- Required sections, frontmatter, naming conventions.
- Glossary alignment (organizational terminology).
- Cross-document consistency (API spec vs. implementation vs. user-facing docs).
- Stale-document detection.

### 8.8 Self-Improving Governance [meta-domain]

This Rule Repository itself uses its own Proposal flow, Snapshots, and Effectiveness scoring to govern its own evolution. The improvements proposed in this document, once accepted, are registered as meta-rules and tracked through the same machinery as user rules.

---

## 9. Technical Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM (default) | Gemini 3 Flash and Gemini 3.1 Pro via `google-genai` |
| LLM (planned providers) | Anthropic Claude, OpenAI GPT, vLLM/Ollama (self-hosted) |
| Document parsing/OCR | Gemini Files API + document understanding |
| Relational DB | PostgreSQL 17 with Row-Level Security |
| Search | Elasticsearch 8.17 with dense_vector + BM25 |
| Graph DB | Neo4j 5 (multi-database for multi-tenancy) |
| Job queue | arq + Redis 7 |
| Object storage | S3-compatible (MinIO for local, S3/GCS for production) |
| Tracing/metrics | OpenTelemetry → OTLP collector → Jaeger + Prometheus |
| MCP | FastMCP |
| Auth | OIDC / OAuth2; API keys for SDKs |
| Quality | ruff, mypy, ESLint, Prettier, pre-commit, mutmut, Hypothesis |

The architecture intentionally avoids hard-coding a single LLM provider. The `LLMProvider` Protocol accepts any implementation that performs structured judgment.

---

## 10. Roadmap

The project has reached the end of an aggressive expansion phase. The next 90 days are organized for stabilization, then deliberate domain expansion.

### Phase 1 — Foundation (Storage & Search) [COMPLETE]

Rule data model, document ingestion, multi-modal search, REST/Intent APIs, Python SDK, basic governance.

### Phase 2 — Enforcement [COMPLETE]

Code-Aware Evaluation Engine, Agent Context Delivery via MCP, GitHub PR integration, CI CLI, Agent Hooks, Gateway, Intelligence.

### Phase 3 — Discovery & Learning [COMPLETE]

Automatic Rule Discovery, Correction Feedback Loop with auto-drafter, Cross-Project Federation.

### Phase 3.5 — Adoption Acceleration [IMPLEMENTED]

GitHub repository import, automatic PR correction capture, rule impact preview, conflict resolution transparency, cache analytics.

### Phase 4 — Testing & Deployment Safety [COMPLETE]

Playground, per-rule test cases, proactive alerts, snapshots with rollback and impact simulation.

### Phase 5 — Self-Improving Governance [LARGELY IMPLEMENTED]

Batched evaluation, evaluation persistence, outcome-oriented dashboard, correction-to-rule flywheel, active rule injection, zero-config bootstrapping (partial), structured remediation, maturity model, advanced intelligence (partial).

### Phase 6 — Platform & Ecosystem [PARTIALLY IMPLEMENTED]

Collaborative governance proposals (implemented), agent governance with trust levels (implemented, auto-promotion gated), marketplace (removed — see §6.18).

### Phase 7 — Stabilization and Integration Audit [TIER 0, WEEKS 1–2]

The current immediate priority. No new feature work.

- Feature freeze for net-new functionality.
- `scripts/spec_audit.py` runs and publishes status to `development/spec_implementation_audit.md`.
- Feature interaction matrix documented (Federation × Snapshot, Snapshot × Marketplace, Proposal × Federation, Maturity × Snapshot, etc.).
- Integration tests for the first 10 high-impact interactions.
- Status discipline applied throughout PROJECT.md and CLAUDE.md.

**Value delivered**: "We trust what we have."

### Phase 8 — Reliability and Foundation [TIER 1, WEEKS 3–6]

- `EvaluationDomainAdapter` interface; relocate code-evaluation logic into `adapters/code/`.
- Continuous Conflict Detector worker.
- Idempotency-Key handling.
- Consensus voting for CRITICAL rules.
- Audit-log inspection API and `/audit` frontend page.
- Audit-chain verification CI nightly.
- PII Tokenizer, Sensitivity tag, encrypted evaluation context.
- Unified `rulerepo` CLI replacing fragmented entry points.

**Value delivered**: "What we have is verifiable, sealed, and trustworthy."

### Phase 9 — Domain Expansion [TIER 2, WEEKS 7–10]

- `business_event` adapter for HR / finance / procurement.
- `document_diff` adapter for contracts (clause segmenter, classifier, reference resolver).
- `documentation` adapter and `documentation-standards.yaml` template.
- `Subject` and `ContractScope` value objects.
- Counterexample Generator on rule create/update.
- Why API and Provenance Lineage (separate from federation graph in Neo4j).
- Confluence and Notion source connectors.

**Value delivered**: "We support the full domain matrix, not just code."

### Phase 10 — Operations and Differentiation [TIER 3, WEEKS 11–14]

- Multi-tenancy with Postgres RLS, Elasticsearch routing, Neo4j multi-database.
- OpenTelemetry instrumentation and Prometheus metrics endpoint.
- LLM Provider abstraction with Anthropic and OpenAI adapters.
- Cost Ledger and dashboard panel.
- Eval harness with golden sets, nightly verdict-accuracy gate.
- Frontend persona-based reorganization.
- Data retention policies and tiered storage worker.
- E2E Playwright suite (3 personas × 1 happy path).

**Value delivered**: "We are production-grade."

### Phase 11 — Cross-Domain and Regulatory [TIER 4, WEEKS 15+]

- `communication` adapter and Slack/Teams/Email gateways.
- Regulatory feed connectors (e-Gov, EUR-Lex, Federal Register).
- Polyglot Rules with continuous equivalence verification.
- Rule Tutor frontend.
- Verdict Drift monitor.
- Bulk Impact Preview for multi-rule proposals.
- Self-governance meta-rules registered and enforced.

**Value delivered**: "We govern any rule, in any language, across any system, including ourselves."

---

## 11. Success Metrics

- **Coverage**: percentage of rules in target source documents successfully extracted and registered.
- **Latency**: p50 / p95 / p99 evaluation latency in `preflight` mode (target: p95 < 2s for code domain, < 5s for document_diff).
- **Accuracy**: human-rated correctness of verdicts on a held-out test set; precision and recall on conflict detection (target: > 90%).
- **Adoption**: number of integrated systems and active rules; volume of evaluation requests per day.
- **Governance health**: percentage of rules with complete metadata, current rationale, and active owners.
- **Time-to-comply on regulatory change**: median time between an upstream-law amendment and the corresponding internal rule revision being approved (target: < 30 days).
- **Shadow-to-enforcement rate**: > 70% of experimental rules reach stable within 60 days.
- **Auto-fix rate**: > 40% of SHOULD violations auto-fixed via structured remediations.
- **Flywheel throughput**: > 5 rules/month auto-drafted from correction clusters; correction rate decreases > 30% after flywheel rule activation.
- **Time-to-rule**: < 1 week from correction pattern detection to approved rule.
- **Tenant isolation correctness** [new]: zero cross-tenant data leakage in security audits.
- **LLM cost per evaluation** [new]: tracked monthly; target reduction trajectory documented.
- **Audit chain integrity** [new]: 100% chain verification pass rate.
- **Eval harness pass rate** [new]: > 90% on the golden set, no more than 5pp regression PR-over-PR.

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Always log full evaluation context; human review on high-severity denials; consensus voting for CRITICAL; refinement feedback loop; verdict drift monitor. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator; refinement loop; per-rule unit tests; mutation testing on test cases. |
| LLM costs scale poorly with rule corpus size | Two-stage evaluation (metadata pre-filter, then LLM); aggressive caching; tiered model selection; batched evaluation; cost ledger with alerts. |
| Sensitive data leaks through evaluation context | PII tokenization; at-rest encryption of context column; tenant isolation; sensitivity-aware provider routing; self-hosted LLM for RESTRICTED. |
| Rule changes break dependent systems | Change Impact Simulator; bulk impact preview; staged rollouts via `effective_period`; sidecar mode for shadow testing; snapshot rollback. |
| Over-reliance reduces human judgment | Position as decision support, not replacement; preserve rationale visibility; require human approval for rule revisions; trust-level gating on agent autonomy. |
| Conflicts with existing IAM/GRC tools | Position as complementary semantic layer; integration points rather than competing controls. |
| Feature interactions produce inconsistent verdicts | Feature interaction matrix tests; explicit semantics documentation; freeze period before next major addition. |
| Spec drifts from implementation | `scripts/spec_audit.py` weekly CI; status markers throughout PROJECT.md and CLAUDE.md; section-renumbering audit. |
| Multi-tenancy bug leaks cross-tenant data | Postgres RLS as defense in depth; independent security audit; integration tests for tenant isolation. |
| LLM provider outage disrupts service | Circuit breaker; multi-provider fallback; degraded-mode UX; CI exit code 3. |
| Audit log tampering | Hash chaining; nightly verification; WORM tier for old records; chain-bridge across archival boundary. |
| Auto-promotion of agent trust enables abuse | `AGENT_TRUST_PROMOTION_ENABLED=false` default; human approval until adversarial scenarios are evaluated. |

---

## 13. Glossary

- **Rule**: a natural-language normative statement, plus structured metadata, managed as a first-class object.
- **Statement**: the canonical natural-language text of a rule.
- **Modality**: the strength of the obligation (MUST, MUST_NOT, SHOULD, MAY, INFO).
- **Scope**: the set of subjects, systems, or contexts to which a rule applies.
- **Subject**: a structured value object describing the actor of a business event (employment type, role, location, etc.).
- **Verdict**: the result of an evaluation (ALLOW, DENY, NEEDS_CONFIRMATION, UNKNOWN_LLM_DOWN).
- **Reason graph**: a structured DAG explaining which facts triggered which conditions in which rules.
- **Meta-rule**: a rule whose subject is other rules.
- **Provenance lineage**: the chain of derivation from a higher-level source (e.g., a law) down to operational rules and contract clauses. Distinct from federation hierarchy.
- **Federation hierarchy**: organizational composition of rules (org → team → project) with override semantics.
- **Domain Adapter**: a pluggable component that parses domain-specific input into the uniform `EvaluationContext` and resolves domain-specific scopes.
- **Preflight / Posthoc / Sidecar**: three modes of integration.
- **Maturity**: lifecycle level of a rule (EXPERIMENTAL → STABLE → PROVEN).
- **Sensitivity**: data classification of a rule (PUBLIC → INTERNAL → CONFIDENTIAL → RESTRICTED).
- **LLM-as-Judge**: the architectural pattern of using a large language model to evaluate whether an action complies with a natural-language rule.
- **Polyglot Rule**: a rule maintained in multiple languages with continuous equivalence verification.
- **Effectiveness**: a 0–100 score combining precision, prevention rate, and agent adoption.
- **Snapshot**: an immutable versioned rule set deployable to an environment with rollback support.
- **Flywheel**: the self-improving cycle of correction capture → clustering → rule auto-draft → approval → effectiveness measurement.

---

## 14. Open Questions

These remain to be resolved during ongoing design iterations:

- What is the SLO budget for `preflight` evaluations across each domain? (Drives model selection and caching strategy per domain.)
- For the `business_event` domain, how should the system handle rules that depend on slowly-changing external data (e.g., approved-vendor lists)? Should the system poll, or should consumers push updates?
- What is the integration semantics between snapshots and federation? When a parent rule changes, do child snapshots become stale or stay frozen? (The current proposal: stay frozen, alert generated.)
- What is the integration semantics between snapshots and marketplace subscriptions? When a subscribed package version updates, do active snapshots auto-update or stay frozen? (The current proposal: stay frozen, alert generated.)
- How are exception requests scoped temporally? Should an approved exception apply to past evaluations or only future ones?
- What is the policy on cross-tenant rule reuse? Should anonymized templates published to the marketplace remain marketplace-internal, or eventually move to a public repository?
- How are corrections from low-trust agents weighted in the flywheel? (Risk: a malfunctioning agent's pattern of "corrections" could pollute the rule corpus.)
- For polyglot rules, what is the resolution policy when one language's version is updated and the other has not yet been? (Default: shadow the updated side until both are aligned.)

---

## 15. Project Self-Governance

This project commits to using its own machinery to manage its own evolution.

- This document and CLAUDE.md are themselves rules in the system, registered with `scope: meta/project` and `modality: MUST` for the rules of project conduct.
- Changes to PROJECT.md or CLAUDE.md follow the Proposal flow (`POST /api/v1/proposals` with `type: amend`, target rule = the PROJECT.md or CLAUDE.md meta-rule).
- New phases are deployed as Snapshots to the `development` environment, then promoted to `production` after acceptance criteria are met.
- The Effectiveness Score for each phase tracks: did the value delivered match the value promised?
- The Spec Audit Tool keeps PROJECT.md and CLAUDE.md honest with the implementation.

This is not a stylistic flourish. A rule-management system that does not govern itself with its own rules has not earned the right to govern others' rules.

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect.*
