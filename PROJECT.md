# Rule Repository

> A cross-organization norm management platform — store, search, evaluate, and enforce natural-language rules across legal, HR, finance, engineering, sales, and beyond, powered by LLMs and AI agents.

This document is the canonical specification for the Rule Repository project. It defines the vision, domain model, architecture, components, and roadmap. Implementation details and operational guidance for contributors live in `CLAUDE.md`. Implementation history is recorded in `docs/09_changelog/`.

---

## 1. Project Overview

The **Rule Repository** is a system that stores human-authored norms in their original natural-language form and makes them operationally useful: searchable, applicable, and enforceable across business systems, AI agents, and software development environments. Where traditional rule engines require translating human rules into a formal language (and losing nuance in the process), the Rule Repository keeps the rule as written and uses LLMs and AI agents to interpret, search, and enforce them at runtime.

### 1.1 Primary positioning

The Rule Repository is **a cross-organization norm management platform**. A single deployment serves the whole organization — General Counsel, HR business partners, Compliance Officers, Engineering Managers, Sales Operations, and beyond — with one canonical store for the rules that govern the business.

Different organizational functions have different rule sources, different consumption patterns, and different enforcement models. The Rule Repository unifies these under one substrate while accommodating each function's specific needs through:

- A **domain-neutral evaluation core** that delegates to domain-specific evaluators (code, document, content, transaction, form, conversation, factual query)
- A **Fact Store** that resolves external facts (employee state, sanctions list status, contract metadata) at evaluation time
- A **persona-driven UX** with dedicated entry points for legal, HR, compliance, security, and engineering personas
- **Connectors to business systems** — HRIS, CRM, ERP, contract management, ITSM, regulatory feeds — so rules are evaluated where work happens

### 1.2 Inspiration and differentiation

This approach generalizes the concept of **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea in four directions:

- **Wider scope of rules**: not only AI agent guardrails, but laws, regulations, contracts, HR policies, engineering rules, content guidelines, transaction policies, and documentation conventions
- **Wider scope of consumers**: human users, business systems (HRIS/CRM/ERP), IDEs, CI pipelines, customer-facing applications, and AI agents
- **Wider scope of evaluation timing**: pre-flight checks, post-hoc audits, sidecar observation, and continuous compliance monitoring
- **Wider scope of organizational coverage**: from a single team's coding rules to organization-wide regulatory frameworks like J-SOX, GDPR, or EU AI Act

The Rule Repository fills a gap that no current category of software addresses cleanly:

| Existing category | What it does | What it misses |
|---|---|---|
| Document management systems | Stores source documents | Doesn't understand the rules inside them |
| Rule engines (Drools, DMN, OPA) | Executes formally encoded rules | Loses the original semantics; expensive to maintain |
| GRC platforms (Drata, Vanta, OneTrust) | Tracks compliance status | Doesn't enforce rules at the point of action |
| Semantic Governance products | Applies natural-language constraints | Binds them to specific AI agents, not as organization-wide assets |
| Contract Lifecycle Management | Manages contract documents | Doesn't connect to other organizational rule sources |
| Compliance training platforms | Educates humans | Doesn't enforce or evaluate compliance |

The Rule Repository treats **rules themselves as first-class, versioned, governed assets**, decoupled from any single consumer and reusable across the entire organization.

### 1.3 Core design principles

1. **Statement is the source of truth.** The natural-language rule statement is the canonical form. Structured metadata exists for indexing, filtering, and prioritization — never to override the meaning of the statement.
2. **Domain-neutral core, domain-specific edges.** The evaluation orchestrator, rule selector, and verdict aggregator know nothing about code or contracts or HR forms. Each domain is a plugin.
3. **Postgres is the system of record.** Elasticsearch is a derived search index. Neo4j is a derived relationship graph. If they disagree, Postgres wins and derivatives are rebuilt.
4. **Tenant isolation is mandatory.** Every business object carries a `tenant_id`. Cross-tenant access is impossible by construction, not by convention.
5. **LLM verdicts are decision support, not decision automation.** High-severity verdicts route to humans. Every verdict is reproducible (model, prompt, inputs, outputs are logged).
6. **No rule is ever deleted.** Rules retire via `effective_period.valid_until`. Past evaluations remain re-explainable.
7. **Quality is measurable.** An eval harness with golden datasets per domain provides objective verdict-quality metrics. New domains do not go to production without baseline metrics.

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository operates in this design space, but with a deliberate organizational scope. Many existing products solve part of the problem for one persona (legal counsel or HR operations or platform engineers), but none solve it for the organization as a whole. As a result:

- Legal rules live in a contract management system, accessible only to legal
- HR policies live in a handbook PDF, with no programmatic access
- Engineering rules live in CLAUDE.md and linter configs, invisible to other teams
- Regulatory updates require manual cross-walks between source law, internal policy, and contract templates
- An employee, contractor, or AI agent has no single place to ask "what rules apply to what I'm about to do?"

The Rule Repository is the answer to that question.

---

## 3. Goals and Non-Goals

### 3.1 Goals

**Storage and discovery**
- Store rules in natural language, with full traceability to their source documents (laws, contracts, policy PDFs, handbooks, configs)
- Provide rich search (full-text, vector, category, hybrid, intent-based, contextual) over rule corpora across all domains
- Bootstrap rules from existing artifacts: contract templates, HR handbooks, statutory PDFs, code, linter configs, wiki pages

**Evaluation**
- Enable runtime evaluation across multiple input types (code change, document, content, transaction, form, conversation, factual query)
- Resolve external facts (employee state, sanctions data, contract metadata) at evaluation time via a Fact Store
- Support pre-flight, post-hoc, and sidecar enforcement modes
- Produce reproducible verdicts with reason graphs, repair suggestions, and structured remediation

**Governance**
- Make rule provenance, rationale, jurisdiction, legal force, and revision history first-class
- Detect conflicts, redundancies, and dead rules across the corpus
- Provide approval workflows differentiated by rule category, with segregation of duties
- Track regulatory amendments and propagate impact through `derives_from` lineage

**Operations and platform**
- Provide ergonomic SDKs (Python, eventually TypeScript) and CLI tools so business systems and AI agents can integrate easily
- Multi-tenant isolation by construction; SSO, SCIM, ABAC, regional data routing
- Connectors to common business systems (HRIS, CRM, ERP, contract management, ITSM, regulatory feeds)
- Persona-driven UX — Legal, HR, Compliance, Security, Engineering each have a dedicated entry point

**Quality and trust**
- Eval harness with golden datasets per domain; no domain ships without baseline metrics
- Hash-chained, immutable audit log of every evaluation with model, prompt, inputs, outputs
- PII redaction, right-to-erasure, customer-managed encryption keys
- Verdict quality is measurable, monitored, and auditable

