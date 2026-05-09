# Rule Repository

> An **organization-wide normative management platform**.
>
> Manages laws, contracts, internal policies, HR regulations, financial procedures, sales playbooks, communication standards, documentation conventions, and engineering rules — in their original natural language. Every team — Legal, HR, Finance, Sales, Compliance, IT, executive, and engineering — can discover, search, evaluate, and enforce the rules that govern their work, through APIs, AI agents, and persona-specific operator consoles.
>
> Inspired by Semantic Governance, generalized to the entire organization.

---

## 1. Project Overview

The **Rule Repository** stores human-authored rules in their original natural-language form and makes them operationally useful: searchable, applicable, and enforceable across business systems, business processes, and software development environments. Where traditional rule engines require translating human rules into formal logic — and lose nuance in the process — the Rule Repository keeps the rule as written and uses LLMs and AI agents to interpret, search, and enforce them at runtime.

This approach is inspired by **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea in three directions:

- **Wider scope of rules**: laws, regulations, contracts, HR policies, financial procedures, communication standards, sales playbooks, marketing compliance, AI agent guardrails, and engineering conventions.
- **Wider scope of consumers**: human users, business systems, IDEs, CI pipelines, AI agents, and any application that needs to ask "is this action compliant with the rules that govern it?"
- **Wider scope of time**: pre-flight checks, post-hoc audits, sidecar observation, and continuous regulatory tracking.

### 1.1 Core Premise

Most rules that govern an organization are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality. The Rule Repository is built on this premise and treats **rules themselves as first-class, versioned, governed assets**, decoupled from any single consumer and reusable across the entire organization.

### 1.2 Code is One Surface Among Many

This project explicitly does **not** privilege any single domain. Code changes are *one* surface that the system evaluates. Contract clauses, HR events, financial transactions, business documents, and human-to-human communications are *equal* surfaces. The architecture is designed so that adding a new surface — or a new business domain — is a matter of contributing a *Domain Pack*, not modifying the evaluation core.

---

## 2. Background and Motivation

The Rule Repository fills a gap that no current category of software addresses cleanly:

- **Document management systems** store the source documents but do not understand the rules inside them.
- **Rule engines (Drools, DMN, OPA)** require formal encoding and lose the original semantics.
- **GRC platforms** track compliance status but do not enforce rules at the point of action.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.
- **Coding rule and PR-review tools** focus solely on the engineering surface and cannot govern legal, HR, financial, or operational compliance.

The Rule Repository is the only system that simultaneously:

1. Stores rules in natural language with full provenance.
2. Evaluates any subject (code, contract, action, transaction, document, message) against those rules through a unified LLM-as-Judge pipeline.
3. Tracks **norm lineage** (which corporate policy derives from which regulation that derives from which law) so upstream changes propagate.
4. Surfaces persona-specific dashboards so a Legal Counsel, an HR Manager, a Compliance Officer, and an Engineering Lead each see a console aligned to their workflow.

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Store rules in natural language, with full traceability to their source documents and to their upstream norms.
- Provide rich search (full-text, vector, category, hybrid, intent-based) over rule corpora.
- Enable runtime evaluation: "given this *subject* and this *intent*, is the action compliant with the relevant rules?"
- Support any *Surface* — code, contract, human action, transaction, document, message — through pluggable adapters.
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Detect conflicts, redundancies, and dead rules across the corpus.
- Track norm lineage from law down to operational rule, and propagate upstream changes downstream.
- Make rule provenance, rationale, and revision history first-class.
- Provide ergonomic SDKs so business systems and AI agents can integrate easily.
- Offer **persona-specific consoles** for Legal, HR, Finance, Compliance, Sales, Engineering, and Admin roles.
- Ship by **Domain Pack**: a reusable bundle of rules, adapters, prompts, UI, and samples for one business domain.

### 3.2 Non-Goals

- Replacing IAM, RBAC, ABAC, or network-layer access control. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel, compliance officers, HR managers, or accountants. The system surfaces issues; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts on behalf of users.
- Generating the rules themselves without human approval. Discovery and feedback loops *propose*; humans *approve*.

---

## 4. Architecture

The system is composed of three top-level components and a set of pluggable extensions.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Rule Management Server                           │
│                                                                          │
│  Extraction   Search(5)   Subject-Aware    Intelligence    Discovery    │
│  Pipeline     BM25+Vec    Evaluation       Health+Recs     + Import     │
│  (multi-      +Project    Engine           Effectiveness   Federation   │
│   format)     filter      (LLM-as-Judge)   Digest+Compare  Snapshots    │
│                           per Subject       Flywheel        Alerts      │
│  Norm Lineage Templates   per Surface      Agent Tracking  Playground   │
│  Tracking                                                                │
│                                                                          │
│  Proposals    Agent Gov   Persona Consoles                              │
│  (lifecycle,  (trust,     (Legal / HR / Finance / Compliance /         │
│   voting,     challenge,  Engineering / Admin)                          │
│   comments)   sessions)                                                 │
│                                                                          │
│  PostgreSQL    Elasticsearch    Neo4j      Redis        Audit Log      │
│  (truth)       (search)         (graph)    (jobs)       (immutable +    │
│                                                          surface-aware) │
└────────────┬────────────────────────────────────┬───────────────────────┘
             │                                    │
   ┌─────────┼────────────────────────────────────┼─────────────────┐
   │         │                                    │                 │
