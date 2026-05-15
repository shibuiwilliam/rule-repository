# Rule Repository

> A software platform for managing, searching, serving, and enforcing natural-language rules — laws, contracts, internal policies, HR regulations, financial controls, sales policies, communication standards, engineering guidelines, and documentation standards — using LLMs and AI agents, across human users, business systems, and autonomous agents.

This document is the canonical specification for the Rule Repository project. It supersedes earlier revisions and represents the project's **refocused** direction toward a true Cross-Organizational Rule Platform optimized for local execution. For implementation guidance and developer conventions, see `CLAUDE.md`. For the analytical rationale behind the refocus, see `IMPROVEMENT.md`.

---

## 1. Project Overview

The **Rule Repository** is a system that stores human-authored rules in their original natural-language form and makes them operationally useful: **searchable**, **applicable**, **evaluable**, and **enforceable** across every part of an organization. Where traditional rule engines require translating human rules into a formal language (and losing nuance along the way), the Rule Repository keeps rules as written and uses LLMs and AI agents to interpret, search, enforce, and improve them at runtime — supplementing LLM-based judgment with a deterministic layer for the parts that have correct answers.

This approach generalizes the concept of **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies, which apply natural-language constraints as runtime guardrails for AI agents) in three directions:

- **Wider scope of rules**: not only AI agent guardrails, but laws, contracts, HR policies, finance controls, sales policies, communication standards, engineering guidelines, and documentation conventions.
- **Wider scope of subjects**: not only code changes, but business events, document artifacts, transactions, communications, and generic decision requests — all evaluated through the same engine.
- **Wider scope of consumers**: human users (lawyers, HR managers, finance managers, salespeople, engineers, compliance officers), business systems (HR, ERP, contract management, CRM), IDEs, CI pipelines, and AI agents.
- **Wider scope of time**: pre-flight checks, post-hoc audits, and sidecar/continuous compliance monitoring.

The Rule Repository treats **rules themselves as first-class, versioned, governed, multilingual assets**, decoupled from any single consumer or domain and reusable across the entire organization.

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository fills a gap that no current category of software addresses cleanly:

- **Document management systems** store the source documents but do not understand the rules inside them.
- **Rule engines (Drools, DMN, OPA)** require formal encoding and lose the original semantics.
- **GRC platforms** track compliance status but do not enforce rules at the point of action.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.
- **AI-coding-agent governance tools** focus on developer workflows and treat non-developer use cases as out of scope.

The Rule Repository treats **rules themselves as first-class, versioned, governed, multilingual assets**, decoupled from any single consumer or domain and reusable across the entire organization. The platform is built so that adding a new business domain (legal, HR, finance, sales, communication) requires authoring a Domain Pack — not modifying the core engine.

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Store rules in natural language, with full traceability to their source documents.
- Provide rich search (full-text, vector, category, hybrid, intent-based) over rule corpora.
- Enable runtime evaluation of **any business subject** — code changes, business events, document artifacts, transactions, communications, decision requests — against the rules that apply to it, returning a verdict with a human-readable reason and structured reason graph.
- Combine a **deterministic evaluation layer** (numeric checks, schema validations, state-machine validations, lookups) with an **LLM evaluation layer** (normative interpretation, exception evaluation, principle-level reasoning). Each rule is evaluated by the appropriate layer for its semantic type.
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Provide structured **Domain Packs** so legal, HR, finance, sales, communication, and engineering teams each get domain-specific prompts, analyzers, templates, and UI views.
- Provide **persona-aware** access — engineers, legal counsel, HR managers, finance managers, sales managers, and compliance officers each see the system framed for their work.
- Provide first-class **multilingual** support with verified equivalence between rules expressed in different languages.
- Support cross-domain **hierarchical governance** (organization → team → project) and **attribute-based access control** (domain × action × principal).
- Detect conflicts, redundancies, and dead rules across the corpus.
- Make rule provenance, rationale, and revision history first-class.
- Provide ergonomic SDKs so business systems and AI agents can integrate easily.
- Run **fully locally** via Docker Compose with no required external services beyond the LLM API.

### 3.2 Non-Goals

- Replacing IAM, RBAC, ABAC, or network-layer access control at the infrastructure level. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel or compliance officers. The system surfaces issues and proposes; humans decide.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts on behalf of users.
- Operating as a public marketplace, observability SaaS, or external connector hub in the current scope. These directions remain in the codebase under feature flags but are deferred until the cross-organizational core is solid.

---

## 4. Strategic Refocus

The Rule Repository has reached substantial implementation depth in software-engineering use cases — code-aware evaluation, GitHub PR review, CI integration, MCP integration with coding agents, and discovery of rules from `CLAUDE.md` and linter configs. This is real value. However, the project's stated vision is **cross-organizational**, not engineering-specific.

This document formalizes a **refocus** of the project to fulfill the cross-organizational vision:

1. **Generalize the core abstractions** so that code changes become one variant of evaluation subject among many, rather than the default.
2. **Introduce a Domain Pack mechanism** so each business domain contributes its own metadata, prompts, analyzers, templates, and (optionally) UI views, without modifying the core.
3. **Re-shape the frontend around personas** so each team type — engineering, legal, HR, finance, sales, compliance — sees the system framed for its work.
4. **Add a deterministic evaluation layer** alongside the LLM layer for rule kinds that have exact answers.
5. **Defer Marketplace, external observability, broad external connectors, and GitHub-App-centric flows** behind feature flags to free engineering bandwidth for the above.

The rest of this document describes the system **as it will be after this refocus is implemented**. Current code paths that contradict this specification are migration targets, not authoritative state.

---

## 5. Architecture

The system is composed of three top-level layers plus a Domain Pack mechanism:

```
                         ┌────────────────────────────────┐
                         │       Domain Packs (loaded)     │
                         │  legal | hr | finance | sales | │
                         │  communication | engineering    │
                         │  - metadata extensions          │
                         │  - extraction prompts           │
                         │  - evaluation prompts           │
                         │  - templates                    │
                         │  - analyzers                    │
                         └──────────────┬─────────────────┘
                                        │ register
┌──────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                      │
│                                                                   │
│  Universal Submissions API ────► Evaluation Service              │
│  (POST /api/v1/submissions)      ┌─────────────────────────┐    │
│  REST API                        │ Subject Dispatcher       │    │
│  Intent API                      ├─────────────────────────┤    │
│                                   │ Code Change | Business  │    │
│  ┌────────────┐  ┌────────────┐  │ Event | Document        │    │
│  │ Extraction │  │   Search   │  │ Artifact | Transaction  │    │
│  │  Pipeline  │  │  (FT/Vec/  │  │ | Communication | ...   │    │
│  │  (domain-  │  │  Cat/Hyb)  │  └────────────┬────────────┘    │
│  │  adaptive) │  │            │               │                  │
│  └────────────┘  └────────────┘  ┌────────────▼────────────┐    │
│                                   │ Deterministic Layer      │    │
│                                   │ (numeric / schema /      │    │
│                                   │  state machine / lookup) │    │
│                                   ├──────────────────────────┤    │
│                                   │ LLM Layer                │    │
│                                   │ (normative / exception / │    │
│                                   │  principle)              │    │
│                                   └────────────┬────────────┘    │
│                                                │                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────▼────────────┐    │
│  │ Discovery  │  │ Rule Store │  │ Verdict Aggregator       │    │
│  │  Engine    │  │ (PG+ES+    │  │ + Reason Graph Builder   │    │
│  │            │  │  Neo4j)    │  │                          │    │
│  └────────────┘  └────────────┘  └──────────────────────────┘    │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────┐        │
│  │ Governance │  │ Federation │  │  Context Delivery    │        │
│  │ ABAC       │  │ (Org/Team/ │  │  (MCP + Formatter +  │        │
│  │            │  │  Project)  │  │   Persona Views)     │        │
│  └────────────┘  └────────────┘  └──────────────────────┘        │
│                                                                   │
│  Intelligence (essentials) │ Proposals │ Snapshots │ Playground   │
│  Audit Log (append-only, hash-chained)                            │
└───┬──────────────────────────────────────────────────────────────┘
    │
    ┌─────────────┬──────────────┬─────────────┬───────────────┐
    │             │              │             │               │
┌───▼────┐  ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐    ┌─────▼─────┐
│  Rule  │  │ Agentic │   │   MCP     │  │   CLI   │    │ Frontend  │
│ Client │  │ Client  │   │  Server   │  │  Tools  │    │ (Persona- │
│  SDK   │  │  SDK    │   │ (agents)  │  │ (CI/    │    │  aware)   │
│        │  │         │   │           │  │  hooks) │    │           │
└────────┘  └─────────┘   └───────────┘  └─────────┘    └───────────┘
    │           │              │             │               │
    ▼           ▼              ▼             ▼               ▼
Business    HR/Contract/   AI coding     CI pipelines    Legal /
systems     Finance/Sales  agents +      (optional)      HR / Finance /
            event sources  any MCP-                       Sales /
                           connected                       Engineering /
                           agent                           Compliance
                                                           users
```

### 5.1 Layer Responsibilities

- **Domain Packs**: contribute domain-specific knowledge (prompts, analyzers, templates, metadata extensions) without modifying the core. Loaded at server startup.
- **Core engine**: domain-agnostic. Provides the subject dispatcher, evaluation pipeline (deterministic + LLM), storage, search, governance, federation, audit log.
- **Consumers**: SDKs, MCP server, CLI tools, frontend. Each composes with the core for a specific access pattern.

### 5.2 Trust and Data Boundaries

- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and judgments they are authorized to see, per the ABAC governance model.
- All evaluation calls produce immutable audit records on the server side.
- The audit log uses a hash chain for non-repudiation; the application layer cannot bypass this.

### 5.3 Three Stores, One Source of Truth

PostgreSQL holds canonical data. Elasticsearch is a derived search index. Neo4j is a derived relationship graph. If they disagree, **Postgres wins**. Reconciliation scripts rebuild the derived stores from Postgres.

---

## 6. Domain Model

### 6.1 The `Rule` Entity

A rule is the central first-class object. It is **not** a regex or a code expression; it is a structured envelope around a natural-language statement.

| Field | Type | Description |
|---|---|---|
| `id` | string | Stable identifier |
| `statement` | string | The rule text in natural language (the canonical form) |
| `language` | ISO 639-1 string | Language of the statement (default `en`) |
| `kind` | `RuleKind` | Semantic type of the rule (see §6.3) |
| `body` | typed body | Kind-specific structured body (expression, state machine, definition, etc.) |
| `source_refs` | list | Pointers to the source document, section, and offset |
| `scope` | `Scope` | Structured multi-axis scope (see §6.2) |
| `modality` | enum | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `effective_period` | range | `valid_from` / `valid_until` |
| `preconditions` | string | Facts required to evaluate the rule |
| `exceptions` | list | References to other rules or carve-outs |
| `rationale` | string | Why the rule exists (purpose, intent) |
| `context` | string | Surrounding document text, section hierarchy, regulatory authority |
| `severity` | enum | LOW / MEDIUM / HIGH / CRITICAL |
| `tags` | list[string] | Free-form taxonomic labels |
| `domain_attributes` | dict | Domain-specific metadata defined by the Domain Pack |
| `translations` | list[`TranslationLink`] | Equivalent rules in other languages (see §6.8) |
| `governance` | object | Owner, approvers, revision history |
| `maturity_level` | enum | EXPERIMENTAL / STABLE / PROVEN (with shadow-mode semantics) |
| `embedding` | vector | Vector representation (derived) |

The `statement` is the **source of truth**. Structured fields exist for indexing, filtering, prioritization, and routing — never to override the meaning of the statement.

### 6.2 Structured Scope (Multi-Axis)

Scope is a structured value, not a flat string.

```python
@dataclass(frozen=True)
class Scope:
    domain: str                      # "legal" | "hr" | "finance" | "sales" | "engineering" | "communication" | ...
    org_unit: str | None = None      # "acme", "acme/legal", "acme/jp/sales", ...
    subject_type: str | None = None  # "contract" | "employee" | "expense" | "code_file" | "email" | ...
    attributes: dict[str, str] = field(default_factory=dict)
                                     # region: "US", role: "manager", currency: "USD", ...
```

**Matching semantics**: a rule's scope matches a request's scope when:
- the rule's `domain` is equal (or `None` = global)
- the rule's `org_unit` is `None` or is an ancestor of the request's `org_unit`
- the rule's `subject_type` is `None` or equals the request's `subject_type`
- every attribute key in the rule's `attributes` is present and equal in the request's `attributes`

The Federation hierarchy (§6.10) walks `org_unit` ancestry to compose effective rule sets.

### 6.3 Rule Kind Taxonomy

Rules differ semantically and should be evaluated by appropriate strategies. `kind` distinguishes the **semantic type** of the rule, distinct from `modality` (obligation strength).