### 3.2 Non-Goals

- Replacing IAM, RBAC at the network or application layer, or cloud-native policy engines like OPA. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline access control.
- Replacing legal counsel, compliance officers, HR business partners, or any other human professional. The system surfaces issues and supports decisions; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts, employment agreements, or regulatory filings on behalf of users.
- Providing exhaustive coverage of every regulation in every jurisdiction out of the box. Regulatory content is a curation effort, not a code effort.
- Operating as a fully autonomous decision-maker on high-severity matters. Human approval is required for `CRITICAL` rule changes and `DENY` verdicts on `legal_force=statutory` rules by default.

---

## 4. Architecture

The system is composed of a domain-neutral core, a plugin layer for domain-specific behavior, a Fact Store for external data resolution, and an integration surface for human and machine consumers.

### 4.1 Architectural overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                           │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                    Domain-Neutral Core                          │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────────┐  │  │
│  │  │ Storage   │  │ Search    │  │ Evaluation│  │ Governance  │  │  │
│  │  │ (Rule,    │  │ (FT/Vec/  │  │ Orches-   │  │ (Proposals, │  │  │
│  │  │  Bundle,  │  │  Hybrid/  │  │ trator    │  │  Approvals, │  │  │
│  │  │ Snapshot) │  │  Context) │  │           │  │  SoD)       │  │  │
│  │  └───────────┘  └───────────┘  └───────────┘  └─────────────┘  │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────────┐  │  │
│  │  │ Fact      │  │ Audit Log │  │ Tenant /  │  │ Eval        │  │  │
│  │  │ Store     │  │ (hash-    │  │ Identity  │  │ Harness     │  │  │
│  │  │           │  │  chained) │  │ (RBAC/ABAC│  │ (golden     │  │  │
│  │  │           │  │           │  │  /SoD)    │  │  datasets)  │  │  │
│  │  └───────────┘  └───────────┘  └───────────┘  └─────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                       Domain Plugins                            │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐  │  │
│  │  │Engineer-│ │ Legal/  │ │   HR    │ │ Finance │ │ Marketing│  │  │
│  │  │  ing    │ │Contract │ │/ Labor  │ │ /Procur.│ │ /Content │  │  │
│  │  │         │ │         │ │         │ │         │ │          │  │  │
│  │  │ Code    │ │ Document│ │ Form    │ │ Trans-  │ │ Content  │  │  │
│  │  │ Evalua- │ │ Evalua- │ │ Evalua- │ │ action  │ │ Evalua-  │  │  │
│  │  │ tor     │ │ tor     │ │ tor     │ │ Evalu.  │ │ tor      │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘  │  │
│  │                                                                 │  │
│  │  Each plugin: extractors, evaluators, prompts, persona UX,      │  │
│  │  golden dataset, connectors                                     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │              Connector Hub & Integration Surface                │  │
│  │   HRIS │ CRM │ Contract │ ERP │ ITSM │ Office │ Regulatory      │  │
│  │   Workday/SmartHR │ Salesforce │ DocuSign │ SAP │ ServiceNow    │  │
│  │   M365/GWS │ e-Gov/EUR-Lex/Federal Register                     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│   REST API │ Intent API │ Evaluate API │ Gateway API │ MCP Server     │
└──────────────┬──────────────────────────────────────────────┬──────────┘
               │                                              │
   ┌───────────┼──────────────┬──────────────┬───────────────┼──────────┐
   │           │              │              │               │          │