┌──▼───┐ ┌───▼──┐ ┌───────────┐ ┌──────────┐
│ Rule │ │Agent │ │    MCP    │ │   CLI    │
│ SDK  │ │ SDK  │ │  Server   │ │  Tools   │
│      │ │      │ │ (subject- │ │(per      │
│      │ │      │ │  agnostic │ │ surface) │
│      │ │      │ │  tools)   │ │          │
│      │ │      │ │           │ │          │
└──────┘ └──────┘ └───────────┘ └──────────┘
```

### 4.1 The Three Top-Level Components

- **Rule Management Server** (single FastAPI process): the system of record. Owns the canonical rule corpus, evaluation engine, search, intelligence, governance, and audit log.
- **Rule Client SDK / Agentic Rule Client SDK / CLI / MCP Server**: the consumer-facing libraries and binaries. Surface-agnostic: a contract-review agent and a coding agent both use the same MCP server with different tools.

### 4.2 Two Orthogonal Hierarchies

The system maintains two distinct hierarchical axes for every rule. They are **orthogonal**:

- **Norm Lineage** (what is the rule's authority and ancestry): Law → Regulation → Guideline → Corporate Policy → Department Rule → Operational Rule.
- **Org Federation** (who in the organization owns and is bound by the rule): Organization → Team → Project / Department / Function.

A rule can be simultaneously "derived from the Labor Standards Act" (norm axis) and "owned by the HR department" (org axis). The two axes are modeled separately, navigated separately in the UI, and queried separately by the evaluation engine.

### 4.3 Trust and Data Boundaries

- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and judgments they are authorized to see.
- All evaluation calls produce immutable, surface-aware audit records on the server side.

---

## 5. Domain Model

### 5.1 The `Rule` Entity

A rule is the central first-class object. It is **not** a regex, decision tree, or code expression; it is a structured envelope around a natural-language statement.

| Field | Description |
|---|---|
| `id` | Stable identifier |
| `statement` | The rule text in natural language (the canonical form) |
| `statement_translations` | Map of locale → translated statement (for bilingual rules, e.g. EN/JA contracts) |
| `locale` | Canonical locale of `statement` (default `en`) |
| `source_refs` | Pointers to the source document, section, and offset |
| `context` | Surrounding document text, section hierarchy, and qualifying information that disambiguates the rule |
| `applies_to_surfaces` | List of `Surface` values this rule can be evaluated against |
| `tech_scope` | Technical scope — file globs, languages, services (e.g., `engineering/python`, `service:payments`) |
| `org_scope` | Organizational scope — departments, teams, roles, regions (e.g., `hr/department/sales`, `region:jp`) |
| `modality` | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `effective_period` | `valid_from` / `valid_until` |
| `preconditions` | Facts required to evaluate the rule |
| `exceptions` | References to other rules or carve-outs |
| `rationale` | Why the rule exists (purpose, intent) — distinct from `context` |
| `norm_tier` | LAW / REGULATION / GUIDELINE / CORPORATE_POLICY / DEPARTMENT_RULE / OPERATIONAL_RULE |
| `norm_authority` | Free-form citation of upstream authority (e.g., "Labor Standards Act, Article 36") |
| `tags` | Free-form taxonomic labels |
| `governance` | Owner, approvers, revision history |
| `maturity_level` | EXPERIMENTAL / STABLE / PROVEN |
| `embedding` | Vector representation (derived) |

**Invariants:**

- `statement` is the *source of truth*. Structured fields exist for indexing, filtering, and prioritization — never to override the meaning of the statement.
- Every rule has exactly one canonical `locale`. Translations are explicit and maintained as semantic twins.
- A rule belongs to one `norm_tier` and zero or more `applies_to_surfaces`.

### 5.2 `Subject` and `Surface`

The unit of evaluation is a `Subject` — an abstract envelope around whatever is being evaluated. Surfaces define the kinds of things that can be Subjects.

| Field | Description |
|---|---|
| `surface` | Enum: `CODE`, `CONTRACT`, `HUMAN_ACTION`, `TRANSACTION`, `DOCUMENT`, `MESSAGE`, `GENERIC` |
| `identifier` | Stable subject reference (e.g., `pr#42`, `contract:ACME-2025-Q1`, `attendance:E001/2025-04`) |
| `payload` | Surface-specific data (diff text, clause text, event fields) |
| `facts` | Normalized facts that any rule may consult (numeric thresholds, dates, parties) |
| `actor` | Who is acting / being evaluated — see §5.4 |
| `timestamp` | When the subject came into being |
| `locale` | Locale of the payload (`en`, `ja`, ...) |

**Surfaces the system supports out of the box:**

- `CODE` — unified diffs, file changes, repository state. Engineering use cases.
- `CONTRACT` — clauses, redlines, contract metadata. Legal use cases.
- `HUMAN_ACTION` — events from business systems (attendance registration, expense claim, leave application, transfer request). HR, finance, procurement use cases.
- `TRANSACTION` — journal entries, invoices, payments. Finance use cases.
- `DOCUMENT` — whole documents or document regions (policies, reports, marketing copy). Compliance and marketing use cases.
- `MESSAGE` — emails, Slack messages, customer conversation logs. Communication compliance use cases.
- `GENERIC` — fallback for anything else. Treats `payload` as opaque text plus `facts`.

**Surface adapters** (one per surface) translate domain-specific input formats into `Subject` instances and may inject surface-specific hints into the evaluation prompt.

### 5.3 Rule Relationships

Rules form a graph, not a flat list. Relationships are first-class:

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level norm — the spine of the Norm Lineage |
| `succeeds` | A new revision that replaces a prior version |
| `translates` | This rule is a parallel-language translation of another rule |

The `derives_from` edge backbones the **Norm Lineage**. When a rule with `norm_tier = LAW` is amended (its `effective_period` is extended or its statement is revised), all rules transitively reachable via `derives_from` are flagged for review.

### 5.4 The `Actor` Entity

`Actor` represents the entity whose action is under evaluation. It is uniformly modeled across human, system, and AI:

| Field | Description |
|---|---|
| `kind` | `human` / `system` / `agent` |
| `identifier` | Stable identifier (`user:E001`, `system:expense_app`, `agent:claude-code`) |
| `attributes` | Free-form claims (role, department, trust_level, locale) |

This unification means agent-governance features (trust levels, mastery, personalized rules) generalize naturally to humans and business systems.

### 5.5 Norm Lineage

`Norm Lineage` is the chain of derivation from upstream legal/regulatory authority down to operational rules. It is modeled by:

- Each `Rule` carries `norm_tier` and `norm_authority`.
- The graph relationship `derives_from` connects a downstream rule to one or more upstream rules.
- A periodic worker walks the lineage upward to detect upstream changes (e.g., "this regulation was amended on date X") and flags downstream rules for review.

This produces, per organization, a navigable graph: *Labor Standards Act* → *Working Hours Order* → *ACME Working-Hours Policy* → *ACME Engineering Department Overtime Rule* → *ACME Backend-Team Overtime Operational Rule*.

### 5.6 Org Federation

`Federation` (the existing model) represents organizational hierarchy: Organization → Team → Project. It is **distinct from norm lineage**.

- Norm lineage answers: "what is the legal/policy ancestry of this rule?"
- Org federation answers: "which part of the organization owns this rule, and which descendants inherit it?"

Both axes are independently queryable and rendered in separate UIs.

### 5.7 Meta-Rules

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy", "Every operational rule must derive from a corporate policy or higher norm"). Meta-rules are evaluated by the same engine, with the rule corpus itself as the Subject.

---

## 6. Components

### 6.1 Rule Management Server

