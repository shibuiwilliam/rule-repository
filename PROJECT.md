# Rule Repository

> A software platform for managing, searching, serving, and enforcing natural-language rules — laws, contracts, internal policies, engineering guidelines, communication standards, and documentation conventions — across departments using LLMs and AI agents.

---

## 1. Project Overview

The **Rule Repository** is a system that stores human-authored rules in their original natural-language form and makes them operationally useful: searchable, applicable, and enforceable across business systems and software development environments. Where traditional rule engines require translating human rules into a formal language (and losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs and AI agents to interpret, search, and enforce them at runtime.

This approach is inspired by, and generalizes, the concept of **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea in **four** directions:

- **Wider scope of rules**: not only AI agent guardrails, but laws, contracts, HR policies, financial rules, sales communication standards, engineering rules, and documentation conventions.
- **Wider scope of consumers**: human users (in any department), business systems, IDEs, CI pipelines, and AI agents.
- **Wider scope of time**: pre-flight checks, post-hoc audits, and continuous compliance monitoring.
- **Wider scope of subjects**: the system evaluates not only code changes but also document drafts, business transactions, communications, and workflow steps as first-class evaluation subjects.

The product positioning is a **Cross-Organizational Rule Platform**: a single system where Legal, HR, Finance, Sales, Engineering, IT, General Affairs, Compliance, and Executive teams co-manage their respective rules under one governance fabric, while keeping department-level ownership intact.

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository fills a gap that no current category of software addresses cleanly:

- **Document management systems** store the source documents but do not understand the rules inside them.
- **Rule engines (Drools, DMN, OPA)** require formal encoding and lose the original semantics.
- **GRC platforms** track compliance status but do not enforce rules at the point of action.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.
- **Department-specific tools** (CLM for legal, expense systems for finance, HRIS for HR) handle their own rules but cannot cross-reference each other — and an HR rule that affects a contract clause has no shared substrate.

The Rule Repository treats **rules themselves as first-class, versioned, governed, department-owned assets**, decoupled from any single consumer and reusable across the entire organization.

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Store rules in natural language, with full traceability to their source documents and clause-level provenance.
- Provide rich search (full-text, vector, category, hybrid, intent-based) over rule corpora.
- Enable runtime evaluation against **multiple subject types**: code changes, document drafts, business transactions, communications, and workflow steps.
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Detect conflicts, redundancies, and dead rules across the corpus, including across departments.
- Make rule provenance, rationale, department ownership, and revision history first-class.
- Provide ergonomic SDKs so business systems and AI agents can integrate easily.
- Provide an end-user-facing **Conversational Rule Assistant** so non-technical staff can ask "is this allowed?" in natural language.
- Run fully on a single local stack (Docker Compose) without external SaaS dependencies beyond the Gemini API key.

### 3.2 Non-Goals

- Replacing IAM, RBAC, ABAC, or network-layer access control. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel or compliance officers. The system surfaces issues; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts on behalf of users.
- **Operating as a connector hub** to SaaS products. Integration with external business systems is the integrating system's responsibility — they push events to the Rule Repository, not the other way around.

---

## 4. Architecture

The system is composed of three top-level components:

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                         │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ Extraction  │  │   Search     │  │  Subject Evaluation Engine │ │
│  │ Pipeline    │  │   (FT/Vec/   │  │  ┌───────────────────────┐ │ │
│  │  + Domain   │  │   Cat/Hyb)   │  │  │ Code Path             │ │ │
│  │  Extractors │  │              │  │  │ Document Path         │ │ │
│  └─────────────┘  └──────────────┘  │  │ Transaction Path      │ │ │
│                                      │  │ Communication Path    │ │ │
│  ┌─────────────┐  ┌──────────────┐  │  │ Workflow Path         │ │ │
│  │ Discovery   │  │  Rule Store  │  │  │ Agent-Action Path     │ │ │
│  │  Engine     │  │  (PG+ES+     │  │  └───────────────────────┘ │ │
│  │  + Sources  │  │   Neo4j)     │  └────────────────────────────┘ │
│  └─────────────┘  └──────────────┘                                  │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ Governance  │  │  Compliance  │  │  Conversational Assistant  │ │
│  │  + RBAC     │  │  Cockpit     │  │  (Intent + Why + Tutor)    │ │
│  │  + Federation│ │              │  │                            │ │
│  │  + Department│ │              │  │                            │ │
│  └─────────────┘  └──────────────┘  └────────────────────────────┘ │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │ Intelligence│  │  Business    │  │  Context Delivery (MCP)    │ │
│  │  & Feedback │  │  Event       │  │  + Smart Rule Selection    │ │
│  │  Loop       │  │  Ingestion   │  │  + Polyglot Resolution     │ │
│  └─────────────┘  └──────────────┘  └────────────────────────────┘ │
│                                                                      │
│  ┌─────────────┐                                                    │
│  │ Audit Log   │                                                    │
│  │ (hash-      │                                                    │
│  │  chained)   │                                                    │
│  └─────────────┘                                                    │
│                                                                      │
│ REST│Intent│Evaluate│EvaluateDocument│EvaluateTransaction│Events    │
└────┬───────────┬───────────┬────────────────┬────────────┬─────────┘
     │           │           │                │            │
  ┌──▼──────┐ ┌──▼──────┐ ┌──▼─────────┐ ┌────▼────────┐ ┌─▼─────────┐
  │  Rule   │ │ Agentic │ │    MCP     │ │  CLI Tools  │ │ Frontend  │
  │ Client  │ │ Client  │ │  Server    │ │  (CI/hooks) │ │ Operator  │
  │  SDK    │ │  SDK    │ │  (agents)  │ │             │ │ + Assist. │
  └─────────┘ └─────────┘ └────────────┘ └─────────────┘ └───────────┘
       │           │            │              │              │
       ▼           ▼            ▼              ▼              ▼
   Business     HR / Legal    Claude Code    CI pipelines  Department
   systems      systems       + any MCP      (GH Actions)  end users
   (any domain) (transaction) agent          (engineering)  (legal/HR/
                                                            finance/...)
```

### 4.1 Trust and Data Boundaries

- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and judgments they are authorized to see, filtered by **department membership** (§5.7) and federation hierarchy (§6.14).
- All evaluation calls produce immutable audit records on the server side.
- All external delivery (notifications, alerts, digests) is replaceable with internal storage in local-first mode.

### 4.2 Optional / Frozen Components

The following components exist in the codebase but are **disabled by default** under the Cross-Organizational direction. They remain in code for future re-enablement but are not part of the supported surface:

- **Multi-Agent Governance Sessions** — disabled via `MULTI_AGENT_SESSIONS_ENABLED=false`. Single-agent profile, personalized rules, trust levels remain active.
- **GitHub App webhook receiver** — disabled via `GITHUB_APP_ENABLED=false`. CLI tools (`rulerepo-check`) for CI integration remain active.
- **External webhook normalizers** (Slack, GitHub) — only the generic normalizer is active by default.

See §11 for the full freeze policy.

---

## 5. Domain Model

### 5.1 The `Rule` Entity

A rule is the central first-class object. It is **not** a regex or a code expression; it is a structured envelope around a natural-language statement.

| Field | Description |
| --- | --- |
| `id` | Stable identifier |
| `statement` | The rule text in natural language (the canonical form, in `primary_language`) |
| `primary_language` | Language code of `statement` (e.g., `ja`, `en`) |
| `translations` | Map of language code → translated statement; semantic equivalence verified periodically |
| `equivalence_verified_at` | When translations were last re-verified against the primary statement |
| `source_refs` | Pointers to the source document, section path (`clause:3.2.1`, `第36条第2項`), and offset |
| `scope` | Who/what the rule applies to (org units, roles, systems, regions, business processes) |
| `department` | Owning department (legal/hr/finance/sales/engineering/it/ga/compliance/exec/public) |
| `modality` | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `kind` | Taxonomic axis: mandatory / guideline / template / informational / meta |
| `effective_period` | `valid_from` / `valid_until` |
| `preconditions` | Facts required to evaluate the rule |
| `exceptions` | References to other rules or carve-outs |
| `rationale` | Why the rule exists (purpose, intent) |
| `context` | Surrounding document text, section hierarchy, regulatory authority |
| `following_examples` | Concrete examples of compliant behavior from the source |
| `violation_examples` | Concrete examples of non-compliant behavior from the source |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `confidence_required` | Minimum LLM confidence below which verdicts become `NEEDS_CONFIRMATION` |
| `applicable_subject_types` | Subject types this rule can be evaluated against (e.g., `[document_draft, code_change]`) |
| `tags` | Free-form taxonomic labels |
| `governance` | Owner, approvers, revision history |
| `maturity_level` | EXPERIMENTAL / STABLE / PROVEN |
| `embedding` | Vector representation (derived) |

The `statement` is the **source of truth**. Structured fields exist for indexing, filtering, and prioritization — never to override the meaning of the statement.

### 5.2 Rule Relationships

Rules form a graph, not a flat list. Modeling these relationships explicitly is what turns the repository from a list into a **provenance and impact graph**.

| Relationship | Meaning |
| --- | --- |
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision that replaces a prior version |
| `cross_references` | A rule from one department references a rule from another (e.g., a contract clause rule references the procurement policy) |

### 5.3 Meta-Rules

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy"). Meta-rules are evaluated by the same engine but are scoped to govern the rule corpus itself.

### 5.4 Evaluation Subject

Evaluation accepts a polymorphic `Subject` rather than a fixed code-change input. This is the load-bearing abstraction that lets the system evaluate diverse artifacts uniformly.

```python
class SubjectType(StrEnum):
    CODE_CHANGE   = "code_change"     # unified diff + files (existing path)
    DOCUMENT_DRAFT = "document_draft" # contract, email, minutes, proposal, press release, report
    TRANSACTION   = "transaction"     # expense, purchase order, payroll, attendance
    COMMUNICATION = "communication"   # Slack post, outbound email, public statement
    WORKFLOW_STEP = "workflow_step"   # an approval step in a chain
    DATA_RECORD   = "data_record"    # master data update, customer record change
    AGENT_ACTION  = "agent_action"   # an AI agent's candidate action
```

```python
@dataclass(frozen=True)
class EvaluationSubject:
    type: SubjectType
    payload: dict           # type-specific structure (CodeChangeSubject, DocumentDraftSubject, ...)
    metadata: dict          # language, document format, request ID
    actor: ActorRef         # who initiated (employee ID, agent ID)
    context_facts: dict     # surrounding facts (department, role, amount, history)
```

### 5.5 Business Event

Business systems integrate with the Rule Repository by pushing **business events** to a single ingestion endpoint. The event carries a `Subject` plus correlation metadata.

```python
@dataclass(frozen=True)
class BusinessEvent:
    event_type: str          # "expense.submitted", "contract.draft.created", "attendance.registered"
    actor: ActorRef
    subject: EvaluationSubject
    occurred_at: datetime
    correlation_id: str      # the business system's own ID
    mode: Literal["preflight", "posthoc", "sidecar"]
```

`event_type` resolves to a scope set, which seeds rule selection. The handler dispatches by `subject.type` to the appropriate evaluator.

### 5.6 Polymorphic Remediation

When evaluation produces a denial or warning, it returns one or more `Remediation` items. Remediations are typed:

| Kind | Use |
| --- | --- |
| `code_edit` | Code: replace lines `[start_line, end_line]` with new content |
| `text_rewrite` | Document: replace span `[offset_start, offset_end]` with new text |
| `field_change` | Transaction: change a specific field (e.g., reduce expense amount to limit) |
| `approval_add` | Workflow: insert an additional approver |
| `process_reroute` | Workflow: route through a different process (e.g., purchase RFQ instead of direct order) |
| `clarification` | Document: insert a missing required disclosure or qualifier |
| `block` | Not auto-fixable; requires human judgment |

Each kind has typed payload. `auto_applicable=true` is set only when confidence is high and the kind permits unambiguous mechanical fixes.

### 5.7 Department and Membership

A user belongs to one or more **departments**, each with one or more roles.

```python
class Department(StrEnum):
    LEGAL = "legal"
    HR = "hr"
    FINANCE = "finance"
    SALES = "sales"
    ENGINEERING = "engineering"
    IT = "it"
    GENERAL_AFFAIRS = "ga"
    COMPLIANCE = "compliance"
    EXEC = "exec"
    PUBLIC = "public"   # readable by everyone

class DepartmentRole(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    APPROVER = "approver"
    OWNER = "owner"
```

A rule has a single owning `department`. Authorization is enforced at API and service layers:

- Listing/searching rules: filtered by caller's `viewer` membership.
- Editing a rule: requires `editor` in that rule's department.
- Approving / enacting a proposal: requires `approver` in that rule's department.
- Evaluating: only rules visible to the caller participate.

`Department` is **orthogonal** to Federation (§6.14). Federation governs vertical inheritance (org → team → project); Department governs horizontal ownership (which function maintains the rule).

---

## 6. Components

### 6.1 Rule Management Server

The server is the system of record for all rules.

**Capabilities:**

- **Rule CRUD** with revision history and effective-date semantics.
- **Extraction pipeline** with **domain-specific extractors** (§6.12) that ingest contracts, regulations, handbooks, minutes, and tabular data.
- **Search APIs**:
  - Full-text search
  - Vector search (semantic similarity)
  - Category/tag/department search
  - Hybrid search (BM25 + vector reranking)
  - Context search: given a body of facts, return applicable rules
  - Impact search: given a proposed rule change, return affected rules
- **Intent API**: a natural-language endpoint that classifies the user's intent and routes to the appropriate backend.
- **Subject Evaluation Engine** (§6.4): given a `Subject` + relevant rules, returns a verdict with reason graph and polymorphic Remediations.
- **Audit log**: append-only, hash-chained record of all evaluations including inputs, applied rules, model identity, and verdict.
- **Governance**: department-aware role-based access (§5.7), revision approval workflow, effective-date scheduling, federation hierarchy.

### 6.2 Rule Client (Python SDK)

A thin, ergonomic wrapper over the server APIs.

```python
from rulerepo import RuleClient

async with RuleClient(server_url="...", api_key="...") as client:
    rules = await client.search.hybrid("overtime monthly limit", scope="hr/attendance")
    answer = await client.intent.ask("What are the rules for refunding orders over $500?")
    rule = await client.rules.get("rule_abc123")
    await client.rules.update(rule.id, statement="...", revision_note="...")
```

### 6.3 Agentic Rule Client (Python SDK)

A higher-level client that wraps `RuleClient` and adds agent capabilities for systems that need to **enforce** rules, not merely query them.

**Added capabilities:**

- **Subject construction helpers**: `client.evaluate.code(...)`, `client.evaluate.document(...)`, `client.evaluate.transaction(...)`.
- **Domain-specific rule retrieval**: `client.get_rules_for_contract(...)`, `client.get_rules_for_transaction(...)`, `client.get_rules_for_communication(...)`.
- **Domain-specific evaluation**: `client.evaluate_contract(...)`, `client.evaluate_transaction(...)`, `client.evaluate_communication(...)`.
- **Surface-aware rule selection**: `client.get_applicable_rules_for_surface(surface, ...)`.
- **Automatic context gathering**: given an event, pull related facts before evaluation (via Context Provider §6.20).
- **Two-stage evaluation**: narrow the rule set by metadata + embeddings, then evaluate the narrow set.
- **Result caching**: hash-keyed cache, automatically invalidated on rule revision.
- **Reason graphs**: structured DAG of which facts triggered which conditions in which rules.
- **Polymorphic Remediation handling**: applies `code_edit` and `text_rewrite` automatically when `auto_applicable`; surfaces `approval_add` and `block` to the calling system.
- **Three integration modes**: `preflight`, `posthoc`, `sidecar`.

### 6.4 Subject Evaluation Engine

The evaluation engine is the core differentiator. It accepts a `Subject` as polymorphic input, maps to relevant rules, and returns verdicts with subject-appropriate remediation.

**Pipeline**: Subject Receipt → Scope Resolution → Rule Selection → Subject-Specific Evaluator → Verdict Aggregation

- **Subject Receipt**: accepts `EvaluationSubject` directly or constructs one from legacy diff/files inputs.
- **Scope Resolution**: maps subject metadata (file paths for code, document type for documents, event type for transactions) to scope tags.
- **Rule Selector**: narrows the corpus to ~5–20 relevant rules via scope/severity/modality/department/applicable_subject_types filtering, then semantic ranking. Runs in <50 ms.
- **Subject Dispatcher**: routes to the path matching `subject.type`:
  - `code_change` → `evaluation/code/` (existing batch evaluator with diff parser, function extractor)
  - `document_draft` → `evaluation/document/` (span-aware text evaluation with text-offset Remediations)
  - `transaction` → `evaluation/transaction/` (field-level evaluation with `field_change` Remediations)
  - `communication` → `evaluation/text/` (free-text evaluation with `text_rewrite` Remediations)
  - `workflow_step` → `evaluation/workflow/` (approval-chain evaluation with `approval_add` Remediations)
  - `agent_action` → `evaluation/agent/` (Semantic-Governance-style guardrail)
- **Tiered model selection**: Flash for LOW/MEDIUM, Flash+medium-thinking for HIGH, Pro+high-thinking for CRITICAL. Uniform across all subject paths.
- **Verdict Aggregator**: combines per-rule verdicts (any DENY → overall DENY) and builds the reason graph + Remediation list.

The shared infrastructure (rule selector, batch evaluator, verdict aggregator, cache, audit log) is **subject-agnostic**. Only prompt templates and Remediation parsing branch by subject type.

### 6.5 Document Evaluation Path

A first-class path for evaluating natural-language documents (contracts, emails, minutes, proposals, press releases, reports).

- **Endpoint**: `POST /api/v1/evaluate/document`
- **Input**: document content (text/markdown), `document_type`, `language`, `scope`, `context_facts`.
- **Prompt**: includes the document type and the rule's `context` and `violation_examples` to anchor judgment.
- **Output**: per-rule verdicts plus **span-level `text_rewrite` Remediations** that point to the offending sentence/clause and propose a compliant alternative.
- **Use cases**: contract clause review, email pre-send screening, press release compliance, performance review language.

### 6.6 Transaction Evaluation Path

A first-class path for evaluating business transactions (expense submissions, purchase orders, attendance registrations, payroll changes, master data updates).

- **Endpoint**: `POST /api/v1/evaluate/transaction`
- **Input**: structured transaction record, `transaction_type`, `actor`, `context_facts` (counterparty, amount, prior history).
- **Prompt**: presents the transaction as structured fields and asks rule-by-rule whether each is compliant.
- **Output**: per-rule verdicts plus `field_change`, `approval_add`, or `process_reroute` Remediations.
- **Use cases**: HR attendance, expense policy enforcement, procurement controls, anti-bribery checks.

### 6.7 Agent Context Delivery (MCP + Smart Rule Selection)

Exposes the Rule Repository to AI coding agents via the Model Context Protocol (MCP). The key innovation is **active context delivery** — rules reach the agent at the right moment without being asked.

- **MCP Server**: FastMCP server with stdio (for Claude Code) and streamable-http (for remote agents) transports.
- **Tools**: `search_rules`, `evaluate_compliance`, `evaluate_document`, `evaluate_transaction`, `explain_rule`, `find_conflicts`, `get_rules_for_context`, plus domain-specific tools: `get_rules_for_contract_review` (legal agents), `get_rules_for_transaction` (finance/HR agents), `get_rules_for_communication` (content/compliance agents), `evaluate_contract`, `evaluate_communication`.
- **Resources**: `rule://{id}` (single rule), `ruleset://{scope}` (dynamic CLAUDE.md section).
- **Prompts**: `compliance_check`, `rule_summary`, `impact_analysis`.
- **Rule Formatter**: three output formats — `instructions`, `checklist`, `detailed`.
- **Scope Registry**: file-glob-to-rule mapping for engineering scopes; **event-type-to-scope mapping** for business event scopes.
- **CLAUDE.md Generator**: exports rules as static CLAUDE.md sections for engineering teams.

### 6.8 Development Workflow Integration

Integration into the places where code is written, reviewed, and merged. Engineering-specific paths are kept as-is.

- **CI Pipeline CLI** (`rulerepo-check`): runs `git diff` → evaluates → exits 0/1/2. Supports `--format text|json|github-actions`.
- **Agent Hooks** (`rulerepo-hook`): `preflight` injects applicable rules before edit; `posthoc` evaluates after edit. Designed for Claude Code hooks.
- **Rule Ingestion** (`rulerepo-ingest`): imports CLAUDE.md and other code-side configs as rule sources.
- **GitHub PR Review (optional)**: webhook receiver, disabled by default, enabled via `GITHUB_APP_ENABLED=true`.

### 6.9 Rule Intelligence

Analytics, health scoring, and automated improvement recommendations.

- **Health Scorer**: per-rule score (0–100) across 6 dimensions — completeness, clarity, **effectiveness** (domain-aware: code=volume, legal=precision, transaction=override-rate), freshness, activity, owner engagement.
- **Evaluation Analytics**: corpus-wide and per-rule metrics from the audit log — fire rate, deny rate, latency, trends, **department-segmented breakdowns**.
- **Recommender**: automated suggestions — retire dormant rules, clarify ambiguous ones, escalate persistent violations, strengthen SHOULD→MUST.
- **Effectiveness Score**: domain-aware measurement — code rules use evaluation volume, legal/document rules use precision against expected deny rate, transaction/event rules use override rate.
- **Rule Status Classification**: `dormant` (no evaluations, active >90 days), `ineffective` (>50% override rate), `over_broad` (>95% ALLOW rate on high volume).
- **Weekly Digest**: compliance trend, rule changes, top violations, attention needed, corrections — delivered to local file by default, optionally to webhook.

### 6.10 Compliance Cockpit

A separate dashboard for Compliance, Legal, and Executive users — distinct from the rule-engineer-oriented Intelligence dashboard.

- **Department violation trends**: deny-rate sparklines per department.
- **Per-policy fire and deny rates**: e.g., labor-law-derived rules, expense rules, anti-bribery rules.
- **Regulatory propagation view**: when a `derives_from`-upstream rule changes, list downstream rules that need review.
- **Action queue**: unapproved proposals, rules with effectiveness < 30, rules dormant > 90 days.
- **Audit summary**: last 30 days of evaluation count, denial count, manual override count.

Implemented as `services/compliance/cockpit.py` and `/compliance` frontend route. Builds on the same data sources as Intelligence; the projection is what differs.

### 6.11 Business Event Ingestion

Single endpoint for business systems to push events for evaluation.

- **Endpoint**: `POST /api/v1/events/ingest`
- **Input**: `BusinessEvent` (§5.5).
- **Behavior**: scope resolution from `event_type` → rule selection → subject dispatch → synchronous verdict + async audit.
- **Modes**: `preflight` blocks; `posthoc` audits; `sidecar` observes without affecting the calling flow.
- **Replaces** the engineering-specific webhook gateway as the cross-organizational ingress. The legacy `/api/v1/gateway/...` endpoints continue to work for engineering use cases but are no longer the primary ingress.

### 6.12 Automatic Rule Discovery

Solves the cold-start problem: instead of requiring humans to write rules from scratch, the system discovers rules that already exist implicitly in a project's artifacts.

- **Source Analyzers**:
  - **Code-side** (existing): `claude_md.py`, `linter_config.py`, `code_patterns.py`, `github_importer.py`.
  - **Business-side (extraction pipeline)**:
    - `contract.py` — extracts clauses from contract PDFs/DOCXs with `Article–Section–Clause` hierarchy.
    - `regulation.py` — handles regulation documents with `第N条/第M項/第L号` (or English equivalent) structure; auto-creates `derives_from` chains.
    - `handbook.py` — employee handbooks and operational manuals.
    - `minutes.py` — meeting minutes; extracts decisions and action items only.
    - `tabular.py` — Excel/CSV tables (expense limits, approval matrices) with one rule per row.
    - `email_archive.py` — past email corpora to discover de-facto patterns.
  - **Cross-domain discovery analyzers** (Phase 8):
    - `contract_corpus.py` — detects common clause patterns across contract corpora; proposes standard-practice rules.
    - `hr_policy.py` — extracts quantitative thresholds from HR handbooks and employment regulations.
    - `expense_guideline.py` — extracts approval matrices, category restrictions, documentation requirements.
    - `communication_standard.py` — extracts tone/voice rules, prohibited language, required disclaimers.
- **Pattern Detector**: deduplication and confidence scoring across sources.
- **Candidate Generator**: Gemini-powered refinement of raw patterns into structured rule candidates.
- **Human Review Queue**: all candidates go through approve/edit/dismiss before becoming active rules.
- **API**: `POST /api/v1/discover/scan` accepts a heterogeneous source list with file paths.
- **MCP Tool**: `discover_rules` — bootstraps rules from any local corpus.
- **Frontend**: `/discover` page with source selector, scan progress, candidate review.

### 6.13 Agent Correction Feedback Loop

Captures human corrections of AI-generated artifacts and converts them into rule improvements, creating a flywheel.

- **Correction Capture**: code-side via merged-PR diff comparison; document-side via revision tracking on draft documents (when supplied by the integrating system).
- **Correction Analyzer**: classifies as `new_rule`, `improve_existing`, or `adjust_scope`.
- **Candidate Generation**: Gemini drafts a rule from correction context.
- **Background Workers**: arq + Redis for clustering, drafting, statistics.
- **Intelligence Integration**: correction trends, top violated rules, coverage gaps, effectiveness metrics.
- **API**: `POST /api/v1/feedback/corrections`, `GET /api/v1/feedback/stats`, approve/dismiss workflow.
- **Frontend**: `/feedback` page; trends in `/intelligence`.

### 6.14 Cross-Project Rule Federation

Hierarchical rule composition across organizational boundaries: organization → team → project. Rules at higher levels automatically apply to all descendants, with project-level overrides.

- **Hierarchy**: organization rules apply to all teams and projects; team rules apply to all projects in the team; project rules apply only to that project.
- **Federation Resolver**: walks the ancestor chain, collects rules, applies overrides.
- **Domain Model**: `RuleFederation` (id, name, level, parent_id, default_scope) and `RuleFederationMembership` (rule_id, federation_id, override_parent_rule_id).
- **Evaluation Integration**: `rule_selector` accepts `federation_id`. When set, rules are resolved through the hierarchy.
- **API**: full CRUD at `/api/v1/federations`, plus `effective-rules` and `diff` endpoints.
- **Frontend**: `/federations` tree view with effective rules and override controls.

### 6.15 Department-Aware RBAC

Enforces department ownership of rules and authorization on every operation.

- **Domain**: `Department` enum (§5.7), `Membership` model linking users to departments with roles.
- **Service**: `services/department/authz.py` with `can_view(user, rule)`, `can_edit(user, rule)`, `can_approve(user, rule)`.
- **Middleware**: applied to all routers; injects the user's effective department set into request context.
- **API**: `/api/v1/departments` for membership management; rule listing/search endpoints respect membership filters.
- **Frontend**: department badge on every rule card; department filter in sidebar; admin-only `/departments` management page.

### 6.16 Rule Playground & Testing Framework

Interactive sandbox and regression testing for rules across all subject types.

- **Playground**: `POST /api/v1/playground/evaluate` accepts a draft rule + sample subject (code, document, or transaction) and returns a verdict without persisting.
- **Per-Rule Test Cases**: each rule has test cases (sample subject + expected verdict). Subject-aware: the test case's `subject_type` matches one of the rule's `applicable_subject_types`.
- **Test Runner**: executes all test cases, compares actual vs expected, reports pass/fail.
- **Test Generator**: subject-specific generators (`test_generator_code.py`, `test_generator_document.py`, `test_generator_transaction.py`) ask Gemini to produce realistic compliant and non-compliant samples.
- **Frontend**: `/playground` with subject-type tabs; Test Cases tab on rule detail page.

### 6.17 Proactive Alert System

Background workers generate alerts when they detect problems during scheduled analysis.

- **Alert Types**: `dormant_rule`, `high_deny_rate`, `health_decline`, `conflict_detected`, `effectiveness_decline`, `language_drift` (polyglot).
- **Alert Lifecycle**: `active` → `acknowledged` → `resolved`.
- **Local-first delivery**: written to the in-app inbox by default. External webhook delivery is opt-in (`ALERT_WEBHOOK_URL`).
- **API**: `GET /api/v1/alerts`, acknowledge, resolve.

### 6.18 Rule Set Snapshots & Environment Deployment

Versioned snapshots of the rule corpus with environment-based deployment and impact simulation.

- **Snapshots**: immutable frozen copies of all rules matching a scope filter at a point in time. JSONB storage in Postgres.
- **Environment Deployment**: deploy a snapshot to `production`, `staging`, or `development`. One active deployment per environment.
- **Rollback**: reactivate the previous deployment.
- **Impact Simulation**: replay historical evaluations against the proposed snapshot.
- **Evaluation Integration**: `evaluate` endpoints accept an `environment` parameter.

### 6.19 Conversational Rule Assistant

End-user-facing chat surface — the entry point for non-technical staff.

- **Frontend**: `/assistant` page with chat UI, inline rule citations, verdict badges, and remediation hints.
- **Backend**: thin orchestrator over Intent API + Why API + Tutor.
- **Capabilities**:
  - Compliance Q&A: "Can I expense JPY 30,000 for entertaining a client?" → answer with rule citations.
  - Pre-flight: "Is this email okay to send?" → paste content, get verdict + suggested rewrites.
  - Tutorial: "Explain HR overtime rules" → walks the user through their department's rules.
- **Department awareness**: assistant filters rules by the user's visible departments and surfaces the most relevant ones first.
- **Multilingual**: respects user language preference and returns answers in that language using polyglot rule translations (§6.21).

### 6.20 Context Provider Abstraction

For evaluation cases where the calling system did not include all necessary facts in `context_facts`, the server can fetch facts via a Provider plugin.

```python
class ContextProvider(Protocol):
    async def fetch(self, subject: EvaluationSubject) -> dict: ...

class StaticFileProvider(ContextProvider):
    """Loads facts from local JSON/CSV (employees.json, approval_matrix.csv)."""

class HttpProvider(ContextProvider):
    """Calls a /facts endpoint hosted by the integrating business system."""
```

Local-first principle: providers are file-based or in-cluster HTTP.

### 6.21 Polyglot Rules

Maintains semantically equivalent rule statements across languages.

- **Domain**: `Rule.primary_language`, `Rule.translations`, `Rule.equivalence_verified_at`.
- **Verification**: weekly cron checks each translation's semantic equivalence against the primary; drift triggers a proposal.
- **Evaluation**: at evaluation time, if the subject language differs from the rule's primary language, use the matching translation; if absent, fall back with a `language_mismatch_warning`.
- **Why this matters**: most Japanese enterprises operate with policies in Japanese, contracts in English, and code comments in English.

---

## 7. Key Features

### 7.1 Foundational

- Natural-language rule storage with full provenance to source documents.
- Multi-modal search (full-text, vector, category, hybrid).
- Rule lifecycle: draft → review → approved → effective → superseded → retired.
- REST API, Intent API, Subject-specific Evaluate APIs (`/evaluate`, `/evaluate/document`, `/evaluate/transaction`).
- Python SDK (Rule Client) and Agentic SDK.
- Department-aware RBAC.

### 7.2 Differentiating

- **Cross-Subject Evaluation**: code, documents, transactions, communications, workflows under one engine.
- **Cross-Departmental Governance**: Legal, HR, Finance, Sales, Engineering co-manage rules with department-level ownership.
- **Domain Extractors**: contract clauses, regulations, handbooks, minutes, tabular data, email archives — all become rules.
- **Conflict Detector**: continuously scans for `conflicts_with` candidates.
- **Counterexample Generator**: minimal compliant/non-compliant examples per rule, by subject type.
- **Rule Coverage**: dormant and over-triggered rules surfaced from event logs.
- **Change Impact Simulator**: replay historical events against proposed rule revisions.
- **Refinement Feedback Loop**: human corrections become rule improvements.
- **Polyglot Rules**: semantically equivalent rule pairs across languages, continuously verified.
- **Provenance Lineage**: Law → Internal Policy → Department Rule → Contract Clause chains, propagated when upstream changes.
- **Conversational Rule Assistant**: end-user-friendly chat surface.
- **Compliance Cockpit**: Compliance/Legal/Exec dashboard distinct from rule-engineer view.
- **Why API**: multi-level rationale traversing `rationale` and `source_refs`.
- **Automatic Rule Discovery**: bootstraps rules from any local corpus.
- **Cross-Project Federation**: org → team → project inheritance.
- **Rule Playground**: interactive sandbox for testing rules.
- **Proactive Alerts**: background workers detect problems and notify.
- **Versioned Snapshots**: atomic deployment of rule sets with rollback.

### 7.3 Cross-Cutting

- Immutable audit log with hash-chained integrity.
- Tiered LLM strategy: small/fast for screening, large/accurate for high-severity, optional consensus voting for `CRITICAL`.
- PII sanitization on inputs and masking on logs.
- Department-aware RBAC, federation hierarchy.
- Local-first operation: no required outbound network calls beyond the Gemini API.

---

## 8. Use Cases

### 8.1 HR — Attendance and Overtime

The HR system registers attendance and overtime. The Rule Repository holds work regulations and 36-Agreement constraints. The HR system pushes `attendance.registered` business events. The Transaction Evaluation Path validates each registration in `preflight` mode and alerts on legal-limit violations or missing 36-Agreement filing.

**Subject type**: TRANSACTION. **Owning department**: HR. **Templates**: `hr-attendance-jp`.

### 8.2 Legal — Contract Review

The contract management system stores contracts under negotiation. The Rule Repository holds standard clauses, dangerous-clause patterns, and procurement policy. When a counterparty's NDA draft is uploaded, Document Evaluation flags risky clauses (unlimited liability, foreign jurisdiction) with span-level suggested rewrites.

**Subject type**: DOCUMENT_DRAFT. **Owning department**: Legal. **Templates**: `contract-clause-standard`.

### 8.3 Finance — Expense and Procurement

Expense submissions and purchase orders push business events. The Transaction Evaluation Path checks them against expense policy, anti-bribery rules, and procurement controls. Violations produce `field_change` (cap the amount) or `approval_add` (escalate to additional approvers) Remediations.

**Subject type**: TRANSACTION. **Owning departments**: Finance, Compliance. **Templates**: `expense-policy-jp`, `bribery-prevention`, `procurement-rules`.

### 8.4 Engineering — Software Development

CI pipelines evaluate pull requests. AI coding agents receive applicable rules via MCP. The Code Evaluation Path produces line-level `code_edit` Remediations. Existing engineering features (PR review, hooks, CI CLI) remain unchanged.

**Subject type**: CODE_CHANGE. **Owning department**: Engineering. **Templates**: `python-fastapi`, `typescript-react`, `security-owasp`, `api-design`, `testing-standards`.

### 8.5 Sales — Outbound Communication

Sales drafts customer-facing emails through the company portal. Each draft is evaluated by the Document Evaluation Path against pharmaceutical-claim restrictions, consumer-protection rules, and confidentiality classification. Inline `text_rewrite` Remediations flag risky phrasing.

**Subject type**: DOCUMENT_DRAFT or COMMUNICATION. **Owning departments**: Sales, Compliance. **Templates**: `internal-communication`, `privacy-protection-jp`.

### 8.6 Compliance — Regulatory Compliance

A financial institution stores regulations in the repository, with derived internal procedures linked via `derives_from`. When a regulation is amended, the Provenance Lineage and Change Impact Simulator identify all downstream procedures that need review. The Compliance Cockpit shows organization-wide violation trends and the action queue.

**Owning department**: Compliance. **Cross-references**: Legal, HR, Finance.

### 8.7 AI-Assisted Development

A team uses Claude Code with the Rule Repository. Rule Discovery bootstraps 50+ rules from existing CLAUDE.md, linter configs, and code conventions in an afternoon. Agents receive applicable rules via MCP. Human corrections feed the Correction Flywheel. Organization-wide engineering standards are shared across team repositories via Federation.

**Subject type**: AGENT_ACTION + CODE_CHANGE. **Owning department**: Engineering.

### 8.8 General Affairs / Documentation Standards

Internal wiki posts, status reports, decision memos, and external press releases pass through Document Evaluation against documentation standards and confidentiality rules.

**Subject type**: DOCUMENT_DRAFT or COMMUNICATION. **Owning department**: General Affairs (with Compliance for sensitive content).

---

## 9. Technical Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Document parsing | Gemini Files API + document understanding (PDF, text, markdown) |
| Spreadsheet parsing | `openpyxl` (Python) for tabular extractor |
| Email parsing | `email` stdlib + `mail-parser` for `.eml` corpus |
| Data | PostgreSQL 17, Elasticsearch 8.17, Neo4j 5, Redis 7 |
| MCP | FastMCP, 24 tools (18 core + 6 domain-specific) |
| Jobs | arq (background cron) |
| Quality | ruff + mypy, ESLint + Prettier, pre-commit hooks |
| Local orchestration | Docker Compose |

The architecture intentionally avoids hard-coding a single LLM provider. The `Evaluator` interface accepts any model that can perform structured judgment.

---

## 10. Roadmap

The project is structured in eight phases. Phases 1–5 follow the original architecture. Phases 6–7 established the Cross-Organizational direction. Phase 8 achieved full domain parity.

### Phase 1 — Foundation (Storage & Search) [COMPLETE]
- Rule data model and persistence
- Document ingestion and rule extraction pipeline
- Full-text, vector, category, hybrid search
- REST and Intent API
- Rule Client (Python SDK)
- Basic governance

### Phase 2 — Enforcement (Evaluation & Integration) [COMPLETE]
- Code-Aware Evaluation Engine
- Agent Context Delivery via MCP
- Development Workflow Integration (CI CLI, agent hooks, optional GitHub PR review)
- Agentic Rule Client with real evaluation
- Rule Enforcement Gateway (engineering-side)
- Rule Intelligence

### Phase 3 — Discovery & Learning [COMPLETE]
- Automatic Rule Discovery (code-side analyzers)
- Agent Correction Feedback Loop
- Cross-Project Rule Federation

### Phase 3.5 — Adoption Acceleration [COMPLETE]
- One-click GitHub repository import
- Automatic PR correction capture
- Rule impact preview
- Conflict resolution transparency
- Cache + top violations analytics

### Phase 4 — Testing & Deployment Safety [COMPLETE]
- Rule Playground
- Per-Rule Test Cases
- Proactive Alerts (with local-first delivery)
- Rule Set Snapshots
- Environment-based evaluation

### Phase 5 — Self-Improving Governance [COMPLETE]
- 5a Batched Evaluation [COMPLETE]
- 5b Evaluation Result Persistence [COMPLETE]
- 5c Outcome-Oriented Dashboard [COMPLETE]
- 5d Correction-to-Rule Flywheel [COMPLETE]
- 5e Active Rule Injection [COMPLETE] — `rulerepo-hook preflight/posthoc` with `--prompt` option; `rulerepo-hook install` writes `.claude/settings.json`
- 5f Zero-Config Bootstrapping [COMPLETE] — `rulerepo init` CLI + frontend onboarding wizard + `POST /api/v1/rules/import`
- 5g Structured Remediation [COMPLETE] — polymorphic RemediationKind with 7 kinds (code_edit, text_rewrite, field_change, approval_add, process_reroute, clarification, block)
- 5h Rule Maturity Model [COMPLETE]
- 5i Advanced Intelligence [COMPLETE] — continuous conflict scanner (daily cron) + verdict drift detection (daily, 30-day windows, 20pp threshold, alert generation)
- 5j Infrastructure Tiers [COMPLETE] — Tier 1 (Postgres only) / Tier 2 (+ES, Redis) / Tier 3 (+Neo4j, MCP) with graceful degradation (Postgres FTS fallback, adjacency table for graph)

### Phase 6 — Platform Governance [COMPLETE]

Phases 6a and 6b ship under the Cross-Organizational direction. Phase 6c is **deferred**.

- **6a. Collaborative Governance Workflow [COMPLETE]** — Proposals (draft → review → approve/enact), multi-approver voting, change impact preview, threaded comments with suggestions, notification inbox.
- **6b. Autonomous Agent Governance Loop [COMPLETE]** — Agent profile, trust levels, personalized rules, verdict challenges, exception requests are active. Multi-agent governance sessions are frozen behind `MULTI_AGENT_SESSIONS_ENABLED=false` (returns 404 when disabled). This is the intended final state under the Cross-Organizational direction.
- **6c. Cross-Organization Rule Marketplace [REMOVED]** — Removed. Cross-organization rule sharing is not a goal of this product. Rules ship as domain packs instead.

### Phase 7 — Cross-Organizational Subject Expansion [COMPLETE]

The expansion that turned the Rule Repository from a code-centric guardrail into a true cross-organizational platform. All sub-phases are complete and the four acceptance scenarios in §11.5 pass.

#### 7a. Subject Type Abstraction [COMPLETE]
- `SubjectKind` enum (8 kinds: code_diff, clause_set, event, transaction, creative, decision, identity, document) with `SubjectAdapter` protocol in `domain/subject.py`.
- `RemediationKind` enum (7 kinds: code_edit, text_rewrite, field_change, approval_add, process_reroute, clarification, block) with `PolymorphicRemediation` in `domain/remediation.py`.
- `EvaluationSubject` with `from_legacy_diff()` backward compatibility.
- Surface adapter registry dispatches by subject kind.
- Legacy `POST /api/v1/evaluate` with diff/files payload continues to work.

#### 7b. Document Evaluation Path [COMPLETE]
- `services/evaluation/surfaces/document/` with adapter, subject, and prompts.
- Span-aware evaluation with `text_rewrite` Remediations.
- Document-type-aware prompts (contract_clause, email, minutes, proposal, press_release, report).

#### 7c. Transaction Evaluation Path [COMPLETE]
- `services/evaluation/surfaces/transaction/` with adapter, subject, and prompts.
- `services/evaluation/surfaces/message/` for communication evaluation.
- Remediations: `field_change`, `approval_add`, `process_reroute`.

#### 7d. Department-Aware RBAC [COMPLETE]
- `DepartmentType` enum (10 types) and `Capacity` enum (owner, reviewer, auditor, subscriber) in `domain/department.py`.
- `services/departments/authz.py` with `can_view`, `can_edit`, `can_approve`, `visible_departments`.
- `services/departments/service.py` with CRUD for departments and capacity assignments.
- Frontend `/departments` admin page.

#### 7e. Universal Business Event Schema [COMPLETE]
- `BusinessEvent` and `ActorRef` domain objects in `domain/business_event.py`.
- `services/events/scope_resolver.py` with `DEFAULT_EVENT_SCOPE_MAP`.
- `services/events/ingest.py` with `EventIngestionService`.
- `POST /api/v1/events/ingest` endpoint.

#### 7f. Domain-Specific Extractors [COMPLETE]
- 6 extractors implementing the `Extractor` protocol in `services/extraction/extractors/`:
  - `contract.py` — clause segmentation with hierarchy detection.
  - `regulation.py` — Japanese 条/項/号 and English Article/Section/Clause parsing.
  - `handbook.py` — section-heading-based extraction for employee manuals.
  - `minutes.py` — extracts decisions and action items only.
  - `tabular.py` — Excel/CSV via openpyxl (one rule per row).
  - `email_archive.py` — pattern discovery from .eml corpora.

#### 7g. Conversational Rule Assistant [COMPLETE]
- `services/assistant/orchestrator.py` with intent classification (compliance_question, pre_send_check, tutorial_request).
- `POST /api/v1/assistant/turn` endpoint with citations.
- Frontend `/assistant` page with chat UI and inline rule citations.
- Department-aware filtering.

#### 7h. Compliance Cockpit [COMPLETE]
- `services/compliance/cockpit.py` with department trends, policy metrics, regulatory propagation, action queue, audit summary.
- `GET /api/v1/compliance/dashboard`, `/propagation`, `/action-queue` endpoints.
- Frontend `/compliance` page with department violation trends and per-policy metrics.

#### 7i. Polyglot Rules Completion [COMPLETE]
- `services/polyglot/verifier.py` with semantic equivalence checking (DRIFT_THRESHOLD = 0.85).
- Weekly `validate_polyglot_equivalence` cron (Sunday 6am).
- Translation drift detection with automatic alert generation.

#### 7j. Non-Code Test Cases [COMPLETE]
- `services/playground/test_generator_document.py` — document test case generator.
- `services/playground/test_generator_transaction.py` — transaction test case generator.

#### 7k. Context Provider Abstraction [COMPLETE]
- `services/context/providers.py` with `ContextProvider` protocol.
- `StaticFileProvider` (local JSON/CSV lookup) and `HttpProvider` (in-cluster HTTP).
- `ContextProviderRegistry` for merging facts from multiple providers.

#### 7l. Sample Templates Expansion [COMPLETE]
- 30 templates across all departments: HR (5), Finance (5), Legal (4), Compliance (2), Security (3), Engineering (5), Communication (1), Procurement (1), Marketing (1), Meta (1), Cross-domain (2).
- All templates include: statement, modality, severity, classification, subject_kinds, scope, jurisdiction, rationale, tags, violation_examples.

**Phase 7 success criteria**: the four end-to-end scenarios in §11.5 pass — verified by `make crossorg.acceptance` (18 tests, all green).

### Phase 8 — Cross-Organizational Parity [COMPLETE]

Phase 7 established the multi-domain architecture. Phase 8 eliminated the remaining code-centric bias in shared infrastructure, deepened non-code domain implementations to feature parity, and ensured every domain is a first-class citizen.

#### 8a. Universal Rule Selector Defaults [COMPLETE]
- Removed hard-coded `["code_diff"]` fallback in `rule_selector.py`. Rules with `applicable_subject_types = None` are now treated as **universal** (visible to all surfaces), not code-only.
- Added `ALL_SUBJECT_TYPES` constant in `domain/subject.py`.
- Migration `032_backfill_applicable_subject_types` explicitly marks code-scoped rules as `["code_diff"]`; all others remain universal.

#### 8b. Surface-Based Batch Evaluation Routing [COMPLETE]
- `batch_evaluator.py` now routes by `context.surface` (not by `if context.diff`).
- 7 surface-specific batch prompt templates: `evaluate_batch_{code,contract,transaction,document,message,human_action,generic}.txt`.
- Non-code evaluations are first-class paths, not fallback modes.

#### 8c. Domain-Neutral Output Schemas [COMPLETE]
- `services/evaluation/schemas/location_schemas.py` defines per-surface location schemas (CODE_LOCATION, CONTRACT_LOCATION, TRANSACTION_LOCATION, DOCUMENT_LOCATION, MESSAGE_LOCATION, HUMAN_ACTION_LOCATION, GENERIC_LOCATION).
- `evaluation_core.py` accepts `surface` parameter and injects the appropriate schema into structured output.
- Non-code evaluations no longer receive meaningless `file_path`/`line_number` fields.

#### 8d. Deep Surface Adapters [COMPLETE]
- Contract adapter (333 LOC): clause hierarchy detection (Japanese 条/項/号 + Western Article/Section), party extraction, governing law detection, 18 contract-type → scope mappings, risk classification.
- Transaction adapter (330 LOC): type detection (explicit + heuristic), field validation (11 types × required fields), threshold analysis with FX approximation, approval chain extraction, 20 type → scope mappings.
- Message adapter (322 LOC): 16-channel classification, audience detection (internal/external/regulatory), PII scanning (7 patterns), claim detection (health/financial/legal/superlative), confidentiality marker detection, channel+audience → scope mapping.
- Human Action adapter (391 LOC): 50+ action classification, actor context enrichment, temporal analysis (business hours, fiscal period, deadline), authority verification, department+action → scope mapping.
- All prompt hints are proactive guidance (not defensive "don't do code" language).

#### 8e. Equalized Prompt Templates [COMPLETE]
- `evaluate_hr_event.txt`: 88 lines (from 26) with overtime decision tree, 36-agreement checks, preconditions, auto-remediation criteria.
- `evaluate_contract_clause.txt`: 91 lines with risk classification tree, jurisdiction checks, clause-level remediations.
- `evaluate_expense_claim.txt`: 96 lines with threshold tree, category validation, receipt rules, tax compliance.
- `evaluate_message.txt`: 95 lines (new) with PII detection tree, claim verification, channel-specific rules.

#### 8f. Cross-Domain Discovery Analyzers [COMPLETE]
- `ContractCorpusAnalyzer` (214 LOC): detects common clause patterns across contract corpora.
- `HrPolicyAnalyzer` (376 LOC): extracts quantitative thresholds from HR handbooks and employment regulations.
- `ExpenseGuidelineAnalyzer` (418 LOC): extracts threshold tables, category restrictions, documentation requirements.
- `CommunicationStandardAnalyzer` (401 LOC): extracts tone rules, prohibited language, required disclaimers.
- All registered in `discovery/service.py` and accessible via `POST /api/v1/discover/scan`.

#### 8g. Domain-Aware SDK and MCP Tools [COMPLETE]
- MCP tools: `get_rules_for_contract_review`, `get_rules_for_transaction`, `get_rules_for_communication`, `evaluate_contract`, `evaluate_transaction`, `evaluate_communication` — each described as "the primary tool for [domain] agents".
- Agentic client: `get_rules_for_contract()`, `get_rules_for_transaction()`, `get_rules_for_communication()`, `evaluate_contract()`, `evaluate_transaction()`, `evaluate_communication()`.
- Rule client: `client.contracts`, `client.transactions`, `client.communications` domain resources.

#### 8h. Plugin Ecosystem Parity [COMPLETE]
- HR plugin: 2,122 LOC (from 397) — AttendanceSystemExtractor, AttendanceEvaluator (deterministic 36-agreement checks), ViolationPatternCapture.
- Finance plugin: 2,602 LOC (from 394) — ApprovalMatrixExtractor, ExpensePolicyExtractor, ExpenseEvaluator (8 deterministic checks), AuditFindingsCapture.
- Legal plugin: 1,891 LOC (from 655) — ContractTemplateExtractor, RiskClassifier (deterministic risk indicators), NegotiationHistoryCapture.
- Marketing plugin: 1,801 LOC (from 358) — BrandGuidelinesExtractor, RegulatoryAdvertisingExtractor (薬機法/景品表示法/特定商取引法), CreativeComplianceEvaluator, CampaignComplianceCapture.
- All exceed the Engineering plugin baseline (1,394 LOC).

#### 8i. Frontend Domain Parity [COMPLETE]
- Finance dashboard: 505 LOC with real API calls (`getDepartmentDashboard`, `getDepartmentEvaluations`, `getDepartmentRules`); sub-pages for expenses, controls, audit.
- Marketing dashboard: 680 LOC with real API; sub-pages for creative-reviews, guidelines.
- HR dashboard: 649 LOC with real API; sub-pages for attendance, leave, lifecycle, policies, violations.
- Legal dashboard: 926 LOC with real API; sub-pages for clauses, redlines, lineage.
- No mock data remaining.

#### 8j. Domain-Aware Health Scoring [COMPLETE]
- Replaced code-centric "Test Coverage" dimension with domain-aware "Effectiveness":
  - Code rules: volume-based (unchanged — evaluation_count × 20).
  - Legal/document rules: precision-based (actual deny rate vs expected).
  - Transaction/event rules: override-rate-based (low overrides = effective).
  - Generic rules: balanced formula; 50 (neutral) when untested.
- Added `classify_rule_status()` for Compliance Cockpit: `dormant` (0 evals, active >90d), `ineffective` (override rate >50%), `over_broad` (>95% ALLOW rate).
- Backward-compatible: `test_coverage` key remains as alias for `effectiveness`.

**Phase 8 success criteria**: 830 unit tests pass (no regressions); mypy clean; all non-code domains have ≥120 LOC of adapter logic, ≥50-line prompt templates, dedicated discovery analyzers, SDK/MCP entry points, 1,000+ LOC plugins, and real frontend dashboards.

---

## 11. Frozen / Deferred Components

The following components exist in code but are **disabled by default** and not part of the supported surface under the Cross-Organizational direction. They are kept for future re-enablement.

| Component | Default | Reason |
|---|---|---|
| `MULTI_AGENT_SESSIONS_ENABLED` | `false` | Multi-agent governance sessions are excessive for local single-organization deployments. Single-agent profiles, personalized rules, and trust levels remain active. |
| `GITHUB_APP_ENABLED` | `false` | The GitHub App webhook receiver is opt-in. The CLI (`rulerepo-check`) provides equivalent functionality. Enable per-deployment if needed. |
| `EXTERNAL_WEBHOOK_NOTIFICATIONS` | `false` | `ALERT_WEBHOOK_URL` and `DIGEST_WEBHOOK_URL` are opt-in; the default is local file output and frontend inbox. |
| `gateway/normalizers/{github,slack}.py` | not registered | Only `generic.py` is registered by default. |

The frontend hides routes for disabled components from the sidebar.

### 11.5 Verification (Cross-Organizational Acceptance)

Four end-to-end scenarios are added to CI as the **acceptance criteria** for "Rule Repository is a Cross-Organizational Rule Platform":

1. **Expense policy round-trip**: expense policy PDF (Japanese) → `regulation` extractor → candidate rules → human approval → expense submission `BusinessEvent` (over the per-day limit) → DENY + `field_change` Remediation.
2. **Contract clause review**: standard NDA template + counterparty's draft (markdown) → `evaluate/document` → flagged dangerous clauses + `text_rewrite` Remediations targeting specific spans.
3. **HR attendance enforcement**: employee handbook + 36-Agreement → applicable rules → attendance registration `BusinessEvent` (60h overtime) → DENY + repair suggestion.
4. **Sales email pre-send**: outbound email draft → `evaluate/document` → privacy / pharmaceutical / consumer-protection checks → flagged spans + suggested rewrites.

All four must pass on every PR for the Cross-Organizational claim to hold.

---

## 12. Success Metrics

- **Subject coverage**: number of subject types in active use (target: 4+ — code, document, transaction, communication).
- **Department coverage**: number of departments with ≥10 active rules each (target: 5+).
- **Coverage**: percentage of rules in target source documents successfully extracted and registered.
- **Latency**: p50 / p95 / p99 evaluation latency in `preflight` mode, by subject type.
- **Accuracy**: human-rated correctness of verdicts on a held-out test set; precision and recall on conflict detection; precision on document `text_rewrite` Remediations.
- **Adoption**: number of integrated systems and active rules; volume of evaluation requests per day.
- **Governance health**: percentage of rules with complete metadata, current rationale, active owners, and a department.
- **Time-to-comply on regulatory change**: median time between source-law amendment and corresponding internal rule revision being approved.
- **Shadow-to-enforcement rate**: >70 % of experimental rules reach stable within 60 days.
- **Auto-fix rate**: >40 % of SHOULD violations auto-fixed via auto-applicable Remediations (across all kinds).
- **Flywheel throughput**: >5 rules/month auto-drafted from correction clusters.
- **Time-to-rule**: <1 week from correction pattern detection to approved rule.
- **Cross-Organizational acceptance suite pass rate**: 100 % (the four scenarios in §11.5).

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Always log full evaluation context; require human review on high-severity denials; consensus voting for CRITICAL rules; refinement feedback loop. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity; refinement loop suggests rewrites; require unit tests on each rule. |
| LLM costs scale poorly with rule corpus size | Two-stage evaluation (metadata pre-filter, then LLM); aggressive caching; tiered model selection; batched evaluation. |
| Sensitive data leaks through evaluation context | Input sanitization; log masking; **department-aware RBAC** prevents cross-department leakage; optional fully self-hosted model deployment. |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via `effective_period`; sidecar mode for shadow testing; snapshot rollback. |
| Over-reliance reduces human judgment | Position the system as decision support, not decision replacement; preserve rationale visibility; require human approval for rule revisions. |
| Conflicts with existing IAM / GRC tools | Position the Rule Repository as a complementary semantic layer; provide integration points (Business Event API) rather than competing with baseline controls. |
| **Subject Type abstraction breaks engineering use cases** | Backward-compatible API: legacy diff/files inputs continue to work as `CODE_CHANGE` subjects. CI test suite validates engineering scenarios against every change to the abstraction. |
| **Department RBAC misconfiguration locks users out** | Default `public` department for legacy rules; admin override; comprehensive RBAC integration tests. |
| **Polyglot translations drift from primary** | Weekly verification cron; automatic proposal generation when drift detected; UI badge indicating verification freshness. |

---

## 14. Glossary

- **Rule**: a natural-language normative statement, plus structured metadata, managed as a first-class object.
- **Statement**: the canonical natural-language text of a rule, in `primary_language`.
- **Modality**: the strength of the obligation (MUST, MUST_NOT, SHOULD, MAY, INFO).
- **Kind**: taxonomic axis (mandatory / guideline / template / informational / meta).
- **Scope**: the set of subjects, systems, business processes to which a rule applies.
- **Department**: the function (legal/hr/finance/sales/engineering/it/ga/compliance/exec/public) that owns the rule.
- **Verdict**: the result of an evaluation (ALLOW, DENY, NEEDS_CONFIRMATION).
- **Reason graph**: a structured DAG explaining which facts triggered which conditions in which rules.
- **Subject**: the artifact being evaluated. Polymorphic — code, document, transaction, communication, workflow step, agent action.
- **Subject Type**: enum classifying a subject. The evaluation engine dispatches on this.
- **Remediation**: a typed proposal for fixing a violation. Polymorphic kinds (code_edit, text_rewrite, field_change, approval_add, process_reroute, clarification, block).
- **Business Event**: a structured payload by which business systems push artifacts to the Rule Repository for evaluation.
- **Meta-rule**: a rule whose subject is other rules.
- **Provenance lineage**: the chain of derivation from a higher-level source (e.g., a law) down to operational rules and contract clauses.
- **Preflight / Posthoc / Sidecar**: three modes of integration corresponding to before-action, after-action, and parallel-observation enforcement.
- **LLM-as-Judge**: the architectural pattern of using a large language model to evaluate whether an action complies with a natural-language rule.
- **Federation**: the vertical hierarchy (org → team → project) used for rule inheritance.
- **Membership**: the user-to-department-to-role binding used for RBAC.
- **Polyglot rule**: a rule with semantically equivalent statements in multiple languages, periodically re-verified.

---

## 15. Open Questions

Most Phase 7 questions have been resolved. Remaining open questions:

- ~~What is the canonical schema for `scope` across non-engineering subjects?~~ **RESOLVED**: Convention `{department}/{domain}` (e.g., `finance/expense`, `hr/attendance`, `legal/contract`). Surface adapters map domain-specific inputs to these scopes automatically.
- ~~How should `event_type` be mapped to scope in `/events/ingest`?~~ **RESOLVED**: Convention `{department}.{action}.{noun}` with `DEFAULT_EVENT_SCOPE_MAP` in `events/scope_resolver.py`.
- Should the Conversational Assistant have memory of previous user conversations, or be stateless per turn? (Currently stateless per turn with session_id for grouping.)
- ~~How are department memberships managed when no enterprise IdP is integrated?~~ **RESOLVED**: Self-managed via `/api/v1/departments/memberships` endpoints. SCIM provisioning available for enterprise deployments.
- What is the expected SLO for `preflight` evaluations on document subjects? Document evaluation is more expensive than code evaluation; users may accept higher latency. (Currently no differentiated SLO; monitoring in place.)
- ~~How are deprecated rules archived without losing the ability to re-evaluate historical events?~~ **RESOLVED**: Rules use `effective_period.valid_until` for retirement; never deleted. Historical evaluations reference rule snapshots.
- ~~For polyglot rules, when primary statement and translation drift in semantics, who decides which is canonical?~~ **RESOLVED**: Primary language statement is always canonical. Drift triggers a proposal to update the translation (not the primary).
- How are department-cross-references (a contract clause rule depends on an HR rule) handled when one department retires the underlying rule? (Partially addressed by `CROSS_REFERENCES` relationship and regulatory propagation alerts, but no blocking mechanism yet.)

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes should follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect. The improvements captured in Phase 7 are derived from `IMPROVEMENT.md`; that document is the source for the rationale and prioritization.*