┌──▼───┐  ┌────▼────┐  ┌─────▼─────┐  ┌────▼────┐  ┌──────▼─────┐  ┌──▼──────┐
│ Rule │  │ Agentic │  │ MCP Tools │  │  CLI    │  │  Connector │  │ Persona │
│ SDK  │  │  SDK    │  │ (12+ tools│  │ rulerepo│  │  Webhooks  │  │ Portals │
│      │  │         │  │  + agent  │  │ -check, │  │            │  │ (Legal, │
│      │  │         │  │   gov)    │  │ -hook,  │  │            │  │  HR,    │
│      │  │         │  │           │  │ -ingest │  │            │  │ Compl.) │
└──────┘  └─────────┘  └───────────┘  └─────────┘  └────────────┘  └─────────┘
```

### 4.2 Layering rules

- The **Domain-Neutral Core** has no knowledge of code, contracts, employees, or any specific domain artifact. Its types are `Rule`, `RuleSet`, `EvaluationContext` (opaque payload), `Verdict`, `ReasonGraph`, `Tenant`, `Bundle`, `Snapshot`.
- **Domain Plugins** consume the core via stable interfaces. They register `Evaluator`, `Extractor`, `FeedbackSource`, and `Connector` implementations. They never modify core code.
- **Integration Surface** (REST/MCP/CLI/SDKs) exposes core functionality plus plugin-specific endpoints. Plugins register their own routes under `/api/v1/plugins/<name>/`.
- **Tenant Isolation** is enforced at every layer. The core mediates all access; plugins receive tenant-scoped views; the integration surface derives `tenant_id` from the authenticated principal, never from the request body.

### 4.3 Trust and data boundaries

- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and judgments they are authorized to see, scoped by tenant, ABAC policy, and rule classification.
- All evaluation calls produce immutable audit records on the server side.
- LLM calls happen only inside the core (via `services/evaluation/` and `services/extraction/`), never inside plugins or the integration surface. This ensures that prompts, model selection, and audit logging are uniform.
- Sensitive fields are tagged with classification levels and redacted before transmission to LLMs.

---

## 5. Domain Model

### 5.1 The `Rule` entity

A rule is the central first-class object. It is **not** a regex or a code expression; it is a structured envelope around a natural-language statement.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Stable identifier |
| `tenant_id` | UUID | Tenant boundary; mandatory on every row |
| `domain` | enum | Top-level domain partition: `engineering`, `legal`, `hr`, `finance`, `marketing`, `procurement`, `security`, `general` |
| `statement` | text | The rule text in natural language (the canonical form) |
| `language` | ISO code | Primary language of the statement (`ja`, `en`, etc.) |
| `language_variants` | list[Rule ref] | Equivalent rules in other languages |
| `source_refs` | list[ref] | Pointers to the source document, section, and offset |
| `scope` | structured | Who/what the rule applies to (org units, roles, systems, regions, channels) |
| `modality` | enum | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `severity` | enum | LOW / MEDIUM / HIGH / CRITICAL |
| `consequence_type` | list[enum] | `criminal`, `civil_liability`, `administrative_fine`, `disciplinary`, `reputational`, `operational` |
| `legal_force` | enum | `statutory`, `regulatory`, `contractual`, `internal_policy`, `guidance`, `industry_norm` |
| `jurisdiction` | string | Legal jurisdiction (`JP`, `JP-13`, `US-CA`, `EU`, `GLOBAL`) |
| `governing_authority` | string | Issuing or controlling body |
| `effective_period` | range | `valid_from` / `valid_until` |
| `preconditions` | text | Facts required to evaluate the rule |
| `external_facts_required` | list[string] | Facts the Fact Store must resolve |
| `exceptions` | list[ref] | References to other rules or carve-outs |
| `interpretive_guidance` | list[ref] | Court rulings, circulars, Q&A documents |
| `binding_parties` | structured | Roles or entities the rule binds |
| `rationale` | text | Why the rule exists (purpose, intent) |
| `context` | text | Surrounding document context (section hierarchy, regulatory authority) |
| `tags` | list[string] | Free-form taxonomic labels |
| `governance` | structured | Owner, approvers, revision history |
| `maturity_level` | enum | `experimental`, `stable`, `proven` |
| `review_cadence` | enum | `annual`, `on_law_change`, `quarterly`, `none` |
| `last_reviewed_at` | timestamp | When the rule was last formally reviewed |
| `false_positive_count` | int | For maturity computation |
| `true_positive_count` | int | For maturity computation |
| `embedding` | vector | Derived |

The `statement` is the **source of truth**. Structured fields exist for indexing, filtering, and prioritization — never to override the meaning of the statement.

### 5.2 Rule relationships

Rules form a graph, not a flat list. Modeling these relationships explicitly is what turns the repository from a list into a **provenance and impact graph**.

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision that replaces a prior version |
| `interprets` | An administrative circular or court ruling that interprets a higher-level rule |
| `cites` | The rule cites another rule, case law, or authoritative source |
| `supersedes_in_jurisdiction` | Jurisdictional override (GDPR over a national law within EU member states) |
| `applies_when` | Conditional applicability where the condition itself is another rule |
| `cross_references` | Symmetric reference without strict hierarchy |

Postgres is the source of truth for relationship existence. Neo4j is the projection used for traversal and impact analysis. The reconciler script (`scripts/reconcile_graph.py`) rebuilds Neo4j from Postgres.

### 5.3 Tenant hierarchy

```
Tenant > Organization > Team > Project > Bundle
```

- **Tenant** is the billing and isolation boundary. All business data is partitioned by `tenant_id`.
- **Organization** is a legal entity inside a tenant. A multi-subsidiary group has multiple organizations under one tenant.
- **Team** is an internal organizational unit (legal, HR, engineering, sales).
- **Project** scopes rules to a specific initiative, codebase, or domain area.
- **Bundle** is purposeful grouping (`FY2026 Labor Law Compliance`, `IPO Readiness`, `EU AI Act`). Bundles cut across teams and projects.

Each level can carry rules. Rules at higher levels apply to all descendants (Federation). Project-level rules can override inherited rules.

### 5.4 `RuleBundle` — purposeful grouping

A `RuleBundle` is a curated set of rules unified by a business purpose, equivalent to a control framework in GRC platforms.

- `id`, `tenant_id`, `name`, `description`, `owner`
- `target_completion_date`
- Member rules (overlapping with other bundles is allowed)
- Status calculation: % effective, % with current owners, % evaluated in last 30 days
- Dashboard widgets show bundle progress

Bundles are how a Compliance Officer answers "where are we against J-SOX?" or how a Legal team tracks "EU AI Act readiness".

### 5.5 Meta-rules

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy"). Meta-rules are evaluated by the same engine but scoped to govern the rule corpus itself.

### 5.6 `Tenant`, `Identity`, and `Principal`

- `Tenant`: opaque identifier, billing reference, settings (data residency, LLM region, key management)
- `Organization`: legal entity within a tenant
- `User`: human identity, federated via OIDC/SAML
- `Group`: collection of users, provisioned via SCIM
- `ServiceAccount`: machine identity with scoped API keys
- `Principal`: the authenticated entity for any request (User or ServiceAccount), always carrying `tenant_id`
- `Role`: domain-aware role (e.g., `legal_director`, `dpo`, `hr_business_partner`, `engineering_manager`)
- `ABACPolicy`: declarative policy that gates access on principal attributes and resource attributes

### 5.7 `Verdict`, `ReasonGraph`, `Remediation`

- `Verdict`: `ALLOW`, `DENY`, `NEEDS_CONFIRMATION`
- `ReasonGraph`: structured DAG showing which facts triggered which conditions in which rules
- `Remediation`: structured fix proposal — type (`replace`/`insert`/`delete`/`rewrite`), location, original, replacement, description, `auto_applicable` flag

---

## 6. Components

### 6.1 Rule Management Server (Domain-Neutral Core)

The server is the system of record for all rules.

**Capabilities:**

- **Rule CRUD** with revision history and effective-date semantics
- **Tenant management**: tenant CRUD, settings, RLS enforcement
- **Identity and access**: OIDC/SAML SSO, SCIM provisioning, RBAC, ABAC policy evaluation, segregation-of-duties enforcement
- **Domain registry**: registers active domain plugins; plugin discovery at startup
- **Search APIs**: full-text, vector (semantic), category/tag, hybrid, context (given facts → applicable rules), impact (given proposed change → affected rules)
- **Intent API**: a natural-language endpoint that classifies the user's intent (`lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`, `regulatory_horizon`) and routes to the appropriate backend
- **Evaluation orchestrator**: domain-neutral pipeline that selects rules, calls the appropriate evaluator (from a domain plugin), aggregates verdicts, persists results, and returns a response
- **Fact Store**: registers fact providers, resolves required facts at evaluation time
- **Bundle and Snapshot management**: purposeful grouping and versioned freezes
- **Audit log**: append-only, hash-chained record of all evaluations including inputs, applied rules, model identity, prompt version, and verdict
- **Governance**: revision approval workflow with category-aware approval policies, mandatory consultation roles, SLA-bound approvals, emergency procedures
- **Eval Harness integration**: golden dataset management, regression runs, drift detection
- **Intelligence**: health scoring, analytics, recommendations, weekly digests

### 6.2 Evaluation Engine (Pluggable)

The evaluation engine is split into a domain-neutral orchestrator and pluggable evaluators.

**Orchestrator pipeline**: Tenant Resolution → Context Assembly → Fact Resolution → Rule Selection → Evaluator Dispatch → Verdict Aggregation → Persistence

**Evaluator plugins:**

| Evaluator | Input type | Domains | Status |
|---|---|---|---|
| `code_change` | unified diff, file path | engineering | Existing |
| `document` | document text or PDF | legal, hr, regulatory | Phase 7 |
| `content` | text, channel metadata | marketing | Phase 7 |
| `transaction` | structured transaction record | finance, procurement | Phase 7 |
| `form` | form fields | hr, finance | Phase 7 |
| `conversation` | chat log, transcript | sales, support | Phase 8 |
| `factual_query` | structured facts | general | Phase 7 |

Each evaluator owns its own prompt templates, input schema, output formatter, and golden dataset. They share the orchestrator's selection, batching, caching, aggregation, and persistence logic.

**Tiered model selection:**

- `minimal` thinking, Flash model: routine evaluation, high throughput
- `low` thinking, Flash model: standard evaluation
- `medium` thinking, Flash model: HIGH severity rules
- `high` thinking, Pro model: CRITICAL severity rules
- **Consensus voting**: for `legal_force=statutory` + `severity=CRITICAL`, three independent evaluations with different prompts; flag dissensus for human review

### 6.3 Fact Store

The Fact Store resolves external facts that no input artifact contains, but that rules depend on for accurate evaluation.

**Examples of facts resolved:**

- `36_agreement_status(employee_id, month)` — does a valid 36-agreement exist?
- `ofac_match(party_name, country)` — is the party on the OFAC sanctions list?
- `employee_grade(employee_id, date)` — what was the employee's grade on a given date?
- `product_regulatory_category(product_id)` — what regulatory category applies?
- `vendor_screening_status(vendor_id)` — is the vendor cleared by anti-social-forces screening?

**Fact Provider interface:**

```python
class FactProvider(Protocol):
    name: str
    domain: Domain
    async def supported_facts(self) -> list[FactSchema]: ...
    async def fetch(self, key: str, context: dict) -> Fact | None: ...
    async def health_check(self) -> bool: ...
