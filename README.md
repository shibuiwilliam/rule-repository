# Rule Repository

An organization-wide platform for managing rules in natural language -- laws, contracts, HR regulations, expense policies, communication standards, engineering conventions, and everything in between. Store them once, search them instantly, enforce them everywhere.

Traditional rule engines force you to translate human-written rules into code or formal logic. That translation is expensive, lossy, and drifts from the original intent over time. The Rule Repository takes a different approach: keep every rule exactly as written, and let LLMs interpret, search, and enforce them at runtime.

A legal counsel reviewing an NDA, an HR manager checking overtime compliance, a finance officer screening an expense claim, and an engineer running a pre-commit check all use the same platform -- each through a console designed for their workflow.

---

## Table of Contents

- [Quick Start](#quick-start)
- [What You Can Do](#what-you-can-do)
- [How It Works](#how-it-works)
- [Surfaces and Domain Packs](#surfaces-and-domain-packs)
- [Architecture](#architecture)
- [Deployment Tiers](#deployment-tiers)
- [Business Event Ingestion](#business-event-ingestion)
- [MCP Server](#mcp-server)
- [CLI Tools](#cli-tools)
- [Frontend](#frontend)
- [Evaluation Engine](#evaluation-engine)
- [Norm Lineage](#norm-lineage)
- [Rule Kinds](#rule-kinds)
- [Structured Scope](#structured-scope)
- [Multilingual Rules](#multilingual-rules)
- [Rule Extraction](#rule-extraction)
- [Rule Templates](#rule-templates)
- [Compliance and Privacy](#compliance-and-privacy)
- [Eval Harness](#eval-harness)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-started/) and Docker Compose v2
- A [Gemini API key](https://ai.google.dev/gemini-api/docs) (optional -- the stack runs without one, but LLM features will return placeholder verdicts)

### Start the full stack

```bash
git clone https://github.com/shibuiwilliam/rule-repository.git && cd rule-repository
cp .env.example .env          # add GEMINI_API_KEY if you have one
make up                       # docker compose up --build -d
make seed                     # load sample rules across all domains
```

After about a minute:

| Service | URL | Purpose |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI server (40 API routers) |
| Swagger UI | http://localhost:8000/docs | Interactive API explorer |
| Frontend | http://localhost:3000 | Persona-specific consoles (57 pages, 9 route groups) |
| PostgreSQL | localhost:5432 | Source of truth with Row-Level Security |
| Elasticsearch | localhost:9200 | Full-text + vector hybrid search |
| Neo4j | localhost:7474 | Rule relationship graph + norm lineage |
| Redis | localhost:6379 | Background job queue (arq, 9 cron jobs) |
| MCP Server | localhost:8001 | AI agent tool integration (24 tools) |

### Start with Postgres only (Tier 1)

For quick exploration without the full infrastructure:

```bash
make up.tier1                 # server + frontend + postgres only
```

Tier 1 uses Postgres FTS for search, adjacency tables for graph queries, and in-process scheduling. No Elasticsearch, Neo4j, or Redis required.

### Try it

```bash
# Search for rules across any domain
curl -X POST http://localhost:8000/api/v1/search/fulltext \
  -H "Content-Type: application/json" \
  -d '{"query": "overtime limit"}'

# Ingest a business event for evaluation
curl -X POST http://localhost:8000/api/v1/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "finance.expense.submitted",
    "actor": {"type": "employee", "id": "E001", "department": "sales"},
    "subject": {
      "type": "transaction",
      "payload": {"amount_jpy": 50000, "category": "entertainment"},
      "context_facts": {"remaining_budget_jpy": 100000}
    },
    "occurred_at": "2026-04-01T10:00:00+09:00",
    "correlation_id": "expense-12345",
    "mode": "preflight"
  }'

# Review a contract clause against legal rules
curl -X POST http://localhost:8000/api/v1/evaluate/contract \
  -H "Content-Type: application/json" \
  -d '{
    "subject": {
      "surface": "contract",
      "identifier": "nda-draft-1",
      "payload": {
        "clause_text": "The receiving party may share Confidential Information with any affiliate.",
        "clause_type": "confidentiality",
        "parties": ["Acme Corp", "Beta Inc"]
      },
      "facts": {},
      "locale": "en"
    },
    "mode": "posthoc"
  }'

# Check an HR action against labor regulations
curl -X POST http://localhost:8000/api/v1/evaluate/human_action \
  -H "Content-Type: application/json" \
  -d '{
    "subject": {
      "surface": "human_action",
      "identifier": "overtime-check",
      "payload": {
        "action": "register_overtime",
        "actor_id": "E001",
        "facts": {"hours": 50, "month": "2025-04"}
      },
      "facts": {"hours": 50},
      "locale": "en"
    },
    "mode": "posthoc"
  }'

# Evaluate a code change
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"diff": "- pass\n+ password = os.environ[\"SECRET\"]", "scope": "engineering/python"}'

# Ask a question in natural language
curl -X POST http://localhost:8000/api/v1/assistant/turn \
  -H "Content-Type: application/json" \
  -d '{"user_message": "Can I expense JPY 30,000 for a client dinner?", "language": "ja"}'

# Ask a simpler question
curl -X POST http://localhost:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the overtime limits for employees?"}'
```

### Stop

```bash
make down                     # stop containers, keep data
docker compose down -v        # stop and delete all volumes
```

---

## What You Can Do

The Rule Repository stores rules as natural-language statements and evaluates any kind of work artifact against them using LLMs. Rules can come from any domain:

- **Legal**: Review contract clauses against NDA/MSA templates, detect missing protections, track regulatory changes
- **HR / Labor**: Check overtime against 36-agreement caps, validate leave requests, monitor attendance compliance
- **Finance**: Screen expense claims, enforce approval thresholds, validate procurement rules
- **Communications**: Flag harassment, detect confidential data in chat channels, ensure product-claim accuracy
- **Engineering**: Enforce coding standards, catch security issues (OWASP), validate API design
- **IT Security**: Review IaC plans, check access control, verify encryption requirements
- **Sales**: Validate advertising claims, enforce discount authority, check quote accuracy
- **Compliance**: Track regulatory amendments, monitor department violation trends, manage action queues

Each rule carries structured metadata: modality (MUST / MUST_NOT / SHOULD / MAY / INFO), severity (LOW through CRITICAL), kind (normative / computational / procedural / definitional / principle), structured scope with multi-axis dimensions, department ownership, effective period, locale, maturity level, rationale, and examples of both compliance and violation.

---

## How It Works

1. **Store rules in natural language.** Import them from PDFs, Word documents, Excel tables, email archives, meeting minutes, employee handbooks, or create them directly. Each rule keeps its original wording, source reference, department ownership, and full revision history.

2. **Evaluate anything against those rules.** Send a *Subject* -- a code diff, a contract clause, an HR event, a financial transaction, a chat message, or any text -- and the system selects the relevant rules, sends them to an LLM alongside the subject, and returns per-rule verdicts with typed remediations (`code_edit`, `text_rewrite`, `field_change`, `approval_add`, `process_reroute`, `clarification`, or `block`).

3. **Ingest business events.** External systems push events (expense submissions, attendance registrations, contract drafts) to a single endpoint. The system resolves scope from the event type and evaluates automatically.

4. **Track norm lineage.** Rules don't exist in isolation. A department overtime policy *derives from* the Labor Standards Act. When the law changes, every downstream rule is automatically flagged for review.

5. **Act on the results.** Integrate via REST API, MCP tools for AI agents, CLI commands in CI/CD, or the Conversational Assistant for end users. Each persona (Legal, HR, Finance, Engineering, Compliance, Marketing, Security, Sales, Admin) has a dedicated console.

---

## Surfaces and Domain Packs

### Surfaces

A **Surface** defines a type of thing being evaluated. The evaluation engine is surface-agnostic -- it does not know or care whether it is evaluating code or a contract. Each surface has its own adapter that translates domain-specific input into a uniform Subject.

| Surface | What it evaluates | Example input |
|---|---|---|
| **Code** | Diffs, file changes, repository state | `git diff` output |
| **Contract** | Clauses, redlines, contract metadata | NDA clause text + parties |
| **Human Action** | HR events, attendance, leave requests | Overtime registration |
| **Transaction** | Expenses, invoices, purchase orders, journal entries | Expense claim with amount |
| **Document** | Policies, reports, marketing copy | Internal policy section |
| **Message** | Emails, chat messages, social media | Chat message content |
| **Generic** | Anything else | Free-form text + facts |

Each surface provides: a `SurfaceAdapter` (parses input, resolves scopes, provides prompt hints), a subject dataclass, a PII field list, surface-specific location types (e.g., `CodeLocation` with file/line, `ContractLocation` with clause ref), and a default audit retention period.

### Domain Packs

A **Domain Pack** bundles prompts, analyzers, templates, and metadata schemas for one business domain. Adding a new domain is an additive operation -- no changes to the evaluation core.

The server ships 9 built-in domain packs (Code, Contract, HR Attendance, Communication, Expense, Legal, Sales, IT Security, Governance), plus 7 external domain packs under `packages/domain-packs/` with their own prompt templates and rule templates.

| Pack | Surface | Persona | Example rules |
|---|---|---|---|
| **Code** | Code | Engineering | Coding standards, security, API design |
| **Contract** | Contract, Document | Legal | NDA clauses, MSA terms, SOW templates |
| **HR Attendance** | Human Action | HR | Labor regulation, overtime caps, leave |
| **Communication** | Message | Compliance | Communication policies, marketing rules |
| **Expense** | Transaction | Finance | Fiscal policy, approval thresholds |
| **Legal** | Contract | Legal | Contract review, regulatory compliance |
| **Sales** | Generic | Sales | Pricing policy, discount authority |
| **IT Security** | Code, Document | Security | Access control, IaC/Terraform, OWASP |
| **Governance** | Generic | Compliance | Corporate governance, meta-rules |

---

## Architecture

```
+-----------------------------------------------------------------+
|                     Rule Repository Server                      |
|                                                                 |
|  +------------------+  +------------------------------------+  |
|  | Domain-Neutral   |  | Surfaces (7)                       |  |
|  | Core             |  |                                    |  |
|  |                  |  | Code  Contract  Human Action       |  |
|  | Rule CRUD+Search |  | Transaction  Document  Message     |  |
|  | Evaluation Engine|  | Generic                            |  |
|  | Norm Lineage     |  |                                    |  |
|  | Audit+Compliance |  | Each: adapter, subject dataclass,  |  |
|  | Intelligence     |  | prompt hints, PII config           |  |
|  | Proposals+Gov.   |  +------------------------------------+  |
|  | Fact Store       |  | Domain Packs (9)                   |  |
|  | Department RBAC  |  |                                    |  |
|  | Risk+Attestation |  | Code  Contract  HR Attendance      |  |
|  | Multi-tenant     |  | Communication  Expense  Legal      |  |
|  +------------------+  | Sales  IT Security  Governance     |  |
|                         +------------------------------------+  |
|                                                                 |
|  +------------------+  +------------------------------------+  |
|  | LLM Abstraction  |  | Integration Layer                  |  |
|  |                  |  |                                    |  |
|  | Primary/fallback |  | 40 REST API routers                |  |
|  | Gemini, Anthropic|  | MCP Server (24 tools)              |  |
|  | OpenAI, self-host|  | Business Event Ingestion           |  |
|  +------------------+  | CLI (8 commands)                   |  |
|                         +------------------------------------+  |
|                                                                 |
|  PostgreSQL 17     Elasticsearch 8     Neo4j 5     Redis 7     |
|  (source of truth) (search index)      (graph)     (jobs)      |
+-----------------------------------------------------------------+
```

**Design principles:**

- **Postgres is the source of truth.** Elasticsearch and Neo4j are derived projections. If they disagree, Postgres wins and projections are rebuilt via reconciliation scripts.
- **The evaluation core is surface-agnostic.** Surface adapters own all domain knowledge -- scope resolution, prompt hints, PII fields, location types, remediation formats. The core pipeline never branches on surface type.
- **All LLM calls go through a single router** with primary/fallback chains, per-scope provider overrides, and support for Gemini, Anthropic, OpenAI, and self-hosted models. No business logic calls a provider directly.
- **Department RBAC is non-bypassable.** Every endpoint that returns or mutates rules applies department visibility filtering via 10 department types and 4 capacity levels.
- **Multi-tenant by construction.** Every entity carries `tenant_id`. Postgres Row-Level Security enforces isolation at the data layer.
- **Norm lineage and organizational federation are orthogonal.** A rule sits on two independent axes: its norm tier (Law to Operational Rule) and its organizational owner (Org to Team to Project).

---

## Deployment Tiers

The server detects available services at startup and adapts automatically. Application code uses the same interfaces regardless of tier.

| | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| **Make target** | `make up.tier1` | `make up.tier2` | `make up` |
| **PostgreSQL** | Yes | Yes | Yes |
| **Elasticsearch** | No (Postgres FTS) | Yes | Yes |
| **Neo4j** | No (adjacency tables) | No (adjacency tables) | Yes |
| **Redis + arq** | No (in-process) | Yes | Yes |
| **MCP Server** | No | No | Yes |
| **Services** | 3 | 7 | 11 |
| **Best for** | Pilots, local dev | Standard production | Full capability |

---

## Business Event Ingestion

External business systems integrate by pushing events to a single endpoint. The Rule Repository resolves scope from the event type, selects applicable rules, evaluates the subject, and returns verdicts synchronously.

```
POST /api/v1/events/ingest
```

Supported event types follow a `{department}.{entity}.{action}` pattern:

| Event type | Resolved scopes |
|---|---|
| `finance.expense.submitted` | `finance/expense`, `compliance/anti-bribery` |
| `hr.attendance.registered` | `hr/attendance`, `hr/overtime` |
| `hr.leave.requested` | `hr/leave` |
| `legal.contract.draft_created` | `legal/contract` |
| `sales.email.drafted` | `sales/communication`, `compliance/privacy` |
| `marketing.creative.submitted` | `marketing/compliance` |
| `engineering.pr.opened` | `engineering/code` |

Three modes:
- **preflight** -- blocks until evaluation completes; use when the calling system needs a go/no-go decision before proceeding
- **posthoc** -- evaluates and persists the audit record; the calling system has already acted
- **sidecar** -- observes without affecting the calling flow

---

## MCP Server

The MCP (Model Context Protocol) server lets AI agents interact with the rule repository through 24 tools:

| Tool | Purpose |
|---|---|
| `search_rules` | Find rules by natural-language query with scope/severity filters |
| `explain_rule` | Detailed explanation with rationale, provenance, and relationships |
| `find_conflicts` | Detect conflicts between rules |
| `evaluate_compliance` | Evaluate whether a code change or action complies with rules |
| `evaluate_subject` | Evaluate any subject against rules (surface-agnostic) |
| `evaluate_contract` | Evaluate a contract clause against applicable rules |
| `evaluate_transaction` | Evaluate a financial transaction against applicable rules |
| `evaluate_communication` | Evaluate a communication draft against applicable rules |
| `discover_rules` | Propose rules from code, configs, or documents |
| `get_rules_for_context` | Get rules relevant to a coding context |
| `get_rules_for_contract_review` | Get rules relevant to a contract review |
| `get_rules_for_transaction` | Get rules relevant to a financial transaction |
| `get_rules_for_communication` | Get rules relevant to communications |
| `list_available_surfaces` | List all registered evaluation surfaces |
| `lookup_norm_lineage` | Walk the norm hierarchy upstream or downstream |
| `find_clause_conflicts` | Detect conflicts in contract clauses |
| `check_action` | Check whether a human action is compliant |
| `review_communication` | Review a message for policy compliance |
| `create_proposal` | Submit a rule change proposal |
| `get_proposal_status` | Check proposal approval status |
| `register_agent` | Register an agent with the governance system |
| `get_personalized_rules` | Get rules tailored to an agent's trust level |
| `challenge_verdict` | Challenge a verdict with evidence |
| `request_exception` | Request a one-time exception to a rule |

```bash
# stdio mode (for Claude Code, Cursor, Windsurf, etc.)
uv run rulerepo-mcp

# HTTP mode (for remote agents)
MCP_TRANSPORT=streamable-http uv run rulerepo-mcp
```

---

## CLI Tools

The unified `rulerepo` CLI consolidates all commands. Legacy standalone entry points (`rulerepo-check`, etc.) are preserved for backwards compatibility.

```bash
# Evaluate a code change in CI
rulerepo check --diff "$(git diff main...HEAD)" --format github-actions

# Review a contract document
rulerepo review-contract --file ./contracts/draft.docx --output redline.html

# Check an HR action against labor regulations
rulerepo check-action --action register_overtime --actor user:E001 --json '{"hours":50}'

# Pre-commit hook for AI agents
rulerepo hook preflight --file src/api/handler.py --prompt "Adding authentication"

# Install hooks into Claude Code settings
rulerepo hook install --server-url http://localhost:8000

# Ingest rules from a document
rulerepo ingest --source pdf --file ./policy.pdf --scope hr/attendance/jp

# Export rules to YAML
rulerepo export --project backend-api --output rules.yaml

# Zero-config project setup
rulerepo init --name my-project

# Check system health
rulerepo doctor

# Verify audit chain integrity
rulerepo audit verify
```

---

## Frontend

A Next.js 15 + React 19 + Tailwind CSS frontend with 57 pages organized into 9 persona-specific route groups. Each persona sees a dashboard aligned to their workflow, not a generic engineering view. The frontend supports English and Japanese via `next-intl`, with a locale switcher in every console.

| Console | Route group | Pages | Key features |
|---|---|---|---|
| **Main Dashboard** | `(dashboard)` | 25 | Rules, search, proposals, playground, intelligence, audit, assistant, departments, onboarding |
| **Legal** | `(legal)` | 5 | Contract review, clause library, redlines, norm lineage |
| **HR** | `(hr)` | 7 | Violations, attendance, leave, lifecycle, policies, event detail |
| **Finance** | `(finance)` | 5 | Transaction detail, expense policies, audit reports, controls |
| **Compliance** | `(compliance)` | 5 | Bundles, audit packets, exception tracking, regulatory feed |
| **Marketing** | `(marketing)` | 4 | Creative review, guidelines |
| **Admin** | `(admin)` | 3 | Tenant management, user provisioning |
| **Sales** | `(sales)` | 1 | Sales dashboard |
| **Security** | `(security)` | 1 | Classification overview |

The sidebar is organized into sections: **Observe** (dashboard, intelligence, compliance cockpit, feedback, audit), **Manage** (rules, discover, documents, proposals, snapshots, departments), **Use** (assistant, ask, search, playground), and **Enforce** (review, gateway, federations).

Each persona console has a themed layout with its own accent color, sidebar navigation, and vocabulary. Shared components like `PersonaSwitcher`, `NormLineageViewer`, `RuleGraph`, and `RelationshipManager` adapt to the active persona context.

---

## Evaluation Engine

The evaluation pipeline works the same regardless of the surface being evaluated:

1. **Surface adapter** -- transforms domain-specific input (diff, contract clause, HR event, expense claim, etc.) into a uniform Subject with surface-specific location types
2. **Rule selection** -- multi-stage filter: structured scope dimensions, subject type, artifact type, severity, and relevance scoring
3. **Kind dispatch** -- rules are partitioned by `kind`. Computational, procedural, and definitional rules are resolved deterministically without LLM calls. Only normative rules proceed to the LLM.
4. **Fact resolution** -- the Fact Store resolves external facts (employee grade, 36-agreement status, contract value, remaining budget). Context Providers (`StaticFileProvider`, `HttpProvider`) can supply missing facts automatically.
5. **LLM evaluation** -- the selected normative rules and the subject are sent to the LLM with surface-specific prompt hints. Cross-locale fallback selects translated rule statements when available.
6. **Verdict aggregation** -- per-rule verdicts are aggregated into ALLOW / DENY / NEEDS_CONFIRMATION / ALLOW_WITH_CONDITIONS / REQUIRES_DISCLOSURE
7. **Remediation** -- typed remediation proposals per surface: `code_edit` (line-level patches), `text_rewrite` (document span replacement), `field_change` (transaction field correction), `approval_add` (escalate to approver), `process_reroute` (redirect workflow), `clarification` (request missing information), `block` (requires human judgment)
8. **Audit persistence** -- model ID, prompt version, inputs, outputs, latency, surface, actor, and locale are logged to the append-only, hash-chained audit log

Additional features:

- **Multi-judge consensus** for CRITICAL-severity rules (a second LLM provider confirms)
- **Confidence calibration** via conformal prediction
- **Verdict drift detection** -- daily cron alerts when the same rule + input produces different verdicts over time (30-day windows, 20pp threshold)
- **Maturity levels** -- rules progress through `experimental` (shadow mode, DENY downgraded to NEEDS_CONFIRMATION), `stable` (warning mode), and `proven` (full enforcement)
- **Prompt injection defense** -- user content is wrapped in delimiters and screened for known injection patterns
- **Cost guardrails** with per-tenant monthly budget, 80% warning, and 100% hard cap
- **Data classification routing** -- RESTRICTED-sensitivity rules are evaluated on self-hosted LLMs only; logs purge after 90 days
- **Idempotent evaluation** -- optional `submission_id` returns the same verdict within a configurable window

---

## Norm Lineage

Every rule has a **norm tier** that places it in a regulatory hierarchy:

```
LAW --> REGULATION --> GUIDELINE --> CORPORATE_POLICY --> DEPARTMENT_RULE --> OPERATIONAL_RULE
```

Rules are linked via `DERIVES_FROM` relationships. Walking the chain answers questions like *"Which law is this overtime policy derived from?"* or *"If this regulation changes, which internal rules are affected?"*

- **Upstream walk**: from an operational rule back to its source law
- **Downstream walk**: from a law to all derived internal rules (breadth-first)
- **Amendment propagation**: when a LAW or REGULATION rule changes, a background worker flags every transitive downstream rule with `pending_norm_change_review`
- **Polyglot drift detection**: a weekly worker compares EN/JA rule translations and flags semantic drift above threshold (0.85 equivalence score)

The norm lineage is **orthogonal** to the organizational federation (Org / Team / Project). A single rule can simultaneously derive from the Labor Standards Act (norm axis) and be owned by the HR department (org axis).

---

## Rule Kinds

Not all rules require LLM judgment. The `kind` field on each rule determines its evaluation strategy, saving LLM tokens and improving determinism where possible.

| Kind | Evaluation approach | Example |
|------|-------------------|---------|
| **normative** | Full LLM-as-Judge reasoning | "Code reviews must address security concerns" |
| **computational** | Deterministic threshold check first, LLM only for edge cases | "Monthly overtime MUST NOT exceed 45 hours" |
| **procedural** | State-transition / ordering verification | "36 Agreement must be filed before assigning overtime" |
| **definitional** | Always ALLOW (reference only, no violations) | "'Force majeure' means acts of God, war, or government action" |
| **principle** | Always ALLOW (evaluated through derived normative rules) | "All dealings must be transparent and honest" |

The kind dispatcher partitions rules before the LLM batch call. Computational rules extract numeric thresholds from the rule statement (supporting both English units like "45 hours" and Japanese units like "45時間") and compare them against subject facts deterministically via `asteval`. Procedural rules check that preconditions appear in the workflow steps. Only normative rules -- which require genuine judgment -- are sent to the LLM.

Each kind has a typed body variant: `NormativeBody`, `ComputationalBody` (expression + required inputs + unit), `ProceduralBody` (states + transitions), `DefinitionalBody` (term + definition + lookup table), and `PrincipleBody` (guidance + derived rule IDs).

---

## Structured Scope

Rules use multi-axis structured scope for precise applicability filtering. This prevents cross-domain contamination (an HR overtime rule won't match against a finance expense query) and enables fine-grained rule selection.

```yaml
structured_scope:
  path: "hr/attendance/jp"
  dimensions:
    domain: "hr"                  # legal | hr | finance | sales | engineering | ...
    org_unit: "acme/jp/tokyo"     # organizational hierarchy
    subject_type: "attendance"    # contract | expense | code_file | employee | ...
    jurisdiction: "JP"            # optional attribute
```

Three primary dimension keys receive first-class treatment in indexing and selection: `domain`, `org_unit`, and `subject_type`. Additional dimensions (jurisdiction, confidentiality level, customer segment, etc.) are supported as generic key-value pairs.

The rule selector uses structured scope dimensions for relevance scoring, boosting rules whose dimensions overlap with the query. Elasticsearch indexes all dimensions as keyword fields for efficient filtering. The `org_unit` dimension supports ancestor matching -- a rule scoped to `acme/jp` also applies to `acme/jp/tokyo`.

---

## Multilingual Rules

Rules can be authored in any language and linked to translations in other languages. The system verifies that translations remain semantically equivalent over time.

**How it works:**

1. **Author a rule** with a `locale` (e.g., `ja` for Japanese, `en` for English).
2. **Link a translation** via `POST /api/v1/rules/{id}/translations` -- this creates a new rule in the target language and a `rule_translations` link record.
3. **Verify equivalence** via `POST /api/v1/rules/{id}/translations/verify` -- the `PolyglotVerifier` sends both statements to the LLM and returns a 0.0-1.0 semantic equivalence score. Scores below 0.85 are flagged as drift.
4. **Search by language** using the `language` query parameter or the `Accept-Language` HTTP header on search endpoints.

**Background workers** run automatically:
- **Translation drift checker** (daily, 3:30 AM) -- compares each rule's `statement_translations` against the canonical statement
- **Polyglot equivalence validator** (weekly, Sunday 6 AM) -- groups rules by `equivalence_id` and verifies pairwise semantic equivalence
- **Translation pair verifier** (daily, 5:30 AM) -- re-scores all linked translation pairs

---

## Rule Extraction

Six domain-specific extractors bootstrap rules from existing organizational documents:

| Extractor | Input | What it produces |
|---|---|---|
| **Contract** | PDF/DOCX contracts | Clause-level rules with Article-Section-Clause hierarchy |
| **Regulation** | Regulation documents | Normative statements with 条/項/号 (or English) structure, automatic `derives_from` edges |
| **Handbook** | Employee handbooks, manuals | Section-heading-organized rules from normative paragraphs |
| **Minutes** | Meeting minutes | Decisions and action items only (discussion text ignored) |
| **Tabular** | Excel/CSV tables | One rule per row (e.g., expense limit tables, approval matrices) |
| **Email Archive** | `.eml` file directories | De-facto communication patterns (disclaimers, signatures, conventions) |

The extraction pipeline runs in stages: structural parsing (PDF/markdown/text) -> normative detection -> coreference resolution -> domain-specific metadata inference via domain pack prompts -> relationship suggestion -> human review. All extractors produce `CandidateRule` objects that go through human review before becoming active rules.

```bash
# Extract rules from a regulation PDF
rulerepo ingest --source regulation_doc --file ./policies/employee_handbook.pdf --scope hr/attendance

# Extract from an expense limits spreadsheet
rulerepo ingest --source spreadsheet --file ./policies/expense_limits.xlsx
```

---

## Rule Templates

33 ready-to-use templates covering 300+ rules across 9 domains:

| Domain | Templates | Example topics |
|---|---|---|
| Engineering | 5 | Python/FastAPI, TypeScript/React, API design, testing, documentation |
| Legal / Contract | 7 | NDA review, contract clauses, contracts (JP), IP protection, regulatory compliance |
| HR | 5 | Attendance (JP labor law), leave management, evaluation fairness, harassment prevention, overtime |
| Finance | 6 | Expense policy (JP), expense policy (standard), journal entries, invoice compliance, purchase orders, revenue recognition |
| Sales | 1 | Pricing policy (discount caps, approval authority, resale price maintenance) |
| Compliance | 2 | Anti-corruption (FCPA, UK Bribery Act), data privacy (JP APPI) |
| IT Security | 3 | Access control, IaC/Terraform, OWASP |
| Communication | 1 | Internal communication standards |
| Cross-domain | 3 | Procurement rules, advertising (JP pharma), meta-rules (rules about rules) |

Many templates include `kind` annotations: computational rules for numeric thresholds (overtime caps, expense limits), procedural rules for approval workflows, and definitional rules for term definitions.

Load templates with `make seed` or through the onboarding wizard at `/onboarding`.

Japanese-language rules are included for labor law (Labor Standards Act), privacy (APPI), civil code, childcare/family care leave, and tax regulations.

> **Note:** Business-domain templates are reference implementations. Review them with qualified domain counsel before use in production compliance workflows.

---

## Compliance and Privacy

- **Department RBAC**: 10 department types (Legal, HR, Finance, Sales, Marketing, IT, Operations, R&D, Executive, Custom) with 4 capacity levels (Owner, Reviewer, Auditor, Subscriber). Every endpoint enforces department visibility -- this is non-bypassable.
- **Data classification**: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED. RESTRICTED rules are routed to self-hosted LLMs; CONFIDENTIAL evaluation logs are masked on the frontend.
- **PII scrubbing**: Each surface declares its PII-sensitive fields. The `PIIScrubMiddleware` and the evaluation pipeline redact them before they reach the LLM.
- **Surface-aware retention**: Audit records are retained per surface (e.g., shorter for code evaluations, longer for contract evaluations).
- **Prompt injection defense**: All LLM-bound user content is wrapped in stable delimiters and screened against known injection patterns. A dedicated safety test suite validates this.
- **Audit trail**: Append-only, hash-chained audit log in Postgres. Each entry links to the previous via SHA-256, verified by `scripts/verify_audit_chain.py`.
- **Multi-tenant isolation**: Every entity carries `tenant_id`. Postgres Row-Level Security enforces isolation at the data layer.
- **Compliance cockpit**: Department violation trends, per-policy fire/deny rates, regulatory propagation view, and an action queue for compliance officers.
- **GDPR erasure**: Right-to-be-forgotten data deletion support.
- **Regional data routing**: Data residency enforcement for JP, US, and EU regions.
- **Customer-managed encryption keys** (CMEK) support.
- **Approval workflows**: Configurable approval chains for rule changes and exception requests.

---

## Eval Harness

The eval harness validates LLM-driven features against curated golden datasets:

```bash
make eval                     # run all domains
make eval.domain DOMAIN=legal # run one domain
make eval.json                # output JSON report
```

Golden test cases across 8 domains (engineering, legal, HR, finance, IT security, sales, communications, governance) in JSONL format. A CI workflow runs the harness on PRs that touch prompts or evaluators and fails if precision drops more than 5%. The harness also supports A/B testing via a splitter module and drift detection for monitoring evaluation consistency over time.

---

## Development

### Commands

```bash
make help                     # list all 66 make targets
make up                       # start full stack (Tier 3, 11 services)
make up.tier1                 # start with Postgres only (3 services)
make up.tier2                 # start with Postgres + Elasticsearch + Redis (7 services)
make seed                     # load sample rules + templates
make check                    # format + lint + test (run before committing)
make eval                     # run eval harness
make dev.server               # FastAPI with hot-reload on :8000
make dev.frontend             # Next.js with hot-reload on :3000
make test                     # all tests
make test.unit                # unit tests only
make test.cov                 # with coverage report
make test.e2e                 # end-to-end tests
make crossorg.acceptance      # cross-organizational acceptance tests
make db.migrate               # run Alembic migrations
make reconcile                # rebuild Neo4j graph from Postgres
make mcp.stdio                # run MCP server in stdio mode
make mcp.http                 # run MCP server in HTTP mode
```

### Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Frontend | TypeScript, React 19, Next.js 15, Tailwind CSS, next-intl |
| LLM | Gemini via `google-genai` (pluggable: Anthropic, OpenAI, self-hosted) |
| Data | PostgreSQL 17 (RLS), Elasticsearch 8, Neo4j 5, Redis 7 (arq) |
| MCP | FastMCP (mcp >= 1.9) |
| Quality | ruff + mypy, ESLint + Prettier, eval harness (8 golden datasets) |
| Packages | uv (Python), pnpm (frontend) |

### Repository layout

```
rule-repository/
├── apps/
│   ├── server/                        # FastAPI backend
│   │   ├── src/rulerepo_server/
│   │   │   ├── api/v1/                # 40 REST API routers
│   │   │   ├── core/                  # Config, auth, PII, feature flags, LLM safety
│   │   │   ├── domain/               # 27 pure domain models (Rule, Verdict, Scope, ...)
│   │   │   ├── services/             # 33 service modules
│   │   │   │   ├── evaluation/        # Surface-agnostic evaluation engine
│   │   │   │   │   ├── surfaces/      # 7 surface adapters
│   │   │   │   │   ├── deterministic/ # Numeric, schema, state-machine, lookup evaluators
│   │   │   │   │   └── subjects/      # 6 subject context assemblers
│   │   │   │   ├── extraction/        # 6 extractors + structural parsers + contract pipeline
│   │   │   │   ├── intelligence/      # Health scoring, drift detection, analytics (14 modules)
│   │   │   │   ├── norm_lineage/      # Upstream/downstream lineage walker
│   │   │   │   ├── assistant/         # Conversational rule assistant
│   │   │   │   ├── compliance/        # Cockpit, erasure, CMEK, regional routing
│   │   │   │   ├── departments/       # Department RBAC + authorization
│   │   │   │   ├── events/            # Business event ingestion + scope resolution
│   │   │   │   ├── feedback/          # Correction capture, auto-drafting, analysis
│   │   │   │   ├── polyglot/          # Multilingual rule verification
│   │   │   │   └── ...               # federation, playground, proposals, governance, ...
│   │   │   ├── domain_packs/          # 9 built-in packs
│   │   │   ├── adapters/              # Postgres, ES, Neo4j, LLM router, Gemini, file storage
│   │   │   ├── mcp/                   # MCP server (24 tools)
│   │   │   └── workers/               # 9 cron jobs + on-demand tasks
│   │   ├── eval_harness/              # Golden datasets (8 domains) + metrics + regression gates
│   │   └── tests/                     # 105 test files (unit, integration, e2e, acceptance, safety)
│   └── frontend/                      # Next.js 15 (57 pages, 9 route groups)
│       ├── app/
│       │   ├── (dashboard)/           # Main dashboard (25 pages)
│       │   ├── (legal)/               # Legal console (5 pages)
│       │   ├── (hr)/                  # HR console (7 pages)
│       │   ├── (finance)/             # Finance console (5 pages)
│       │   ├── (compliance)/          # Compliance console (5 pages)
│       │   ├── (marketing)/           # Marketing console (4 pages)
│       │   ├── (admin)/               # Admin console (3 pages)
│       │   ├── (security)/            # Security console (1 page)
│       │   └── (sales)/               # Sales console (1 page)
│       ├── components/                # 12 shared components
│       └── messages/                  # en.json, ja.json (i18n)
├── packages/
│   ├── rule-client/                   # Python SDK (rulerepo)
│   ├── agentic-client/                # Agentic Python SDK (rulerepo-agentic)
│   ├── cli/                           # CLI tools (8 entry points)
│   └── domain-packs/                  # External domain pack prompts + templates
│       ├── _core/                     # Shared manifest + registry
│       ├── engineering/               # Evaluation prompts
│       ├── legal/                     # Prompts + contract templates (EN/JP)
│       ├── hr/                        # Prompts + attendance/conduct templates
│       ├── finance/                   # Prompts + expense/procurement templates
│       ├── sales/                     # Prompts + pricing template
│       └── communication/             # Prompts + marketing template
├── sample_rules/                      # 33 templates (300+ rules) + domain rule sets
├── infra/                             # Docker, Postgres init + RLS, ES templates, Neo4j constraints
├── scripts/                           # 6 scripts: seed, reconcile, reindex, audit verify, spec audit
├── PROJECT.md                         # Vision, domain model, roadmap
├── CLAUDE.md                          # Operational guide for contributors
└── docker-compose.yml                 # Full stack (Tier 3)
```

### Python SDKs

```python
from rulerepo import RuleClient

async with RuleClient("http://localhost:8000") as client:
    results = await client.search.hybrid("overtime limit", scope="hr/attendance")
```

| Package | Path | Purpose |
|---|---|---|
| `rulerepo` | `packages/rule-client/` | Python SDK for rule CRUD and search |
| `rulerepo-agentic` | `packages/agentic-client/` | Python SDK wrapping evaluation for AI agents |
| `rulerepo-cli` | `packages/cli/` | CLI tools (check, hook, ingest, export, context, review-contract, check-action, init, doctor, audit) |

### Background jobs

9 scheduled cron jobs keep the system healthy:

| Job | Schedule | Purpose |
|---|---|---|
| Health scoring | Daily 2:00 AM | Recompute health scores, alert on unhealthy/dormant rules |
| Recommendations | Daily 3:00 AM | Generate improvement recommendations, detect high deny rates |
| Translation drift | Daily 3:30 AM | Check bilingual rules for semantic drift |
| Auto-promote rules | Daily 4:00 AM | Promote/demote rules by false-positive rate (experimental -> stable -> proven) |
| Verdict drift | Daily 4:30 AM | Monitor verdict distributions, alert on DENY rate changes > 20pp |
| Cluster corrections | Daily 5:00 AM | Cluster recent corrections and auto-draft rule proposals |
| Correction stats | Hourly | Aggregate correction statistics by type and status |
| Translation equivalence | Daily 5:30 AM | Verify translation pair equivalence scores |
| Weekly digest | Monday 9:00 AM | Generate governance digest |

Plus an on-demand `propagate_norm_amendment` task that flags downstream rules when a law or regulation is amended.

---

## Contributing

1. Read [CLAUDE.md](CLAUDE.md) -- it is the operational contract for this project
2. Run `make precommit.install` to set up pre-commit hooks
3. Branch from `main`, use Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`)
4. Run `make check` before pushing
5. Mock the LLM in unit tests -- never call real providers
6. If your change touches prompts or evaluators, include `make eval` output in the PR
7. New surfaces go in `services/evaluation/surfaces/<name>/`. New domain packs go in `domain_packs/<name>/`. Neither requires changes to the evaluation core.

---

## License

Apache License 2.0. See [LICENSE](./LICENSE).