| `kind` | Evaluator | Examples |
|---|---|---|
| `normative` | LLM Judge | "Employees must take 5 paid leave days per year." |
| `computational` | Sandboxed expression engine + LLM exception check | "Overtime is hours worked above 8 per day per employee." |
| `procedural` | State-machine validator | "Purchase orders follow Quote → Approve → Contract → PO." |
| `definitional` | Reference lookup + LLM | "A 'manager' is an employee at level L5 or above." |
| `principle` | LLM with high context | "Customer trust is paramount." |

Each `kind` has a corresponding typed body. Example for `computational`:

```yaml
kind: computational
statement: "Monthly overtime hours must not exceed 45 hours unless a special 36-agreement clause applies."
body:
  expression: "sum(daily_overtime_hours[month]) <= 45"
  required_inputs: ["daily_overtime_hours", "month"]
  unit: "hours"
  exception_predicate: "has_active_special_36_agreement"
```

The evaluator computes the expression deterministically, then asks the LLM only whether the `exception_predicate` is satisfied for the given context.

### 6.4 Rule Relationships

Rules form a graph, not a flat list. Modeling these relationships explicitly turns the repository from a list into a **provenance and impact graph**.

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision that replaces a prior version |
| `translates` | Bidirectional link between rules with equivalent meaning in different languages |

### 6.5 Meta-Rules

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy"). Meta-rules are evaluated by the same engine but are scoped to govern the rule corpus itself.

### 6.6 `EvaluationSubject` Abstraction

The evaluation engine accepts any of several `EvaluationSubject` kinds. Each kind has a dedicated context assembler, rule selector strategy, and evaluation prompt set. **Code change is one variant among many, not the default.**

| `kind` | Description | Example consumers |
|---|---|---|
| `code_change` | A unified diff or set of file changes | CI pipelines, AI coding agents, PR review |
| `business_event` | A discrete event in a business workflow with a payload | HR systems (overtime register), travel systems, attendance |
| `document_artifact` | A document or document section under review | Contract management, marketing asset review, policy authoring |
| `transaction` | A financial or commercial transaction with amount and parties | Expense systems, ERP, procurement, payment systems |
| `communication` | An outbound message or public artifact | Email gateways, social media tools, internal chat moderation |
| `decision_request` | A generic approval request | Workflow systems, approval queues |

The evaluation service dispatches on `kind` to the appropriate handler. The pipeline (context assembly → rule selection → deterministic checks → LLM checks → verdict aggregation) is otherwise uniform.

### 6.7 Domain Pack

A **Domain Pack** is a self-contained module that extends the system for a specific business domain. Packs are loaded at server startup.

Each pack defines:

- **Manifest** (`pack.yaml`): domain name, version, supported subject types, metadata extensions schema, default modality, preferred subject kinds.
- **Metadata schema**: extensions to `Rule.domain_attributes` (e.g., legal adds `jurisdiction`, `statute_id`).
- **Prompts**: domain-specific templates for extraction, metadata inference, and evaluation.
- **Analyzers**: domain-specific document analyzers (e.g., contract PDF analyzer for legal).
- **Templates**: ready-to-import YAML rule sets for the domain.
- **Samples**: representative documents and test fixtures.
- **(Optional) UI views**: React component snippets for persona-specific views.

The Rule Repository ships with the following packs:

- `engineering` (existing functionality, migrated into a pack)
- `legal`
- `hr`
- `finance`
- `sales`
- `communication`

The core remains domain-agnostic; new domains are added by writing a new pack, not by modifying the core.

### 6.8 Multilingual Rules

Rules carry an explicit `language` field and may be linked to siblings in other languages via `translations`. Translation equivalence is periodically verified by a background job that uses Gemini to score semantic equivalence. Drops below a threshold trigger alerts.

```python
@dataclass(frozen=True)
class TranslationLink:
    sibling_rule_id: str
    language: str
    equivalence_verified_at: datetime | None
    equivalence_score: float          # 0..1
```

API behavior:
- `GET /api/v1/rules?language=ja` filters by language.
- `GET /api/v1/rules/{id}/translations` returns the equivalence cluster.
- Evaluation accepts `Accept-Language` and prefers rules in that language; falls back to siblings.

### 6.9 Governance: ABAC-Style Policies

Per-rule Owner / Approver / Reader (legacy) is augmented by attribute-based policies.

```python
@dataclass(frozen=True)
class GovernancePolicy:
    domain: str | None                # None = applies to all domains
    org_unit: str | None              # None = applies to all units
    action: str                       # "rule.read" | "rule.edit" | "rule.approve" | "rule.evaluate"
    principals: list[str]             # "group:legal-team", "role:approver", "user:alice"
    effect: Literal["allow", "deny"]
```

Resolution: explicit deny > explicit allow > inherited allow > default deny.

This expresses, for example: "the Legal department can edit Legal rules, can read all rules, but can approve only Legal rules; Engineering can read all rules but edit only Engineering rules; Compliance Officers can read all and approve only HR rules."

### 6.10 Federation: Hierarchical Composition

Federation provides organization → team → project hierarchy with inheritance and overrides. Rules at higher levels automatically apply to all descendants, with project-level overrides. Federation is orthogonal to ABAC governance: federation answers "which rules apply here?"; ABAC answers "who may act on this rule?".

---

## 7. Components

### 7.1 Rule Management Server

The server is the system of record for all rules.

**Capabilities:**
- **Rule CRUD** with revision history and effective-date semantics.
- **Domain Pack loader** that registers prompts, analyzers, templates, and metadata schemas at startup.
- **Extraction pipeline** with structural parsing (PDF/MD/text), normative-sentence detection, coreference resolution, domain-adaptive metadata inference, and human review.
- **Search APIs**: full-text, vector (semantic), category/tag, hybrid (BM25 + kNN), context (given facts, return applicable rules), impact (given a proposed rule change, return affected rules).
- **Intent API**: classifies a natural-language query into one of `lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change` and routes accordingly.
- **Universal Submissions API** (`POST /api/v1/submissions`): a single, generic intake for any `EvaluationSubject` kind. The legacy `POST /api/v1/evaluate` becomes a thin wrapper that constructs a `CodeChangeSubject`.
- **Evaluation service** (subject-dispatched): given an `EvaluationSubject` and applicable rules, runs deterministic checks first, then LLM checks for rules that need interpretation, then aggregates verdicts.
- **Hybrid Evaluation Engine** (deterministic + LLM): described in §6.3 and §7.2.
- **Audit log**: append-only, hash-chained record of all evaluations including inputs, applied rules, model identity, deterministic-layer results, LLM-layer results, and final verdict.
- **Governance**: ABAC-style policies, federation, revision approval workflow (Proposals), and effective-date scheduling.