The server is the system of record for all rules. It exposes REST, Intent, Evaluate, Gateway, Intelligence, Discovery, Feedback, Federation, Norm Lineage, Proposals, Agent Governance, Playground, Snapshots, and Alerts APIs. Internally:

```
src/rulerepo_server/
├── api/v1/                 # REST routers
├── core/                   # config, logging, errors, auth, middleware, surface-aware PII
├── domain/                 # Rule, Subject, Surface, Actor, Verdict (pure)
├── services/
│   ├── evaluation/         # Subject-Aware Evaluation Engine
│   │   ├── core/           # rule × subject → verdict (universal)
│   │   └── surfaces/       # per-surface adapters and prompts
│   ├── extraction/         # Document ingestion (multi-format)
│   ├── search.py           # Multi-modal search
│   ├── intent.py           # Intent classification
│   ├── intelligence/       # Health, analytics, recommendations, persona dashboards
│   ├── discovery/          # Bootstrap rules from existing artifacts
│   ├── feedback/           # Correction → rule flywheel
│   ├── federation/         # Org-axis rule composition
│   ├── norm_lineage/       # Norm-axis rule provenance and propagation
│   ├── playground/         # Sandbox + test cases
│   ├── snapshots/          # Versioned, environment-deployable rule sets
│   ├── proposals/          # Multi-approver governance workflow
│   └── agent_governance/   # Trust, mastery, personalized rules — for any Actor
├── domain_packs/           # Vertical bundles (see §6.4)
├── adapters/
│   ├── postgres / elasticsearch / neo4j / gemini / files
├── mcp/                    # MCP server (subject-agnostic tools)
├── gateway/                # Webhook-driven enforcement
├── integrations/           # GitHub App, CI formatters
└── workers/                # Cron jobs (arq + Redis)
```

**Server capabilities:**

- **Rule CRUD** with revision history and effective-date semantics.
- **Multi-format extraction pipeline**: ingests PDFs, docx, markdown, txt, regulatory XML, and contract templates. Specialized parsers for legal/regulatory document structure (chapter / article / paragraph / item / appendix). Bilingual pairing for parallel-language documents. Redline differ for revision capture.
- **Search APIs**: Full-text, Vector, Category, Hybrid (BM25 + kNN), Context (subject → applicable rules), Impact (rule change → affected subjects).
- **Intent API**: classifies natural-language queries (`lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`, `lookup_norm_lineage`) and routes to the appropriate backend.
- **Subject-Aware Evaluation Engine** (§6.5): given a Subject and the rule corpus, returns `ALLOW` / `DENY` / `NEEDS_CONFIRMATION` with reason and structured remediations.
- **Audit log**: append-only, hash-chained record of all evaluations including model identity, prompt version, inputs, outputs, surface, locale, and actor. Retention is **surface-aware** (see §10.2).
- **Governance**: role-based access (Owner / Approver / Reader) per rule category, revision approval workflow, effective-date scheduling, multi-approver proposals.

### 6.2 Surface Adapters

Surface Adapters are pluggable modules under `services/evaluation/surfaces/`. Each adapter:

- Defines a `Subject` payload schema for its surface.
- Translates external input formats into Subjects (e.g., `code` adapter parses unified diffs into `CodeChange` subjects; `contract` adapter splits contracts into `ContractClause` subjects).
- Provides surface-specific evaluation hints that augment the universal evaluation prompt.
- Provides surface-specific PII sanitization rules.
- Provides surface-specific audit retention defaults.

Built-in adapters at v1:

| Surface | Primary input | Example Subject |
|---|---|---|
| `code` | unified diff, file paths | `CodeChange(diff, files, language, function_signatures)` |
| `contract` | docx / PDF / markdown contract | `ContractClause(text, position, clause_type, parties)` |
| `human_action` | structured event from business system | `HumanAction(actor, action_type, parameters, system, timestamp)` |
| `transaction` | journal entry / invoice / payment | `BusinessTransaction(amount, currency, accounts, parties, references)` |
| `document` | document or document region | `DocumentRegion(text, section_path, document_metadata)` |
| `message` | email / Slack / transcript | `Message(channel, sender, recipients, content, locale)` |
| `generic` | free-form text + facts | `GenericSubject(text, facts)` |

### 6.3 Domain Packs

A **Domain Pack** is a vertical bundle for one business domain. Packs live under `domain_packs/`:

```
domain_packs/
├── code/                   # Engineering rules (existing functionality, repackaged)
├── contract/               # Legal / contract management
├── hr_attendance/          # HR, attendance, labor compliance
├── expense/                # Expense reports, travel, entertainment
├── procurement/            # Purchase orders, vendor management
├── communication/          # Email / Slack / customer correspondence
├── compliance/             # Bribery, anti-social, FCPA, AML
├── governance/             # Board, disclosure, insider trading
└── marketing/              # Ad copy, landing-page compliance, claim substantiation
```

Each pack contains:

```
domain_packs/<pack>/
├── pack.yaml               # name, version, surfaces, persona, default_scopes, dependencies
├── rules/                  # YAML rule templates ready to import
├── adapters/               # symlinks or imports of the surface adapters this pack uses
├── ui/                     # frontend components and pages for the pack's persona
├── prompts/                # surface-specific evaluation hints
├── connectors/             # business-system connectors recommended by this pack
└── samples/                # anonymized seed data
```

`pack.yaml` schema:

```yaml
name: contract
version: 0.1.0
display_name: Contract Pack
description: Contract review, clause-vs-policy compliance, redline tracking
surfaces: [contract, document]
required_adapters: [contract, document]
default_scopes:
  org: [legal/contract]
  tech: []
ui_routes: [/domain/contract]
seed_rules_path: rules/
persona: legal
required_connectors: []
optional_connectors: [docusign, salesforce]
```

**Why Domain Packs:**

- Code becomes "one of many", correcting the structural drift toward dev-only use.
- New domains are added by adding a pack, not modifying the core.
- Marketing gains shippable units: "Contract Pack 1.0 is now available."

### 6.4 Subject-Aware Evaluation Engine

The evaluation engine is surface-agnostic. It accepts a `Subject` and a candidate rule set, and returns per-rule verdicts.

**Pipeline**: Subject Assembly → Rule Selection → LLM-as-Judge → Verdict Aggregation.