```

**Initial providers (Phase 7):**
- `EmployeeAttributesProvider` — backed by HRIS sync table
- `OFACSanctionsProvider` — fetches and caches OFAC data
- `InternalMasterDataProvider` — generic key-value lookup against tenant master data
- `RegulatoryFeedProvider` — wraps regulatory feed integrations

**Caching and invalidation:** providers may declare TTL per fact type. Cached facts are tied to the evaluation cache key.

### 6.4 Domain Plugins

Each domain plugin is a self-contained module that registers extractors, evaluators, feedback sources, prompts, persona UX, golden datasets, and connectors with the core.

**Plugin contract:**

```python
class DomainPlugin(Protocol):
    name: Domain  # one of the domain enum values

    def register_evaluators(self, registry: EvaluatorRegistry) -> None: ...
    def register_extractors(self, registry: ExtractorRegistry) -> None: ...
    def register_feedback_sources(self, registry: FeedbackRegistry) -> None: ...
    def register_fact_providers(self, registry: FactStoreRegistry) -> None: ...
    def register_connectors(self, registry: ConnectorRegistry) -> None: ...
    def register_prompts(self, registry: PromptRegistry) -> None: ...
    def register_routes(self, app: FastAPI) -> None: ...
    def register_persona_views(self, registry: UIRegistry) -> None: ...
```

**Initial plugin set (Phase 7):**

- **Engineering plugin** (existing logic, refactored): code change evaluator, CLAUDE.md/linter discovery, PR correction capture, agent governance, code-aware MCP tools
- **HR/Labor plugin**: employee form evaluator, employee fact provider, HRIS connectors, attendance compliance dashboard, persona UX for HR business partners
- **Legal/Contract plugin**: clause-level extractor, document evaluator, standard clause library, contract diff API, persona UX for general counsel
- **Regulatory plugin**: regulatory feed integrations, amendment diff service, compliance horizon calendar, citation engine

### 6.5 Connector Hub

The Connector Hub provides bidirectional integration with business systems. Connectors implement two interfaces:

- `EventSource` — pushes events into the evaluation engine (preflight or sidecar)
- `Sink` — receives evaluation outcomes, alerts, and notifications

**Initial connectors (Phase 7):**

| Category | Connectors |
|---|---|
| HRIS | Workday, SuccessFactors, freee 人事労務, SmartHR |
| CRM | Salesforce, HubSpot |
| Contract management | DocuSign, Ironclad, LegalForce |
| ERP | SAP S/4, Oracle Cloud, NetSuite, freee 会計 |
| ITSM | ServiceNow, Jira Service Management |
| Office | Microsoft 365, Google Workspace |
| Communication | Slack, Microsoft Teams |
| Regulatory feeds | e-Gov 法令, Federal Register, EUR-Lex |

Each connector is a separately versioned package under `packages/connectors/<name>/`.

### 6.6 Eval Harness

The Eval Harness is a first-class quality system that measures verdict accuracy across domains.

**Components:**

- **Golden datasets per domain**: 50–200 expert-labeled cases for each of (engineering, legal, hr, content, transaction). Stored under `apps/server/eval/datasets/<domain>/`.
- **Regression runner**: nightly job that runs current prompts and models against golden datasets; reports precision, recall, F1, and per-case verdicts
- **Drift detector**: tracks scores over time; alerts on threshold violations
- **A/B testing framework**: routes a configured percentage of production traffic to a candidate prompt or model; tracks divergence
- **Tenant-bring-your-own-eval**: tenants upload their own golden datasets and run them against their tenant's configuration

**Quality gates:**
- A new domain plugin cannot ship until its golden dataset achieves baseline precision/recall thresholds
- A prompt change requires a regression run with no degradation
- A model upgrade requires a full eval-harness run

### 6.7 SDKs and CLI

**Rule Client (Python SDK):** thin wrapper over server APIs.

```python
from rulerepo import RuleClient

async with RuleClient(server_url, api_key) as client:
    rules = await client.search.hybrid("overtime monthly limit", domain="hr")
    rule = await client.rules.get(rule_id)
    await client.rules.update(rule.id, statement=..., revision_note=...)
```

**Agentic Rule Client (Python SDK):** higher-level client for systems that need to **enforce** rules.

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient(server_url, scope="hr/attendance") as client:
    result = await client.evaluate(
        evaluator_type="form",
        context={"employee_id": "E001", "month": "2025-04", "overtime_hours": 50},
        intent="register_overtime",
        mode="preflight",
    )
    if result.verdict == "DENY":
        for v in result.violations:
            print(v.rule_statement, v.reason, v.suggested_fix)
```

**CLI:**

