# Rule Repository

> A **cross-organizational normative management platform** for storing, searching, evaluating, and enforcing natural-language rules — laws, regulations, contracts, internal policies, engineering standards, marketing claims, financial controls, HR policies — across every department of an organization, using LLMs and AI agents.

---

## 1. Project Overview

The **Rule Repository** is the system of record for an organization's rules. It stores rules in their original natural-language form and makes them operationally useful: searchable, applicable, evaluable, and enforceable across business systems, document workflows, financial transactions, marketing content, and software development environments. Where traditional rule engines require translating human rules into a formal language (and losing nuance along the way), the Rule Repository keeps rules as written and uses LLMs to interpret, search, and enforce them at runtime.

This positioning is intentional and has three implications that shape every architectural decision:

1. **Cross-organizational** means Legal, HR, Finance, Sales, Marketing, IT, Operations, Engineering, and Executive functions are all first-class users. The system is not specialized for any one domain.
2. **Normative management** means rules are first-class assets with provenance, lineage, ownership, classification, lifecycle, audit trail — not configuration values attached to applications.
3. **Platform** means rules are decoupled from any single consumer. The same rule corpus drives runtime guardrails for AI agents, pre-flight checks for business transactions, post-hoc audits for compliance, and reference material for human reviewers.

This approach is inspired by, and generalizes, the concept of **Semantic Governance** (Google Cloud's Semantic Governance Policies), which uses natural-language constraints as runtime guardrails for AI agents. The Rule Repository extends that idea in four directions:

- **Wider scope of rules**: not only AI agent guardrails, but laws, regulations, contracts, HR policies, financial controls, marketing claim restrictions, and engineering conventions.
- **Wider scope of consumers**: human users, business systems, IDEs, CI pipelines, AI agents, and audit tools.
- **Wider scope of subjects**: not only agent tool-call attempts, but contract clauses, attendance events, financial transactions, marketing creatives, KYC profiles, and code changes.
- **Wider scope of time**: pre-flight checks, post-hoc audits, continuous monitoring, and historical re-evaluation under prior rule versions.

---

## 2. Background and Motivation

Most rules that govern organizations are written in natural language. Translating them into code or formal logic is expensive, lossy, and quickly drifts from the human-readable source of truth. Until recently this was an unavoidable cost of automation. With modern LLMs, natural-language rules can be interpreted directly by software at acceptable cost and quality, opening a new design space.

The Rule Repository fills a gap that no current category of software addresses cleanly:

- **Document management systems** (SharePoint, Confluence, Notion) store source documents but do not understand the rules inside them.
- **Rule engines** (Drools, DMN, OPA) require formal encoding and lose the original semantics.
- **GRC platforms** (ServiceNow GRC, Workiva, MetricStream) track compliance status but do not enforce rules at the point of action.
- **Contract review tools** (Ironclad AI, LinkSquares) operate only on contracts.
- **Code governance tools** (linters, SAST, code review platforms) operate only on code.
- **Semantic Governance products** apply natural-language constraints, but bind them to specific AI agents rather than treating rules as first-class, organization-wide assets.

The Rule Repository treats **rules themselves as first-class, versioned, governed, and classified assets**, decoupled from any single consumer and reusable across every department of an organization. The strategic claim is that the chain "law → regulation → internal policy → departmental rule → operational procedure → contract clause → engineering standard" is a single graph and should be governed as such, not as separate document silos.

---

## 3. Goals and Non-Goals

### 3.1 Goals

- Store rules in natural language with full traceability to source documents and upstream legal authorities.
- Provide rich search (full-text, vector, category, hybrid, intent-based) over rule corpora.
- Enable runtime evaluation across multiple subject types: code diffs, contract clauses, business events, financial transactions, marketing creatives, identity profiles, and arbitrary documents.
- Support pre-flight, post-hoc, and sidecar enforcement modes.
- Detect conflicts, redundancies, and dormant rules across the corpus.
- Make rule provenance, rationale, ownership, classification, and revision history first-class.
- Model the organization's functional structure (Legal, HR, Finance, etc.) explicitly, with rule ownership and approval routing tied to it.
- Provide compliance-grade audit trails suitable for SOX, J-SOX, ISO 27001, and GDPR procedures.
- Provide ergonomic SDKs and connectors so business systems, AI agents, and document repositories can integrate easily.
- Support multi-jurisdictional deployments with locale-aware rules and parallel-language consistency.

### 3.2 Non-Goals

- Replacing IAM, RBAC, ABAC, or network-layer access control. The Rule Repository is a **complementary semantic layer**, not a substitute for baseline security.
- Replacing legal counsel, compliance officers, auditors, or HR specialists. The system surfaces issues; humans resolve them.
- Acting as a general-purpose document management system. Document storage is a dependency, not a deliverable.
- Authoring legally binding contracts on behalf of users.
- Enforcing rules outside the scope of subjects the system understands. Subject coverage is explicit; out-of-scope situations are surfaced rather than silently allowed.

---

## 4. Architecture

The system is composed of layered components, designed so that the existing engineering-focused capabilities and the new cross-organizational capabilities share the same core.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Rule Management Server                              │
│                                                                           │
│   Extraction      Search(5)       Domain Evaluation Engines              │
│   Pipeline        BM25+Vector     ┌─────────────────────────────────┐    │
│   ─ Code           ─ Hybrid       │ Code Diff │ Contract │ Event   │    │
│   ─ Policy PDF     ─ Project      │ Transaction │ Creative │ ID    │    │
│   ─ DOCX           ─ Intent       │  ─ shared Rule Selector        │    │
│   ─ Confluence                    │  ─ shared Verdict Aggregator   │    │
│   ─ Regulation                    │  ─ subject-specific Subject    │    │
│   ─ Linter cfg                    │      Adapter + Prompt           │    │
│                                   └─────────────────────────────────┘    │
│                                                                           │
│   Discovery       Intelligence    Federation     Marketplace              │
│   (multi-source)  ─ Health        ─ Org/Dept     ─ Packages              │
│                   ─ Effectiveness ─ Inheritance  ─ Subscribe             │
│   Proposals       ─ Trends        ─ Override     ─ Conflicts             │
│   ─ Lifecycle     ─ Recommend     ─ Capacity                              │
│   ─ Voting        ─ Digest                                                │
│                                                                           │
│   Agent Gov       Classification  Compliance     Multilingual            │
│   ─ Trust         ─ PUBLIC/...    Audit          ─ Locales               │
│   ─ Mastery       ─ RLS           ─ Hash chain   ─ Jurisdiction          │
│   ─ Sessions      ─ PII           ─ WORM mirror                           │
│   ─ Exceptions    ─ Clearance     ─ Evidence                              │
│                                   ─ Legal hold                            │
│                                   ─ Regulator export                      │
│                                                                           │
│   Feedback        Playground      Snapshots      Alerts                  │
│   ─ PR diffs      ─ Sandbox       ─ Versioned    ─ Dormant               │
│   ─ Decisions     ─ Test cases    ─ Environment  ─ High deny             │
│   ─ Approvals     ─ Counter-      ─ Rollback     ─ Health decline        │
│   ─ Audits        │   examples    ─ Simulation                            │
│   ─ Disputes                                                              │
│                                                                           │
│   PostgreSQL    Elasticsearch   Neo4j      Redis     Audit (PG+WORM)     │
│                                                                           │
│   REST │ Intent │ Evaluate │ Gateway │ MCP │ Integration                  │
└─────┬──────┬──────┬───────────┬─────────┬───────────────────────────────┘
      │      │      │           │         │
   Rule    Agentic  CLI    Department  Connector Catalog
   SDK     SDK      Tools  UIs (HR/    (HR / ERP / Contract /
                           Legal/Fin)   Document Repos / iPaaS)
      │      │      │           │         │
      ▼      ▼      ▼           ▼         ▼
   Business  HR/Contract   CI/Hooks   Department    SAP / Workday /
   systems   /Finance      GitHub PR  Operators     Salesforce /
             systems       Agents     (non-eng)     Confluence / etc.
```

### 4.1 Architectural Layers

**Subject Layer** (new, foundational). Every evaluation flows through a `Subject` abstraction with a discriminator (`SubjectKind`). Concrete subjects supply parsing, feature extraction, prompt construction, and remediation generation. The rest of the evaluation pipeline is subject-agnostic.

**Rule Layer**. Rules are first-class natural-language statements with structured metadata (modality, scope, severity, classification, ownership, lineage, locale, jurisdiction, lifecycle).

**Organizational Layer** (new, foundational). Departments, capacities, and rule ownership are explicit. Approval routing, notifications, marketplace publishing, and audit access derive from this layer.

**Storage Layer**. PostgreSQL (system of record, append-only audit log with hash chain), Elasticsearch (derived search index), Neo4j (derived relationship graph), Redis (job queue), pluggable WORM storage (immutable audit mirror).

**Service Layer**. Domain evaluation engines, discovery analyzers, intelligence services, federation, marketplace, governance proposals, agent governance, feedback loop, playground.

**Delivery Layer**. REST API, Intent API, Gateway API, MCP server, integration connectors, CLI tools, SDKs.

### 4.2 Trust and Data Boundaries

- The server is the only component that holds the canonical rule corpus.
- Clients receive only the rules and judgments they are authorized to see, governed by the user's department, capacity, and clearance.
- All evaluation calls produce immutable audit records on the server side, with optional mirroring to WORM storage for compliance-grade scenarios.
- PII in evaluation context is masked in audit logs by default; explicit opt-in is required for retaining it.
- Cross-tenant isolation is enforced at the database (Row-Level Security) and search-index (document-level security) layers, not only at the API.

---

## 5. Domain Model

### 5.1 The `Rule` Entity

A rule is the central first-class object. It is **not** a regex or a code expression; it is a structured envelope around a natural-language statement.

| Field | Description |
|---|---|
| `id` | Stable identifier |
| `statement` | The rule text in natural language (the canonical form) |
| `locales` | Optional `dict[locale, LocalizedStatement]` for multilingual rules |
| `source_refs` | Pointers to the source document, section, and offset |
| `scope` | Who/what the rule applies to (org units, roles, systems, jurisdictions, file globs) |
| `subject_kinds` | The set of `SubjectKind`s this rule can evaluate (e.g., `[CLAUSE_SET]`, `[CODE_DIFF, DOCUMENT]`) |
| `modality` | MUST / MUST_NOT / SHOULD / MAY / INFO (RFC 2119-style) |
| `effective_period` | `valid_from` / `valid_until` |
| `preconditions` | Facts required to evaluate the rule |
| `exceptions` | References to other rules or carve-outs |
| `rationale` | Why the rule exists (purpose, intent) |
| `context` | Surrounding document text, regulatory authority, qualifying conditions |
| `severity` | LOW / MEDIUM / HIGH / CRITICAL |
| `classification` | PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED |
| `tags` | Free-form taxonomic labels |
| `following_examples` | Concrete examples of compliant behavior |
| `violation_examples` | Concrete examples of non-compliant behavior |
| `governance` | `RuleOwnership` — owner department, delegated approvers, revision history |
| `maturity_level` | EXPERIMENTAL / STABLE / PROVEN |
| `embedding` | Vector representation (derived) |

The `statement` is the **source of truth**. Structured fields exist for indexing, filtering, and prioritization — never to override the meaning of the statement.

### 5.2 The `Subject` Entity (Polymorphic)

A subject is what gets evaluated against rules. The `Subject` protocol is the central architectural abstraction enabling cross-domain coverage.

```
SubjectKind:
    CODE_DIFF       # software development
    CLAUSE_SET      # legal / contracts
    EVENT           # HR, operations (single event with optional sequence context)
    TRANSACTION     # finance, procurement (with optional graph context)
    CREATIVE        # marketing (text, image, video, multi-modal)
    DECISION        # operations (approval, denial, exception grants)
    IDENTITY        # KYC, sanctions, beneficial ownership
    DOCUMENT        # arbitrary text (policies, communications, drafts)
```

Each subject carries:

- `kind`: discriminator
- `identifier`: stable identity for audit
- `facts`: domain-specific structured payload
- `attachments`: binary or referenced evidence (PDFs, images, transcripts)
- `locale`: ISO language tag for locale-aware rule selection
- `jurisdiction`: legal jurisdiction (JP, US, EU, ...)
- `pii_fields`: which fact paths contain PII (used for redaction)

Subject classes own their `render_for_llm()` implementation, which produces the prompt-friendly representation. This is the seam at which domain knowledge enters the evaluation pipeline.

### 5.3 The `Department` and `Capacity` Entities

The organizational model is first-class and mandatory.

```
Department:
    id, name, type (LEGAL / HR / FINANCE / SALES / MARKETING / IT /
                    OPERATIONS / RND / EXECUTIVE / CUSTOM)
    parent_id, head, cost_center, locale

RuleOwnership:
    rule_id, owner_department_id, delegated_to,
    classification (PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED)

CapacityAssignment:
    department_id, user_or_group, capacity (OWNER / REVIEWER /
                                            SUBSCRIBER / AUDITOR),
    rule_filter
```

The implications are pervasive: approval routing, notifications, marketplace publishing rights, and audit access are all derived from this model. A change to a rule owned by Legal Department routes to Legal's REVIEWERs; alerts about HR rules notify HR's REVIEWERs; only a department's AUDITORs can read its restricted-classification audit records.

### 5.4 Rule Relationships

Rules form a graph, not a flat list. Modeling these relationships explicitly turns the repository from a list into a **provenance and impact graph**.

| Relationship | Meaning |
|---|---|
| `refines` | A specific rule that operationalizes a more abstract one |
| `overrides` | A rule that takes precedence over another |
| `conflicts_with` | Two rules that contradict each other (must be resolved) |
| `depends_on` | Evaluation requires another rule's verdict |
| `derives_from` | This rule originates from a higher-level rule (e.g., a law) |
| `succeeds` | A new revision that replaces a prior version |
| `localizes` | This rule is the locale-translation of another rule |

The lineage chain "law → regulation → industry guideline → internal policy → departmental rule → contract clause" is expressed entirely through `derives_from`. When an upstream node changes, the system identifies all downstream nodes and proposes review.

### 5.5 Verdict and Reason Graph

Every evaluation produces:

- `Verdict`: ALLOW / DENY / NEEDS_CONFIRMATION
- `confidence`: model confidence on a 0–1 scale
- `reason_graph`: structured DAG of which facts triggered which conditions in which rules
- `remediations`: structured `Remediation` array with `auto_applicable` flags
- `evidence_refs`: optional pointers to supporting documents

For experimental-maturity rules, DENY is downgraded to NEEDS_CONFIRMATION with `[SHADOW]` prefix.

### 5.6 Evidence

Evaluations may attach evidence — signed approvals, prior verdicts, reviewer comments, supporting documents.

```
EvidenceRef:
    type (DOCUMENT / VERDICT / APPROVAL / COMMENT / EXTERNAL),
    storage_uri (content-addressed),
    hash, classification, attached_at, attached_by
```

Evidence is content-addressed; tampering is detectable. Storage backend is pluggable (`adapters/evidence_storage`).

### 5.7 Audit Entry

Every evaluation, rule mutation, governance action, and access to restricted data is recorded in an append-only audit log with hash chaining. For `RESTRICTED` and `CONFIDENTIAL` classifications, mirroring to WORM storage is mandatory.

### 5.8 Meta-Rules

The system supports **rules about rules** ("Any contract clause must not contradict the procurement policy"; "All HR rules must have a designated owner in HR Department"; "Rules of CRITICAL severity require two approvers"). Meta-rules use the same evaluation pipeline but operate over the rule corpus itself.

---

## 6. Components

### 6.1 Rule Management Server

The server is the system of record. It exposes:

- **REST API** at `/api/v1/...` for CRUD on rules, documents, evaluations, departments, capacities.
- **Evaluate API** at `/api/v1/evaluate` accepting `subject_kind` and dispatching to the matching domain engine.
- **Intent API** at `/api/v1/intent` classifying natural-language queries (`lookup_rule`, `check_compliance`, `find_conflicts`, `explain_rule`, `simulate_change`).
- **Gateway API** at `/api/v1/gateway/...` for webhook-driven enforcement.
- **Intelligence API** for health, effectiveness, comparison, digest, agent analytics.
- **Discovery API** for multi-source rule discovery.
- **Federation API** for organizational hierarchy.
- **Proposals, Marketplace, Agent Governance, Snapshots, Playground, Alerts** as in the existing implementation, generalized for non-engineering domains.

**Capabilities** include rule CRUD with revision history and effective-date semantics; multi-source extraction (code, PDF, DOCX, Confluence, SharePoint, Notion, regulation feeds); five search modalities plus context and impact search; LLM-as-Judge evaluation via subject-aware engines; append-only audit log with hash chaining and WORM mirror; classification-aware access control; department-aware governance.

### 6.2 Subject Adapters

Located under `services/evaluation/subjects/`, one module per `SubjectKind`. Each implements the `Subject` protocol, owns a prompt template directory, and provides feature extraction and remediation parsing tailored to its domain.

The **Subject Registry** in `services/evaluation/subject_registry.py` maps `SubjectKind` values to adapter classes and is the single dispatch point.

### 6.3 Domain Evaluation Engines

The shared evaluation orchestrator (`services/evaluation/service.py`) is subject-agnostic: it assembles context, narrows rules through the rule selector, calls the appropriate subject's prompt, and aggregates verdicts. Each domain engine consists of (a) a Subject Adapter, (b) prompt templates, and optionally (c) domain-specific aggregation logic.

#### 6.3.1 Code Diff Engine

The original engine, refactored to operate behind `CodeDiffSubject`. Continues to support unified diffs, file paths, language detection, function extraction, and line-level remediation. Powers GitHub PR review, CI gating, and Claude Code integration.

#### 6.3.2 Contract Clause Engine (Legal)

Operates on `ClauseSetSubject` containing structured clauses extracted from a contract draft, with contract type, counterparty profile, and deal metadata. Supports modes: self-conformance against company standard clauses, cross-contract conflict detection, regulatory compliance, and risk scoring. Returns clause-scoped remediations with proposed rewrites.

New components: `adapters/contract_parser.py`, `adapters/contract_compare.py`, `services/evaluation/clause_aggregator.py`, `RuleVerdict.clause_remediation` extending `Remediation`.

#### 6.3.3 Event Engine (HR / Operations)

Operates on `EventSubject` with optional `EventWindow` (temporal context). Supports modes: single-event compliance, sequence-aware evaluation (monthly accumulations), and calendar-aware evaluation (annual ceilings, special-clause activation thresholds).

Used for attendance, expense, leave, business trip approvals. Connects via HR system adapters to systems like Workday, SAP SuccessFactors, SmartHR, freee人事労務.

#### 6.3.4 Transaction Engine (Finance / Procurement)

Operates on `TransactionSubject` with optional graph context (related transactions, accounts, parties). Supports modes: authorization (segregation of duties, approval limits), anti-fraud (anomalous patterns), tax compliance (invoice format, withholding, transfer pricing), sanctions (counterparty screening, beneficial owner traversal).

This engine's output is operationally bound to SOX/J-SOX requirements; compliance-grade audit (§6.7) is a prerequisite.

#### 6.3.5 Creative Engine (Marketing)

Operates on `CreativeSubject` carrying multi-modal content (text, image, video) via Gemini Files API. Supports modes: 景表法 (JFTC Act), 薬機法 (PMD Act), industry-specific claim restrictions, brand guideline enforcement.

#### 6.3.6 Identity Engine (KYC / Sanctions)

Operates on `IdentitySubject` carrying customer/counterparty profile data. Supports modes: PEP/sanctions screening with name fuzzy matching, adverse media via Google Search grounding, beneficial owner graph traversal, country-risk scoring.

### 6.4 Multi-Source Discovery

Discovery is the cold-start engine. It analyzes existing artifacts to propose rules.

**Code-based analyzers** (existing, retained):

- `claude_md.py` — CLAUDE.md parsing
- `linter_config.py` — ruff, eslint, tsconfig, prettier
- `code_patterns.py` — static analysis of conventions

**Policy-based analyzers** (new):

- `pdf_policy.py` — regulation/policy PDFs via Gemini Files API
- `docx_policy.py` — Word policy documents
- `contract_corpus.py` — extract de-facto standard clauses from historical contracts
- `regulation_feed.py` — e-Gov API, FSA notices, industry feeds, with `derives_from` linkage

**Source connectors** (new):

- `confluence_space.py`, `sharepoint_site.py`, `notion_workspace.py`, `google_drive_folder.py`, `box_folder.py`

The **`DocumentSource` Protocol** unifies sources. The **`IncrementalSource`** variant supports continuous ingestion: when an upstream regulation amends, descendants are flagged for review automatically.

All discovered rules pass through a human review queue before activation.

### 6.5 Federation and Organizational Model

The `Federation` model captures hierarchical rule composition (organization → team → project) and is now combined with the `Department` model (§5.3) for functional organizational structure. Rules at higher levels apply to descendants; descendants override locally.

The **Federation Resolver** walks the ancestor chain and applies overrides. The **Department Resolver** maps a user or system to its departments and capacities.

Rule ownership, approval routing, and notification fan-out flow through the Department Resolver. Marketplace publishing rights, audit access, and classification-based filtering flow through the Federation Resolver in conjunction with classification.

### 6.6 Classification and Multi-Tenancy

Classification is a property of rules, documents, evaluations, and audit entries:

- `PUBLIC` — readable by all authenticated users
- `INTERNAL` — readable by org members
- `CONFIDENTIAL` — readable by department members and approved subscribers
- `RESTRICTED` — readable by named individuals or auditors only

Enforcement happens at three layers:

1. **PostgreSQL Row-Level Security**: every session sets `current_user_clearance` and `current_user_departments`. Queries return only rows the user can read.
2. **Elasticsearch document-level security**: mirrors RLS in the search index.
3. **MCP-side clearance**: agents register with a clearance level. The MCP server filters rule retrieval and evaluation context to the agent's clearance.

PII fields are marked at `Subject` construction time and are redacted in audit logs by default.

### 6.7 Compliance-Grade Audit

The audit subsystem provides:

- **Append-only PostgreSQL audit log** with hash chaining (each entry includes the hash of the previous entry).
- **WORM storage mirror** for `RESTRICTED` and `CONFIDENTIAL` audit entries via pluggable backends (S3 Object Lock, Azure Blob Immutable Storage, GCS Bucket Locks).
- **Separation of duties**: application DB user has no SELECT on audit tables; only the `auditor` DB role does, and its access is itself logged.
- **Public hash anchoring**: periodic anchoring of the chain head to a transparency log (Sigstore Rekor or independent timestamp service).
- **Legal hold** primitives: `LegalHoldModel` ties scope filters to retention enforcement.
- **Evidence attachment**: content-addressed `EvidenceRef` array on `EvaluationRecord`.
- **Regulator export**: `POST /api/v1/audit/export?format=jsox|sox|fsa|gdpr` produces formatted artifacts satisfying specific frameworks. Each format is a separate adapter.

### 6.8 Multi-Source Feedback Loop

The feedback abstraction generalizes the existing PR-diff flywheel.

```
FeedbackEvent:
    kind: CODE_CORRECTION / DECISION_OVERRIDE / APPROVAL_OVERRIDE /
          EXCEPTION_GRANTED / AUDIT_FINDING / DISPUTE_OUTCOME /
          POLICY_CLARIFICATION / EXPLICIT_VERDICT_OVERRIDE
    original_verdict, corrected_verdict, reason, evidence_refs
```

Capture implementations:

| Capture | Domain |
|---|---|
| `pr_capture.py` (existing) | Software (PR diffs) |
| `contract_capture.py` | Legal (final vs drafted clauses, reviewer comments) |
| `decision_capture.py` | HR / Ops (reversed denials, exception grants) |
| `audit_capture.py` | Finance (auditor findings, correcting entries) |
| `deal_capture.py` | Sales (legal-review modifications, rejected deals) |
| `dispute_capture.py` | Legal (dispute outcomes, settlements) |
| `explicit_capture.py` | All (direct human "this verdict was wrong" feedback) |

`auto_drafter.py` becomes subject-aware: clustering uses subject-specific embedding spaces, drafting uses subject-specific prompts. The flywheel survives but generalizes across domains.

### 6.9 Agent Context Delivery (MCP)

Exposes the Rule Repository to AI agents via the Model Context Protocol. Agents register with type and clearance; subjects are formed from agent context; verdicts are returned with reasoning.

Agent types are no longer engineering-only:

- `coding_assistant`, `code_reviewer`, `security_scanner`, `deployment_agent` (existing)
- `contract_reviewer`, `clause_negotiator` (legal)
- `hr_processor` (HR)
- `expense_auditor`, `kyc_screener` (finance / compliance)
- `creative_reviewer` (marketing)
- `custom`

Each type has an `AgentTypeProfile` defining domain-appropriate trust thresholds, mastery measurement (e.g., "code rule mastery" vs "clause-pattern mastery"), and exception semantics.

MCP tools (12+) include: `search_rules`, `evaluate_compliance`, `explain_rule`, `find_conflicts`, `get_rules_for_context`, `register_agent`, `get_personalized_rules`, `challenge_verdict`, `request_exception`, `create_proposal`, `get_proposal_status`.

### 6.10 Marketplace

Versioned rule packages with publishing, subscribing, composition conflict detection, and quality scoring. Quality scoring is **domain-aware**: code packages weight evaluation accuracy; legal packages weight deal closure rate and dispute absence; HR packages weight policy stability.

`quality_score_breakdown` is exposed so subscribers understand how the score was computed.

### 6.11 Governance Proposals

Structured rule change management with:

- **Proposal lifecycle**: Draft → Review → Approved → Enacted, with revertable enactment.
- **Multi-approver voting** with thresholds derived from rule severity and classification.
- **Department-aware routing**: proposals route to OWNER and REVIEWER capacity holders of the rule's owning department.
- **Threaded comments** with inline suggestions.
- **Conflict analysis** (Neo4j) and **impact preview** (replay historical evaluations) before enactment.
- **Notification inbox** with capacity-aware fan-out.

Meta-rules (§5.8) govern proposal lifecycle (e.g., "CRITICAL severity rules require N approvers from the owning department").

### 6.12 Playground and Test Cases

Sandbox evaluation that does not persist to audit log, cache, or rule store. Per-rule test cases support manual creation, auto-generation from historical evaluations, and Gemini-generated examples (compliant + non-compliant).

Playground variants per `SubjectKind`:

- Code Playground (existing)
- Contract Playground — paste a draft clause, test rules
- HR Playground — paste an event JSON, test rules
- Transaction Playground — paste a journal entry or PO

### 6.13 Snapshots and Environment Deployment

Versioned, deployable rule sets per environment (development, staging, production). Atomic deployment, rollback, and impact simulation. Evaluation API accepts `environment` to use only rules from the active snapshot.

### 6.14 Proactive Alerts

Background workers detect dormant rules, high deny rates, health decline, effectiveness decline, locale inconsistency, classification mismatch, and rule conflicts. Alert types are extensible. Webhook delivery to Slack, email, or generic endpoints.

### 6.15 Multilingual and Jurisdictional Support

`Rule.locales` holds parallel-language rule statements. A cron job verifies semantic equivalence between locales using Gemini and raises `conflict_locale` alerts on divergence. Evaluation prefers the rule locale matching the subject's locale.

`scope.jurisdiction` filters applicable rules during evaluation. The frontend supports i18n with parallel JA/EN content.

### 6.16 Integrations Catalog

Connectors under `adapters/integrations/` organized by category, each implementing one or more of `DocumentSource`, `EventStream`, `TransactionStream`, `IdentityStream`.

Phase A (highest priority):

- HR: SmartHR, freee人事労務, Workday, SAP SuccessFactors
- Finance: freee会計, MoneyForward, SAP, Oracle EBS
- Contract: ContractS, Hubble, DocuSign, Ironclad
- Documents: Confluence, SharePoint, Notion, Google Drive, Box

Phase B:

- CRM: Salesforce, HubSpot
- ERP: SAP S/4HANA, Oracle Fusion, NetSuite
- Data: Snowflake, BigQuery, Databricks
- Identity: Okta, Azure AD, Google Workspace (organizational source for §5.3)

iPaaS compatibility (Workato, Zapier, n8n) is mandatory; every integration must also be reachable from the public REST API.

---

## 7. Key Features

### 7.1 Foundational

- Natural-language rule storage with full provenance to source documents.
- Subject-polymorphic evaluation across code, contracts, events, transactions, creatives, identities, decisions, and documents.
- Multi-source discovery (code artifacts and policy documents).
- Multi-modal search (full-text, vector, category, hybrid, intent, context, impact).
- Rule lifecycle: draft → review → approved → effective → superseded → retired.
- First-class organizational model (Department, Capacity, Ownership).
- Classification-aware multi-tenancy with RLS and document-level security.
- REST API, Intent API, Evaluate API, Gateway API, Integration API.
- Python SDKs (Rule Client, Agentic Rule Client) and TypeScript SDK.

### 7.2 Differentiating

- **Subject Polymorphism**: one platform, many evaluation domains.
- **Single Provenance Graph**: law → regulation → policy → rule → clause as one Neo4j graph traversable end-to-end.
- **Compliance-Grade Audit**: WORM, separation of duties, public anchoring, legal hold, evidence attachment, regulator export.
- **Multi-Source Cold-Start**: Day-one experience populated from existing policy libraries, contract corpora, regulation feeds — not just code.
- **Conflict Detector**: continuously scans for `conflicts_with` candidates across the corpus.
- **Counterexample Generator**: minimal compliant and non-compliant examples for every rule.
- **Rule Coverage**: dormant and over-triggered rule detection from event logs.
- **Change Impact Simulator**: replay historical events against proposed rule revisions.
- **Refinement Feedback Loop**: multi-domain feedback drives rule rewrites.
- **Polyglot Rules**: parallel-locale rule pairs with continuous equivalence verification.
- **Provenance Lineage**: upstream regulation changes auto-flag downstream rules for review.
- **Why API**: multi-level rationale traversing `rationale`, `context`, `source_refs`.
- **Automatic Rule Discovery**: bootstraps rules from many source types — solves the cold-start problem.
- **Cross-Project Federation**: org → team → project rule inheritance with overrides.
- **Department-Aware Governance**: ownership, approval, and notification routing through functional organization.
- **Rule Marketplace**: versioned packages, domain-aware quality scoring.
- **Autonomous Agent Governance**: per-agent profiles, trust levels, mastery, exception negotiation.

### 7.3 Cross-Cutting

- Immutable audit log with hash chain and optional WORM mirror.
- Tiered LLM strategy: model selection by `(subject_kind, severity, historical_disagreement_rate)`.
- PII-aware redaction in evaluation context and audit logs.
- Classification-aware RBAC: capacity (OWNER / REVIEWER / SUBSCRIBER / AUDITOR) per department.
- Pluggable LLM provider layer (Gemini default; Anthropic, OpenAI, self-hosted as alternatives).
- Per-department LLM quotas and rate limits.
- Latency budgets per subject (sub-second for code preflight, tens of seconds for contract review, sub-second for HR events).
- Evaluation request tracing with model ID, prompt version, latency, classification.

---

## 8. Use Cases

### 8.1 HR / Attendance Management

The HR system registers attendance and overtime events. The Rule Repository holds work regulations from the Labor Standards Act, the company's work rules, and any 36-Agreement special clauses. The Agentic Rule Client validates each registration in `preflight` mode and alerts on violations: monthly overtime exceeding the legal cap, annual ceilings approached, missing 36-Agreement filings. Event sequences over windows of varying lengths are evaluated together, not in isolation.

### 8.2 Contract Management

A legal team negotiates contracts using a contract management system. The Rule Repository holds internal procurement policies, prior contract terms, and sector regulations. When a counterparty draft is uploaded, the Contract Clause Engine extracts clauses, compares them against the company's standard clauses, detects conflicts with prior contracts, checks regulatory compliance (subcontracting law, antitrust), and proposes clause-level rewrites. Final contracts feed back through `contract_capture.py` to refine standard-clause rules.

### 8.3 Software Development

The Rule Repository stores engineering coding standards, security policies, documentation conventions, and architectural decisions. CI pipelines use `rulerepo-check` to evaluate pull requests; the GitHub App posts structured review comments. Claude Code uses MCP to receive applicable rules at edit time and after edit. Discovery bootstraps initial rules from CLAUDE.md, linter configs, and code patterns. Corrections flow into the flywheel and refine rules.

### 8.4 Regulatory Compliance

A financial institution stores consumer-protection laws, FSA notices, AML/KYC requirements, and internal procedures derived from them via `derives_from`. When a regulation is amended (auto-detected via the regulation feed), the Provenance Lineage and Change Impact Simulator identify all downstream procedures that need review. Compliance officers review proposals routed to them through the Department-aware governance flow. The audit trail satisfies regulatory examination procedures.

### 8.5 Marketing and Creative Review

Marketing produces ad copy, landing pages, social posts, and product label content. The Creative Engine reviews each item against 景表法, 薬機法 (when applicable), industry-specific claim restrictions, and brand guidelines. Multi-modal content (text + image) flows through Gemini Files API. Reviewer overrides feed back through `decision_capture.py` to refine rules.

### 8.6 Finance / SOX

Procurement, accounts payable, and finance teams operate on transactions in ERP. The Transaction Engine evaluates each authorization, payment, and journal entry against segregation-of-duties controls, approval-limit policies, anti-fraud signals, and tax compliance requirements. Audit findings feed back to refine controls. The audit trail is WORM-mirrored for SOX/J-SOX procedures and exportable in regulator-friendly formats.

### 8.7 KYC / Sanctions

Customer onboarding screens new accounts. The Identity Engine performs PEP/sanctions screening, adverse media checks (via Google Search grounding), beneficial owner graph traversal, and country-risk scoring. Edge cases route to compliance reviewers; resolution feeds back through `explicit_capture.py`.

### 8.8 AI-Assisted Development

A team uses Claude Code with the Rule Repository. Discovery bootstraps 50 rules from CLAUDE.md, linter configs, and code conventions in an afternoon. Agents receive applicable rules via MCP. Human corrections flow through the flywheel. Organization-wide engineering standards propagate via Federation, with project-specific overrides.

---

## 9. Technical Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS |
| LLM | Gemini 3 Flash + Gemini 3.1 Pro via `google-genai` (pluggable) |
| Document parsing | Gemini Files API (PDF), `python-docx` (DOCX), markdown parsers |
| Search | Elasticsearch 8.x with kNN |
| Graph | Neo4j 5.x |
| Relational | PostgreSQL 17 with pgvector (embeddings), RLS for multi-tenancy |
| Cache & queue | Redis 7 + arq |
| WORM storage | S3 Object Lock / Azure Immutable Blob / GCS Bucket Lock (pluggable) |
| Public anchoring | Sigstore Rekor (default) or pluggable timestamp authority |
| MCP | FastMCP (mcp >= 1.9), 12+ tools |
| Auth | OIDC / OAuth2 |
| Quality | ruff + mypy, ESLint + Prettier, pre-commit hooks |
| Deployment | Container-native, Kubernetes-ready |

The architecture intentionally avoids hard-coding a single LLM provider. The `LLMProvider` interface accepts any model that can perform structured judgment.

---

## 10. Roadmap

The project is structured in phases. Phases 1 through 6 represent the existing implementation; phases 7 through 10 represent the cross-organizational expansion described in this document.

### Phase 1 — Foundation [COMPLETE]

Storage and search: rule data model, document ingestion, multi-modal search, REST/Intent APIs, Python SDK, basic governance.

### Phase 2 — Enforcement [COMPLETE]

Code-Aware Evaluation Engine, Agent Context Delivery (MCP), GitHub PR review, CI CLI, agent hooks, Enforcement Gateway, Rule Intelligence.

### Phase 3 — Discovery and Learning [COMPLETE]

Automatic Rule Discovery (code-based), Agent Correction Feedback Loop (PR-based), Cross-Project Rule Federation.

### Phase 4 — Testing and Deployment Safety [COMPLETE]

Rule Playground, per-rule test cases, proactive alerts, versioned snapshots, environment-based evaluation.

### Phase 5 — Self-Improving Governance [COMPLETE]

Batched evaluation, evaluation persistence, outcome-oriented dashboard, correction-to-rule flywheel, active rule injection, zero-config bootstrapping, structured remediation, rule maturity model, advanced intelligence.

### Phase 6 — Platform and Ecosystem [PARTIALLY COMPLETE]

Collaborative Governance Workflow (Proposals) [DONE], Autonomous Agent Governance Loop [DONE], Rule Marketplace [DONE].

### Phase 7 — De-coding the Foundation [COMPLETE]

The pivot from engineering-centric to cross-organizational. All four streams shipped: Subject Polymorphism (`SubjectKind` enum, `@register` decorator, subject-agnostic orchestrator), Department/Capacity model (`DepartmentService`, `resolve_owner`/`resolve_approvers`/`resolve_audience`), Classification and RLS (PostgreSQL RLS policies, `with_user_context`, Elasticsearch document-level security, PII redactor), and Domain Template Pack v1 (60 rules across HR attendance, contract NDA/MSA, and expense policy packs with 100% field coverage). 500 tests pass with zero regressions.

**Value delivered**: Legal, HR, and Finance can put their actual rules in this system, trust who sees them, and route approvals through functional ownership.

### Phase 8 — Domain Engines and Discovery

- **Contract Clause Engine** with self-conformance, cross-contract conflict, regulatory compliance, risk scoring.
- **Event Engine** with single-event, sequence-aware, calendar-aware evaluation.
- **Document Discovery analyzers**: PDF, DOCX, Confluence, SharePoint, Notion, Google Drive, contract corpus mining, regulation feeds with `derives_from` linkage.
- **Domain-aware UX**: `/contracts/review/[id]`, `/events/[id]`, no-code rule editor, intent-first search, department-aware home dashboards.

**Value delivered**: The system understands contracts and events, and discovery works against existing policy libraries.

### Phase 9 — Compliance Grade

- **Audit hardening**: WORM storage, separation of duties, public hash anchoring, legal hold, evidence attachment, regulator export (J-SOX, SOX, FSA, GDPR).
- **Multilingual and Jurisdiction**: `Rule.locales`, locale consistency cron, locale-aware evaluation, frontend i18n, `scope.jurisdiction`.

**Value delivered**: Auditors can run their procedures against the system as-is. Global enterprises can adopt across jurisdictions.

### Phase 10 — Expansion (continuous)

- **Integration catalog**: Phase A (HR systems, ERP, contract platforms, document repositories), then Phase B (CRM, data lakes, identity).
- **Transaction, Creative, Identity engines**: financial controls, marketing claim review, KYC.
- **Feedback diversification**: contract, decision, audit, deal, dispute, explicit capture implementations.
- **Domain-adaptive model selection**: `(subject_kind, severity, disagreement_rate) → model`.

**Value delivered**: The system reaches into every domain where rules govern work, and learns from every domain's feedback signals.

---

## 11. Success Metrics

- **Coverage**: percentage of rules in target source documents successfully extracted and registered, per domain.
- **Latency**: p50 / p95 / p99 evaluation latency in `preflight` mode, broken down by `SubjectKind`.
- **Accuracy**: human-rated correctness of verdicts on held-out test sets, per domain; precision and recall on conflict detection.
- **Adoption**: number of integrated systems and active rules; volume of evaluation requests per day, broken down by `SubjectKind` and department.
- **Cross-domain breadth**: number of `SubjectKind`s with active rules and >100 evaluations per month.
- **Governance health**: percentage of rules with complete metadata, current rationale, classified properly, and an active owner department.
- **Time-to-comply on regulatory change**: median time between a source-law amendment and the corresponding internal rule revision being approved.
- **Audit readiness**: time required to assemble regulator export for a defined audit scope; should be sub-hour for routine scopes.
- **Shadow-to-enforcement rate**: >70% of experimental rules reach stable within 60 days.
- **Auto-fix rate**: >40% of SHOULD-level violations auto-fixed via structured remediations (where applicable).
- **Flywheel throughput**: >5 rules/month auto-drafted from correction clusters (per active domain); correction rate decreases >30% after flywheel rule activation.
- **Time-to-rule**: <1 week from correction pattern detection to approved rule.
- **Cross-org adoption signal**: percentage of departments (Legal/HR/Finance/Marketing/etc.) with active rule sets and active OWNERs.

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM verdicts are non-deterministic and may be wrong | Always log full evaluation context; require human review on high-severity denials; consensus voting for CRITICAL rules; refinement feedback loop. |
| Subject Polymorphism refactor breaks existing engineering integrations | Existing code path isolated as `CodeDiffSubject`; default `subject_kind=CODE_DIFF` preserves backward compatibility; existing tests must pass before new subjects ship. |
| Rule wording ambiguity leads to inconsistent verdicts | Counterexample generator surfaces ambiguity; refinement loop suggests rewrites; per-rule test cases required for `STABLE` graduation. |
| LLM costs scale poorly with rule corpus size | Two-stage evaluation (metadata pre-filter, then LLM); aggressive caching with rule-revision invalidation; tiered model selection; batched evaluation. |
| Sensitive data leaks through evaluation context | Subject-level PII marking; mandatory redaction in audit logs; per-classification storage isolation; pluggable self-hosted LLM. |
| Rule changes break dependent systems | Change Impact Simulator; staged rollouts via `effective_period`; sidecar mode for shadow testing; snapshot rollback. |
| Over-reliance reduces human judgment | Position the system as decision support, not decision replacement; preserve rationale visibility; require human approval for rule revisions. |
| Conflicts with existing IAM / GRC tools | Position as a complementary semantic layer; provide integration points; do not replace baseline access control. |
| Compliance audit accepts the system as evidence | WORM storage with public anchoring; separation of duties on audit access; regulator-export adapters. |
| Cross-domain expansion outpaces team capacity | Subject Polymorphism enables domains to be added independently; templates and connectors are parallel work streams; community contribution path via marketplace. |
| Multilingual divergence creates legal risk | Locale consistency cron; explicit `localizes` relationship; alerts on divergence; locale-tagged audit. |

---

## 13. Glossary

- **Rule**: a natural-language normative statement, plus structured metadata, managed as a first-class object.
- **Statement**: the canonical natural-language text of a rule.
- **Subject**: the polymorphic input to evaluation — code diff, clause set, event, transaction, creative, decision, identity, or document.
- **SubjectKind**: discriminator for `Subject`. Determines which adapter, prompt, and aggregator are used.
- **Modality**: the strength of the obligation (MUST, MUST_NOT, SHOULD, MAY, INFO).
- **Classification**: data sensitivity tier (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED).
- **Scope**: the set of subjects, systems, jurisdictions, or contexts to which a rule applies.
- **Department**: a functional organizational unit (Legal, HR, Finance, etc.) with rule-ownership rights.
- **Capacity**: a user's relationship to a rule set within a department (OWNER, REVIEWER, SUBSCRIBER, AUDITOR).
- **Verdict**: the result of an evaluation (ALLOW, DENY, NEEDS_CONFIRMATION).
- **Reason graph**: a structured DAG explaining which facts triggered which conditions in which rules.
- **Meta-rule**: a rule whose subject is other rules.
- **Provenance lineage**: the chain of derivation from a higher-level source (e.g., a law) down to operational rules and contract clauses.
- **Preflight / Posthoc / Sidecar**: three modes of integration corresponding to before-action, after-action, and parallel-observation enforcement.
- **LLM-as-Judge**: the architectural pattern of using a large language model to evaluate whether an action complies with a natural-language rule.
- **Maturity Level**: rule lifecycle stage (EXPERIMENTAL → STABLE → PROVEN).
- **Shadow Mode**: experimental rules return NEEDS_CONFIRMATION instead of DENY, with `[SHADOW]` reasoning prefix.
- **WORM**: Write-Once-Read-Many storage, used for compliance-grade audit mirroring.
- **Federation**: hierarchical rule composition (organization → team → project) with inheritance and override.
- **Locale / Jurisdiction**: language and legal-jurisdiction tags for rules and subjects.
- **Effectiveness Score**: 0–100 composite of precision, prevention rate, and adoption.

---

## 14. Open Questions

These will be resolved during ongoing design iterations:

- What is the canonical schema for `scope`? Free-form tags vs. structured org/role/system/region/jurisdiction tuples vs. a hybrid.
- How should the system handle rules that depend on external data sources (e.g., a list of approved vendors that changes daily)?
- What is the expected SLO for `preflight` evaluations per `SubjectKind`? This drives model selection and caching strategy per domain.
- Should the audit log be exposed to tenants in raw form, or only as derived reports? Should regulator-export formats be tenant-customizable?
- What is the multi-tenant isolation model? Single-tenant deployments for highly-regulated customers, multi-tenant for SaaS, or both with shared codebase?
- How are deprecated rules archived without losing the ability to re-evaluate historical events? What is the WORM retention policy default?
- How should `auto_applicable=true` remediations be governed for non-code subjects? Auto-applying contract changes is dangerous; auto-applying SHOULD-level lint fixes is fine. Per-subject defaults are needed.
- Should agent governance allow agents to *propose* rule changes (not just challenge verdicts)? If so, with what governance gating?
- What is the policy for cross-organization marketplace? Public publishing is feature 6.10; permissions, attribution, and quality gates need definition.

---

*This document is the canonical specification for the Rule Repository project. It is itself subject to revision, and changes should follow the same review process expected of high-importance rules: proposed in draft, reviewed by stakeholders, and approved before taking effect.*