- **Subject Assembler**: Routes the input to the correct Surface Adapter, which produces a `Subject`.
- **Rule Selector**: Narrows the corpus to ~5–20 relevant rules. Filters: `applies_to_surfaces`, `tech_scope`, `org_scope`, `severity`, `modality`, `effective_period`, `maturity_level`, then semantic ranking. Norm lineage is consulted to preserve hierarchy precedence.
- **Evaluation Core**: One universal prompt (`evaluate_subject.txt`) with surface-specific hints injected. Tiered model selection: Flash for screening, Pro for HIGH/CRITICAL. Structured JSON output. Batched evaluation (single LLM call for all selected rules) with automatic per-rule fallback.
- **Verdict Aggregator**: Combines per-rule verdicts (any DENY → overall DENY for MUST/MUST_NOT rules at HIGH+), produces structured remediations, builds the reason graph, and resolves conflicts via Neo4j relationships.

**Subject-aware features**: every rule can read `subject.surface`, `subject.payload`, `subject.facts`, `subject.actor`, and `subject.locale`. The evaluation engine never assumes any of these — code, contract, action, transaction are all first-class.

**Code-aware features** (one set of surface-specific behaviors): file-path-to-scope matching, diff-aware function/line targeting, code remediations as actionable fix suggestions. These live exclusively in `surfaces/code/`.

### 6.5 Rule Client (Python SDK)

A thin, ergonomic wrapper over the server APIs.

```python
from rulerepo import RuleClient

client = RuleClient(server_url="...", api_key="...")

# Search
rules = await client.search.hybrid("overtime monthly limit", org_scope="hr/attendance")

# Intent
result = await client.intent.ask("What are the rules for refunding orders over $500?")

# CRUD
rule = await client.rules.get("rule_abc123")
await client.rules.update(rule.id, statement="...", revision_note="...")

# Norm Lineage
lineage = await client.norm_lineage.upstream("rule_abc123")
```

### 6.6 Agentic Rule Client (Python SDK)

A higher-level client that wraps `RuleClient` and adds agent capabilities for systems that need to **enforce** rules, not merely query them.

```python
from rulerepo.agentic import AgenticRuleClient

client = AgenticRuleClient(server_url="...", default_scope="hr/attendance")

# Surface-aware evaluation: human action surface
result = await client.evaluate(
    subject={
        "surface": "human_action",
        "identifier": "attendance:E001/2025-04",
        "payload": {
            "actor": "E001",
            "action_type": "register_overtime",
            "month": "2025-04",
            "overtime_hours": 50,
        },
        "facts": {"agreement_36_active": False},
    },
    mode="preflight",
)

if result.verdict == "DENY":
    print(result.violations)
    print(result.reason_graph)
    print(result.suggested_fix)
    print(result.remediations)
```

**Capabilities:**

- **Automatic context gathering** via Connectors.
- **Two-stage evaluation**: metadata + embedding pre-filter, then LLM judgment on the narrowed set.
- **Surface dispatch**: chooses the right Surface Adapter from the input.
- **Caching**: hash-keyed cache, automatically invalidated on rule revision.
- **Reason graphs**: structured DAG of which facts triggered which conditions in which rules.
- **Repair suggestions**: structured `Remediation` objects for surfaces where an automated fix is meaningful (code, transaction, action).
- **Three integration modes**: `preflight`, `posthoc`, `sidecar`.

### 6.7 Agent Context Delivery (MCP + Smart Rule Selection)

Exposes the Rule Repository to AI agents via the Model Context Protocol (MCP). Tools are **subject-agnostic**:

| Tool | Purpose |
|---|---|
| `get_applicable_rules(subject_ref, surface)` | Returns rules that apply to the given subject |
| `evaluate_subject(subject_payload, surface)` | Runs the evaluation engine on the given subject |
| `search_rules(query, scope_filters)` | Multi-modal search |
| `explain_rule(rule_id)` | Returns rationale and norm lineage |
| `find_clause_conflicts(contract_text)` | Contract-specific conflict detection |
| `lookup_norm_lineage(rule_id)` | Returns upstream chain (Law → Internal Policy → ...) |
| `explain_regulation_impact(law_id, change_summary)` | Replays historical evaluations against a hypothetical regulation amendment |
| `check_action(actor, action, payload)` | Generic human-action compliance check |
| `review_communication(channel, content)` | Communication compliance for messages |
| `discover_rules(source_uri, source_type)` | Bootstrap rules from a source |
| `register_agent / get_personalized_rules / challenge_verdict / request_exception` | Agent governance |
| `create_proposal / get_proposal_status` | Collaborative governance |

**Resources**: `rule://{id}` (single rule), `ruleset://{scope}` (dynamic context section), `lineage://{rule_id}` (norm-lineage tree).

**Prompts**: `compliance_check`, `rule_summary`, `impact_analysis`, `clause_review`, `action_review`.

The legacy `get_rules_for_context(files=...)` remains as a backwards-compatible alias for the code surface.

### 6.8 Surface-Specific Workflow Integrations

Integration into the places where work actually happens. Each surface has its own integrations:

- **Code** — GitHub PR Review (webhook), CI pipeline CLI (`rulerepo-check`), agent hooks (`rulerepo-hook preflight/posthoc`), rule ingestion (`rulerepo-ingest`).
- **Contract** — DocuSign envelope hooks, Salesforce CPQ, contract-management-system webhooks, redline review CLI.
- **Human action** — HRIS pull integrations (Workday, ADP), workflow webhooks (Kintone, ServiceNow), expense-system webhooks (Concur, SAP).
- **Transaction** — ERP webhooks (SAP, NetSuite), accounting-system pulls.
- **Message** — Slack message events, Outlook / Gmail message hooks, Teams transcript hooks.
- **Document** — generic document upload + scheduled re-evaluation, SharePoint / Google Drive watchers.

Each integration ultimately routes through the Subject-Aware Evaluation Engine; the integration is responsible only for normalizing its input.

### 6.9 Rule Intelligence & Observability

Analytics, health scoring, and automated improvement recommendations.

- **Health Scorer**: Per-rule score (0–100) across 6 dimensions — completeness, clarity, test coverage, freshness, activity, owner engagement.
- **Effectiveness Score**: Per-rule composite of precision (40%), prevention rate (35%), and adoption (25%).
- **Evaluation Analytics**: Corpus-wide and per-rule metrics — fire rate, deny rate, latency, trends. Slicable by `surface`, `org_scope`, `actor.kind`, `locale`.
- **Recommender**: Automated suggestions — retire dormant rules, clarify ambiguous ones, escalate persistent violations, strengthen SHOULD→MUST.
- **Norm Lineage Tracker**: Detects upstream amendments (regulatory changes) and lists affected downstream rules with proposed updates.

### 6.11 Persona-Specific Operator Consoles

The frontend is reorganized so each persona sees a console aligned with its workflow.