### 7.2 Hybrid Evaluation Engine

The evaluation engine is structured in two layers.

**Pipeline:**

```
Subject + Selected Rules
        │
        ▼
┌────────────────────────────────┐
│ Deterministic Layer             │
│  - schema validation            │
│  - numeric expressions          │
│  - lookups against tables       │
│  - state-machine checks         │
└────────────┬───────────────────┘
             │ DeterministicVerdict per rule
             ▼
┌────────────────────────────────┐
│ LLM Layer                       │
│  - normative interpretation     │
│  - exception evaluation         │
│  - principle-level rules        │
└────────────┬───────────────────┘
             │ FinalVerdict per rule
             ▼
        Verdict Aggregator
        Reason Graph Builder
```

For each rule, the system first checks whether a deterministic verdict is possible:
- Rules of `kind=computational` → deterministic always.
- Rules of `kind=normative` whose body includes a numeric or schema predicate → partial deterministic check first.
- Rules of `kind=principle` → LLM only.

The deterministic layer produces a strict pass/fail with auditable arithmetic. The LLM then evaluates remaining uncertainty (exceptions, edge cases) and produces the final verdict.

**Code-aware features** (preserved from the engineering use case): the engine understands file paths for scope matching, parses diffs to evaluate only what changed, references specific functions and lines in remediations, and returns actionable fix suggestions. These features now live behind the `code_change` subject kind, not at the engine level.

### 7.3 Rule Client (Python SDK)

A thin, ergonomic wrapper over the server APIs.

```python
from rulerepo import RuleClient

async with RuleClient(server_url="...", api_key="...") as client:
    # Search
    rules = await client.search.hybrid("monthly overtime limit",
                                       scope={"domain": "hr"})

    # Intent
    result = await client.intent.ask(
        "What are the rules for refunding orders over $500?"
    )

    # CRUD
    rule = await client.rules.get("rule_abc123")
    await client.rules.update(rule.id,
                              statement="...",
                              revision_note="...")
```

### 7.4 Agentic Rule Client (Python SDK)

A higher-level client that wraps `RuleClient` and adds AI-agent capabilities for systems that need to **enforce** rules, not merely query them.

**Added capabilities:**
- **Automatic context gathering**: given an event, pull related facts from surrounding systems before evaluation.
- **Two-stage evaluation**: first narrow the rule set by metadata and embeddings, then evaluate with appropriate models.
- **Result caching**: hash-keyed cache, automatically invalidated on rule revision.
- **Reason graphs**: structured DAG of which facts triggered which conditions in which rules.
- **Repair suggestions**: when an action is denied, propose the minimum modification that would make it compliant.
- **Three integration modes**: `preflight`, `posthoc`, `sidecar`.

```python
from rulerepo.agentic import AgenticRuleClient

async with AgenticRuleClient(server_url="...",
                              scope={"domain": "hr"}) as client:
    result = await client.evaluate(
        subject={
            "kind": "business_event",
            "event_type": "register_overtime",
            "payload": {"employee_id": "E001", "month": "2026-04",
                        "overtime_hours": 50},
        },
        intent="preflight_validation",
        mode="preflight",
    )

    if result.verdict == "DENY":
        print(result.violations)        # which rules were violated
        print(result.reason_graph)      # why
        print(result.suggested_fix)     # how to comply
```

### 7.5 Subject-Specific Workflows

Each `EvaluationSubject` kind has a workflow front-door. These are not separate engines; they share the core evaluation service.

#### Code Change Workflow
- Accepts unified diffs, file paths, or free-form facts.
- Parses diffs into structured `FileChange` objects with language detection and function extraction.
- Per-rule verdicts with line-level locations, structured remediations, conflict resolution via Neo4j graph.
- Integration points: `rulerepo-check` (CI CLI), `rulerepo-hook` (agent hooks), MCP server, GitHub PR review (optional).

#### Business Event Workflow
- Accepts a structured event with `event_type`, `payload`, `actor`, `occurred_at`.
- Context assembler can fetch related facts from configured sources (employee record, attendance history, etc.).
- Per-rule verdicts with reasoning, including deterministic-layer results.
- Integration points: `POST /api/v1/submissions`, Python SDK, agent SDK.

#### Document Artifact Workflow
- Accepts a document (PDF/MD/text) or document sections with intent (e.g., "draft_review", "publish_check").
- Uses the Gemini File API for PDF understanding (hierarchical section extraction).
- Returns per-section findings with severity, suggested rewrites, and clause-level references.
- Integration points: contract review UI, marketing asset review UI, policy authoring UI.

#### Transaction Workflow
- Accepts a transaction with `transaction_type`, `amount`, `currency`, `counterparties`, `line_items`.
- Deterministic layer handles thresholds, currency normalization, vendor lookups.
- Integration points: expense systems, ERP, procurement systems.

#### Communication Workflow
- Accepts a message with `channel`, `sender`, `recipients`, `content`.
- Evaluates against communication policy rules (marketing claims, regulated industries, internal disclosure).
- Integration points: email gateway, social media tools.

### 7.6 Agent Context Delivery (MCP + Smart Rule Selection)

Exposes the Rule Repository to AI agents via the Model Context Protocol (MCP). The key innovation is **active context delivery** — rules reach the agent at the right moment without being asked.

- **MCP Server**: FastMCP server with stdio (for Claude Code) and streamable-http (for remote agents) transports.
- **Tools**: `search_rules`, `evaluate_compliance`, `explain_rule`, `find_conflicts`, `get_rules_for_context`, `register_agent`, `request_exception` (and a small set of others).
- **Resources**: `rule://{id}` (single rule), `ruleset://{scope}` (dynamic CLAUDE.md section or persona-appropriate context).
- **Prompts**: `compliance_check`, `rule_summary`, `impact_analysis`.
- **Rule Formatter**: output formats optimized for the consumer — `instructions` (concise MUST/SHOULD hierarchy), `checklist` (PR review), `detailed` (full metadata), `persona_briefing` (a persona-tailored briefing for non-engineering use).
- **Scope Registry**: scope resolution for non-code subjects as well as code subjects.

### 7.7 Development Workflow Integration

Integration into the places where work happens. These are integrations, not the system's center of gravity.