- `rulerepo-check` — CI integration, evaluates a code diff
- `rulerepo-hook` — agent hooks for Claude Code (preflight/posthoc)
- `rulerepo-ingest` — imports CLAUDE.md, contract templates, HR handbooks
- `rulerepo-export` — exports rules as portable `rules.yaml`
- `rulerepo-context` — generates CLAUDE.md sections from server rules
- `rulerepo-eval` — runs the eval harness locally

### 6.8 MCP Server

Exposes the Rule Repository to AI coding agents via the Model Context Protocol. The Engineering plugin provides code-specific tools; the core provides domain-neutral tools.

**Core tools (always available):**
- `search_rules`, `evaluate_compliance`, `explain_rule`, `find_conflicts`, `get_rules_for_context`, `create_proposal`, `get_proposal_status`

**Engineering-plugin tools:**
- `register_agent`, `get_personalized_rules`, `challenge_verdict`, `request_exception`, `discover_rules`

### 6.9 Persona Portals

Each major persona has a dedicated entry point in the frontend:

- **Legal Portal**: contract review queue, clause library, regulatory horizon, citation graph, jurisdictional filter
- **HR Portal**: attendance compliance dashboard, employee fact viewer, policy clarification queue, HRIS connection status
- **Compliance Portal**: bundle status (J-SOX, GDPR, EU AI Act), control framework progress, audit packet generator, exception tracking
- **Security Portal**: data classification configuration, encryption key management, eval harness status, penetration test results
- **Engineering Portal**: project rule view, agent leaderboard, PR evaluation history, CLAUDE.md sync status (existing UX)

Each portal hides irrelevant features and surfaces persona-specific actions.

---

## 7. Key Features

### 7.1 Foundational

- Natural-language rule storage with full provenance to source documents
- Multi-modal search (full-text, vector, category, hybrid, context, intent)
- Rule lifecycle: draft → review → approved → effective → superseded → retired
- REST API, Intent API, Evaluate API
- Multi-tenancy with tenant isolation by Row-Level Security
- OIDC/SAML SSO, SCIM provisioning, RBAC, ABAC
- Hash-chained immutable audit log with right-to-erasure support
- Python SDK (Rule Client) and Agentic SDK; CLI tools

### 7.2 Differentiating

- **Domain-neutral evaluation core** with pluggable evaluators per domain
- **Fact Store** that resolves external facts at evaluation time
- **Pluggable extractors** for code, documents (contracts, HR handbooks, statutory PDFs), linter configs, content, and forms
- **Conflict Detector**: continuously scans for `conflicts_with` candidates across the corpus
- **Counterexample Generator**: minimal compliant and non-compliant examples per rule, used as regression tests
- **Rule Coverage**: dormant and over-triggered rule detection
- **Change Impact Simulator**: replays historical evaluations against a proposed rule revision
- **Refinement Feedback Loop**: human corrections drive auto-drafted rule rewrites
- **Polyglot Rules**: maintains semantically equivalent rule pairs across languages with continuous verification
- **Provenance Lineage**: tracks Law → Internal Policy → Department Rule → Contract Clause; upstream changes propagate downstream
- **Rule Tutor**: LLM-powered conversational interface that explains relevant rules to new employees
- **Why API**: multi-level rationale traversal from verdict to source law
- **Automatic Rule Discovery**: bootstraps rules from existing artifacts (code, contracts, handbooks)
- **Cross-Project Federation**: org → team → project rule inheritance with overrides
- **Rule Bundles**: purposeful grouping for control frameworks (J-SOX, GDPR, EU AI Act)
- **Rule Playground**: interactive sandbox for testing rules against sample inputs
- **Proactive Alerts**: dormant rules, high deny rates, health decline, regulatory amendments
- **Versioned Snapshots**: atomic deployment of rule sets to environments
- **Cross-Tenant Marketplace**: discoverable catalog of rule packages from any tenant who chooses to publish
- **Regulatory Feed Integration**: amendment detection and impact propagation
- **Eval Harness**: golden datasets per domain with regression and drift monitoring

### 7.3 Cross-Cutting

- Tiered LLM strategy: small/fast models for screening, large/accurate models for high-severity judgments, consensus voting for `CRITICAL` + `statutory` rules
- PII classification, redaction, and tokenization before LLM transmission
- Customer-managed encryption keys (CMEK)
- Regional data routing (LLM region, storage region, cache region per tenant)
- Per-tenant LLM budget enforcement
- Persona-driven UX across legal, HR, compliance, security, and engineering
- OpenTelemetry instrumentation; Prometheus-compatible metrics; per-tenant cost dashboards
- Tiered infrastructure: Postgres-only (Tier 1) → +ES/Redis (Tier 2) → +Neo4j/MCP/arq (Tier 3)
- Disaster recovery: WAL archiving, audit log mirroring to WORM storage, quarterly DR drills

---

## 8. Use Cases

The Rule Repository serves multiple personas across the organization. Each use case below corresponds to a feature combination demonstrated end-to-end with a connector, fact store, persona UX, and golden dataset.

### 8.1 HR / Labor Management (primary launch vertical)

The HR system registers attendance, overtime, and leave. The Rule Repository holds work regulations and the Labor Standards Act-derived policies. The Agentic Rule Client validates each registration in `preflight` mode, calling the HR plugin's `form_evaluator` with employee context resolved by the Fact Store.

**Example flow:** an employee registers 50 hours of overtime in April 2025. The Fact Store resolves `36_agreement_status(employee_id, "2025-04")` and `employee_grade(employee_id, "2025-04-30")`. The form evaluator selects 8 applicable rules from the HR domain. The evaluation returns `DENY` with reason "Monthly overtime exceeds 45-hour limit; 36-agreement special clause not applicable for grade=junior" and a repair suggestion to redistribute hours.

**Persona:** HR business partner reviews aggregated violations on a dedicated dashboard. Connectors: Workday or SmartHR. Golden dataset: 100 hand-labeled overtime registrations.

### 8.2 Contract Management

The contract management system stores contracts under negotiation. The Rule Repository holds internal procurement rules and a curated library of standard clauses. When a counterparty draft is registered, the Legal plugin's `document_evaluator` runs clause-level extraction, compares each clause against the standard library, and identifies risk clauses (unlimited liability, foreign governing law, data export).

**Example flow:** a vendor sends an MSA draft. The system extracts 23 clauses, finds 5 deviations from the standard library, and flags 2 high-risk clauses. The Negotiation Playbook proposes fallback clauses for each. The General Counsel reviews via the Legal Portal.

**Persona:** General Counsel and contract reviewers. Connectors: DocuSign, Ironclad. Golden dataset: 50 hand-labeled contract drafts with known risk patterns.

### 8.3 Regulatory Compliance