```
apps/frontend/app/
├── (admin)/                 # Rule administrators (intelligence, health, full corpus)
├── (engineering)/           # Engineering operations (PR/CI integration, code rules, agent hooks)
├── (legal)/                 # Legal counsel
│   ├── contracts/           # Contracts under review
│   ├── clauses/             # Clause search and conflict detection
│   ├── lineage/             # Norm Lineage Viewer
│   └── redlines/            # Revision diffs
├── (hr)/                    # HR managers
│   ├── violations/          # Employee/event-level violations
│   ├── attendance/          # 36-agreement and overtime tracking
│   ├── lifecycle/           # Onboarding/offboarding/transfer compliance
│   └── policies/            # Which policies cover which roles
├── (finance)/               # Finance, accounting, audit
│   ├── transactions/        # Transaction-vs-rule audit
│   ├── expenses/            # Expense-report compliance
│   └── tax/                 # Tax-related rule applicability
└── (compliance)/            # Compliance officers, executive
    ├── overview/            # Cross-organization compliance state
    ├── audits/              # Audit trail browser
    ├── regulatory/          # Regulatory-change response status
    └── incidents/           # Cross-domain incident view
```

**Hero metric per persona** (set in §11):

- Engineering: compliance rate + 7-day trend
- Legal: open contract reviews, unresolved conflicts, recent upstream-law amendments
- HR: this month's violations, 36-agreement headroom, regulation-change-affected employees
- Finance: this month's transaction violations, expense-rejection rate, tax-rule-change impact
- Compliance: regulatory-amendment-to-internal-rule lead time, regulations with active internal mappings, open critical alerts

### 6.12 Norm Lineage Tracker

A first-class subsystem that:

- Walks the `derives_from` graph upward from any rule to the highest-tier norm.
- Subscribes to upstream-amendment signals (manual entry plus optional integrations with official gazettes).
- Flags downstream rules for review when an upstream change occurs.
- Displays the lineage as a navigable tree in the `/legal/lineage/` and `/compliance/regulatory/` pages.
- Computes the "regulatory-change response time" KPI.

### 6.13 Multi-Language Support

- `Rule.locale` defines the canonical language.
- `Rule.statement_translations` holds parallel-language versions (e.g., EN/JA contracts).
- The evaluation engine selects the rule statement matching `subject.locale` when available.
- A periodic worker (`verify_translation_drift`) uses the LLM to compare translations and flags semantic drift for human review.
- Per-pack default locale is configurable; Japanese is supported as a first-class locale alongside English.

### 6.14 Extraction Pipeline

The extraction pipeline ingests source documents (contracts, regulations, policy PDFs, employee handbooks, marketing checklists, code documentation) and proposes candidate rules through a multi-stage process:

1. **Format detection**: PDF / docx / markdown / txt / XML / HTML.
2. **Structural parsing**: chapter / article / paragraph / item / appendix; section hierarchy preservation.
3. **Cross-reference resolution**: "the preceding article", "Article 5, paragraph 2", "the foregoing".
4. **Bilingual pairing** (when applicable): pair source-language and target-language clauses.
5. **Normative-sentence detection**: identify statements that express an obligation, permission, or prohibition.
6. **Coreference resolution**: complete elided subjects.
7. **Metadata inference**: infer `modality`, `severity`, `applies_to_surfaces`, `tech_scope`, `org_scope`, `norm_tier`.
8. **Relationship suggestion**: propose `refines`, `derives_from`, `conflicts_with`, `succeeds` candidates against the existing corpus.
9. **Human review**: every candidate goes through approve / edit / dismiss.

### 6.15 Automatic Rule Discovery

Bootstraps rules that already exist implicitly in an organization's artifacts. Source analyzers cover:

- `claude_md.py` — agent instruction files
- `linter_config.py` — engineering linter configurations
- `code_patterns.py` — code-base conventions
- `policy_pdf.py` — corporate policy PDFs
- `handbook_md.py` — employee handbooks
- `contract_template.py` — contract templates
- `regulation_xml.py` — regulation files in standard XML formats
- `sales_playbook.py` — sales playbooks
- `ad_compliance_doc.py` — marketing legal-review checklists

Patterns detected independently from multiple sources receive higher confidence. Gemini refines patterns into structured rule candidates. Humans approve.

### 6.16 Correction Feedback Loop

Captures human corrections of AI-generated work — initially code, generalized to any surface — and converts them into rule improvements.

- **Correction capture**: surface-specific (PR-based for code, redline-based for contracts, post-edit detection for documents and messages).
- **Correction analyzer**: classifies as `new_rule`, `improve_existing`, or `adjust_scope`.
- **Auto-drafter**: clusters similar corrections and uses Gemini to draft candidate rule proposals.
- **One-click approval**: approved drafts start with `maturity_level = experimental` (shadow mode).
- **Effectiveness tracking**: precision, prevention rate, and adoption feed the auto-promotion / auto-demotion workers.

### 6.17 Rule Enforcement Gateway

Event-driven, zero-code rule enforcement via webhooks. Receives events at `/api/v1/gateway/ingest/{source}`, normalizes them via the Connector layer into Subjects, matches enforcement policies, and triggers evaluations. Default normalizers cover GitHub, Slack, Email, Salesforce, Workday, SAP, DocuSign, Kintone, Teams, and a generic webhook normalizer.

### 6.18 Other Components (Continued)

The remaining components from the prior architecture are preserved and operate identically across surfaces:

- **Proposals** — Multi-approver rule-change governance with conflict analysis and impact preview.
- **Agent Governance** — Trust levels, mastery tracking, personalized rules, verdict challenges, exception requests, governance sessions. Generalized to any `Actor`.
- **Playground** — Sandbox evaluation and per-rule test cases for any surface.
- **Snapshots** — Versioned, environment-deployable rule sets with rollback and impact simulation.
- **Alerts** — Background workers detect dormant rules, high deny rates, health decline, conflicts, effectiveness decline.
- **Audit Log** — Immutable, hash-chained, surface-aware retention.

---

## 7. Key Features

### 7.1 Foundational

- Natural-language rule storage with full provenance.
- Multi-modal search (full-text, vector, category, hybrid, context).
- Rule lifecycle: draft → review → approved → effective → superseded → retired.
- REST API, Intent API, Evaluate API, Gateway API.
- Python SDKs (Rule Client, Agentic Rule Client) and CLI.

### 7.2 Differentiating