- **CI Pipeline CLI** (`rulerepo-check`): runs `git diff` → evaluates → exits 0/1/2. Supports `--format text|json|github-actions` for inline PR annotations.
- **Agent Hooks** (`rulerepo-hook`): `preflight` injects applicable rules before edit, `posthoc` evaluates changes after edit. Designed for Claude Code hooks and similar.
- **Rule Ingestion** (`rulerepo-ingest`): imports rule sources through the extraction pipeline.
- **Rule Export** (`rulerepo-export`): emits a `rules.yaml` snapshot.
- **Optional GitHub App**: webhook receiver that processes `pull_request` events, evaluates, and posts review comments. Disabled by default in local mode; one integration option among many.

### 7.8 Persona-Aware Frontend

The frontend is the operator console. Personas drive the default view, sidebar, vocabulary, and dashboard.

| Persona | Default landing view | Primary actions |
|---|---|---|
| Engineer | Code compliance dashboard | Run check on PR, view rules for current file, view CI status |
| Legal Counsel | Contract review queue | Review contract, propose rule change, search by jurisdiction |
| HR Manager | Employee event compliance | Review pending HR events, view dormant rules, propose policy update |
| Finance Manager | Transaction approval queue | Approve expense, view spending against rules, review supplier compliance |
| Sales Manager | Deal & discount review | Review proposed discounts, view price-policy compliance |
| Compliance Officer | Cross-domain compliance summary | Audit log, conflict alerts, regulatory change impact |

Each persona has tailored:
- Landing dashboard
- Sidebar items
- Default rule kind and domain filters
- Action shortcuts
- Vocabulary in UI strings (i18n-style per persona)

Shared functionality (rule detail, search, proposals, settings, notifications) lives under `(shared)` and is reachable from any persona.

### 7.9 Rule Intelligence (Essentials)

Analytics, health scoring, and automated improvement recommendations — focused on essentials, not extensive observability.

- **Health Scorer**: per-rule score (0-100) across dimensions — completeness, clarity, test coverage, freshness, activity, owner engagement.
- **Evaluation Analytics**: corpus-wide and per-rule metrics from the evaluations table and audit log — fire rate, deny rate, latency, trends.
- **Recommender**: automated suggestions — retire dormant rules, clarify ambiguous ones, escalate persistent violations, strengthen SHOULD → MUST.
- **Effectiveness Score**: per-rule composite (precision, prevention rate, agent adoption).
- **Dashboard**: persona-aware summary cards. Advanced drill-downs and webhook delivery of digests are feature-flagged off.

### 7.10 Discovery (Cross-Domain)

Bootstraps rules from existing artifacts. Domain Packs contribute analyzers.

- **Engineering analyzers**: `CLAUDE.md` parser, linter config parser (ruff/eslint/tsconfig/prettier), code pattern analyzer.
- **Legal analyzer**: contract clause analyzer that extracts clauses with type detection (governing law, indemnification, etc.).
- **HR analyzer**: employment regulation PDF analyzer with section hierarchy detection (条/項/号 for Japanese, "Section/Subsection" for English).
- **Finance analyzer**: expense policy and procurement policy analyzer.
- **Pattern Detector**: deduplication and confidence scoring across sources.
- **Candidate Generator**: Gemini-powered refinement into structured rule candidates with statement, kind, modality, severity, scope, rationale.
- **Human Review Queue**: approve/edit/dismiss workflow. High-confidence candidates can be batch approved.
- **API**: `POST /api/v1/discover/scan`, `GET /api/v1/discover/candidates`, `POST /api/v1/discover/candidates/{id}/approve`.

### 7.11 Correction Feedback Loop

Captures human corrections of AI-generated work and converts them into rule improvements. This applies to code corrections (existing) and is generalized to non-code corrections in this refocus.

- **Correction Capture**: passive (compare evaluated diff or document against final approved state) and active (agent-hook-based for code; explicit submission API for non-code).
- **Correction Analyzer**: classifies each correction as `new_rule`, `improve_existing`, or `adjust_scope`.
- **Candidate Generation**: Gemini drafts a rule (or rewrite) from the correction context.
- **Background Workers**: clustering (cosine similarity), auto-drafting, statistics aggregation.
- **Intelligence Integration**: correction trends, top violated rules, coverage gaps, effectiveness.

### 7.12 Cross-Project Federation

Hierarchical rule composition across organizational boundaries: organization → team → project. Rules at higher levels automatically apply to all descendants, with project-level overrides.

- **Hierarchy**: Organization → Team → Project. Each level can override a parent rule.
- **Federation Resolver**: walks the ancestor chain, collects rules, applies overrides. Feeds the rule selector transparently.
- **API**: full CRUD at `/api/v1/federations`, `GET /api/v1/federations/{id}/effective-rules`, `GET /api/v1/federations/{id}/diff/{other_id}`.

### 7.13 Rule Playground & Testing Framework

Interactive sandbox and regression testing for rules.

- **Playground**: `POST /api/v1/playground/evaluate` accepts a draft rule + sample subject and returns a verdict without persisting. The playground accepts **all subject kinds**, not only code. UI provides input modes for each subject kind (code editor, business event form, document section, transaction, communication).
- **Per-Rule Test Cases**: each rule can have test cases (sample input + expected verdict).
- **Test Runner**: executes all test cases against a rule, reports pass/fail.
- **Test Generator**: Gemini auto-creates compliant and non-compliant examples.

### 7.14 Proactive Alert System

Background workers generate alerts on detected problems.

- **Alert Types**: `dormant_rule`, `high_deny_rate`, `health_decline`, `conflict_detected`, `effectiveness_decline`, `translation_drift`.
- **Alert Lifecycle**: `active` → `acknowledged` → `resolved`.
- **API**: `GET /api/v1/alerts`, `POST /api/v1/alerts/{id}/acknowledge`, `POST /api/v1/alerts/{id}/resolve`.
- **External webhook delivery is feature-flagged off** by default in local mode.

### 7.15 Rule Set Snapshots & Environment Deployment

Versioned snapshots with environment-based deployment and impact simulation.

- **Snapshots**: immutable frozen copies of all rules matching a scope filter at a point in time.
- **Environment Deployment**: deploy a snapshot to `production`, `staging`, or `development`. Only one active deployment per environment.
- **Rollback**: reactivate the previous deployment.
- **Impact Simulation**: compare a proposed snapshot against the current deployment; show rules added/removed and projected verdict deltas on a historical replay sample.

### 7.16 Proposals (Collaborative Governance)

Structured change management for rules.