A financial institution stores regulations (consumer protection laws, AML rules) in the repository, with derived internal procedures linked via `derives_from`. The Regulatory plugin polls e-Gov 法令 and Federal Register feeds. When a regulation is amended, the Provenance Lineage and Change Impact Simulator together identify all downstream procedures, contracts, and HR policies needing review. The Compliance Portal shows the regulatory horizon: "April 2026: revised Labor Standards Act; 12 derived rules need review by end of February."

**Persona:** Chief Compliance Officer, regulatory affairs team. Connectors: e-Gov 法令, EUR-Lex, Federal Register. Golden dataset: 50 amendment-impact analyses.

### 8.4 Software Development

The Rule Repository stores the engineering team's coding standards, documentation conventions, and review checklists. CI pipelines use the Rule Client to evaluate pull requests via the Engineering plugin's `code_change` evaluator. AI coding agents receive applicable rules via MCP and write compliant code from the start. When a human reviews AI-generated code and makes corrections, the Correction Feedback Loop captures the delta, proposes new rules, and the correction rate drops over time.

**Persona:** Engineering Manager, individual contributor, AI coding agent. Connectors: GitHub, GitLab. Golden dataset: 100 PR-reviewed diffs.

### 8.5 Sales and Marketing Content Compliance

A consumer-facing business produces ads, SNS posts, and email campaigns subject to landing-page laws (景表法, 薬機法, 特商法 in Japan; FTC rules in the US). The Marketing plugin's `content_evaluator` reviews each asset against channel-aware rules before publication. The Pre-Publishing Review Queue routes high-risk assets to a human reviewer.

**Persona:** Marketing Operations, Compliance Officer. Connectors: Salesforce Marketing Cloud, HubSpot. Golden dataset: 50 hand-labeled marketing assets.

### 8.6 Financial Transaction Compliance

Journal entries from the ERP are evaluated against accounting policies, expenditure regulations, and approval routing rules. The Finance plugin's `transaction_evaluator` checks each entry; high-amount entries are routed for additional approval per the rules.

**Persona:** Controller, Internal Audit. Connectors: SAP, Oracle, NetSuite, freee 会計. Golden dataset: 100 hand-labeled journal entries.

### 8.7 Cross-Domain Onboarding

A new employee joining the organization needs to learn which rules apply to them. The Rule Tutor (an LLM-powered chat interface) answers questions like "What are the rules for taking parental leave?" or "What clauses do I need to include in a vendor NDA?" by traversing rules across multiple domains, citing the source documents, and adapting explanations to the employee's role and seniority.

---

## 9. Technical Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash (`gemini-3-flash-preview`) and Gemini 3.1 Pro (`gemini-3.1-pro-preview`) via `google-genai` |
| Document parsing | Gemini Files API + document understanding (PDF, text, markdown) |
| Relational DB | PostgreSQL 17 (with Row-Level Security for tenant isolation) |
| Search | Elasticsearch 8 (BM25 + dense_vector hybrid) |
| Graph DB | Neo4j 5 (rule relationship projection) |
| Cache / Job queue | Redis 7 + arq |
| MCP | FastMCP (mcp >= 1.9), 12+ tools |
| Identity | OIDC, SAML 2.0, SCIM 2.0 |
| Secrets | HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager (pluggable) |
| Observability | OpenTelemetry, Prometheus, Grafana |
| Quality | ruff + mypy, ESLint + Prettier, pre-commit hooks; eval harness for LLM verdicts |
| Local orchestration | Docker Compose (3 tiers: starter, standard, full) |
| Container | Apache 2.0 license; SBOM (CycloneDX); signed releases (Sigstore) |

The architecture intentionally avoids hard-coding a single LLM provider. The `Evaluator` interface accepts any model that can perform structured judgment.

---

## 10. Roadmap

### Phase 1 — Foundation [COMPLETE]
Storage, search, extraction pipeline, REST API, Python SDK, basic governance. *Value delivered: "Our rules are organized and findable."*

### Phase 2 — Enforcement [COMPLETE]
Code-Aware Evaluation Engine, MCP server, GitHub PR review, CI CLI, agent hooks, gateway, intelligence. *Value delivered: "Our rules are enforced where work happens."*

### Phase 3 — Discovery & Learning [COMPLETE]
Automatic Rule Discovery, Correction Feedback Loop, Cross-Project Federation. *Value delivered: "Our rules bootstrap themselves and scale across the organization."*

### Phase 3.5 — Adoption Acceleration [COMPLETE]
GitHub repository import, automatic PR correction capture, rule impact preview, conflict resolution transparency. *Value delivered: "Rules bootstrap in minutes."*

### Phase 4 — Testing & Deployment Safety [COMPLETE]
Rule Playground, per-rule test cases, proactive alerts, rule set snapshots, environment-based evaluation. *Value delivered: "Rules can be tested before deployment."*

### Phase 5 — Self-Improving Governance [COMPLETE]
Batched evaluation, evaluation result persistence, outcome-oriented dashboard, correction-to-rule flywheel, active rule injection, zero-config bootstrapping, structured remediation, rule maturity model, advanced intelligence. *Value delivered: "Our rules improve themselves."*

### Phase 6 — Platform & Ecosystem [COMPLETE]
Collaborative governance proposals, autonomous agent governance, cross-organization rule marketplace. *Value delivered: "Rules are a shared organizational asset."*

### Phase 7 — Enterprise Ground [COMPLETE]

This phase repositioned the Rule Repository from "engineering-leaning organizational tool" to "true cross-organization norm management platform". Eight workstreams delivered.

#### 7a. Multi-Tenancy and Identity [COMPLETE]

- Add `tenant_id` column to all business tables; backfill with default tenant
- Apply PostgreSQL Row-Level Security policies enforcing `tenant_id`
- Implement OIDC and SAML SSO (Google, Microsoft Entra ID, Okta, generic)
- Implement SCIM 2.0 user and group provisioning
- Implement attribute-based access control (ABAC) with policy-as-code
- Enforce segregation of duties: rule authors cannot approve own rules; approvers cannot enact own approvals
- Per-tenant settings: data residency, LLM region, encryption keys, LLM budget
- Rebuild Marketplace as cross-tenant (current implementation is single-tenant)

*Value delivered: "Multiple organizations share one platform with hard isolation."*

#### 7b. Domain-Neutral Core + First Vertical Deep-Dive (HR) [COMPLETE]

**7b1. Evaluator Plugin Architecture [COMPLETE]**
- Refactor `services/evaluation/` into domain-neutral `core/` and pluggable `evaluators/`
- Move existing code-aware logic to `services/plugins/engineering/evaluators/code_change_evaluator.py`
- Add `evaluator_type` parameter to `POST /api/v1/evaluate`
- Define `Evaluator` protocol; document plugin registration