- **Subject / Surface abstraction**: code, contract, action, transaction, document, message — one engine, many surfaces.
- **Domain Pack architecture**: business-domain bundles ship rules + adapters + UI together.
- **Norm Lineage**: Law → Regulation → Policy → Operational Rule, with upstream-change propagation.
- **Persona-Specific Consoles**: Legal, HR, Finance, Compliance, Engineering, Admin.
- **Conflict Detector** continuously scans for `conflicts_with` candidates across the corpus.
- **Counterexample Generator** for each rule, generating compliant and non-compliant test cases.
- **Rule Coverage** identifies dormant and over-triggered rules using event logs.
- **Change Impact Simulator** replays history against proposed rule revisions.
- **Refinement Feedback Loop** identifies ambiguous wording and proposes rewrites.
- **Polyglot Rules** maintains semantically equivalent rule pairs across languages and verifies equivalence.
- **Why API** returns multi-level rationale, traversing both `rationale` and `norm_lineage`.
- **Automatic Rule Discovery** bootstraps rules from CLAUDE.md, linter configs, code patterns, policy PDFs, handbooks, contract templates, regulatory XML.
- **Correction Feedback Loop** turns every human fix into a candidate rule.
- **Cross-Project Federation** with org → team → project inheritance.
- **Rule Playground** sandbox testing.
- **Proactive Alerts** for dormant rules, deny rates, effectiveness decline, conflicts.
- **Versioned Snapshots** atomic deployment with rollback and simulation.
- **Autonomous Agent Governance** generalized to any `Actor`.
- **Collaborative Proposals** for multi-approver rule changes.
- **Multi-Language Support** with bilingual drift detection.

### 7.3 Cross-Cutting

- Immutable audit log with hash-chained integrity, **surface-aware retention**.
- Tiered LLM strategy: small/fast for screening, large/accurate for high-severity, optional consensus for `CRITICAL`.
- **Surface-aware PII sanitization**.
- RBAC per rule category with Owner / Approver / Reader separation.
- All evaluation calls record `surface`, `locale`, `actor.kind`, `prompt_version`, `model_id` for slicing.

---

## 8. Use Cases

### 8.1 Contract Review (Legal)

The contract management system stores contracts under negotiation. The Rule Repository holds internal procurement rules, prior contract clauses, and regulatory references. When a new draft contract is uploaded, the Contract Pack splits it into clauses, the Agentic Rule Client checks each clause against the policy corpus and prior contracts, and the legal console displays a clause-level redline view with conflict highlights and suggested standard alternatives.

### 8.2 HR / Attendance Management

The HR system registers attendance, leaves, and overtime. The HR Pack holds work regulations, the Labor Standards Act–derived rules, and 36-agreement constraints. The Agentic Rule Client validates each registration in `preflight` mode and alerts on violations (monthly overtime exceeding the legal limit, missing 36-agreement filing). The HR console aggregates violations by employee and by team, and the HR pack tracks 36-agreement headroom in real time.

### 8.3 Expense Audit (Finance)

The expense reporting system submits new claims to the Rule Repository in `posthoc` mode. The Expense Pack holds the travel and entertainment policy, tax rules (consumption tax, deductibility limits), and approval-route requirements. The system flags violating claims for human review, and the finance console shows the monthly rejection rate and top violation categories.

### 8.4 Communication Compliance

Slack and email connectors send messages to the Rule Repository in `sidecar` mode. The Communication Pack holds rules for harassment, customer-data confidentiality, regulated-substance discussion, and product-claim accuracy. Flagged messages are escalated to the compliance console without blocking the sender's normal workflow.

### 8.5 Procurement and Vendor Management

The procurement system submits new vendor onboarding events and purchase orders to the Rule Repository. The Procurement Pack holds the procurement policy, anti-corruption rules, anti-social-forces screening rules, and country-risk constraints. High-risk vendors are flagged for enhanced due diligence.

### 8.6 Software Development (Code)

The Code Pack — the most mature pack today — holds the engineering team's coding standards, documentation conventions, and review checklists. CI pipelines use the Rule Client to evaluate pull requests; agent hooks deliver applicable rules to coding agents at the moment of edit; and the engineering console tracks compliance trends, top violated rules, and the correction-to-rule flywheel.

### 8.7 Regulatory Compliance

A financial institution stores regulations (consumer protection, KYC, AML) in the repository, with derived internal procedures linked via `derives_from`. When a regulation is amended, the Norm Lineage Tracker identifies all downstream procedures that need review and the compliance console reports the regulatory-amendment-to-internal-rule lead time.

### 8.8 Cross-Domain Compliance Officer Workflow

A compliance officer using the `(compliance)` console sees:

- A unified view of the regulatory landscape applicable to the organization.
- Active alerts across all domains (legal, HR, finance, communication, sales).
- The regulatory-amendment-to-internal-rule median lead time.
- Cross-domain incidents (e.g., a vendor flagged in procurement *and* a contract under review with that vendor).

### 8.9 AI-Assisted Work (Cross-Surface)

Any AI agent — coding agent, contract-review agent, expense-review assistant, HR-policy Q&A bot — connects to the same MCP server. Each agent uses surface-appropriate tools (`evaluate_subject`, `get_applicable_rules`, `check_action`, `find_clause_conflicts`) and operates under the same Agent Governance regime (trust levels, personalized rules, verdict challenges).

---

## 9. Technical Stack

| Layer | Technology |
|---|---|
| Language (server) | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Language (frontend) | TypeScript, React 19, Next.js 15, Tailwind CSS |
| Language (clients) | Python (Rule Client, Agentic Rule Client), TypeScript (planned) |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Document storage | S3-compatible object storage |
| Relational store | PostgreSQL 17 |
| Search | Elasticsearch 8.17 (full-text + dense vector) |
| Graph | Neo4j 5 |
| Cache / Jobs | Redis 7 + arq |
| MCP | FastMCP (mcp ≥ 1.9) |
| Auth | OIDC / OAuth2 |
| Deployment | Container-native, Kubernetes-ready |
| Local orchestration | Docker Compose |

The architecture intentionally avoids hard-coding a single LLM provider. The `Evaluator` interface accepts any model that can perform structured judgment.

---

## 10. Cross-Cutting Concerns

### 10.1 Two Orthogonal Hierarchies (Recap)

- `tech_scope`: file globs, languages, services, systems.
- `org_scope`: departments, teams, roles, regions.
- `norm_tier`: LAW → REGULATION → GUIDELINE → CORPORATE_POLICY → DEPARTMENT_RULE → OPERATIONAL_RULE.
- `Federation`: organizational tree (Org → Team → Project).
- These are queried separately and rendered separately.

