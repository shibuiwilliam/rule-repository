# Rule Repository

> A platform for managing, searching, evaluating, and enforcing natural-language rules across an organization — legal, HR, finance, sales, engineering, communication, and beyond — using LLMs and AI agents.
>
> Rules live as first-class, versioned, governed assets. Domains live as plugins. Subjects under evaluation can be code, documents, business events, transactions, or communications. Engineering is one domain among many.

---

## 1. Project Overview

The **Rule Repository** is a system that stores human-authored rules in their original natural-language form and makes them operationally useful: searchable, applicable, and enforceable across the work of every functional team.

Where traditional rule engines require translating human rules into a formal language (and losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs and AI agents to interpret, search, and enforce them at runtime.

This approach is inspired by, and generalizes, the concept of **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea along three axes:

- **Wider scope of rules**: laws, regulations, contracts, internal policies, HR rules, finance policies, sales conventions, engineering standards, communication norms, documentation conventions.
- **Wider scope of consumers**: human users (legal counsel, HR managers, finance teams, sales reps, engineers, compliance officers), business systems (HR, contract, expense, procurement), IDEs, CI pipelines, and AI agents.
- **Wider scope of subjects**: not only code changes, but business events (an HR action, an expense submission), document artifacts (a contract clause, marketing copy), transactions (a payment, a quote), and communications (an email, a Slack message).

### 1.1 What This Means in Practice

A single Rule Repository deployment serves multiple teams concurrently:

- The **Legal team** uploads contract templates, regulations, and internal procurement policies. They review extracted rules, organize them by jurisdiction, and evaluate draft contracts against them.
- The **HR team** uploads work regulations, labor agreements, and overtime policies. The attendance system submits each employee event for evaluation.
- The **Finance team** uploads expense policies, tax rules, and procurement standards. The expense system submits each reimbursement request for evaluation.
- The **Sales team** uploads pricing policies, discount approval rules, and antitrust guidance. The CPQ system submits each quote for evaluation.
- The **Engineering team** registers coding standards, security rules, and architectural guidelines. CI pipelines and AI coding agents evaluate code changes.
- The **Compliance officer** sees cross-domain dashboards: where conflicts exist, where rules are dormant, where corrections are accumulating.

All of this through one system, one rule corpus model, and one set of APIs.

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository fills a gap that no current category of software addresses cleanly:

- **Document management systems** store source documents but do not understand the rules inside them.
- **Rule engines (Drools, DMN, OPA)** require formal encoding and lose the original semantics.
- **GRC platforms** track compliance status but do not enforce rules at the point of action.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.
- **AI coding assistant guardrails** evaluate code against rules but cannot evaluate a contract, an expense submission, or a business decision.

The Rule Repository treats **rules themselves as first-class, versioned, governed assets**, decoupled from any single consumer or subject type, and reusable across the entire organization.

### 2.1 Why Cross-Organizational Matters

Many rule-aware systems exist for individual domains: contract review tools for legal teams, expense approval engines for finance, compliance checkers for code. Each is siloed, each requires its own setup, each rebuilds the same core capability (natural-language interpretation of rules) from scratch.

A cross-organizational platform consolidates that capability. The same evaluation engine that judges whether a code change conforms to a security rule also judges whether a contract clause conforms to a procurement policy. The same Federation model that lets an engineering org-level rule cascade to a project lets a corporate HR policy cascade to a regional office. **The reuse is in the core, not the surface.**

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Store rules in natural language with full traceability to their source documents.
- Treat each functional domain (legal, HR, finance, sales, engineering, …) as a first-class plug-in with its own metadata extensions, prompts, and templates.
- Treat each subject under evaluation (code change, business event, document artifact, transaction, communication, decision request) as a first-class kind, evaluated by a kind-aware handler.
- Provide rich search across rules (full-text, vector, category, hybrid, intent).
- Provide kind-aware evaluation: numeric rules verified deterministically; normative rules interpreted by LLM; principle rules judged with high-thinking models.
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Detect conflicts, redundancies, and dead rules across the corpus.
- Make provenance, rationale, revision history, and rule lineage first-class.
- Surface persona-appropriate UI for each functional team.
- Run entirely on a local Docker Compose stack for development and small-org deployments.

### 3.2 Non-Goals

- Replacing IAM, RBAC, ABAC, or network-layer access control. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel, compliance officers, HR managers, or finance controllers. The system surfaces issues; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts or policies on behalf of users.
- External Rule Marketplace (publishing rule packages to a public registry). [Frozen — see §10.4]
- External webhook gateways and Slack/email digest delivery. [Frozen — see §10.4]
- Autonomous agent governance loops (trust auto-promotion, multi-agent negotiation). [Frozen — see §10.4]

---

## 4. Architecture

The system is composed of three top-level components — server, clients, and domain packs — connected by an LLM provider and three data stores.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                              │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                   Evaluation Dispatcher                              │ │
│  │  ┌──────┐  ┌──────────┐  ┌────────────┐  ┌───────────┐  ┌────────┐ │ │
│  │  │ Code │  │ Business │  │ Document   │  │Transaction│  │  Comm  │ │ │
│  │  │Change│  │  Event   │  │ Artifact   │  │           │  │        │ │ │
│  │  │  H   │  │    H     │  │     H      │  │     H     │  │   H    │ │ │
│  │  └──────┘  └──────────┘  └────────────┘  └───────────┘  └────────┘ │ │
│  │       Each Handler: normalize → select rules → prompt → judge       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Extraction  │  │   Search     │  │  Discovery   │  │ Intelligence │ │
│  │  (per-domain │  │ (FT/Vec/Cat/ │  │  (cold start │  │  Health+Eff. │ │
│  │  adapters)   │  │  Hybrid/     │  │  bootstrap)  │  │  +Recs+      │ │
│  │              │  │  Intent)     │  │              │  │  Per-domain  │ │
│  │              │  │              │  │              │  │  Quality     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Governance  │  │  Federation  │  │  Snapshots   │  │  Proposals   │ │
│  │  (ABAC by    │  │  (org->team  │  │  (versioned  │  │  (lifecycle, │ │
│  │  domain+org) │  │  ->project)  │  │  rule sets)  │  │  voting,     │ │
│  │              │  │              │  │              │  │  comments)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Domain Packs (Legal, HR, Finance, Sales, Engineering)  │ │
│  │  Each pack: metadata extensions + prompts + analyzers + templates   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  PostgreSQL (truth)   Elasticsearch (search)   Neo4j (graph)   Redis      │
│  ──────────────────   ──────────────────────   ─────────────   ─────      │
│  Audit Log (hash-chained, append-only)                                    │
│                                                                           │
│   REST API   |   Submissions API   |   Intent API   |   MCP Server        │
└───────┬─────────────┬─────────────────┬───────────────────┬──────────────┘
        │             │                 │                   │
   ┌────▼────┐   ┌────▼─────┐   ┌──────▼──────┐   ┌────────▼──────┐
   │  Rule   │   │ Agentic  │   │     CLI     │   │   AI Agents   │
   │ Client  │   │  Client  │   │  (rulerepo- │   │  (via MCP)    │
   │  SDK    │   │   SDK    │   │  check/hook │   │               │
   │ (Python)│   │ (Python) │   │  /context)  │   │               │
   └─────────┘   └──────────┘   └─────────────┘   └───────────────┘
        │             │                 │                   │
        ▼             ▼                 ▼                   ▼
    Business      HR / Contract /    CI pipelines,   Claude Code,
    systems       Expense systems    IDE hooks       and any MCP
                                                      compatible agent
```

### 4.1 Trust and Data Boundaries

- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and verdicts their principal is authorized to see.
- All evaluation calls produce immutable audit records on the server side, regardless of which subject kind was evaluated.

### 4.2 Three Data Stores, One Source of Truth

- **PostgreSQL**: canonical rule store, evaluations, audit log, proposals, federation hierarchy.
- **Elasticsearch**: derived search index (BM25 + dense vector hybrid).
- **Neo4j**: derived relationship graph (refines, overrides, conflicts_with, depends_on, derives_from, succeeds).

If they disagree, **Postgres wins** and the derived stores are rebuilt via reconciler scripts.

---

## 5. Domain Model

### 5.1 The `Rule` Entity

A rule is the central first-class object. It is **not** a regex or a code expression; it is a structured envelope around a natural-language statement.

| Field | Description |
|---|---|
| `id` | Stable identifier |
| `statement` | The rule text in natural language (the canonical form, source of truth) |
| `language` | Language code (e.g., "en", "ja") |
| `translation_group_id` | Links to semantically equivalent rules in other languages |
| `kind` | Rule kind: NORMATIVE / COMPUTATIONAL / PROCEDURAL / DEFINITIONAL / PRINCIPLE |
| `evaluation_spec` | Kind-specific evaluation metadata (e.g., expression for computational rules) |
| `source_refs` | Pointers to the source document, section, and offset |
| `scope` | Structured scope (see §5.2) |
| `modality` | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `effective_period` | `valid_from` / `valid_until` |
| `preconditions` | Facts required to evaluate the rule |
| `exceptions` | References to other rules or carve-outs |
| `rationale` | Why the rule exists (purpose, intent) |
| `context` | Surrounding document text, section hierarchy, regulatory authority |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `tags` | Free-form taxonomic labels |
| `maturity_level` | EXPERIMENTAL / STABLE / PROVEN |
| `governance` | Owner, approvers, revision history |
| `embedding` | Vector representation (derived) |

The `statement` is always the **source of truth**. Structured fields exist for indexing, filtering, prioritization, and evaluator dispatch — never to override the meaning of the statement.

### 5.2 Multi-Axis Scope

Scope replaces what was previously a flat slash-delimited string. Cross-organizational rules need orthogonal axes:

```python
@dataclass(frozen=True)
class Scope:
    domain: str
        # legal | hr | finance | sales | engineering | communication | operations | research | ...
    org_unit: str | None = None
        # "acme/legal" | "acme/jp/sales/east" | None for organization-wide
    subject_type: str | None = None
        # contract | clause | regulation | employee | expense | quote | code_file | message | ...
    attributes: dict[str, str] = field(default_factory=dict)
        # region, role, employment_class, customer_segment, jurisdiction, ...
```

This enables expressing intersected rules such as *"US managerial employees' expense policy"* without ad-hoc string encoding. Rule selection in the evaluator filters by `(domain, subject_type)` first, then `org_unit` ancestry (via Federation), then attribute intersection.

### 5.3 Rule Kinds

Different rule kinds are evaluated differently. The evaluation core dispatches by `kind`:

| Kind | Examples | Evaluator |
|---|---|---|
| `NORMATIVE` | "Overtime MUST NOT exceed 45h/month" | LLM-as-Judge with the rule statement |
| `COMPUTATIONAL` | "Expense limit is ¥100,000" | Deterministic expression evaluator + LLM intent confirmation |
| `PROCEDURAL` | "Approval requires: estimate → review → sign" | State-transition validator |
| `DEFINITIONAL` | "A 'manager' is an employee with title ∈ {…}" | Lookup / predicate evaluator |
| `PRINCIPLE` | "Customer first" | LLM with high-thinking, applied as soft-weight in normative rule evaluation |

For computational rules, the deterministic layer produces the verdict; the LLM only writes the human-readable reason and confirms intent alignment. This dramatically reduces LLM cost on the high-volume numeric rules typical of HR and finance.

### 5.4 Rule Relationships

Rules form a graph, not a flat list. Relationships are stored in Neo4j:

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision that replaces a prior version |

### 5.5 Meta-Rules

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy"). Meta-rules are evaluated by the same engine but are scoped to govern the rule corpus itself.

### 5.6 Evaluation Subjects

Subjects are what get evaluated. The system models them as a sealed kind hierarchy:

```python
class EvaluationSubject(ABC):
    kind: Literal[
        "code_change",
        "business_event",
        "document_artifact",
        "transaction",
        "communication",
        "decision_request",
    ]
```

| Kind | Use Cases | Typical Source |
|---|---|---|
| `code_change` | Engineering rules vs PR diff | CI, IDE, agent hooks |
| `business_event` | HR rules vs attendance event; sales rules vs deal close | HR system, CRM |
| `document_artifact` | Legal rules vs contract draft; marketing rules vs ad copy | Contract mgmt, marketing tools |
| `transaction` | Finance rules vs expense submission; procurement vs purchase order | Expense, procurement |
| `communication` | Communication norms vs outbound email; PR policy vs press release | Email, Slack |
| `decision_request` | Generic "should I do X?" with context facts | Decision-support agents |

Each kind is handled by a dedicated `SubjectHandler` that normalizes the input, selects relevant rules, builds a kind-specific prompt, and aggregates verdicts.

---

## 6. Components

### 6.1 Rule Management Server

The server is the system of record for all rules.

**Capabilities:**

- **Rule CRUD** with revision history and effective-date semantics.
- **Extraction pipeline** that ingests documents (contracts, regulations, policy PDFs, markdown, text) and proposes candidate rules through a multi-stage process:
  - Structural parsing (PDF → sections) — domain-agnostic.
  - Normative-sentence detection — domain-agnostic.
  - **Domain-specific extraction adapters** — legal (Article/Paragraph hierarchy, reference resolution), HR (employment class scoping), finance (account code mapping), sales (discount tier inference), engineering (CLAUDE.md, linter configs, code patterns).
  - Metadata inference — modality, severity, scope, language.
  - Relationship suggestion — refines, conflicts_with, derives_from candidates.
  - Human review — every candidate is approved before becoming an active rule.
- **Search APIs**: full-text, vector, category/tag, hybrid (BM25 + kNN), **context search** (given facts, find rules), **impact search** (given a rule change, find affected rules).
- **Intent API**: a natural-language endpoint that classifies the user's intent (`lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`) and routes to the appropriate backend.
- **Evaluation engine**: dispatched by subject kind (see §6.4).
- **Submissions API**: the canonical entry point for non-code subjects (see §6.7).
- **Audit log**: append-only, hash-chained record of every evaluation, with full inputs, applied rules, model identity, verdict, and subject kind.
- **Governance**: ABAC-style policies (see §6.10).

### 6.2 Rule Client (Python SDK)

A thin, ergonomic wrapper over the server APIs.

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    # Domain-aware search
    rules = await client.search.hybrid(
        "overtime monthly limit",
        scope={"domain": "hr", "subject_type": "employee"},
    )

    # Natural-language intent
    result = await client.intent.ask(
        "What are the rules for refunding orders over $500?"
    )

    # Rule CRUD
    rule = await client.rules.get("rule_abc123")
    await client.rules.update(rule.id, statement="…", revision_note="…")
```

### 6.3 Agentic Rule Client (Python SDK)

A higher-level client that wraps `RuleClient` and adds capabilities for systems that need to **enforce** rules.

**Added capabilities:**

- **Automatic context gathering**: given an event, pull related facts from surrounding systems before evaluation.
- **Two-stage evaluation**: first narrow the rule set by scope and embeddings, then evaluate the narrow set with the appropriate model.
- **Result caching**: hash-keyed cache, automatically invalidated on rule revision.
- **Reason graphs**: structured DAG of which facts triggered which conditions in which rules.
- **Repair suggestions**: when a subject is denied, propose the minimum modification that would make it compliant.
- **Three integration modes**:
  - `preflight` — block actions before they happen.
  - `posthoc` — batch audit after the fact.
  - `sidecar` — observe in parallel without blocking the primary flow.

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient("http://localhost:8000") as client:
    result = await client.evaluate(
        subject_kind="business_event",
        subject={"event_type": "register_overtime",
                 "payload": {"employee_id": "E001", "hours": 50}},
        actor={"id": "E001", "org_unit": "acme/jp/dev"},
        mode="preflight",
    )
    if result.verdict == "DENY":
        print(result.violations)        # which rules were violated
        print(result.reason_graph)      # why
        print(result.suggested_fix)     # how to comply
```

### 6.4 Evaluation Engine (Subject-Aware Dispatcher)

The evaluation engine is built around a dispatcher that routes by `EvaluationSubject.kind` to a specialized handler. Each handler implements the same interface but with kind-appropriate logic.

```python
class SubjectHandler(Protocol):
    async def normalize(self, subject) -> NormalizedSubject: ...
    async def select_rules(self, normalized) -> list[Rule]: ...
    def build_prompt(self, normalized, rules) -> str: ...
    def aggregate(self, verdicts, rules, normalized) -> EvaluationResult: ...
    @property
    def verdict_schema(self) -> dict: ...
```

**CodeChangeHandler**: existing diff-parsing, file-aware logic. Understands unified diffs, file paths, language detection, function extraction. Returns line-level remediations.

**BusinessEventHandler**: validates structured events (HR action, deal close, employee onboarding) against domain rules. Looks up actor attributes, organizational context.

**DocumentArtifactHandler**: evaluates a document or section against rules. Used for contracts, policy drafts, marketing copy. Returns cited clauses and section-level findings.

**TransactionHandler**: validates monetary transactions (expense, procurement, payment) including amount thresholds, party validation, and approval state.

**CommunicationHandler**: evaluates outbound communications (email, posts, press releases) against communication norms and PR rules.

**DecisionRequestHandler**: a fallback for "should I do X?" with free-form context facts. Used by decision-support agents.

For all handlers, the LLM-call infrastructure (model selection, thinking_level, caching, audit logging) is shared. Handlers own only the prompts, the rule selection strategy, and the aggregation logic. **The LLM provider is interchangeable** through a pluggable Evaluator interface (default: Gemini).

### 6.5 Hybrid Evaluation: Deterministic + LLM

For `COMPUTATIONAL`, `PROCEDURAL`, and `DEFINITIONAL` rule kinds, evaluation begins with a deterministic layer:

- Computational: sandboxed expression evaluation (`asteval` or restricted Python).
- Procedural: state-machine validation.
- Definitional: predicate evaluation against actor/subject attributes.

The LLM then confirms intent alignment ("does the rule's stated intent agree with the deterministic verdict?") and produces the human-readable reason. If they disagree, the verdict becomes `NEEDS_CONFIRMATION`. This pattern reduces cost and latency on the high-volume numeric rules typical of HR and finance, and improves auditability.

### 6.6 Agent Context Delivery (MCP)

Exposes the Rule Repository to AI agents via the Model Context Protocol.

- **MCP Server**: FastMCP with stdio (for Claude Code) and streamable-HTTP (for remote agents) transports.
- **Tools** (core, always available): `search_rules`, `evaluate_compliance`, `evaluate_subject`, `explain_rule`, `find_conflicts`, `get_rules_for_context`.
- **Tools** (optional, behind feature flag): `register_agent`, `get_personalized_rules`, `challenge_verdict`, `request_exception`.
- **Resources**: `rule://{id}`, `ruleset://{scope_query}`.
- **Prompts**: `compliance_check`, `rule_summary`, `impact_analysis`.
- **Rule Formatter**: three output formats — `instructions`, `checklist`, `detailed`.
- **CLAUDE.md Generator**: exports rules as static CLAUDE.md sections for teams not yet on MCP.

### 6.7 Submissions API (Universal Entry Point)

`POST /api/v1/submissions` is the canonical entry for any non-code subject. The legacy `POST /api/v1/evaluate` with a `diff` body remains as a code-specialized convenience wrapper.

```http
POST /api/v1/submissions
Content-Type: application/json

{
  "subject_kind": "business_event",
  "subject": {
    "event_type": "register_overtime",
    "payload": { "employee_id": "E001", "month": "2025-04", "hours": 50 }
  },
  "actor": { "id": "E001", "org_unit": "acme/jp/dev" },
  "intent": "register_overtime",
  "mode": "preflight"
}
```

The response is identical in shape to `/api/v1/evaluate`, with verdict, violations, reason graph, and suggested fixes.

### 6.8 Domain Packs

A Domain Pack is a self-contained extension that adds knowledge of one functional domain (legal, HR, finance, sales, engineering, etc.) without modifying the core.

```
packages/domain-packs/
├── legal/
│   ├── pack.yaml            # manifest, metadata schema extensions
│   ├── prompts/             # domain-specific extraction & evaluation prompts
│   ├── analyzers/           # legal-specific structural parsers (Article/Paragraph)
│   ├── templates/           # YAML rule templates by jurisdiction
│   ├── samples/             # sample documents for testing
│   └── ui_hints.yaml        # persona-specific labels, glossary, default filters
├── hr/
├── finance/
├── sales/
└── engineering/             # the existing engineering implementation, repackaged
```

`pack.yaml` declares:

- Display names (multilingual).
- Metadata extensions (e.g., `jurisdiction` for legal, `employment_class` for HR).
- Default subject types and rule kinds.
- Extraction strategy hints (hierarchical structure, reference resolution).

The server discovers and loads packs at startup. The core (Subject Handlers, Search, Federation, etc.) stays domain-agnostic; pack-specific behavior is injected through registered prompts, analyzers, and metadata schemas.

### 6.9 Persona-Aware Frontend

The frontend serves multiple personas, each with their own home dashboard, default filters, navigation, and terminology:

- **Legal Counsel**: contract review queue, clause comparison, statute graph, jurisdiction filter.
- **HR Manager**: policy browser, attendance alerts, employment class views.
- **Finance Manager**: expense review queue, tax compliance, account code mapping.
- **Sales Manager**: quote review, discount approval, price tier check.
- **Engineer**: code-aware evaluation, PR review, rule playground (code mode).
- **Compliance Officer**: cross-domain dashboards, audit trail, risk overview.

A persona switcher in the top navigation determines:

- Which home dashboard renders.
- Default search scopes (filtered by `Scope.domain`).
- Sidebar navigation items.
- Terminology localization.

Shared components (RuleCard, SearchBox, RuleGraph, etc.) are persona-agnostic.

### 6.10 Governance (ABAC)

Authorization uses attribute-based policies, separate from but cooperating with Federation:

```python
class Policy:
    domain: str | None         # "legal" or None for cross-domain
    org_unit: str | None       # "acme/legal" or None
    action: Literal["rule.read", "rule.evaluate", "rule.propose",
                    "rule.approve", "rule.edit", "rule.retire"]
    principals: list[Principal]  # group:legal-team, role:approver, user:U123
```

A principal is allowed action A on rule R iff there exists a Policy P where:
- `P.action == A`
- `P.domain` is None or matches `R.scope.domain`
- `P.org_unit` is None or is an ancestor of `R.scope.org_unit`
- The principal is in `P.principals`

This expresses "Engineering team can read Legal rules but only Legal Approvers can approve them," and similar cross-functional access patterns.

Federation continues to manage hierarchical rule inheritance. ABAC manages authorization. They are orthogonal layers.

### 6.11 Federation

Hierarchical rule composition across organizational boundaries. Federation nodes are identified by `(domain, org_unit)` tuples.

- Organization rules apply to all teams and projects in that organization.
- Team rules apply to all projects in the team.
- Project rules apply only to that project.
- Each level can override an inherited rule.

When the rule selector resolves applicable rules for a scope, it walks the Federation ancestor chain, collects rules from all levels, and applies overrides.

### 6.12 Rule Intelligence

Analytics, health scoring, and automated improvement recommendations — segmented by domain.

- **Health Scorer**: per-rule score (0–100) across 6 dimensions — completeness, clarity, test coverage, freshness, activity, owner engagement.
- **Evaluation Analytics**: corpus-wide and per-rule metrics from the evaluations table — fire rate, deny rate, latency, trends, all segmented by `Scope.domain`.
- **Effectiveness Score**: composite of precision, prevention rate, and adoption rate per rule.
- **Recommender**: automated suggestions — retire dormant rules, clarify ambiguous ones, escalate persistent violations.
- **Per-Domain Quality Metrics**: Faithfulness, Atomicity, Modality Accuracy, Context Coverage, Conflict Discovery Yield — reported per domain.

### 6.13 Rule Playground & Testing

Interactive sandbox and regression testing.

- **Playground**: `POST /api/v1/playground/evaluate` accepts a draft rule statement + sample subject (code, scenario, document, transaction) and returns a verdict without persisting.
- **Per-Rule Test Cases**: each rule can have test cases (subject + expected verdict). Test cases can be manually created, auto-generated from historical evaluations, or generated by the LLM from the rule statement.
- **Test Runner**: executes all test cases against a rule, reports pass/fail.
- **Frontend**: split-pane editor for rule statement and subject; results panel with verdict and reasoning.

### 6.14 Automatic Rule Discovery

Solves the cold-start problem by discovering rules that already exist implicitly in a project's artifacts.

- **Engineering source analyzers**: CLAUDE.md parser, linter config parser, code pattern analyzer.
- **Legal/HR/Finance/Sales source analyzers** (via Domain Pack): regulation parser, policy document parser.
- **Pattern Detector**: frequency analysis and deduplication across sources.
- **Candidate Generator**: Gemini-powered refinement of raw patterns into structured rule candidates.
- **Human Review Queue**: all candidates go through approve/edit/dismiss workflow.

### 6.15 Correction Feedback Loop

Captures human corrections and converts them into rule improvements. Per-domain.

- **Correction Capture**: passive (compares delivered rules with subsequent human edits) and active (agent hooks).
- **Correction Analyzer**: classifies each correction as `new_rule`, `improve_existing`, or `adjust_scope`.
- **Candidate Generation**: clusters corrections and auto-drafts rule proposals via LLM.
- **Approved proposals start in shadow mode** (maturity = experimental) and graduate via the auto-promotion worker.

### 6.16 Snapshots and Environment Deployment

Versioned snapshots of the rule corpus with environment-based deployment and impact simulation.

- **Snapshots**: immutable frozen copies of all rules matching a scope filter at a point in time.
- **Environment Deployment**: deploy a snapshot to `production`, `staging`, or `development`. Only one active deployment per environment.
- **Rollback**: reactivate the previous deployment for an environment.
- **Impact Simulation**: replay historical evaluations against a proposed snapshot to show what would have changed.

### 6.17 Proposals

Structured change management for rules.

- Create proposals (add, modify, retire, merge, split).
- Assign reviewers, collect multi-approver votes.
- Threaded comments with inline suggestions.
- Automated conflict analysis and impact preview before enactment.
- Notifications to scope owners.

---

## 7. Key Features

### 7.1 Cross-Organizational Foundations

- Natural-language rule storage with full provenance to source documents.
- Multi-axis structured scope (domain × org_unit × subject_type × attributes).
- Rule kind taxonomy with kind-appropriate evaluators.
- Five subject kinds (code change, business event, document artifact, transaction, communication) with dedicated handlers.
- Domain Pack architecture for adding new functional domains without core changes.
- Persona-aware frontend with five default personas.

### 7.2 Differentiating

- **Hybrid Evaluation**: deterministic verification for computational/procedural/definitional rules, LLM for normative/principle rules.
- **Polyglot Rules**: semantically-linked rule pairs across languages, continuously verified.
- **Provenance Lineage**: tracks the chain Law → Internal Policy → Department Rule → Contract Clause; upstream changes propagate downstream.
- **Conflict Detector**: continuous scanning for `conflicts_with` candidates across the corpus.
- **Counterexample Generator**: for each rule, minimal compliant and non-compliant examples as regression tests.
- **Rule Coverage**: identifies dormant rules and over-triggered rules.
- **Change Impact Simulator**: replays historical events against a proposed rule revision.
- **Refinement Feedback Loop**: human corrections drive rule rewrite proposals.
- **Why API**: multi-level rationale for any verdict, traversing `rationale` and `source_refs`.
- **Rule Tutor**: LLM-powered conversational interface explaining relevant rules to new team members.
- **Automatic Rule Discovery**: per-domain analyzers bootstrap rules from existing documents and code.

### 7.3 Cross-Cutting

- Immutable audit log with hash-chained integrity, recording subject kind.
- Tiered LLM strategy: small/fast models for screening, large/accurate for high-severity; deterministic for numeric rules.
- PII sanitization on inputs and masking on logs.
- ABAC governance separating editorial authority by domain.
- Per-domain quality metrics in the Intelligence view.

---

## 8. Use Cases

These five use cases form the **acceptance test for v1**. The first four are new capabilities; the fifth is a regression-test of existing engineering support.

### 8.1 Finance — International Travel Expense Review

The finance system submits each expense reimbursement request. The Rule Repository holds the travel policy and entertainment expense policy. Evaluation in `preflight` mode returns DENY for an over-cap submission, with reasons "amount exceeds upper limit" and "international travel requires pre-approval." The repair suggestion proposes splitting the expense or attaching pre-approval documentation.

- Subject kind: `transaction`
- Domain pack: `finance`
- Templates: `finance-expense-jp`

### 8.2 Legal — Contract Clause Review

The contract management system stores contracts under negotiation. The Rule Repository holds internal procurement policy, anti-corruption policy, and prior contract clauses. When a new draft is registered, evaluation in `posthoc` mode highlights clauses that conflict with internal policy or contradict prior contracts, with NEEDS_CONFIRMATION verdicts and cited clauses.

- Subject kind: `document_artifact`
- Domain pack: `legal`
- Templates: `legal-contracts-jp`

### 8.3 HR — Attendance / Overtime Registration

The HR system submits each attendance event. The Rule Repository holds work regulations, the 36-agreement, and overtime policy. Evaluation in `preflight` mode validates each registration against the legal cap, returns DENY for violations with legal citations, and proposes corrections (reduce hours, file an exception, or apply the 36-agreement special clause).

- Subject kind: `business_event`
- Domain pack: `hr`
- Templates: `hr-attendance-jp`

### 8.4 Sales — Quote Discount Approval

The CPQ system submits each quote. The Rule Repository holds the sales pricing policy and antitrust guidance. Evaluation returns ALLOW when the discount is within the standard cap, NEEDS_CONFIRMATION when within the special-approval range, and DENY when outside policy or potentially anti-competitive.

- Subject kind: `document_artifact`
- Domain pack: `sales`
- Templates: `sales-pricing-jp`

### 8.5 Engineering — PR Code Review

CI pipelines submit each PR diff. The Rule Repository holds engineering standards. Evaluation returns per-rule verdicts with line-level remediations. AI coding agents receive applicable rules through MCP and write conforming code from the start. Corrections feed the flywheel.

- Subject kind: `code_change`
- Domain pack: `engineering`
- Templates: `python-fastapi`, `typescript-react`, `security-owasp`, `api-design`, `testing-standards`

### 8.6 Beyond v1

The same architecture supports communications review (outbound press release vs PR policy), research compliance (research protocol vs ethics review), and any other domain where natural-language rules govern an organizational activity. Adding a new domain is a Domain Pack contribution, not a core change.

---

## 9. Technical Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash (`gemini-3-flash-preview`) + Gemini 3.1 Pro (`gemini-3.1-pro-preview`) via `google-genai`; pluggable provider interface |
| Document parsing | Gemini File API with `media_resolution_medium` for PDFs; native text for markdown/txt |
| Relational store | PostgreSQL 17 |
| Search | Elasticsearch 8.17 (BM25 + dense vector hybrid) |
| Graph store | Neo4j 5 (rule relationships) |
| Job queue | arq + Redis 7 |
| Audit log | Append-only Postgres table with hash chain |
| Sandbox expression | `asteval` for computational rule deterministic evaluation |
| Local orchestration | Docker Compose (8 services) |

The LLM provider is intentionally abstracted. The `Evaluator` interface accepts any model that can perform structured judgment.

---

## 10. Roadmap

The project has four delivered phases (v0) and one in-progress generalization phase (v1).

### 10.1 v0 — Delivered Foundations

The following capabilities are in the codebase and operational:

| Capability | Status |
|---|---|
| Rule storage, search (5 modalities), document extraction | Delivered |
| Code-Aware evaluation engine (batched, with conflict resolution, remediations) | Delivered |
| MCP server with 12 tools | Delivered |
| Discovery (CLAUDE.md, linter configs, code patterns, GitHub import) | Delivered |
| Federation (org → team → project) | Delivered |
| Snapshots (versioned rule sets) | Delivered |
| Playground (sandbox + test cases) | Delivered |
| Maturity model (experimental → stable → proven) with shadow mode | Delivered |
| Structured remediations | Delivered |
| Correction feedback loop with auto-drafting | Delivered |
| Health scoring, effectiveness, weekly digest, team comparison | Delivered |
| Proposals (lifecycle, voting, comments) | Delivered |

### 10.2 v1 — Cross-Organizational Generalization (In Progress)

The current sprint focus. v1 makes the system genuinely cross-organizational by generalizing the core.

**Architectural changes:**
- Introduce `EvaluationSubject` abstraction (five subject kinds).
- Replace flat `scope` with multi-axis structured `Scope`.
- Introduce `RuleKind` taxonomy with kind-aware evaluators.
- Introduce Domain Pack architecture; package existing engineering capability as `engineering` pack.
- Introduce hybrid evaluation (deterministic + LLM).
- Introduce ABAC governance.
- Introduce persona-aware frontend with five personas.
- Introduce polyglot rule support.

**Capability additions:**
- Submissions API for non-code subjects.
- Four non-engineering rule templates: `legal-contracts-jp`, `hr-attendance-jp`, `finance-expense-jp`, `sales-pricing-jp`.
- Per-domain quality metrics in the Intelligence view.
- Domain-specific extraction adapters for legal, HR, finance, sales.

**Migration approach (additive-then-deprecating):**
- Phase A: additive — new abstractions added alongside existing. All 212 existing tests pass.
- Phase B: parallel operation — non-code handlers operational, four new templates ship, five validation scenarios green.
- Phase C: deprecation — legacy `scope: str` and `diff`-shaped evaluate signature removed in v2.

**v1 Acceptance Criteria** are documented in §11.

### 10.3 v1.1 — Polish (After v1)

- Full polyglot rule sync verification.
- Statute citation modeling for legal rules.
- Conflict detector continuous scanning enhancement.
- Verdict drift detection (temporal, model, semantic).
- Additional domain packs (communication, research, operations).
- Frontend onboarding wizards per persona.

### 10.4 Frozen Features

The following are implemented in the codebase but disabled by default via feature flags. They are preserved (not deleted) to allow future re-activation, but are not part of v1.

| Feature | Reason for Freeze |
|---|---|
| Marketplace (rule packages, publish/subscribe, composition conflicts) | Out of scope per current direction (local-only operation) |
| Gateway external webhooks (GitHub, Slack, generic ingestion) | Out of scope per current direction |
| GitHub App PR review integration | Should be one integration of many, not a central pillar |
| Autonomous agent governance loops (trust auto-promotion, multi-agent sessions, verdict negotiation) | Compounds engineering bias; complicates core generalization |
| Weekly digest external delivery | Observability beyond essentials |
| Team comparison dashboard | Observability beyond essentials |

Frozen tables are migrated to a `frozen` Postgres schema. Frozen routers, MCP tools, and frontend pages are gated by `FEATURE_*_ENABLED` flags, all defaulting to off.

---

## 11. Success Metrics

### 11.1 v1 Acceptance Metrics

| Metric | Target |
|---|---|
| Subject kinds operational | 5 (code_change, business_event, document_artifact, transaction, communication) |
| Domain packs operational | 5 (legal, hr, finance, sales, engineering) |
| Non-engineering templates | At least 4 (legal-contracts-jp, hr-attendance-jp, finance-expense-jp, sales-pricing-jp) |
| Frontend personas | At least 5 (legal, hr, finance, sales, engineering) |
| Validation scenarios passing | All 5 (§8.1–§8.5) |
| Extraction Faithfulness per domain | ≥ 70% on 20+ documents per domain |
| Test count | ≥ 350 |
| Existing engineering regression | 212 prior tests pass |

### 11.2 Operational Metrics

- **Coverage**: percentage of rules in target source documents successfully extracted and registered. Reported per domain.
- **Latency**: p50 / p95 / p99 evaluation latency by subject kind.
- **Accuracy**: human-rated correctness of verdicts on a held-out test set; precision and recall on conflict detection.
- **Adoption**: number of integrated systems and active rules; evaluation volume per day, per subject kind, per domain.
- **Governance Health**: percentage of rules with complete metadata, current rationale, active owners.
- **Time-to-comply**: median time between source-law amendment and corresponding internal rule revision approval.
- **Shadow-to-enforcement Rate**: >70% of experimental rules reach stable within 60 days.
- **Flywheel Throughput**: rules/month auto-drafted from correction clusters per domain.
- **Auto-fix Rate**: percentage of SHOULD violations auto-fixed via structured remediations (engineering only).

### 11.3 Quality Metrics Per Domain

Reported in the Intelligence view, segmented by `Scope.domain`:

- **Faithfulness**: extracted rules' semantic alignment with source.
- **Atomicity**: rate of single-norm rules.
- **Modality Accuracy**: MUST/SHOULD/MAY classification accuracy vs source.
- **Context Coverage**: % of rules with non-empty `context` field.
- **Conflict Discovery Yield**: conflicts detected per 100 extracted rules.

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Generalization breaks existing engineering features | Strict regression-test gate; `CodeChangeHandler` is existing logic moved, not rewritten. Additive migration strategy. |
| Non-engineering extraction quality remains low | Per-domain quality metrics gate v1 release; iterate with domain experts on prompts. |
| LLM verdicts are non-deterministic and may be wrong | Always log full evaluation context; require human review on high-severity denials; consensus voting for CRITICAL rules; refinement feedback loop. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity; refinement loop suggests rewrites; per-rule test cases. |
| LLM costs scale poorly with rule corpus size | Two-stage evaluation (metadata pre-filter, then LLM); aggressive caching; tiered model selection; deterministic layer for computational rules. |
| Sensitive data leaks through evaluation context | Input sanitization; log masking; ABAC isolation; option for self-hosted LLM. |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via effective_period; shadow mode for new rules; environment snapshots. |
| Over-reliance reduces human judgment | Position the system as decision support; preserve rationale visibility; require human approval for rule revisions. |
| Domain Pack abstraction over-engineered | Start with two pack hooks (metadata extensions, prompts); expand only as concrete needs arise. |
| Multi-axis scope migration produces inconsistent data | One-shot scripted migration with review step; old column retained during transition for rollback. |
| Hybrid evaluation introduces disagreement between layers | Treat disagreement as NEEDS_CONFIRMATION; never silently override LLM with deterministic. |
| Persona splitting overwhelms a small frontend team | Phase B introduces persona dirs as skeletons; only Engineering is fully populated initially. |

---

## 13. Glossary

- **Rule**: a natural-language normative statement plus structured metadata, managed as a first-class object.
- **Statement**: the canonical natural-language text of a rule (the source of truth).
- **Rule Kind**: the type of evaluation a rule requires (NORMATIVE, COMPUTATIONAL, PROCEDURAL, DEFINITIONAL, PRINCIPLE).
- **Modality**: the strength of the obligation (MUST, MUST_NOT, SHOULD, MAY, INFO).
- **Scope**: structured multi-axis applicability (domain, org_unit, subject_type, attributes).
- **EvaluationSubject**: what gets evaluated. One of six kinds: code_change, business_event, document_artifact, transaction, communication, decision_request.
- **SubjectHandler**: the kind-specific logic in the evaluation engine for normalizing, selecting rules, prompting the LLM, and aggregating verdicts.
- **Domain Pack**: a plugin that adds knowledge of one functional domain (legal, HR, finance, sales, engineering) — its metadata extensions, prompts, analyzers, and templates.
- **Verdict**: the result of an evaluation (ALLOW, DENY, NEEDS_CONFIRMATION).
- **Reason Graph**: a structured DAG explaining which facts triggered which conditions in which rules.
- **Meta-rule**: a rule whose subject is other rules.
- **Provenance Lineage**: the chain of derivation from a higher-level source (e.g., a law) to operational rules and contract clauses.
- **Preflight / Posthoc / Sidecar**: three modes of integration corresponding to before-action, after-action, and parallel-observation enforcement.
- **LLM-as-Judge**: the architectural pattern of using a large language model to evaluate whether a subject complies with a natural-language rule.
- **Federation**: the org → team → project hierarchy that lets rules cascade with overrides.
- **Persona**: a frontend role (Legal Counsel, HR Manager, Finance Manager, Sales Manager, Engineer, Compliance Officer) with its own dashboard, defaults, and terminology.

---

## 14. Open Questions

1. **Canonical domain enumeration**: should `Scope.domain` be a constrained enum or free-form? Current recommendation: a constrained core set (legal, hr, finance, sales, engineering, communication, operations, research) with the ability to register custom domains via Domain Pack.

2. **Subject type taxonomy**: how is `subject_type` enumerated across domains? Recommendation: each Domain Pack declares its supported subject types; subjects with unknown types are rejected unless explicitly permitted.

3. **Federation-Scope alignment**: Federation nodes are `(domain, org_unit)` tuples; a rule's `scope.org_unit` references a Federation node id. Confirmed.

4. **Subject kind in audit log**: yes — the audit log records the subject kind for cross-domain analytics.

5. **Reclassification of existing rules**: migration assigns all existing rules to `domain=engineering`. Users can re-classify in bulk through a frontend wizard.

6. **Statute citation modeling for legal rules**: defer to v1.1.

7. **Multi-language extraction quality**: track `Faithfulness × language` as a second dimension.

8. **Deterministic layer aggressiveness**: only for explicit `kind=computational` rules with an `evaluation_spec.expression`. Normative and principle rules remain LLM-judged.

9. **External data dependencies**: how should rules that depend on external lookups (approved vendor lists, exchange rates) be modeled? Open for v1.1.

10. **Multi-tenant isolation**: deferred. Single-tenant local deployments through v1.

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes should follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect.*