**7b2. HR/Labor Vertical Deep-Dive [COMPLETE]**
- Add `domain` enum to `Rule`; backfill existing rules to `domain="engineering"`
- Implement `services/plugins/hr/` with `form_evaluator`, employee context resolver, attendance compliance dashboard
- Build HRIS connector for at least one of: Workday, SuccessFactors, freee 人事労務, SmartHR
- HR persona portal at `/hr/`
- HR golden dataset (100 hand-labeled cases)

*Value delivered: "Engineering is one of several first-class domains; HR is fully supported end-to-end."*

#### 7c. Fact Store [COMPLETE]

- Implement `services/fact_store/` with `FactProvider` protocol and `FactStore` orchestrator
- Add `external_facts_required` to `Rule`
- Wire fact resolution into the evaluation pipeline (between Rule Selection and Evaluator Dispatch)
- Initial providers: `EmployeeAttributesProvider`, `OFACSanctionsProvider`, `InternalMasterDataProvider`
- Per-tenant provider configuration

*Value delivered: "Legal and HR rules become genuinely actionable, not just descriptive."*

#### 7d. Compliance and Privacy Layer [COMPLETE]

- Data Classification Layer with field-level tags (`public`, `internal`, `confidential`, `pii`, `pii_special`)
- PII redaction pipeline before audit log persistence; encrypted shadow store for original values
- Right-to-Erasure API with hash-chain-preserving logical deletion
- Regional Routing: tenant config selects LLM region (Vertex AI), storage region, cache region
- Customer-Managed Encryption Keys (CMEK) integration
- Read-access logging on rule-detail endpoints
- Approval Policy DSL with category-aware requirements
- Mandatory Consultation roles (e.g., DPO for PII rules)

*Value delivered: "Regulated industries can deploy confidently."*

#### 7e. Eval Harness and Quality Engine [COMPLETE]

- Scaffold `apps/server/eval/` with datasets/, runner.py, reporters/, ab_testing/
- Define golden dataset format (YAML or JSONL)
- Build initial golden datasets per domain (engineering 50 cases, HR 50 cases, legal 50 cases, content 50 cases)
- Nightly regression runner with precision/recall/F1 reports
- Drift detector with threshold alerts
- A/B testing framework for prompt and model rollouts
- Tenant-bring-your-own-eval API

*Value delivered: "Verdict quality is measurable, monitored, and auditable."*

#### 7f. Connector Hub [COMPLETE]

- `services/connectors/` framework with `EventSource` and `Sink` interfaces
- Three reference connectors: one HRIS (SmartHR or Workday), one CRM (Salesforce), one ERP (SAP or freee 会計)
- Per-tenant connector configuration with credential management
- Connector health dashboard

*Value delivered: "Rules are evaluated where work happens, not in a separate UI."*

#### 7g. Persona-Driven UX [COMPLETE]

- Routing layer that selects persona portal based on user role (Legal, HR, Compliance, Security, Engineering)
- Legal Portal: contract review queue, clause library, regulatory horizon
- HR Portal: attendance compliance, employee fact viewer, policy clarification queue
- Compliance Portal: bundle status, control framework progress, audit packet generator
- Security Portal: data classification, encryption keys, eval harness status
- Engineering Portal: existing UX preserved

*Value delivered: "Legal, HR, and compliance teams see a system designed for them, not a developer dashboard."*

#### 7h. Operability [COMPLETE]

- OpenTelemetry instrumentation across the stack
- Prometheus-compatible `/metrics` endpoint
- Per-LLM-call telemetry (model, tokens, latency, cost) attached to traces
- Per-tenant cost dashboards
- Worker leader election (Postgres advisory lock)
- LLM fallback strategies for Gemini outage
- Backup and DR runbooks; quarterly DR drills

*Value delivered: "Production-grade operations."*

#### Phase 7 sequencing

- **Quarter 1**: 7e (Eval Harness) and 7b1 (Evaluator Plugin) in parallel — both foundational
- **Quarter 2**: 7a (Multi-Tenancy) and 7c (Fact Store) in parallel — both invasive, do early
- **Quarter 3**: 7b2 (HR Vertical) and 7g (Persona UX) — demonstrate cross-organization story
- **Quarter 4**: 7f (Connectors), 7d (Privacy Layer), 7h (Operability) — production readiness

### Phase 8 — Vertical Expansion [PLANNED]

After Phase 7 establishes the platform, Phase 8 expands vertical coverage:

- **Legal/Contract plugin**: clause-level extractor, document evaluator, standard clause library
- **Regulatory plugin**: regulatory feed integrations, amendment diff service
- **Marketing/Content plugin**: content evaluator, channel-aware rules, pre-publishing review
- **Finance plugin**: transaction evaluator, period-aware rules, approval routing
- **Conversation plugin**: chat log and call transcript evaluation for sales and support

Each new plugin must ship with: extractor, evaluator, prompts, golden dataset, persona view, at least one connector.

### Phase 9 — Self-Improving Platform [PLANNED]

Three strategic enhancements that transform the Rule Repository from a deployed platform into a continuously improving one:

- **Self-healing rules**: when a rule's effectiveness drops below threshold, the system auto-generates a rewrite proposal citing corrections that revealed the problem
- **Conflict auto-resolution**: when two rules contradict, the system proposes a merged rule or scope narrowing
- **Proactive rule suggestions**: pattern analysis across all tenants (with consent) suggests rules that no organization has written yet but that emerging regulations imply

---

## 11. Success Metrics

### 11.1 Coverage and adoption
- **Domain coverage**: number of active domains (target: 4 domains by end of Phase 7)
- **Tenant adoption**: number of distinct tenants in production (target: 10 by end of Phase 7)
- **Rule corpus size**: total rules in production by domain (target: 500+ per active domain)
- **Daily evaluation volume**: target: 10,000/day across all tenants by end of Phase 7

### 11.2 Quality
- **Eval harness scores**: precision, recall, F1 per domain (target: ≥0.85 for engineering, ≥0.80 for HR/legal at Phase 7 launch)
- **Verdict reproducibility**: % of evaluations replayable from audit log (target: 100%)
- **Drift detection**: zero P0 drift incidents per quarter
- **False positive rate**: per-domain false positive rate from production corrections (target: <5%)

### 11.3 Operations
- **Latency**: p50/p95/p99 evaluation latency in `preflight` mode (target: p95 <2s, p99 <5s)
- **Availability**: 99.9% monthly uptime
- **Time-to-comply on regulatory change**: median time from amendment publication to derived-rule revision approval (target: <2 weeks)