- **Proposal lifecycle**: Draft → Review → Approved → Enacted (or Closed).
- **Proposal types**: create, amend, retire, merge, split, override.
- **Threaded comments** with suggestion and resolution types.
- **Multi-approver voting**: rules above a severity threshold require N approvals before activation.
- **Automated analysis on submit**: conflict analysis (using `conflicts_with` graph + LLM check) and impact preview (replay historical evaluations).
- **Notification routing**: rule changes notify affected scope owners through the in-app notification inbox.

### 7.17 Deferred Subsystems (Feature-Flagged Off)

The following exist in the codebase but are disabled by default in the refocused project:

- **Marketplace** (cross-organization rule package sharing): preserved in code, flagged off.
- **External webhook gateway** for ingesting events from public sources (Slack, generic webhooks): preserved, internal-API form only enabled by default.
- **Observability digest delivery** to external webhooks (weekly digest, team comparison): metrics still computed; external delivery flagged off.
- **GitHub-App-centric workflow**: optional integration; not required for setup.
- **Advanced autonomous agent governance** beyond agent identity tracking (trust-level auto-promotion, negotiation, multi-agent sessions): flagged off.

These will be revisited once cross-organizational core abstractions are mature.

---

## 8. Key Features

### 8.1 Foundational
- Natural-language rule storage with full provenance to source documents.
- Multi-modal search (full-text, vector, category, hybrid) with structured scope filtering.
- Rule lifecycle: draft → review → approved → effective → superseded → retired.
- REST API, Intent API, and Universal Submissions API.
- Python SDK (Rule Client) and Agentic SDK.
- Domain Packs (engineering, legal, HR, finance, sales, communication).

### 8.2 Cross-Domain
- Multiple `EvaluationSubject` kinds (code change, business event, document artifact, transaction, communication, decision request).
- Multiple `RuleKind` evaluators (normative, computational, procedural, definitional, principle).
- Hybrid evaluation (deterministic + LLM) for verifiable arithmetic and reference checks.
- Persona-aware frontend (engineer, legal, HR, finance, sales, compliance).
- Multilingual rules with verified equivalence.
- Domain-adaptive extraction (PDF section hierarchy, legal references, HR scope, finance taxonomies).

### 8.3 Differentiating
- **Conflict Detector**: continuously scans for `conflicts_with` candidates across the corpus.
- **Counterexample Generator**: minimal compliant and non-compliant examples per rule.
- **Rule Coverage**: dormant rules and over-triggered rules surfaced from event logs.
- **Change Impact Simulator**: replay historical events against a proposed rule revision.
- **Refinement Feedback Loop**: human corrections drive rule rewrites.
- **Polyglot Rules**: semantically equivalent rule pairs across languages with continuous verification.
- **Provenance Lineage**: Law → Internal Policy → Department Rule → Contract Clause, with downstream propagation.
- **Rule Tutor**: LLM-powered conversational interface explaining relevant rules to new team members.
- **Why API**: multi-level rationale for any verdict.
- **Automatic Rule Discovery**: bootstrap from existing artifacts in any domain.
- **Cross-Project Federation**: organization-wide governance with project-level overrides.
- **Rule Playground**: interactive sandbox across all subject kinds.
- **Proactive Alerts**: dormant rules, high deny rates, health decline, translation drift.
- **Versioned Snapshots**: atomic deployment with rollback and impact simulation.
- **ABAC Governance**: domain × action × principal policies.

### 8.4 Cross-Cutting
- Immutable audit log with hash-chained integrity.
- Tiered LLM strategy: small/fast for screening, large/accurate for high-severity judgments; deterministic layer for verifiable parts.
- PII sanitization on inputs and masking on logs.
- ABAC policies per (domain × action × principal).
- Feature flags for deferred subsystems.

---

## 9. Use Cases

### 9.1 HR / Attendance Management

The HR system registers attendance and overtime. The Rule Repository holds the work regulations as `kind=computational` (overtime formulas) and `kind=normative` (compliance obligations) rules in the `hr` Domain Pack. The HR system submits `BusinessEventSubject` instances at `POST /api/v1/submissions`. The deterministic layer evaluates numeric thresholds (45 hours/month, daily limits). The LLM layer evaluates exception clauses (active 36-agreement, manager exemption). Violations alert in `preflight` mode; audits run in `posthoc` mode.

### 9.2 Contract Management

The contract management system stores contracts under negotiation. The Rule Repository holds internal procurement rules and standard clause requirements in the `legal` Domain Pack. When a new contract is registered, the system submits a `DocumentArtifactSubject` and receives per-section findings with severity (missing anti-social-forces clause, unlimited liability flagged, governing law not specified, etc.). Each finding includes a suggested rewrite. Contract review proceeds clause-by-clause.

### 9.3 Finance / Expense and Procurement

ERP systems submit `TransactionSubject` instances for expense reports, purchase orders, and payments. The deterministic layer evaluates thresholds (per-person entertainment limit, payment-term lower bound per Subcontracting Act), currency normalization, and vendor sanctions checks. The LLM layer evaluates intent and justification narratives. Finance managers review the approval queue with attached verdicts.

### 9.4 Sales / Pricing and Discounting

CRM systems submit deal proposals as `BusinessEventSubject` or `DecisionRequestSubject`. The Rule Repository holds discount policies, customer-specific pricing approval rules, resale-price-maintenance restrictions, and MAP policies. Sales managers see a deal-review queue with pre-evaluated verdicts and suggested escalation paths for special discounts.

### 9.5 Communication / Marketing Compliance

Marketing tools submit advertising copy and social media drafts as `CommunicationSubject`. The Rule Repository holds misleading-representation rules (景品表示法), pharmaceutical-claim restrictions (薬機法), industry-specific advertising rules, and sponsorship disclosure rules. The LLM evaluates copy with context; deterministic checks evaluate explicit prohibited terms.

### 9.6 Software Development

CI pipelines submit `CodeChangeSubject` (via `rulerepo-check`). AI coding agents receive applicable rules via MCP. The Rule Repository holds engineering coding standards, security checklists (OWASP-derived), API design rules, and documentation conventions in the `engineering` Domain Pack. This use case is unchanged from current behavior; the code path is now one variant.

### 9.7 Regulatory Compliance

A regulated organization stores regulations (e.g., consumer protection laws, financial regulations, data protection laws) in the repository with `derives_from` links to internal procedures. When a regulation is amended, the Provenance Lineage and Change Impact Simulator together identify all downstream procedures that need review. Proposals automatically draft revision plans for the affected internal rules.

### 9.8 AI-Assisted Cross-Domain Work