### 10.2 Surface-Aware Audit Retention

| Surface | Default retention |
|---|---|
| `code` | 1 year |
| `contract` | 10 years |
| `human_action` | 7 years |
| `transaction` | 10 years (tax-law-driven) |
| `document` | 10 years |
| `message` | 3 years |
| `generic` | 7 years |

Configurable per deployment and per scope.

### 10.3 Surface-Aware PII Sanitization

Each Surface Adapter ships a `pii.py` module with surface-appropriate sanitization rules. Code redacts secrets and tokens; HR redacts employee names by default; finance redacts bank/card numbers; messages redact email addresses and customer IDs; contracts redact natural-person names where rules don't depend on them.

### 10.4 Multi-Locale Operations

Japanese is a first-class locale. Sample data, evaluation prompts, and UI labels support `en` and `ja` at parity. Adding additional locales requires only translations and locale-tagged sample rules.

---

## 11. Roadmap

The project has two eras: the **historical phases (1–6)** that built the foundation but drifted toward code-only use, and the **corrective phases (7+)** that re-establish the cross-organizational mission while preserving 80% of the historical implementation.

### Phase 1 — Foundation [COMPLETE]

Rule data model, persistence, document ingestion, multi-modal search, REST + Intent APIs, Python SDK, basic governance.

### Phase 2 — Enforcement [COMPLETE]

Code-Aware Evaluation Engine, MCP server, GitHub PR review, CI CLI, agent hooks, Rule Enforcement Gateway, Rule Intelligence.

### Phase 3 — Discovery & Learning [COMPLETE]

Automatic Rule Discovery, Correction Feedback Loop, Cross-Project Federation.

### Phase 3.5 — Adoption Acceleration [COMPLETE]

GitHub one-click import, automatic PR correction capture, rule impact preview, conflict resolution transparency.

### Phase 4 — Testing & Deployment Safety [COMPLETE]

Rule Playground, Per-Rule Test Cases, Proactive Alerts, Snapshots.

### Phase 5 — Self-Improving Governance [COMPLETE]

Batched Evaluation, Evaluation Persistence, Outcome-Oriented Dashboard, Correction-to-Rule Flywheel, Active Rule Injection (Claude Code hooks), Zero-Config Bootstrapping, Structured Remediation, Rule Maturity Model, Advanced Intelligence (agent tracking, effectiveness scores, weekly digest, team comparison), Infrastructure Tiers.

### Phase 6 — Platform & Ecosystem [COMPLETE]

Collaborative Governance Workflow (Proposals), Autonomous Agent Governance.

### Phase 7 — Stop the Bleeding [PRIORITY]

Goal: prevent further drift while planning the structural fix.

- **Freeze new feature work** on Agent Governance, Federation, Snapshots additions. In-flight Phase 5–6 sub-features may complete; new ones do not start.
- **Rewrite README** to lead with cross-organizational mission. Code becomes one example, not the cover story.
- **Update PROJECT.md §6** to position Code-Aware Evaluation as the Code Surface Adapter, not the differentiator.
- **Set GitHub About**: "Cross-organizational normative management for laws, contracts, policies, and operations."
- **Add Topics**: `governance`, `compliance`, `regtech`, `legal-tech`, `policy-management`, `rule-engine`, `semantic-governance`, `llm-as-judge`. Remove or relegate code-only topics.
- **Add Contract Pack v0.1 seed** (3 NDA-derived rules, 3 MSA-derived rules) and **HR Pack v0.1 seed** (5 Labor-Standards-Act-derived rules). Make `make seed` install these alongside (not after) code samples.

**Value delivered**: "The project is once again recognizable as a cross-organizational normative platform."

### Phase 8 — Surface Abstraction

Goal: introduce the `Subject` / `Surface` model and reorganize the evaluation core.

- Define `Surface`, `Subject`, `Actor` in `domain/evaluation.py`.
- Move `diff_parser.py` and the code-specific portions of `context_assembler.py` into `services/evaluation/surfaces/code/`.
- Author `evaluate_subject.txt` (universal prompt) with surface-specific hint files.
- Add `POST /api/v1/evaluate/{surface}` endpoint; keep `POST /api/v1/evaluate` as backwards-compatible code path.
- Add `applies_to_surfaces` to the Rule model (migration); backfill existing rules to `[Surface.CODE]`.
- Split `scope` into `tech_scope` and `org_scope` (migration with heuristic split + manual review).
- Replace `agent_id` with `Actor` reference (migration with backwards-compatible alias).

**Value delivered**: "The evaluation engine is surface-agnostic. New domains are now an additive change, not a core refactor."

### Phase 9 — First Non-Code Domain Pack (Contract)

Goal: ship the cross-organizational mission with concrete proof.

- Build **Contract Pack** end-to-end:
  - Surface adapter: `surfaces/contract/`
  - Ingestion: `docx_clause_extractor.py`, `redline_differ.py`, `clause_normalizer.py`
  - Rules: 30+ template clauses (NDA, MSA, SOW)
  - UI: `(legal)/contracts`, `(legal)/clauses`, `(legal)/redlines`
  - Sample data: 3 anonymized contracts across NDA / MSA / SOW
- Add `(legal)` persona pages.
- Run a real legal-team pilot. Publish results.

**Value delivered**: "Legal teams have a working contract-review tool."

### Phase 10 — Norm Lineage and Multi-Language

Goal: support regulatory tracking and bilingual operations.

- Add `norm_tier` and `norm_authority` columns. Build the Norm Lineage Viewer.
- Implement upstream-amendment propagation: when a `LAW` rule's `effective_period.valid_until` is updated, all transitive `derives_from` descendants are flagged.
- Add `locale` and `statement_translations` to the Rule model.
- Implement the bilingual drift checker (worker).
- Add Japanese sample rules sourced from 労働基準法 / 個人情報保護法 / 会社法.

**Value delivered**: "Regulatory changes are tracked. Bilingual operations are supported."

### Phase 11 — Second and Third Domain Packs

Goal: prove the Domain Pack architecture is general.

- **HR Pack**: HRIS connector (Workday at minimum), `human_action` adapter, 36-agreement tracking, overtime-violation alerting, `(hr)` persona pages.
- **Communication Pack**: Slack and email connectors, customer-correspondence compliance, harassment / data-leak scanning.
- **Finance Pack** (alongside or after): expense audit, transaction adapter, `(finance)` persona pages.

**Value delivered**: "Three domain packs in production. The architecture is proven."

### Phase 12 — Connector Layer Maturation

Goal: integrate with the business systems where work actually happens.