### 11.4 Governance health
- **Metadata completeness**: % of rules with full metadata, current rationale, active owners (target: ≥90%)
- **Bundle progress**: % of rules in active bundles with current status (target: 100% for tracked bundles)
- **Approval SLA compliance**: % of approvals completed within SLA (target: ≥95%)

### 11.5 Self-improvement
- **Shadow-to-enforcement rate**: % of experimental rules reaching stable within 60 days (target: ≥70%)
- **Auto-fix rate**: % of SHOULD violations auto-fixed via structured remediations (target: ≥40%)
- **Flywheel throughput**: rules auto-drafted from correction clusters per month (target: ≥5)
- **Time-to-rule**: median time from correction pattern detection to approved rule (target: <1 week)

### 11.6 Cost
- **Per-evaluation LLM cost**: target: <$0.01 average across cached + uncached
- **Cache hit rate**: target: ≥60% for repeated evaluations
- **Per-tenant cost predictability**: tenant LLM spend within 20% of forecast monthly

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Eval harness with golden datasets; consensus voting for CRITICAL+statutory rules; human review on high-severity denials; refinement feedback loop |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity; refinement loop suggests rewrites; required test cases per rule; eval harness measures impact of rewording |
| LLM costs scale poorly with rule corpus size | Two-stage evaluation (metadata pre-filter, then LLM); aggressive caching; batched evaluation; tiered model selection; per-tenant budgets |
| Sensitive data leaks through evaluation context | Data Classification Layer; PII redaction; tokenization; tenant isolation; regional routing; CMEK; right-to-erasure |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via `effective_period`; sidecar mode for shadow testing; snapshot rollback |
| Over-reliance reduces human judgment | Position as decision support, not decision automation; preserve rationale visibility; require human approval for high-severity verdicts; audit log enables disputes |
| Conflicts with existing IAM / GRC tools | Position as complementary semantic layer; provide integration points |
| Regulatory feeds become inaccurate or delayed | Multi-source corroboration; manual override; version history of all amendments |
| Multi-tenant data leakage | RLS at the database level; tenant-derived from authenticated principal only; never from request body; quarterly third-party penetration testing |
| Plugin authors break the core | Plugin contract is versioned; plugins go through CI checks against the core's protocol tests; only signed plugins load in production |
| Eval harness disagreement with production | Treat eval harness as the authority; alert on production-vs-harness divergence |
| Vendor lock-in to Gemini | `Evaluator` interface accepts any structured-output LLM; pluggable provider layer; documented migration path |

---

## 13. Glossary

- **Rule**: a natural-language normative statement, plus structured metadata, managed as a first-class object
- **Statement**: the canonical natural-language text of a rule
- **Domain**: the top-level partition of rules by business function (`engineering`, `legal`, `hr`, `finance`, `marketing`, `procurement`, `security`, `general`)
- **Modality**: the strength of the obligation (MUST, MUST_NOT, SHOULD, MAY, INFO)
- **Severity**: the severity of consequences on violation (LOW, MEDIUM, HIGH, CRITICAL)
- **Legal Force**: the legal weight of the rule (`statutory`, `regulatory`, `contractual`, `internal_policy`, `guidance`, `industry_norm`)
- **Jurisdiction**: the legal jurisdiction of applicability (`JP`, `US-CA`, `EU`, etc.)
- **Scope**: the structured set of subjects, systems, channels, or contexts to which a rule applies
- **Consequence Type**: the category of consequence on violation (`criminal`, `civil_liability`, `administrative_fine`, `disciplinary`, `reputational`, `operational`)
- **Verdict**: the result of an evaluation (`ALLOW`, `DENY`, `NEEDS_CONFIRMATION`)
- **Reason graph**: a structured DAG explaining which facts triggered which conditions in which rules
- **Remediation**: a structured fix proposal — type, location, original, replacement, description, `auto_applicable` flag
- **Meta-rule**: a rule whose subject is other rules
- **Provenance lineage**: the chain of derivation from a higher-level source (e.g., a law) down to operational rules and contract clauses
- **Preflight / Posthoc / Sidecar**: three modes of integration corresponding to before-action, after-action, and parallel-observation enforcement
- **LLM-as-Judge**: the architectural pattern of using a large language model to evaluate whether an action complies with a natural-language rule
- **Domain Plugin**: a self-contained module that registers extractors, evaluators, feedback sources, prompts, persona UX, golden datasets, and connectors with the core
- **Evaluator**: a domain-specific implementation that takes an `EvaluationContext` and a rule set and produces verdicts
- **Fact Store**: a subsystem that resolves external facts required by rules at evaluation time
- **Fact Provider**: a registered backend that resolves a specific class of facts (e.g., employee attributes, sanctions list)
- **Connector**: a bidirectional integration with a business system, implementing `EventSource` and/or `Sink`
- **Tenant**: the billing and isolation boundary; all business data is partitioned by `tenant_id`
- **RuleBundle**: a curated set of rules unified by a business purpose (e.g., "J-SOX Compliance", "EU AI Act Readiness")
- **Eval Harness**: the quality system that measures verdict accuracy against golden datasets
- **Persona Portal**: a frontend entry point tailored to a specific role (Legal, HR, Compliance, Security, Engineering)

---

## 14. Open Questions

These will be resolved during Phase 7 implementation:

- What is the canonical `scope` schema? Free-form tags vs. structured `{org, role, system, region, channel}` tuples? **Tentative answer**: structured tuples with optional free-form supplemental tags.
- How should `tenant_id` interact with the existing `Project` and `Federation` hierarchy during migration? **Tentative answer**: introduce a default tenant per existing deployment; backfill `tenant_id` from `Project.organization_id` where available.
- What is the multi-tenant isolation model for the Marketplace? Tenants opt-in to publish; consumers see only their own subscriptions plus public packages. Cross-tenant analytics require explicit consent.
- How are deprecated rules archived without losing the ability to re-evaluate historical events? **Tentative answer**: soft delete with `valid_until` only; physical retention indefinite; logical access gated by audit role.
- Should plugins be loadable at runtime or compile time? **Tentative answer**: compile time for Phase 7; runtime hot-loading is a Phase 9 consideration.
- What is the expected SLO for `preflight` evaluations across all evaluator types? Drives model selection and caching strategy. **Target**: p95 <2s for cached, p95 <5s for uncached.
- How do we handle regulatory feeds for jurisdictions where machine-readable feeds do not exist? **Tentative answer**: partner with regulatory intelligence providers (e.g., Westlaw, LexisNexis); manual ingestion as fallback.
- What is the upgrade path for existing tenants when the domain enum changes? **Tentative answer**: enum is extensible; migrations add new values without removing old ones; deprecation requires 12-month notice.

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes should follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect.*