A team adopts the Rule Repository organization-wide. Engineering bootstraps rules from existing `CLAUDE.md` and linter configs. Legal team imports the `legal-contracts-jp` template. HR imports the `hr-attendance-jp` and `hr-conduct` templates. Finance imports `finance-expense-jp` and `finance-procurement`. Each team works in its own persona view; rules are managed centrally with federation. AI agents working in any domain can query applicable rules via MCP and receive persona-appropriate briefings.

---

## 10. Technical Stack

| Layer | Technology | Notes |
|---|---|---|
| Backend | Python 3.13, FastAPI | uv-managed |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind | pnpm-managed |
| Python clients | Python 3.13 | uv-managed |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` | tiered model selection |
| Deterministic eval | `asteval` (sandboxed expressions), Pydantic (schema), in-memory state machine | no shell-out, no I/O |
| Document parsing | Gemini File API + domain-adaptive structural parsers | PDF, text, markdown |
| Rule store | PostgreSQL 17 (rules, revisions, audit log) | JSONB for structured scope, alembic migrations |
| Search | Elasticsearch 8 | BM25 + dense_vector hybrid |
| Graph DB | Neo4j 5 | rule relationships |
| Job Queue | Redis + arq | health scoring, correction analysis, translation verification |
| MCP | FastMCP (mcp >= 1.9) | stdio + streamable-http |
| Quality | ruff + mypy, ESLint + Prettier, pre-commit | enforced on PR |
| Local orchestration | Docker Compose | dev + integration tests |

---

## 11. Roadmap

The project is in a **refocused** phase. Earlier phases (1–5) achieved storage, search, code-aware evaluation, MCP integration, discovery, federation, snapshots, playground, and intelligence essentials. Phase 6 partially implemented Proposals, Autonomous Agent Governance, and Marketplace, but accumulated code-centric tilt.

This roadmap supersedes prior phase plans.

### Step 1 — Generalize the Core (Sprints 1–3)

**Objective**: make the system subject-agnostic at the abstraction level.

- Introduce `EvaluationSubject` abstraction with `CodeChangeSubject` as the migrated default. Other kinds are skeletal at this step.
- Replace flat `scope` string with structured `Scope` (multi-axis), with dual-read backward compatibility.
- De-scope Phase 6 features behind feature flags (Marketplace, external observability delivery, broad gateway, GitHub-App centrality, advanced agent governance).
- Establish Domain Pack scaffolding: move existing engineering-specific code into `domain-packs/engineering/`.

**Exit criteria**: existing engineering use cases work unchanged; the abstractions for adding new subjects exist; deferred subsystems are flagged off; the `engineering` Domain Pack runs through the loader.

### Step 2 — Expand to Non-Engineering Domains (Sprints 4–7)

**Objective**: demonstrate the platform serving legal, HR, finance, and sales use cases.

- Build out `legal`, `hr`, `finance`, `sales`, `communication` Domain Packs with manifests, prompts, one analyzer each, and at least one template each.
- Implement domain-adaptive extraction pipeline. Strengthen Gemini File API usage for PDF section hierarchy extraction.
- Add `rule_kind` polymorphism: `normative` and `computational` first, then `definitional`. `procedural` and `principle` as use cases demand.
- Ship initial template library (8 non-engineering templates, ~60 rules total). All non-engineering templates ship as `experimental` (shadow mode).

**Exit criteria**: at least these end-to-end flows work — HR overtime registration via `BusinessEventSubject`, NDA contract review via `DocumentArtifactSubject`, expense submission via `TransactionSubject`. Each uses domain-specific prompts and templates.

### Step 3 — Persona-Aware UX and Universal Intake (Sprints 8–10)

**Objective**: make non-engineering personas first-class citizens.

- Restructure frontend under `(personas)/{engineering,legal,hr,finance,sales,compliance}/`.
- Ship Engineering and Legal personas first as vertical slices; then HR; then Finance; then Sales and Compliance.
- Implement Universal Submissions endpoint (`POST /api/v1/submissions`). Wrap `POST /api/v1/evaluate` over it for backward compatibility.
- Implement Hybrid Evaluation Engine fully: deterministic layer for `kind=computational`, numeric predicates in `kind=normative`, schema validation, and table lookups.

**Exit criteria**: a non-engineering user can navigate the frontend without seeing engineering-specific terminology by default. Business systems can submit any subject kind through the universal endpoint. At least 30% of evaluations on the eval harness are resolved without an LLM call.

### Step 4 — Multilingual and Governance (Sprints 11–13)

**Objective**: address enterprise readiness for international and complex organizational structures.

- Implement first-class multilingual rules with `language` field, `TranslationLink` table, and Gemini equivalence verification (background job).
- Implement ABAC-style governance with domain × action × principal policies. Migrate existing per-rule Owner/Approver/Reader to ABAC over a release.
- Complete remaining Domain Pack contents (legal-en-us, hr-conduct, finance-procurement, etc.).

**Exit criteria**: bilingual contracts (EN/JA) are managed with verified equivalence. Departmental access boundaries are expressed in policies. All six Domain Packs are functional with at least one template each.

### Step 5 — Stabilization (Sprint 14)

- Remove legacy code paths superseded by new abstractions.
- Document the platform from each persona's perspective (`docs/personas/`).
- Audit the test suite for cross-domain coverage; aim for at least 50% of integration tests covering non-engineering subjects.
- Re-evaluate Marketplace and advanced features in light of stabilized core.

---

## 12. Success Metrics

### 12.1 Quantitative

- **Template diversity**: at least 8 templates across 5 non-engineering domains in `domain-packs/*/templates/`.
- **Subject diversity**: integration tests cover all 6 `EvaluationSubject` kinds.
- **Evaluation determinism**: at least 30% of evaluations on the eval harness are resolved without an LLM call.
- **Cross-domain rule coverage**: at least 25% of seeded sample rules are in non-engineering domains.
- **Persona traffic**: at least 4 of the 6 personas have functional landing pages.
- **Coverage**: percentage of rules in target source documents successfully extracted and registered ≥ 70%.
- **Latency**: p50 / p95 / p99 evaluation latency in `preflight` mode within stated SLOs (p95 ≤ 1.5s for code change, ≤ 0.8s for deterministic-only evaluation).
- **Accuracy**: human-rated correctness of verdicts on a held-out test set ≥ 90% for `experimental` rules; ≥ 95% for `proven` rules.
- **Adoption**: number of integrated systems and active rules; volume of evaluation requests per day.
- **Governance health**: percentage of rules with complete metadata, current rationale, and active owners ≥ 80%.
- **Time-to-comply on regulatory change**: median time between a source-law amendment and the corresponding internal rule revision being approved ≤ 14 days.
- **Shadow-to-enforcement rate**: > 70% of experimental rules reach stable within 60 days.
- **Auto-fix rate**: > 40% of SHOULD violations auto-fixed via structured remediations.
- **Flywheel throughput**: > 5 rules/month auto-drafted from correction clusters.
- **Translation drift**: less than 5% of translation pairs flagged for re-verification per month.

### 12.2 Qualitative

- A legal team can register a Japanese employment regulation PDF and produce candidate rules without engineering-team intervention.
- An HR system can submit an overtime registration event through `POST /api/v1/submissions` and receive a verdict with deterministic numeric reasoning.
- A finance team can describe an expense policy in a YAML template, import it, and use the playground to validate against sample expense events.
- A bilingual contract clause pair is recognized as semantically equivalent and managed as such.
- A non-engineering user opens the frontend and recognizes the system as relevant to their work.

### 12.3 Anti-Criteria (signs the refocus is failing)

- Engineering-domain features continue to receive disproportionate development time.
- "Cross-organizational" appears only in marketing copy, not in code paths.
- The frontend home page still shows code-centric content for all personas.
- Templates are added in the engineering domain faster than non-engineering domains.
- The Marketplace flag gets re-enabled before legal/HR/finance vertical slices ship.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Hybrid evaluation puts arithmetic in deterministic layer. Audit log captures full context. Consensus voting for CRITICAL rules. Human review on high-severity denials. Refinement feedback loop. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity. Refinement loop suggests rewrites. Per-rule test cases prevent regression. |
| LLM costs scale poorly with rule corpus size | Two-stage rule selection (metadata pre-filter, then LLM judge). Aggressive caching. Tiered model selection. Deterministic layer offloads arithmetic. |
| Refactoring the evaluation core breaks existing engineering flows | Parity tests; feature flag gating; staged rollout; preserve `evaluate_code_change.txt` semantics; treat the engineering pack as the second implementation, not the reference. |
| Sensitive data leaks through evaluation context | Input sanitization; log masking; tenant isolation; optional fully self-hosted model deployment. |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via `effective_period`; shadow mode for experimental rules; snapshot-based environment deployment. |
| Over-reliance reduces human judgment | Position the system as decision support, not decision replacement; preserve rationale visibility; require human approval for rule revisions. |
| Conflicts with existing IAM / GRC tools | Position the Rule Repository as a complementary semantic layer; provide integration points rather than competing with baseline controls. |
| Cross-domain templates require legal/HR/finance review | Ship all non-engineering templates as `experimental` (shadow mode). Avoid claiming legal/regulatory accuracy. |
| Roadmap pressure leads to skipping the de-scoping step | Make de-scoping the first deliverable. Without it, capacity for Steps 1–4 is unavailable. |
| Multilingualism increases extraction cost | Treat translation verification as a daily background job, not a real-time check. Cache equivalence scores. |
| Domain Pack abstraction over-engineers | Build the legal pack as a vertical slice before generalizing. Validate the abstraction against two non-engineering packs before stabilizing the contract. |

---

## 14. Glossary

- **ABAC**: Attribute-Based Access Control. Authorization model based on attributes of subject, action, and resource.
- **Domain Pack**: A self-contained module that extends the Rule Repository for a specific business domain (legal, HR, finance, sales, communication, engineering).
- **EvaluationSubject**: An abstract input to the evaluation engine. Concrete kinds: code change, business event, document artifact, transaction, communication, decision request.
- **Federation**: Hierarchical composition of rules across organization, team, and project levels with inheritance and override.
- **LLM-as-Judge**: The architectural pattern of using a large language model to evaluate whether an action complies with a natural-language rule.
- **Maturity Level**: A rule's lifecycle stage — experimental (shadow mode) → stable → proven.
- **Meta-rule**: A rule whose subject is other rules.
- **Modality**: The strength of the obligation (MUST, MUST_NOT, SHOULD, MAY, INFO).
- **Persona**: A user role for which the frontend tailors landing view, navigation, vocabulary, and dashboards (Engineer, Legal Counsel, HR Manager, Finance Manager, Sales Manager, Compliance Officer).
- **Preflight / Posthoc / Sidecar**: Three modes of integration corresponding to before-action, after-action, and parallel-observation enforcement.
- **Provenance lineage**: The chain of derivation from a higher-level source (e.g., a law) down to operational rules and contract clauses.
- **Reason graph**: A structured DAG explaining which facts triggered which conditions in which rules.
- **Rule**: A natural-language normative statement plus structured metadata, managed as a first-class object.
- **Rule Kind**: The semantic type of a rule (normative, computational, procedural, definitional, principle), distinct from modality.
- **Scope**: A structured multi-axis value (domain, org_unit, subject_type, attributes) that defines what a rule applies to.
- **Statement**: The canonical natural-language text of a rule.
- **Universal Submissions API**: `POST /api/v1/submissions` — a single intake endpoint for any `EvaluationSubject` kind.
- **Verdict**: The result of an evaluation (ALLOW, DENY, NEEDS_CONFIRMATION).

---

## 15. Open Questions

These remain subjects of design iteration:

- **Domain attribute schema discoverability**: How should clients learn the metadata extensions a Domain Pack defines? Auto-generated OpenAPI from `pack.yaml`, or a separate discovery endpoint?
- **Cross-domain rules**: A rule that spans domains (e.g., "All employee communications about contracts must be reviewed by Legal") — does it live in `hr`, `legal`, or `communication`? Or should there be a `cross-domain` pack? Current answer: it lives in the pack of its primary domain with `tags` referencing the others; revisit after vertical slices ship.
- **Persona membership**: How is a user assigned to a persona? Explicit selection, mapped from organizational role, or inferred from behavior? Current answer: explicit selection with optional auto-suggestion from org_unit.
- **Translation verification thresholds**: What `equivalence_score` triggers an alert? Operationally tunable, default 0.85.
- **Deterministic layer expression language**: `asteval` is the current pick. Limits: no I/O, no imports, no attribute access. Sufficient for thresholds, sums, and lookups; insufficient for graph traversal. Revisit when first procedural rule is implemented.
- **Multi-tenant isolation model**: Single-tenant deployments first; multi-tenant requires per-tenant Domain Packs and ABAC at the tenant level. Revisit after Step 4.
- **External LLM provider abstraction**: The `Evaluator` interface should accept any model that can perform structured judgment. Current implementation is Gemini-only; abstraction is partial. Revisit when a second provider is needed.

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes should follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect. Disagreements with the priorities or proposed designs should be surfaced and resolved before implementation begins.*