- Implement Salesforce, Workday, SAP, DocuSign, Kintone, Teams connectors per pilot demand.
- Standardize the `SubjectConnector` ABC and document the contract.
- Add `(compliance)` persona console with cross-domain views.

**Value delivered**: "The Rule Repository works inside the SaaS landscape, not just GitHub."

### Phase 13 — Self-Improving Cross-Organization Governance

Goal: organizations co-improve through anonymized aggregate insights.

- Anonymized cross-organization effectiveness metrics (opt-in).
- Pack-level continuous improvement: highest-effectiveness pack version becomes the public canonical.
- Federated correction feedback (opt-in): corrections from one organization improve the upstream pack for all subscribers.

**Value delivered**: "Organizations using the Rule Repository improve faster together than alone."

---

## 12. Success Metrics

- **Coverage** — percentage of rules in target source documents successfully extracted, registered, and active.
- **Surface coverage** — number of surfaces in production use; target ≥ 4 by end of Phase 11.
- **Latency** — p50 / p95 / p99 evaluation latency in `preflight` mode, by surface.
- **Accuracy** — human-rated correctness of verdicts, by surface; precision and recall on conflict detection.
- **Regulatory-change response time** — median days from upstream amendment to approved internal-rule revision; target < 14 days for HIGH/CRITICAL norms.
- **Bilingual drift** — percentage of rules with parallel-language statements that pass the drift checker.
- **Adoption** — number of integrated systems and active rules per surface; volume of evaluation requests per day per surface.
- **Persona NPS** — separate NPS measurement for Legal, HR, Finance, Compliance, Engineering personas.
- **Governance health** — percentage of rules with complete metadata, current rationale, active owners.
- **Shadow-to-enforcement rate** — > 70% of experimental rules reach stable within 60 days.
- **Auto-fix rate** — > 40% of SHOULD violations auto-fixed via structured remediations (where applicable to the surface).
- **Flywheel throughput** — > 5 rules/month auto-drafted from correction clusters per active pack.
- **Time-to-rule** — < 1 week from correction-pattern detection to approved rule.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Always log full evaluation context (surface, locale, prompt version, model); require human review on high-severity denials; consensus voting for CRITICAL rules; refinement feedback loop. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity; refinement loop suggests rewrites; per-rule test cases mandatory for proven-tier rules. |
| LLM costs scale poorly with corpus size | Two-stage selection (metadata pre-filter, then LLM); aggressive caching; tiered model selection; batched evaluation. |
| Sensitive data leaks through evaluation context | Surface-aware PII sanitization; log masking; tenant isolation; optional self-hosted model deployment. |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via `effective_period`; sidecar mode for shadow testing; snapshots with rollback. |
| Over-reliance reduces human judgment | Decision support, not decision replacement; preserve rationale visibility; require human approval for rule revisions; agent verdict-challenge mechanism. |
| Cross-locale evaluation drift | Bilingual drift checker; explicit `cross_locale_evaluation` warnings in the audit log; periodic LLM-based equivalence verification. |
| Regulatory tracking gaps (missing upstream amendments) | Manual entry as the primary mechanism; optional integrations with official gazettes as a force-multiplier; humans remain accountable for catching changes the system misses. |
| Domain Pack quality varies | Pack effectiveness scores; "certified" badging; community review; required external domain reviewer at curation time. |
| Conflicts with existing IAM / GRC tools | Position the Rule Repository as a complementary semantic layer; provide integration points rather than competing with baseline controls. |
| The drift toward dev recurs | Architectural separation enforced by directory layout (`surfaces/`, `domain_packs/`); no surface-specific code in `services/evaluation/core/`; non-code packs reach 3+ before any new code-only feature lands. |

---

## 14. Glossary

- **Rule** — a natural-language normative statement plus structured metadata, managed as a first-class object.
- **Statement** — the canonical natural-language text of a rule.
- **Surface** — a kind of thing that can be evaluated (CODE, CONTRACT, HUMAN_ACTION, TRANSACTION, DOCUMENT, MESSAGE, GENERIC).
- **Subject** — an instance of a surface, the unit of evaluation.
- **Actor** — the entity whose action is under evaluation (human / system / agent).
- **Modality** — strength of obligation (MUST, MUST_NOT, SHOULD, MAY, INFO).
- **Severity** — consequence level (LOW, MEDIUM, HIGH, CRITICAL).
- **tech_scope** — technical scope (file globs, languages, services).
- **org_scope** — organizational scope (departments, teams, roles, regions).
- **Verdict** — result of an evaluation (ALLOW, DENY, NEEDS_CONFIRMATION).
- **Reason graph** — structured DAG explaining which facts triggered which conditions in which rules.
- **Norm Lineage** — the chain of derivation from upstream legal/regulatory authority to operational rule.
- **norm_tier** — position on the Norm Lineage (LAW → REGULATION → GUIDELINE → CORPORATE_POLICY → DEPARTMENT_RULE → OPERATIONAL_RULE).
- **Federation** — organizational hierarchy axis (org → team → project).
- **Domain Pack** — a vertical bundle of rules, adapters, prompts, UI, and samples for one business domain.
- **Surface Adapter** — a pluggable module that translates a surface's input format into Subjects and provides surface-specific hints.
- **Connector** — an adapter to an external business system that emits events as Subjects.
- **Meta-rule** — a rule whose subject is other rules.
- **LLM-as-Judge** — the architectural pattern of using an LLM to evaluate compliance with a natural-language rule.
- **Preflight / Posthoc / Sidecar** — three modes of integration: before-action, after-action, parallel-observation.
- **Maturity Level** — `experimental` / `stable` / `proven`. Experimental rules run in shadow mode.
- **Persona Console** — frontend area aligned with one role's workflow (Legal, HR, Finance, Compliance, Engineering, Admin).

---

## 15. Open Questions

These will be resolved during Phase 7–9:

- What is the canonical schema for `org_scope`? Free-form tags vs. structured department/role tuples.
- How are upstream-norm-amendment signals delivered? Manual UI entry only, or optional integrations with official sources?
- What is the SLO for `preflight` evaluations by surface? This drives model selection and caching strategy per surface.
- Should the audit log be exposed to tenants in raw form, or only as derived reports?
- What is the multi-tenant isolation model? Single-tenant first, or multi-tenant from day one?
- How are deprecated rules archived without losing the ability to re-evaluate historical events?
- For bilingual rules, when EN and JA say slightly different things, which is canonical? Is the canonical locale always the rule's `locale` field, or can per-jurisdiction overrides apply?

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect.*
