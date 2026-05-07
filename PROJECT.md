# PROJECT.md

> **Rule Repository** — a software platform for managing, searching, serving, and enforcing natural-language rules across an entire organization. Laws, contracts, internal policies, HR regulations, financial controls, marketing standards, engineering guidelines, and documentation conventions all live as first-class, governed assets, interpreted at runtime by LLMs and AI agents.

---

## 1. Project Overview

The **Rule Repository** stores human-authored rules in their original natural-language form and makes them operationally useful: searchable, applicable, and enforceable across business systems, document workflows, and software development environments. Where traditional rule engines require translating human rules into a formal language (and losing nuance in the process), the Rule Repository keeps each rule as written and uses LLMs and AI agents to interpret, search, evaluate, and enforce them at runtime.

This approach is inspired by, and generalizes, the concept of **Semantic Governance** (e.g., Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea in three directions:

- **Wider scope of rules.** Not just AI-agent guardrails, but laws, contracts, HR policies, financial controls, marketing standards, engineering guidelines, and documentation conventions.
- **Wider scope of consumers.** Human users, business systems (HR, ERP, CRM, contract management), document workflows, IDEs, CI pipelines, and AI agents.
- **Wider scope of time.** Pre-flight checks (block before action), post-hoc audits (review after the fact), and continuous compliance monitoring.

The Rule Repository is, fundamentally, an **organization-wide rule repository**, not a coding-rule manager. Coding governance is one important use case among many; HR, legal, finance, sales/marketing, and regulatory compliance are equally first-class.

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository fills a gap that no current category of software addresses cleanly:

- **Document management systems** store the source documents but do not understand the rules inside them.
- **Rule engines** (Drools, DMN, OPA) require formal encoding and lose the original semantics.
- **GRC platforms** track compliance status but do not enforce rules at the point of action.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.
- **Coding-rule tools** (linters, ruleset products) cover engineering guidelines only and do not generalize to laws or contracts.

The Rule Repository treats **rules themselves as first-class, versioned, governed assets** — decoupled from any single consumer, reusable across the entire organization, and interpretable by LLMs in their original natural-language form.

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Store rules in natural language with full traceability to their source documents.
- Provide rich search (full-text, vector, category, hybrid, intent-based) over rule corpora.
- Enable runtime evaluation: *"given this context and intent, is this action compliant with the relevant rules?"* — across many domains, not just code.
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Detect conflicts, redundancies, and dead rules across the corpus.
- Make rule provenance, rationale, jurisdiction, legal force, and revision history first-class.
- Provide ergonomic SDKs and connectors so business systems and AI agents can integrate easily.
- Support cross-organizational sharing of high-quality rule packages through a marketplace.

### 3.2 Non-Goals

- Replacing IAM, RBAC, ABAC, or network-layer access control. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel or compliance officers. The system surfaces issues; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts on behalf of users.
- Functioning as a primary system of record for HR, ERP, or CRM data.

---

## 4. Architecture

### 4.1 High-Level View

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                          │
│                                                                       │
│  Extraction    Search (5)    Evaluation       Intelligence            │
│  Pipeline      BM25+Vec      Engine           Health + Recommend      │
│  (multi-       +Project      (Subject-aware,  Effectiveness           │
│   source)      filter        batched,         Digest + Compare        │
│                              conflict-aware)  Flywheel                │
│                                                Agent + Persona        │
│                                                                       │
│  Discovery     Federation    Snapshots        Playground              │
│  (code +       (org/team/    (versioned,      (sandbox + tests)       │
│   business)    project)      env-deployed)                            │
│                                                                       │
│  Proposals     Agent Gov     Marketplace      Subject Adapters        │
│  (lifecycle,   (trust,       (packages,       code_change             │
│   voting,      challenge,    subscribe,       hr_event                │
│   comments)    sessions)     conflicts)       contract_clause         │
│                                                expense_claim          │
│                                                marketing_copy         │
│                                                document_revision      │
│                                                transaction            │
│                                                                       │
│  PostgreSQL    Elasticsearch   Neo4j      Redis      Audit Log        │
│  (truth)       (search)        (graph)    (jobs)     (immutable +     │
│                                                       hash-chained +  │
│                                                       optional WORM)  │
│                                                                       │
│  REST API │ Intent API │ Evaluate API │ Gateway API │ MCP             │
└─────┼──────────┼─────────┼──────────────┼───────────┼─────────────────┘
      │          │         │              │           │
   Rule SDK  Agentic   MCP Server     CLI Tools    Business
   (Python)  Client    (12 tools)     (CI/hooks)   Connectors
                                                   (HR, ERP,
                                                    contracts,
                                                    chat, ITSM,
                                                    docs, IdP)
```

**Three data stores, one source of truth.** PostgreSQL holds canonical rules and history. Elasticsearch is a derived search index. Neo4j is a derived relationship graph. If they disagree, Postgres wins and the others are rebuilt.

### 4.2 The Pluggable Subject Architecture

The architectural cornerstone is that the **subject of evaluation is pluggable**. The system does not assume that what is being evaluated is a code change. Instead, every evaluation request carries a typed `Subject` envelope, and a `SubjectAdapter` for that type knows how to parse the payload, gather domain context, format the LLM prompt, and interpret remediations.

```
EvaluateRequest:
  subject:
    type: code_change | hr_event | contract_clause | expense_claim
        | marketing_copy | vendor_onboarding | meeting_minutes
        | email_draft | document_revision | transaction | custom
    payload: <typed schema per subject type>
    context: <attached metadata>
  scope: list[str]
  intent: str
```

This abstraction lets a single evaluation engine, audit log, search index, and governance workflow serve every domain, while keeping each domain's idiosyncrasies (clause segmentation in contracts, line items in expenses, copy phrasing in marketing) cleanly encapsulated.

### 4.3 Trust and Data Boundaries

- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and judgments they are authorized to see.
- All evaluation calls produce immutable audit records on the server side.
- For regulated domains, audit records can be dual-written to a WORM store and time-stamped by an external TSA.

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
| `applicable_subject_types` | Which subject types this rule can evaluate (e.g., `[contract_clause]`) |
| `modality` | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `jurisdiction` | Where the rule applies legally (`jp`, `us-ca`, `eu`, `global`, etc.) |
| `legal_force` | `advisory` / `policy` / `regulatory` / `statutory` |
| `effective_period` | `valid_from` / `valid_until` |
| `review_cadence` | When the rule must be reviewed (`semiannual`, `on-statute-change`, etc.) |
| `preconditions` | Facts required to evaluate the rule |
| `exceptions` | References to other rules or carve-outs |
| `rationale` | Why the rule exists (purpose, intent) |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `tags` | Free-form taxonomic labels |
| `governance` | Owner, approvers, revision history |
| `maturity_level` | `experimental` / `stable` / `proven` |
| `embedding` | Vector representation (derived) |

The `statement` is the **source of truth**. Structured fields exist for indexing, filtering, and prioritization — never to override the meaning of the statement.

### 5.2 Rule Relationships

Rules form a graph, not a flat list. Modeling these relationships explicitly turns the repository from a list into a **provenance and impact graph**.

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule operationalizes a more abstract one |
| `overrides` | A rule takes precedence over another |
| `conflicts_with` | Two rules contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision replaces a prior version |
| `translates` | Two rules express the same content in different languages |

### 5.3 Subjects and Adapters

A `Subject` is the thing being evaluated. The set of subject types is open and extensible:

- `code_change` — diff, file paths, language metadata.
- `hr_event` — employee context, attendance / leave / overtime data.
- `contract_clause` — clause text, contract metadata, counterparty.
- `expense_claim` — line items, receipts, submitter context.
- `marketing_copy` — copy text, distribution channel, target audience.
- `vendor_onboarding` — vendor data, jurisdictions, screening results.
- `meeting_minutes` — text, attendees, decisions.
- `email_draft` — draft text, recipients, attachments.
- `document_revision` — revision diff, document classification.
- `transaction` — amount, parties, jurisdictions, instrument.
- `custom` — for tenant-defined types not covered above.

Each subject type is served by a `SubjectAdapter` that parses payloads, assembles context, picks the right prompt template, and interprets remediations. Adding a new subject type is a contained extension — no changes to the evaluation core, audit log, or governance workflow.

### 5.4 Verdicts

The evaluation engine returns one of:

- `ALLOW` — the action is compliant with all relevant rules.
- `DENY` — the action violates at least one rule.
- `NEEDS_CONFIRMATION` — ambiguous; requires human review.
- `ALLOW_WITH_CONDITIONS` — permitted only after specified conditions are met (e.g., higher-rank approver above an amount threshold).
- `REQUIRES_DISCLOSURE` — permitted but triggers a disclosure obligation (e.g., conflict-of-interest, related-party transaction).

Each verdict carries a structured **reason graph** explaining which facts triggered which conditions in which rules, and a **provenance lineage** showing the genealogy from source law / policy down to the rule that fired.

### 5.5 Remediations

When a verdict is `DENY` or `ALLOW_WITH_CONDITIONS`, the engine returns one or more remediations indicating how to bring the action into compliance. Remediations are typed by subject:

- `CodeRemediation` — file edit (replace / insert / delete).
- `ContractClauseRemediation` — clause-level edit, addition, or deletion.
- `HrEventRemediation` — return for revision, request additional information, route to higher approver.
- `ExpenseRemediation` — adjust amount, request receipt, change account code.
- `WorkflowRemediation` — re-route approval, escalate.

Each remediation carries an `auto_applicable` flag whose meaning is defined per subject type.

### 5.6 Meta-Rules

The system supports **rules about rules** (e.g., "Any contract clause must not contradict the procurement policy"). Meta-rules are evaluated by the same engine but scoped to govern the rule corpus itself.

---

## 6. Components

### 6.1 Rule Management Server

The server is the system of record for all rules.

- **Rule CRUD** with revision history and effective-date semantics.
- **Extraction pipeline** — multi-source: document parsing for PDFs (work regulations, contracts, regulator circulars), DOCX (contract templates, internal handbooks), text and markdown (CLAUDE.md, README), HTML (statutory databases, intranet), and structured sources (linter configs, SaaS APIs).
- **Search APIs** — full-text, vector, category/tag, hybrid (BM25 + vector reranking), context search (given facts, return applicable rules), impact search (given a rule change, return affected rules).
- **Intent API** — natural-language endpoint that classifies and routes (`lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`).
- **Evaluation engine** — see §6.4.
- **Audit log** — append-only, hash-chained record of all evaluations including subject type, inputs, applied rules, model identity, and verdict. Optional WORM dual-write and TSA time-stamping for regulated domains.
- **Governance** — role-based access (Owner / Approver / Reader) per rule category, revision approval workflow, effective-date scheduling.

### 6.2 Rule Client (Python SDK)

A thin, ergonomic wrapper over the server APIs.

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    rules = await client.search.hybrid("overtime monthly limit", scope="hr/attendance/jp")
    result = await client.intent.ask("What are the rules for refunding orders over $500?")
```

### 6.3 Agentic Rule Client (Python SDK)

A higher-level client that wraps `RuleClient` and adds capabilities for systems that need to **enforce** rules, not just query them.

- **Automatic context gathering** — pull related facts from surrounding systems before evaluation.
- **Two-stage evaluation** — first narrow the rule set by metadata and embeddings, then evaluate the narrow set with a high-quality model.
- **Result caching** — hash-keyed; auto-invalidated on rule revision.
- **Reason graphs** — structured DAG of facts → conditions → rules.
- **Repair suggestions** — minimum modification that would make the action compliant.
- **Three integration modes** — `preflight`, `posthoc`, `sidecar`.

```python
from rulerepo_agentic import AgenticRuleClient

async with AgenticRuleClient("http://localhost:8000", scope="hr/attendance/jp") as client:
    result = await client.evaluate(
        subject={
            "type": "hr_event",
            "payload": {"employee_id": "E001", "month": "2025-04", "overtime_hours": 50},
        },
        intent="register_overtime",
        mode="preflight",
    )
```

### 6.4 Subject-Aware Evaluation Engine

The evaluation engine is the core differentiator. It accepts a typed `Subject`, maps it to relevant rules via `applicable_subject_types` and `scope` filters, and returns verdicts with subject-appropriate remediations.

**Pipeline**: Subject Adapter → Context Assembly → Rule Selection → LLM-as-Judge → Verdict Aggregation.

- **Subject Adapter** — chooses the per-subject parser, context assembler, prompt template, and remediation interpreter.
- **Context Assembler** — gathers domain-specific facts. For `hr_event`, this includes employee record, leave balances, prior attendance. For `contract_clause`, counterparty credit, prior-deal history, applicable internal policy. For `code_change`, file structure and surrounding code.
- **Rule Selector** — narrows the corpus to ~5–20 relevant rules via `applicable_subject_types`, scope, severity, modality, jurisdiction, and tag filtering, then semantic ranking.
- **Evaluation Core** — runs selected rules against the context using Gemini with structured JSON output. Tiered model selection by severity: Flash for LOW/MEDIUM, Flash + medium thinking for HIGH, Pro + high thinking for CRITICAL.
- **Verdict Aggregator** — combines per-rule verdicts (any DENY → overall DENY; any REQUIRES_DISCLOSURE bubbles up) and produces a unified remediation summary.

### 6.5 Agent Context Delivery (MCP)

The Rule Repository exposes itself to AI agents via the Model Context Protocol. This is one consumer of the engine, not the engine itself.

- **MCP Server** — FastMCP with stdio (Claude Code) and streamable-http (remote agents).
- **Tools** — `search_rules`, `evaluate_compliance`, `explain_rule`, `find_conflicts`, `get_rules_for_context`, `discover_rules`, plus tools for proposals, marketplace, and agent governance.
- **Resources** — `rule://{id}`, `ruleset://{scope}`.
- **Prompts** — `compliance_check`, `rule_summary`, `impact_analysis`.
- **Rule Formatter** — three output formats (`instructions`, `checklist`, `detailed`).

### 6.6 Business-System Connector Ecosystem

To deliver organization-wide enforcement, the system integrates with the SaaS where business actions actually happen.

| Category | Reference systems | Integration purpose |
|---|---|---|
| Attendance | KING OF TIME, jobcan, freee人事労務 | Webhook on registration → preflight evaluation |
| Expenses | freee, MoneyForward, Concur, RakuRaku Seisan | Webhook on submission → policy check |
| Contracts | DocuSign, CloudSign, Holmes, SmartContract | Draft upload → dangerous-clause detection |
| HR core | SmartHR, Workday, SAP SuccessFactors | Sync employee lifecycle and policy revisions |
| ITSM | ServiceNow, Jira Service Management | Change tickets → CAB-rule compliance |
| CRM | Salesforce, kintone | Discount / credit policy on opportunities and quotes |
| Chat | Slack, Microsoft Teams | Message scanning for policy violations |
| Doc storage | Google Drive, SharePoint, Box | Upload → confidentiality classification |
| Identity | Okta, Azure AD, Google Workspace | Sync RBAC at hire / leave / transfer |

All connectors normalize inbound payloads to a common `BusinessEvent` schema, and dispatch outbound actions (return-for-revision, comment, notification) through a uniform `Action Dispatcher`.

### 6.7 Rule Discovery (Code and Business)

Solves the cold-start problem: instead of writing rules from scratch, the system discovers rules already implicit in an organization's artifacts.

**Code sources** — CLAUDE.md parser, linter config parser (ruff/eslint/tsconfig/prettier), code-pattern analyzer, GitHub URL import.

**Business sources** —
- Work regulation PDFs.
- Standard contract templates (DOCX).
- Regulator circulars (PDF / HTML).
- National statutory databases (e-Gov, EUR-Lex, federalregister.gov) via dedicated legal pipeline.
- SharePoint, Confluence, Notion, kintone pages.
- Email archives (operational rules propagated by mail).
- Meeting minutes (decisions that become rules).
- Spreadsheet-based procedure books.

**Pipeline** — pattern detection with confidence scoring, candidate generation by Gemini, human review queue, batch approval for high-confidence (>0.9) candidates.

**Rule anthropology mode** — mines past judgments (email approvals, "is this OK?" Slack threads, meeting decisions) to surface rules that exist as senior tacit knowledge but were never formalized.

### 6.8 Persona-Based Operator Console

The frontend supports multiple personas with tailored dashboards:

- `Compliance Officer` — regulatory progress, unresolved alerts, audit readiness.
- `Legal Counsel` — contracts awaiting review, dangerous-clause detections, litigation-hold scope.
- `HR Manager` — labor-law violation early warnings, unused paid leave, harassment-report status.
- `Finance Controller` — expense-policy violations, credit-line breaches, revenue-recognition uncertainty.
- `Engineering Lead` — code rule violations, agent performance, top broken rules.
- `Sales Manager` — discount approval queue, special-pricing requests, advertising-law alerts.
- `Executive` — company-wide compliance index, regulatory-cost trend, risk heatmap.

A single global compliance score is replaced with per-domain scores (HR / Legal / Finance / IT / Sales / ESG), surfaced as a heatmap.

### 6.9 Rule Intelligence and Observability

- **Health Scorer** — per-rule score (0–100) across completeness, clarity, test coverage, freshness, activity, owner engagement.
- **Effectiveness Score** — precision (verdict accuracy), prevention rate (did corrections decrease after activation?), agent adoption.
- **Recommender** — suggests retiring dormant rules, clarifying ambiguous ones, escalating persistent violations, strengthening SHOULD → MUST.
- **Conflict Detector** — continuous scan for `conflicts_with` candidates.
- **Verdict Drift Detection** — temporal, model, semantic.
- **Weekly Digest** — compliance trend, top violations, attention-needed rules, pending actions, delivered via webhook.

### 6.10 Rule Enforcement Gateway

Event-driven, zero-code rule enforcement via webhooks. Receives `BusinessEvent` payloads from any source, matches them to enforcement policies, runs the evaluation engine, and dispatches actions.

### 6.11 Correction Feedback Loop (Flywheel)

Captures human corrections of AI- or system-produced output and converts them into rule improvements:

- **PR-based capture** — compares evaluated diff with final merged diff.
- **Agent-hook capture** — detects human edits to files recently modified by an agent.
- **Business-action capture** — detects when a business action was returned-for-revision, edited by an approver, or rejected.

Corrections are clustered, and clusters with sufficient size and confidence trigger Gemini to draft a rule proposal. Approved proposals start in shadow mode (`maturity_level=experimental`) and graduate automatically based on observed accuracy.

### 6.12 Federation, Snapshots, Playground, Alerts, Marketplace, Proposals, Agent Governance

These features (described in detail in `/development/` docs) provide:

- **Federation** — org/team/project hierarchy with inheritance and overrides.
- **Snapshots** — versioned, environment-deployed rule sets with rollback and impact simulation.
- **Playground** — sandbox evaluation with no persistence; per-rule test cases.
- **Proactive Alerts** — background workers detect dormant rules, high deny rates, health decline.
- **Marketplace** — cross-team and cross-organization rule package publishing and subscription.
- **Proposals** — Draft → Review → Approve workflow with multi-approver voting and impact preview.
- **Agent Governance** — agent profiles, trust levels, personalized rules, verdict challenges, exception requests, multi-agent governance sessions.

### 6.13 Audit and Compliance-Grade Traceability

- **Hash-chained audit log** — append-only, with each row referencing the hash of the previous row.
- **Optional WORM dual-write** — for regulated domains (financial, medical, public-sector).
- **Optional TSA time-stamping** — strengthens admissibility of audit records as legal evidence.
- **eDiscovery / litigation hold** — preservation mode locks deletion; export bundles for disclosure.
- **Audit-report export** — endpoints aligned with J-SOX, SOX, ISO 27001, PCI DSS expectations.
- **Automated-decision controls** — for GDPR Article 22 / EU AI Act compliance, includes user-notification and objection paths.

---

## 7. Key Features

### 7.1 Foundational
- Natural-language rule storage with full provenance.
- Multi-modal search (full-text, vector, category, hybrid, intent).
- Rule lifecycle: draft → review → approved → effective → superseded → retired.
- REST, Intent, Evaluate, and Gateway APIs.
- Python SDK (Rule Client) and Agentic SDK.

### 7.2 Differentiating
- **Pluggable Subject** — code, HR, contracts, expenses, marketing, transactions, and beyond, on one engine.
- **Conflict Detector** — continuous scanning for contradictions.
- **Counterexample Generator** — minimal compliant and non-compliant examples per rule.
- **Rule Coverage** — dormant and over-triggered rules from event logs.
- **Change Impact Simulator** — replays history against proposed rule revisions.
- **Refinement Feedback Loop** — corrections propose rule rewrites.
- **Polyglot Rules** — semantically equivalent rule pairs across languages.
- **Provenance Lineage** — Law → Policy → Department Rule → Contract Clause.
- **Rule Tutor** — conversational explainer for new employees and project members.
- **Why API** — multi-level rationale traversing `rationale` and `source_refs`.
- **Automatic Rule Discovery** — code and business sources.
- **Cross-Project Federation** — org/team/project inheritance with overrides.
- **Rule Playground** — interactive sandbox before deployment.
- **Proactive Alerts** — workers detect problems and notify.
- **Versioned Snapshots** — atomic deployment with rollback.
- **Marketplace** — cross-team and cross-org rule sharing.
- **Persona Dashboards** — Compliance, Legal, HR, Finance, Engineering, Sales, Executive.
- **Audit-grade Traceability** — WORM, TSA, eDiscovery, framework-aligned reports.

### 7.3 Cross-Cutting
- Immutable audit log with hash-chained integrity, optional WORM and TSA.
- Tiered LLM strategy: small/fast for screening, large/accurate for high severity, consensus voting for CRITICAL.
- PII sanitization on inputs and masking on logs.
- RBAC per rule category with Owner / Approver / Reader.
- Multi-tenant ready (`tenant_id` reserved on all tables).
- i18n (UI strings) plus Polyglot Rules (rule statements).

---

## 8. Use Cases

The Rule Repository serves a wide set of organizational rule domains. The following are representative; the system is not limited to these.

### 8.1 HR / Attendance Management
The HR system registers attendance and overtime. The Rule Repository holds the work regulations (Labor Standards Act, internal rules, 36-Agreement). The Agentic Rule Client validates each registration in `preflight` mode and alerts on violations such as monthly overtime exceeding the legal limit or missing 36-Agreement filing.

### 8.2 Contract Management
The contract management system stores contracts under negotiation. The Rule Repository holds internal procurement rules and prior contract clauses. When a new contract is registered, the Agentic Rule Client checks for contradictions with internal policy and conflicts with prior contracts. Dangerous clauses (unlimited liability, exclusive jurisdiction in counterparty's country) trigger warnings.

### 8.3 Financial Controls and Expense Compliance
Expense submissions in Concur or freee are evaluated against travel-expense, entertainment-expense, and tax-deductibility rules. Procurement requests are checked for sub-contracting law (下請法) compliance and budget adherence. Revenue recognition is validated against the new revenue standard.

### 8.4 Marketing and Advertising Compliance
Advertising copy is scanned against pharmaceutical-affairs (薬機法), premiums-and-representations (景表法), and specified-commercial-transactions (特商法) regulations before publication. Sales pricing is checked against antitrust constraints.

### 8.5 Regulatory Compliance
A financial institution stores regulations (consumer protection, AML, KYC) in the repository, with derived internal procedures linked via `derives_from`. When a regulation is amended, the Provenance Lineage and Change Impact Simulator together identify all downstream procedures that need review.

### 8.6 AI-Assisted Software Development
A team uses Claude Code with the Rule Repository. Rule Discovery bootstraps 50 rules from existing CLAUDE.md, linter configs, and code conventions. Agents receive applicable rules via MCP and write compliant code from the start. When a human reviews AI-generated code and makes corrections, the Correction Feedback Loop captures the delta, proposes new rules, and the correction rate drops over time.

### 8.7 Document Workflow and Communication
Outgoing emails are checked against confidentiality and conflict-of-interest rules. Slack messages are scanned (with privacy controls) for policy violations. Document uploads to Google Drive are classified and assigned retention periods.

### 8.8 Cross-Organizational Rule Sharing
A consortium of pharmaceutical companies publishes a curated, expert-reviewed pharmaceutical-affairs ruleset to the Marketplace. Member companies subscribe and receive updates as regulations change. Each company can override individual rules locally for its own operating context.

---

## 9. Technical Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` |
| Document parsing / OCR | Gemini Files API + document understanding |
| Relational store | PostgreSQL 17 (with `pgvector` available) |
| Search | Elasticsearch 8.17 |
| Graph store | Neo4j 5 |
| Job queue | Redis 7 + arq |
| MCP | FastMCP (mcp ≥ 1.9), 12 tools |
| Audit storage | Append-only Postgres tables; optional S3 Object Lock (WORM); optional TSA |
| Auth | OIDC / OAuth2 |
| Deployment | Container-native, Kubernetes-ready, Docker Compose for local dev |

The architecture intentionally keeps the LLM interface abstract; the `Evaluator` interface accepts any model that can perform structured judgment. Today's implementation is Gemini-first.

---

## 10. Roadmap

The project has progressed through Phases 1–6 and is now extending into Phase 7 — the cross-organizational rebrand.

### Phases 1–6 (largely complete)
- **Phase 1 — Foundation**: storage, search, extraction pipeline, basic governance.
- **Phase 2 — Enforcement**: evaluation engine, MCP, GitHub PR review, CI CLI, agent hooks.
- **Phase 3 — Discovery & Learning**: rule discovery, correction feedback loop, federation.
- **Phase 3.5 — Adoption Acceleration**: GitHub import, PR correction capture, impact preview, conflict transparency.
- **Phase 4 — Testing & Deployment Safety**: playground, test cases, alerts, snapshots.
- **Phase 5 — Self-Improving Governance**: batched evaluation, evaluation persistence, outcome dashboard, flywheel, active rule injection, structured remediation, maturity model, advanced intelligence.
- **Phase 6 — Platform & Ecosystem**: collaborative governance proposals, autonomous agent governance loop, cross-organization marketplace.

### Phase 7 — Cross-Organizational Generalization (in progress)

#### 7a. Branding fix (high impact, low cost)
- Add ≥ 6 business-domain templates (HR, contracts, expenses, advertising, compliance) — push catalog past 200 rules.
- Rewrite README and PROJECT.md so use cases lead with contracts, HR, sales, and compliance.
- Formalize and publish the Scope naming guideline, treating engineering and business symmetrically.
- Promote `sample_rules/sales_team_rules/` and add `sample_rules/hr_rules/`, `sample_rules/contract_rules/`, etc., to first-class status.

#### 7b. Subject abstraction
- Introduce `SubjectType` enum and `SubjectAdapter` interface.
- Migrate existing `code_change` to the new adapter system, preserving full backward compatibility.
- Implement `hr_event` and `contract_clause` adapters first.
- Add subject-typed `Remediation` subclasses.
- Add subject-typed prompt templates.

#### 7c. Discovery and ingestion expansion
- PDF / DOCX policy ingestion pipeline.
- Dedicated legal-document pipeline with chapter/article structure and amendment tracking.
- SharePoint, Confluence, Notion, kintone connectors.
- Polyglot Rules — full implementation.

#### 7d. Business-system integrations
- Common `BusinessEvent` normalization layer.
- Attendance, expense, contract, HR-core, ITSM, CRM, chat, doc-storage, identity connectors.
- Privacy-aware Slack / Teams scanning.

#### 7e. Persona-based UX
- Persona switcher (Compliance / Legal / HR / Finance / Engineering / Sales / Executive).
- Domain-segmented heatmap dashboards.
- JP / EN i18n.
- Onboarding wizard for business users.

#### 7f. Governance and audit hardening
- Audit-export reports (J-SOX, ISO 27001, SOX, PCI DSS).
- Optional WORM dual-write.
- Optional TSA time-stamping.
- New `Rule` fields: `jurisdiction`, `legal_force`, `review_cadence`, `applicable_subject_types`.

#### 7g. Multi-tenancy foundation
- `tenant_id` migration across all tables.
- Tenant-isolation authorization layer.
- Cross-organization Marketplace publishing.
- Privacy-preserving federated correction aggregation.

### Phase 8 — Industry Specialization (planned)
- Industry-specific rule packs (financial services, healthcare, manufacturing, public sector).
- Expert-review workflow for rule package certification.
- Regulator-feed integrations for automatic statutory updates.

---

## 11. Success Metrics

- **Coverage** — percentage of target source documents successfully extracted and registered.
- **Latency** — p50 / p95 / p99 evaluation latency in `preflight` mode.
- **Accuracy** — human-rated correctness on a held-out test set; precision and recall on conflict detection.
- **Adoption** — number of integrated systems and active rules; volume of evaluation requests per day.
- **Governance health** — percentage of rules with complete metadata, current rationale, active owners.
- **Time-to-comply on regulatory change** — median time between a source-law amendment and the corresponding internal rule revision being approved.
- **Cross-domain balance** — share of rules in non-coding domains (target: > 60% by end of Phase 7).
- **Shadow-to-enforcement rate** — > 70% of experimental rules reach stable within 60 days.
- **Auto-fix rate** — > 40% of SHOULD violations auto-fixed via structured remediations (where applicable).
- **Flywheel throughput** — > 5 rules/month auto-drafted from correction clusters.
- **Marketplace adoption** — number of subscribed rule packages per tenant.

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Always log full evaluation context; require human review on high-severity denials; consensus voting for CRITICAL rules; refinement feedback loop. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity; refinement loop suggests rewrites; require unit tests on each rule. |
| LLM costs scale poorly with rule corpus size | Two-stage evaluation (metadata pre-filter + LLM); aggressive caching; tiered model selection; batched evaluation. |
| Sensitive data leaks through evaluation context | Input sanitization; log masking; tenant isolation; optional fully self-hosted model deployment. |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via `effective_period`; sidecar mode for shadow testing; snapshot rollback. |
| Over-reliance reduces human judgment | Position the system as decision support, not decision replacement; preserve rationale visibility; require human approval for rule revisions. |
| Conflicts with existing IAM / GRC tools | Position the Rule Repository as a complementary semantic layer; provide integration points rather than competing with baseline controls. |
| Low-quality business templates damage credibility | Mark templates `expert_reviewed: true / false (reference only)`; gated marketplace publishing; partnerships with domain experts. |
| Drift back toward code-only positioning | Cross-domain balance metric in §11; review at quarterly cadence; ensure new features have non-code use cases. |
| Audit / regulatory rejection of LLM-based decisions | WORM dual-write; TSA time-stamping; framework-aligned reports; clear automated-decision-making notices and objection paths. |

---

## 13. Glossary

- **Rule** — a natural-language normative statement plus structured metadata, managed as a first-class object.
- **Statement** — the canonical natural-language text of a rule.
- **Modality** — strength of the obligation (MUST / MUST_NOT / SHOULD / MAY / INFO).
- **Scope** — set of subjects, systems, or contexts to which a rule applies.
- **Jurisdiction** — geographic or legal scope of authority (`jp`, `us-ca`, `eu`, `global`, ...).
- **Legal force** — `advisory` / `policy` / `regulatory` / `statutory`.
- **Subject** — the thing being evaluated (a code change, an HR event, a contract clause, etc.).
- **Subject Adapter** — the per-subject-type module that parses payload, assembles context, formats prompt, and interprets remediation.
- **Verdict** — result of an evaluation (ALLOW / DENY / NEEDS_CONFIRMATION / ALLOW_WITH_CONDITIONS / REQUIRES_DISCLOSURE).
- **Reason graph** — structured DAG explaining which facts triggered which conditions in which rules.
- **Provenance lineage** — chain of derivation from a higher-level source (e.g., a law) down to operational rules and contract clauses.
- **Meta-rule** — a rule whose subject is other rules.
- **Preflight / Posthoc / Sidecar** — three modes of integration: before-action, after-action, parallel-observation.
- **LLM-as-Judge** — architectural pattern of using an LLM to evaluate compliance with a natural-language rule.
- **Maturity level** — `experimental` (shadow mode) / `stable` / `proven`.
- **BusinessEvent** — normalized inbound payload schema from any business-system connector.

---

## 14. Open Questions

Most original open questions have been resolved. Remaining:

- **Multi-tenant isolation model.** Single-tenant deployments are first-class; full multi-tenant with per-tenant data isolation, key separation, and connector scoping is the Phase 7g target. Final decision on identity isolation (per-tenant Postgres schema vs row-level security) is pending.
- **External-data refresh strategy.** Rules that depend on external data (approved-vendor list, sanctioned-party list, exchange rates) need a refresh contract. Pending: a generic `ExternalDataSource` interface vs per-domain custom adapters.
- **Audit log retention beyond seven years.** Current default is 7 years (matching Japanese tax law). Some industries require permanent retention. Pending: a tiered storage model (hot Postgres → warm S3 → cold Glacier) with auto-migration.
- **Cross-organization data sovereignty.** Marketplace subscriptions cross tenant boundaries. Pending: a clear data-flow model documenting what crosses, what stays, and how privacy is preserved (especially for federated correction aggregation).
- **Connector certification.** As the connector ecosystem grows, third-party-built connectors will appear. Pending: a certification process and trust model.

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes should follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect. See `IMPROVEMENT.md` for the gap analysis that motivated Phase 7.*
