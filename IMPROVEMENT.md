# IMPROVEMENT.md

> A detailed analysis of issues in the current `rule-repository` codebase and a concrete, phased proposal for fixing them — so that the project becomes what it claims to be: an **organization-wide normative management platform**, not an AI-coding-agent rule manager.

This document is meant to be read alongside `PROJECT.md`, `README.md`, and `CLAUDE.md`. It does **not** replace them. It identifies where the current implementation diverges from the stated vision and proposes specific, actionable fixes.

---

## 1. Executive Summary

The repository's stated mission is **cross-organizational normative management**: laws, contracts, HR regulations, financial procedures, sales policies, communication standards, documentation conventions, and engineering rules — for every team in the organization (legal, HR, finance, sales, IT, executive, engineering, and beyond).

The implementation, however, has drifted. The evaluation core, the discovery pipeline, the MCP tools, the sample data, the templates, the integrations, and the dashboard are all built around **AI-assisted software development** as the primary use case. Non-code surfaces (contracts, HR events, transactions, communications) are treated as second-class paths or are absent entirely.

The drift is **not cosmetic**. It is encoded in the architecture. Renaming files or adding sample data will not fix it. The root cause is a single design decision in `services/evaluation/`: **the evaluation engine takes "code change" as its first-class input type**. Every downstream concept — discovery analyzers, MCP tools, the dashboard's compliance metric, the integration surface, the sample templates — inherits from that decision.

This document proposes a phased refactor that:

1. Introduces a `Subject` / `Surface` abstraction so that **code is one surface among many**, not the center.
2. Introduces a **Domain Pack** mechanism that ships rules, adapters, prompts, and UI together for a business domain (Contract, HR, Finance, etc.), with Code becoming one pack among many.
3. Promotes **Norm Lineage** (Law → Regulation → Internal Policy → Department Rule) to a first-class model alongside the existing organizational Federation.
4. Adds **persona-specific dashboards** for Legal, HR, Finance, Compliance, and Admin — so the operator console stops being an Engineering-only console.
5. Generalizes the **MCP tools** so contract-review agents, expense-review agents, and HR-question agents can be built on the same MCP server.
6. Repositions the README and the GitHub About so the cross-organizational mission is the first impression.

The plan retains roughly 80% of the current implementation. The Code path remains the most mature; it is moved, not destroyed.

---

## 2. Diagnosis: Root Cause of the Drift

The drift is structural. Five concrete pieces of evidence anchor that diagnosis.

### 2.1 The Evaluation Engine is Defined as Code-Centric

`PROJECT.md` §6.4 opens with:

> The evaluation engine is the core differentiator. It accepts code changes as first-class input, maps them to relevant rules, and returns verdicts with code-specific remediation.

Two problems compound here:

- **"Core differentiator" is mis-attributed.** The genuine differentiator is *natural-language rule application via LLM-as-Judge*, not code processing. Code processing is one application of that capability.
- **"First-class input" is too narrow.** Legal compliance, HR violations, financial misposting, ad copy review, and incident response do not arrive as unified diffs. The first-class input should be a *Subject* — an abstract envelope around whatever is being evaluated.

### 2.2 The Evaluation Service Mixes Code Concerns with Universal Concerns

Inside `services/evaluation/`:

- `diff_parser.py` — code-specific
- `context_assembler.py` — accepts diff/file_paths/facts, with diff treated as the primary path
- `evaluation_core.py` — uses `evaluate_code_change.txt` as the primary prompt; `evaluate_facts.txt` exists but is the second-class path
- `batch_evaluator.py` — has separate `evaluate_batch.txt` (code) and `evaluate_batch_facts.txt` (facts)

This is a **layering violation**. A universal concept (rule evaluation) has a domain-specific concept (code change) baked into its core. Adding a new domain (e.g., contract clauses) requires invasive changes to the core, which is precisely the friction that perpetuates the drift.

### 2.3 The MCP Tools Assume Coding Agents

Tools exposed by the MCP server:

- `get_rules_for_context(files=...)` — input is file paths. A legal reviewer asking "does this clause violate our procurement policy?" cannot use this.
- `evaluate_compliance(diff=...)` — diff-typed.
- `discover_rules(repo_path)` — repository-typed.

There are no MCP tools whose signatures fit non-code workflows: clause-vs-policy comparison, expense-vs-regulation check, attendance-event compliance check, or communication review.

### 2.4 Sample Data and Templates are 100% Code

The five YAML rule templates that ship with the repository:

| Template | Rules | Domain |
|---|---|---|
| `python-fastapi` | 15 | Code |
| `typescript-react` | 12 | Code |
| `security-owasp` | 10 | Code |
| `api-design` | 10 | Code |
| `testing-standards` | 10 | Code |

The `sample_rules/` distribution: 11 coding-rule documents, 7 corporate-policy documents, 5 sales-team documents. The defaults are code-heavy and a new user running `make seed` immediately sees a coding-rules tool.

### 2.5 Integrations are GitHub-Centric

The single fully-implemented external integration is the GitHub App / webhook. There is no Slack message integration, no email scanner, no HRIS connector, no ERP connector, no DocuSign or contract-management connector, and no generic business-system connector pattern beyond a webhook gateway. The repository's "enforcement everywhere" reduces to "enforcement in GitHub".

### 2.6 Dashboard Mental Model Assumes Daily PR Volume

The home dashboard's hero metric is *compliance rate* with a 7-day trend. This is a coherent metric **if** the system processes dozens or hundreds of evaluations per day — the volume profile of a software team's PRs. But:

- Legal reviews fire a few times per week, not per day.
- HR violations are monthly cadence.
- Contract renegotiations are quarterly.
- Regulatory changes are annual or rarer.

A single hero metric at this granularity is wrong for any non-development persona. It is a UI manifestation of the same code-centric assumption.

### 2.7 Conclusion

The drift originates from one design decision (Evaluation Core = Code-Aware) and propagates outward through every surface of the system. Surface-level fixes (more sample data, renaming) will not undo it. The fix has to be at the abstraction boundary.

---

## 3. Detailed Issues

### 3.1 Architectural Issues

| ID | Issue | Impact |
|---|---|---|
| A1 | `services/evaluation/` mixes code-specific concerns (diff parsing, file-path context) with universal evaluation logic | Adding a new domain (contract, HR, transaction) requires invasive core changes |
| A2 | The primary evaluation prompt is `evaluate_code_change.txt`; `evaluate_facts.txt` is structurally secondary | Quality and tooling investment skews toward code; non-code prompts under-tested |
| A3 | `scope` namespaces are dominated by `engineering/python`, `engineering/api`, `engineering/testing` | Hard to grow into `legal/contract/nda` or `hr/attendance/overtime` without overlap or rewrites |
| A4 | Discovery analyzers are `claude_md.py`, `linter_config.py`, `code_patterns.py` only | Cannot bootstrap rules from policy PDFs, employee handbooks, contract templates, regulatory XML |
| A5 | The Gateway integration story is GitHub-only | No path for Slack, email, HRIS, ERP, contract systems, e-signature, or workflow tools |
| A6 | MCP tool signatures are coupled to code (file paths, diffs, repos) | Cannot serve legal-review, expense-review, HR-policy, or compliance-Q&A agents through the same MCP server |
| A7 | No `Surface` or `Subject` abstraction in the domain | Every new domain becomes a special case rather than an instance of a general type |

### 3.2 Domain Model Gaps

| ID | Issue | Impact |
|---|---|---|
| D1 | No abstraction for "the thing being evaluated" (code diff, contract clause, attendance event, transaction, message) | `EvaluationContext` is effectively a `diff or facts` union, which leaks into every caller |
| D2 | Norm hierarchy (Law → Regulation → Guideline → Internal Policy → Department Rule → Operational Rule) is not a first-class model | Cannot answer "which internal rules derive from this law that just changed?" without ad-hoc graph queries |
| D3 | Federation conflates organizational hierarchy with norm hierarchy | The two axes are orthogonal: a rule can simultaneously belong to the HR department (org axis) AND derive from the Labor Standards Act (norm axis). The current model collapses them |
| D4 | `scope` is a single namespace doing double duty as technical scope (`engineering/python`) and organizational scope (`hr/department/sales`) | Evaluation logic, RBAC, and federation cannot tell them apart |
| D5 | No multi-language support for rules | Bilingual contracts (EN/JA) cannot be modeled as semantic twins |
| D6 | No `Actor` model that distinguishes humans, business systems, and AI agents as the entity whose action is being evaluated | The `agent_id` field added in Phase 5i is a partial solution that bakes in "agent = AI" |
| D7 | No `effective_period` semantics for *upstream norm changes* — a regulation's amendment date is not propagated automatically to derivative internal rules | Regulatory-change response cannot be measured or automated |

### 3.3 Persona and UI Bias

| ID | Issue | Impact |
|---|---|---|
| P1 | All 23 frontend pages are designed for an Engineering Operations persona | Legal, HR, Finance, and Compliance users have no UI suited to their workflow |
| P2 | The home dashboard's hero metric (compliance rate + 7-day trend) assumes daily evaluation volume | Meaningless or misleading for personas with weekly, monthly, or quarterly cadence |
| P3 | "Top violated rules" presentation lists rule IDs and deny counts | Useful for a developer scanning PR violations; useless for a compliance officer needing audit-trail context |
| P4 | No clause-level redline UI for legal review | Contract review, the highest-value cross-org use case, has no native UI |
| P5 | No employee-event timeline for HR review | Cannot inspect a single employee's compliance history across rules |
| P6 | No transaction-audit UI for finance review | Expense-vs-regulation checks have no consolidated view |
| P7 | ~~"Marketplace" and "Agents" sit prominently in the sidebar~~ | **Resolved.** Marketplace removed. Sidebar now shows persona-specific navigation. |

### 3.4 Ingestion Pipeline Bias

| ID | Issue | Impact |
|---|---|---|
| I1 | No structural parser for legal/regulatory documents (chapter / article / paragraph / item / appendix) | Japanese laws and most internal regulations cannot be ingested at proper granularity |
| I2 | No bilingual pairing: EN/JA contract clauses cannot be linked as semantic twins | Global contract management cannot rely on the system |
| I3 | No regulatory metadata enrichment (effective date, amendment history from official gazettes) | Regulatory-change tracking is manual |
| I4 | No redline differ for document revisions | Cannot extract "what changed in this contract revision?" automatically |
| I5 | No coreference resolver for legal cross-references ("the preceding article", "Article 5, paragraph 2") | Imported rules retain unresolved references that LLM evaluation must guess at |
| I6 | Discovery analyzers only target code-adjacent artifacts (CLAUDE.md, linter configs, code patterns) | Cannot mine rules from corporate policy documents, employee handbooks, training material, or sales playbooks |

### 3.5 Sample Data and Positioning Bias

| ID | Issue | Impact |
|---|---|---|
| S1 | All 5 rule templates are code-domain (Python, TypeScript, OWASP, API design, testing) | First impression after `make seed` is "coding-rules tool" |
| S2 | `sample_rules/` ratio: 11 coding-rule docs, 7 corporate-policy docs, 5 sales docs — code is plurality and listed first in the README | Reinforces the misimpression even before code is examined |
| S3 | README §"What You Can Do" leads with "Evaluate code changes — in batches" and "Get rules delivered to agents automatically" | The cross-org mission is buried |
| S4 | GitHub repository About field is empty; no topics positioning the project as governance / compliance / regtech / legal-tech | The first impression on GitHub is undefined and falls back to README's code-leaning content |
| S5 | No localized sample rules (e.g., Japanese rules sourced from 労働基準法, 個人情報保護法) | Reduces immediate value for Japanese organizations, the natural early-adopter audience |

### 3.6 Feature Complexity Overshoot

The repository implements Autonomous Agent Governance, Federation, Snapshots, Proposals, and Effectiveness Visibility — a remarkable breadth. (Marketplace has been removed as over-engineering.) But:

| ID | Issue | Impact |
|---|---|---|
| F1 | ~~Marketplace is a horizontal mechanism for sharing rule packages~~ | **Resolved.** Marketplace removed; rules now ship as Domain Packs. |
| F2 | Agent Governance trust levels and personalized rules are advanced AI-agent features | The non-AI evaluation path (human reviewer, business system) does not benefit, and these features lock the project further into the AI-agent persona |
| F3 | Phase 5 has 10 sub-phases (5a–5j) refining the existing code path | Sequencing has prioritized depth in code over breadth across domains |
| F4 | 23 frontend pages, 18 API routers, 35 ORM models, 22 migrations, 13 service areas | High change cost; refactor must be surgical, not a rewrite |

### 3.7 Operational Issues

| ID | Issue | Impact |
|---|---|---|
| O1 | `agent_id` is a single string field rather than an `Actor` reference | Cannot model the same rule violation across humans and machines coherently |
| O2 | Audit log retention is uniform across surfaces | Legal evaluations need 7+ year retention; code evaluations are ephemeral. One-size-fits-all retention either over-stores or under-stores depending on the surface |
| O3 | No PII classification on Subject payloads | HR and legal data require sanitization that code diffs do not. The current `core/PII` module is a single uniform layer |
| O4 | No locale on `Rule` or evaluation prompts | Bilingual operations and Japanese-first evaluation cannot be cleanly tested |

---

## 4. Three Guiding Principles for the Fix

These principles drive every concrete proposal in §5.

### Principle 1: Code is One Surface Among Many

Introduce a `Surface` enum and a `Subject` abstraction. The evaluation engine accepts a `Subject` and a set of `Rule` instances; it does not know whether the subject is a code diff, a contract clause, an attendance event, or a transaction. Surface-specific behavior (parsing diffs, splitting contracts into clauses, normalizing transactions) lives in pluggable adapters.

### Principle 2: Norm Hierarchy ⊥ Organizational Federation

These are two distinct axes:

- **Norm Lineage**: Law → Regulation → Guideline → Internal Policy → Department Rule → Operational Rule.
- **Org Federation**: Organization → Team → Project (the existing Federation model).

A given rule is positioned on **both** axes. Conflating them, as the current model implicitly does, makes regulatory-change tracking and organizational-policy-rollout tracking interfere with each other.

### Principle 3: Vertical Delivery via Domain Packs

Ship by domain, not by feature. A *Domain Pack* is a unit that bundles:

- Curated rule templates for that domain
- Ingestion adapters specific to that domain's source documents
- Surface-specific evaluation prompts
- Persona-specific UI components
- Sample / seed data
- Connector hooks to relevant business systems

The first non-code Domain Pack (Contract or HR) is the primary public proof that the project is cross-organizational. Code becomes one pack among many.

---

## 5. Concrete Refactoring Proposals

### 5.1 De-couple the Evaluation Core from Code (highest priority)

**Current layout:**

```
services/evaluation/
├── service.py
├── batch_evaluator.py
├── evaluation_core.py
├── diff_parser.py             # code-specific
├── context_assembler.py       # diff-primary
├── rule_selector.py
├── graph_resolver.py
├── conflict_aggregator.py
├── verdict_aggregator.py
├── impact_preview.py
└── prompts/
    ├── evaluate_code_change.txt    # primary
    ├── evaluate_facts.txt          # secondary
    ├── evaluate_batch.txt          # code
    └── evaluate_batch_facts.txt    # facts
```

**Proposed layout:**

```
services/evaluation/
├── service.py                  # surface-agnostic orchestrator
├── core/
│   ├── evaluator.py            # Rule × Subject → Verdict (universal)
│   ├── batch_evaluator.py
│   ├── rule_selector.py
│   ├── graph_resolver.py
│   ├── conflict_aggregator.py
│   ├── verdict_aggregator.py
│   ├── impact_preview.py
│   └── prompts/
│       ├── evaluate_subject.txt           # one universal prompt
│       └── evaluate_subject_batch.txt
└── surfaces/
    ├── base.py                 # Surface ABC, SurfaceAdapter ABC
    ├── code/
    │   ├── adapter.py          # absorbs diff_parser + context_assembler
    │   ├── subject.py          # CodeChange dataclass
    │   └── prompts/code_hints.txt
    ├── contract/
    │   ├── adapter.py          # splits contracts into ContractClause
    │   ├── subject.py          # ContractClause
    │   └── prompts/contract_hints.txt
    ├── human_action/
    │   ├── adapter.py          # normalizes business-system events
    │   ├── subject.py          # HumanAction(who, what, when, system)
    │   └── prompts/action_hints.txt
    ├── transaction/
    │   ├── adapter.py          # journal entries, expense claims, invoices
    │   └── subject.py          # BusinessTransaction
    ├── document/
    │   ├── adapter.py          # whole documents or sections
    │   └── subject.py          # DocumentRegion
    └── message/
        ├── adapter.py          # email, Slack, transcripts
        └── subject.py          # Message
```

**Key design points:**

- `evaluate_subject.txt` is a universal prompt that takes a `statement`, the `Subject`'s natural-language description, and the `Subject`'s structured payload. Surface-specific hints are injected as auxiliary context, not as a separate prompt.
- `Subject` becomes the input type to the core evaluator; existing `EvaluationContext` is kept as a backwards-compatible shim that constructs a Code Surface `Subject`.
- Existing `diff_parser.py` and `context_assembler.py` are *moved*, not deleted, into `surfaces/code/adapter.py`. Tests pass with no rewrites.

**Public API changes:**

- Existing `POST /api/v1/evaluate` retains its current contract (defaults to Code Surface).
- New `POST /api/v1/evaluate/{surface}` endpoint added: `{surface}` ∈ `code | contract | human_action | transaction | document | message | generic`.
- Existing CLI `rulerepo-check` continues to work unchanged; new CLI verbs `rulerepo-review-contract`, `rulerepo-check-action` etc. layer on top of the new endpoint.

### 5.2 Introduce the `Subject` Abstraction in the Domain Model

Add to `domain/evaluation.py`:

```python
class Surface(StrEnum):
    CODE = "code"
    CONTRACT = "contract"
    HUMAN_ACTION = "human_action"
    TRANSACTION = "transaction"
    DOCUMENT = "document"
    MESSAGE = "message"
    GENERIC = "generic"

@dataclass(frozen=True)
class Actor:
    kind: Literal["human", "system", "agent"]
    identifier: str
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Subject:
    surface: Surface
    identifier: str             # e.g. "pr#42", "contract:ACME-2025-Q1", "attendance:E001/2025-04"
    payload: dict[str, Any]     # surface-specific (diff text, clause text, event fields, ...)
    facts: dict[str, Any]       # normalized facts that any rule may consult
    actor: Actor | None         # who is acting / being evaluated
    timestamp: datetime
    locale: str = "en"
```

Add to `Rule`:

```python
applies_to_surfaces: list[Surface] = [Surface.GENERIC]  # which surfaces this rule can be evaluated against
```

The rule selector consults `applies_to_surfaces` during candidate selection. A "no overtime above 45 hours" rule has `[Surface.HUMAN_ACTION, Surface.TRANSACTION]`. A "no `eval()` in production code" rule has `[Surface.CODE]`. A contract clause rule has `[Surface.CONTRACT, Surface.DOCUMENT]`.

### 5.3 Promote Norm Lineage to a First-Class Model

Add to `Rule`:

```python
norm_tier: NormTier   # LAW | REGULATION | GUIDELINE | CORPORATE_POLICY | DEPARTMENT_RULE | OPERATIONAL_RULE
norm_authority: str | None   # e.g. "Labor Standards Act, Article 36" or "ACME Corp Procurement Policy v3.2"
```

`derives_from` (already in the relationship graph) gains semantic teeth: when a rule with `norm_tier = LAW` is amended, all rules transitively reachable via `derives_from` are flagged for review and assigned a `pending_norm_change_review` status.

Frontend addition: a **Norm Lineage Viewer** that renders the chain *Law → Regulation → Internal Policy → Department Rule → Contract Clause* for any rule, with effective dates and amendment history. This is a high-value differentiator for legal and compliance teams.

The existing `Federation` model is retained unchanged; it represents the *organizational* axis. The two axes are explicitly orthogonal in documentation, in the data model, and in the UI.

### 5.4 Domain Pack Architecture

New directory `domain_packs/`:

```
domain_packs/
├── code/                       # existing functionality, repackaged
│   ├── pack.yaml
│   ├── rules/                  # python-fastapi.yaml, typescript-react.yaml, etc.
│   ├── adapters/               # symlink to surfaces/code/adapter.py
│   ├── ui/                     # existing engineering-facing pages
│   ├── prompts/
│   └── samples/
├── contract/                   # NEW — first non-code pack, highest priority
│   ├── pack.yaml
│   ├── rules/                  # NDA, MSA, SOW, procurement standard clauses
│   ├── adapters/
│   │   ├── docx_clause_extractor.py
│   │   └── redline_differ.py
│   ├── ui/                     # /domain/contract: review, redline, conflict detection
│   ├── prompts/
│   │   └── clause_compliance.txt
│   └── samples/                # anonymized NDA/MSA/SOW
├── hr_attendance/              # NEW — second pack
│   ├── pack.yaml
│   ├── rules/                  # 労基法-derived rules, 36協定, 育児介護休業法
│   ├── adapters/
│   │   ├── attendance_event_adapter.py
│   │   └── hris_pull.py
│   ├── ui/                     # /domain/hr: violations, 36-agreement status, overtime trend
│   ├── prompts/
│   └── samples/
├── expense/                    # NEW — third pack
├── procurement/                # NEW
├── communication/              # NEW — email/Slack/customer-call rule checks
├── compliance/                 # NEW — bribery/anti-social/FCPA/AML
└── governance/                 # NEW — board-of-directors / disclosure / insider-trading
```

Each pack carries a `pack.yaml`:

```yaml
name: contract
version: 0.1.0
display_name: Contract Pack
description: Contract review, clause-vs-policy compliance, and redline tracking
surfaces: [contract, document]
required_adapters: [docx_clause_extractor]
default_scopes: [legal/contract/nda, legal/contract/msa, legal/contract/sow]
ui_routes: [/domain/contract]
seed_rules_path: rules/
required_connectors: []   # optional integrations: docusign, salesforce-cpq, etc.
persona: legal
```

**Effects:**

- Code Pack becomes "one of many", correcting the structural drift.
- New domains are added by adding a pack, not by modifying the core.
- Marketing gains shippable units: "Contract Pack 1.0 is now available."
- Domain Packs are the distribution unit, replacing the former Marketplace approach.

### 5.5 Expand the Ingestion Pipeline

Add to `services/extraction/`:

| New component | Responsibility |
|---|---|
| `structural_parser.py` | Parse hierarchical legal/regulatory structure (chapter, article, paragraph, item, appendix). Strong support for Japanese law and corporate regulations. |
| `bilingual_pairer.py` | Pair EN/JA contract clauses as semantic twins; verify equivalence continuously. |
| `regulatory_metadata_enricher.py` | Optional auto-fetch of effective dates and amendment history from official gazettes (e-Gov for Japan, similar sources elsewhere). |
| `redline_differ.py` | Extract revised rules from old-version vs new-version document diffs. |
| `clause_normalizer.py` | Resolve "the preceding article", "Article 5, paragraph 2", "the foregoing" cross-references. |

Add discovery analyzers in `services/discovery/analyzers/`:

| Analyzer | Source |
|---|---|
| `policy_pdf.py` | Internal regulation PDFs |
| `handbook_md.py` | Employee handbooks |
| `contract_template.py` | Template contracts |
| `regulation_xml.py` | Regulation files in standard XML formats (e.g., 法令標準データ形式) |
| `sales_playbook.py` | Sales playbooks and pitch documents |
| `ad_compliance_doc.py` | Marketing legal-review checklists |

### 5.6 Persona-Specific Dashboards

Restructure `apps/frontend/app/`:

```
app/
├── (admin)/                    # rule administrators (existing intelligence pages, lightly relabeled)
├── (engineering)/              # was (dashboard) — engineering operations
│   ├── page.tsx                # compliance rate, top violated rules, recent corrections
│   └── ...                     # most existing pages live here
├── (legal)/                    # NEW
│   ├── contracts/              # contracts in review
│   ├── clauses/                # clause search and conflict detection
│   ├── lineage/                # norm-lineage viewer
│   └── redlines/               # revision diffs
├── (hr)/                       # NEW
│   ├── violations/             # employee/event-level violation log
│   ├── attendance/             # 36-agreement and overtime tracking
│   ├── lifecycle/              # onboarding/offboarding/transfer compliance
│   └── policies/               # which policies cover which roles
├── (finance)/                  # NEW
│   ├── transactions/           # transaction-vs-rule audit
│   ├── expenses/               # expense report compliance
│   └── tax/                    # tax-related rules and recent applicability
└── (compliance)/               # NEW
    ├── overview/               # cross-organization compliance state
    ├── audits/                 # audit trail browser
    ├── regulatory/             # regulatory change response status
    └── incidents/              # cross-domain incident view
```

**Hero metric per persona:**

- Engineering: compliance rate + 7-day trend (current behavior)
- Legal: open contract reviews, unresolved conflicts, recent upstream-law amendments
- HR: this month's violations, 36-agreement headroom, employees affected by recent regulation revisions
- Finance: this month's transaction violations, expense-claim rejection rate, tax-rule-change impact
- Compliance: median time from regulatory amendment to internal-rule revision, percentage of regulations with active internal mappings, open critical alerts

The home page picks the dashboard based on the user's role; admins can switch between personas.

### 5.7 Generalize the MCP Tools

Replace or supplement code-typed MCP tools with subject-typed tools.

| Replace | With |
|---|---|
| `get_rules_for_context(files=...)` | `get_applicable_rules(subject_ref=..., surface=...)` |
| `evaluate_compliance(diff=...)` | `evaluate_subject(subject_payload=..., surface=...)` |
| `discover_rules(repo_path=...)` | `discover_rules(source_uri=..., source_type=...)` |

Add new tools that fit non-code workflows:

| New tool | Purpose |
|---|---|
| `lookup_norm_lineage(rule_id)` | Returns the upstream chain (Law → Internal Policy → ...) and any pending upstream changes |
| `find_clause_conflicts(contract_text)` | Compares draft contract clauses against the active policy corpus and prior contracts |
| `explain_regulation_impact(law_id, change_summary)` | Replays historical evaluations against a hypothetical regulation amendment |
| `check_action(actor, action, payload)` | Generic human-action compliance check for HR, finance, procurement |
| `review_communication(channel, content)` | Communication compliance for email, Slack, or customer interactions |

The existing code tools remain available; they become surface-specialized variants of `evaluate_subject` and `get_applicable_rules`.

### 5.8 Connector Layer for Business Systems

New `adapters/connectors/`:

```
adapters/connectors/
├── base.py                     # SubjectConnector ABC
├── github/                     # existing
├── slack/                      # NEW
├── email/                      # NEW (IMAP / Microsoft Graph)
├── salesforce/                 # NEW
├── workday/                    # NEW
├── sap/                        # NEW
├── docusign/                   # NEW
├── kintone/                    # NEW (Japanese workflow systems)
├── teams/                      # NEW (Microsoft Teams)
└── webhook_generic/            # existing gateway path, repositioned as "lowest common denominator"
```

Each connector normalizes its source's events into `Subject` instances and pushes them to the evaluation pipeline (in `preflight`, `posthoc`, or `sidecar` mode, per `PROJECT.md`).

### 5.9 Multi-Language Support

- Add `locale` to `Rule` (default `en`).
- Add `statement_translations: dict[str, str]` (locale → translated statement) for rules that have authoritative parallel-language versions (typically contracts).
- Evaluation prompts pick the rule statement matching the subject's locale; if no translation exists, fall back to the canonical statement and flag a `cross_locale_evaluation` warning in the audit log.
- A periodic worker re-checks parallel-language rules for semantic drift using the LLM as a comparison judge.

### 5.10 Decouple Scope into Two Axes

`scope` is overloaded today. Split it:

```python
class Rule:
    tech_scope: list[str]    # e.g. engineering/python, engineering/api — files, languages, services
    org_scope: list[str]     # e.g. hr/department/sales, finance/team/ap — people, departments, roles, regions
```

Both are optional; either or both may be empty. The rule selector consults both with the appropriate matcher (file-glob for `tech_scope`, org-tree for `org_scope`). RBAC keys off `org_scope`. Federation keys off `org_scope`. Evaluation surface-fit keys off `tech_scope` for code subjects and `org_scope` for action/transaction subjects.

Migration: existing single-namespace `scope` values are split heuristically by prefix (`engineering/*` → `tech_scope`, everything else → `org_scope`), with a manual review pass.

### 5.11 Upgrade `agent_id` to `Actor`

The Phase 5i `agent_id` field is replaced (with backwards compatibility) by the `Actor` reference defined in §5.2:

```python
class EvaluationRecord:
    actor: Actor                # was: agent_id: str | None
    ...
```

Existing analytics that aggregate by `agent_id` are preserved by indexing on `actor.identifier` when `actor.kind == "agent"`.

### 5.12 Surface-Aware Audit Retention

Audit-log retention becomes a function of `Subject.surface`:

| Surface | Default retention |
|---|---|
| `code` | 1 year |
| `contract` | 10 years |
| `human_action` | 7 years |
| `transaction` | 10 years (tax law dependency) |
| `document` | 10 years |
| `message` | 3 years |
| `generic` | 7 years |

These are configurable per deployment and overridable per scope.

### 5.13 Surface-Aware PII Sanitization

The `core/PII` module currently applies a single sanitizer to all inputs. Make it `Surface`-aware:

- Code: redact `.env`-shaped lines, AWS-key-shaped tokens, common secret patterns.
- Contract: redact natural-person names where rules don't depend on them.
- Human action: redact employee names by default; surface names to the LLM only when the rule statement requires `actor.identifier`.
- Transaction: redact bank account numbers, card numbers, vendor payment info.
- Message: redact email addresses, phone numbers, customer IDs.

Sanitization rules per surface live in `surfaces/{surface}/pii.py`.

---

## 6. Phased Migration Plan

The refactor is large but does not require a rewrite. The plan below preserves backwards compatibility and ships value at every phase.

### Phase 7 — Stop the Bleeding (1–2 weeks)

Goal: prevent further drift while planning the structural fix.

- **Freeze new feature work** on Agent Governance, Snapshots, Federation. Marketplace has been removed. Phase 5 sub-features in flight may complete; new ones do not start.
- **Rewrite README** to lead with the cross-organizational mission. Move the "Code-Aware Evaluation Engine" out of the cover story.
- **Update `PROJECT.md` §6.4** to remove "core differentiator" framing; reposition Code-Aware Evaluation as one Surface Adapter among several planned ones.
- **Set the GitHub About** field: "Cross-organizational normative management for laws, contracts, policies, and operations."
- **Add Topics**: `governance`, `compliance`, `regtech`, `legal-tech`, `policy-management`, `rule-engine`. Remove or de-prioritize coding-related topics.
- **Add Contract Pack v0.1 seed data** (3 NDA-derived rules, 3 MSA-derived rules) and **HR Pack v0.1 seed data** (5 Labor-Standards-Act-derived rules). Make `make seed` install these alongside (not after) the code samples.

### Phase 8 — Surface Abstraction (2–4 weeks)

Goal: introduce the `Subject` / `Surface` model and reorganize the evaluation core.

- Define `Surface`, `Subject`, `Actor` in `domain/evaluation.py`.
- Move `diff_parser.py` and code-specific portions of `context_assembler.py` into `services/evaluation/surfaces/code/`.
- Author `evaluate_subject.txt` (universal prompt) and verify quality on three surfaces: code, contract clause, human action. The existing code-focused prompts remain as `surfaces/code/prompts/` for surface-specific hints.
- Add `POST /api/v1/evaluate/{surface}` while keeping `POST /api/v1/evaluate` as a backwards-compatible code path.
- Add `applies_to_surfaces` to the Rule model (migration). Backfill existing rules to `[Surface.CODE]`.

### Phase 9 — First Non-Code Domain Pack (3–6 weeks)

Goal: ship the cross-organizational mission with concrete proof.

- Build **Contract Pack** end-to-end:
  - Adapter: `docx_clause_extractor.py`, `redline_differ.py`
  - Rules: 30+ template clauses (NDA, MSA, SOW)
  - UI: `/domain/contract` with clause-level redline view, conflict detection, prior-contract similarity
  - Sample data: 3 anonymized contracts across NDA / MSA / SOW
- Add **`(legal)` persona pages** in the frontend.
- Run a real legal-team pilot. Publish results.

### Phase 10 — Norm Lineage and Multi-Language (4–6 weeks)

Goal: support regulatory tracking and bilingual operations.

- Add `norm_tier` and `norm_authority` columns. Build the Norm Lineage Viewer.
- Implement upstream-amendment propagation: when a `LAW` rule's `effective_period.valid_until` is updated, all transitive `derives_from` descendants are flagged.
- Add `locale` and `statement_translations`. Implement the bilingual drift checker.

### Phase 11 — Second and Third Domain Packs (6–10 weeks)

Goal: prove the Domain Pack architecture is general.

- **HR/Attendance Pack**: HRIS connector, attendance-event subject adapter, 36-agreement tracking, overtime-violation alerting.
- **Communication Pack**: Slack and email connectors, customer-correspondence compliance, harassment / data-leak scanning.
- Add `(hr)` and `(finance)` persona pages.

### Phase 12 — Connector Layer Maturation (ongoing)

Goal: integrate with the business systems where work actually happens.

- Implement Slack, Salesforce, Workday, SAP, DocuSign, Kintone connectors per demand.
- Standardize the `SubjectConnector` ABC and document the contract.

---

## 7. Repositioning (README and About)

A one-day change with outsized effect.

### 7.1 README — Current Opening

> A platform for managing, searching, and enforcing natural-language rules using LLMs and AI agents.
>
> Traditional rule engines force you to translate human rules into formal logic — losing nuance along the way. The Rule Repository keeps rules as written and uses Gemini to interpret, search, enforce, and improve them at runtime.
>
> Whether the rules come from legal regulations, HR policies, engineering standards, or coding conventions, this system stores them in their original natural-language form, makes them searchable across five modalities, evaluates code changes against them in batches, delivers them to AI coding agents at the moment they matter, and **learns from every human correction** to create better rules over time.

The third paragraph commits the framing error: it lists domains broadly but immediately specializes to "evaluates code changes" and "AI coding agents".

### 7.2 README — Proposed Opening

> An organization-wide normative management platform.
>
> The Rule Repository manages laws, contracts, internal policies, HR regulations, financial procedures, sales playbooks, communication standards, documentation conventions, and engineering rules — in their original natural language. Every team — Legal, HR, Finance, Sales, Compliance, IT, executive, and engineering — can discover, search, evaluate, and enforce the rules that govern their work, through APIs, AI agents, and persona-specific operator consoles.
>
> Surfaces supported include human actions (HR events, expense claims, procurement requests), business transactions (journal entries, invoices), contracts (clauses, redlines, prior-version comparison), documents (policies, handbooks, regulations), messages (email, Slack, customer correspondence), and code changes. **Code is one surface among many, not the center of the system.**
>
> Inspired by Semantic Governance, generalized to the entire organization.

### 7.3 GitHub About

Set to:

> Cross-organizational normative management for laws, contracts, policies, and operations. Natural-language rules, LLM-powered evaluation, persona-specific consoles.

### 7.4 GitHub Topics

Add: `governance`, `compliance`, `regtech`, `legal-tech`, `policy-management`, `rule-engine`, `semantic-governance`, `llm-as-judge`.

Remove or relegate (still relevant but not defining): `coding-rules`, `linter`, `code-review`.

### 7.5 The "What You Can Do" Section

Reorder so the first three subsections describe non-code workflows. Examples:

- "Review contracts against your standard playbook"
- "Validate HR events against labor regulations"
- "Audit transactions against tax and procurement policies"

Engineering subsections (PR review, agent hooks, IDE integration) come *after* the cross-organizational examples.

---

## 8. Secondary Issues to Address During the Refactor

These are not the root cause but are worth fixing as the surrounding structure changes.

| ID | Issue | Recommended fix |
|---|---|---|
| X1 | `scope` is overloaded | Split into `tech_scope` and `org_scope` per §5.10 |
| X2 | `agent_id` bakes in "agent = AI" | Replace with `Actor` per §5.11 |
| X3 | Federation and norm-lineage are visually conflated | Build separate UI trees; explicitly label them as "Organizational Hierarchy" and "Norm Lineage" |
| X4 | Sample data is English-only | Add Japanese sample rules sourced from 労働基準法 / 個人情報保護法 / 会社法 |
| X5 | Audit retention is uniform | Make retention surface-aware per §5.12 |
| X6 | PII sanitization is uniform | Make sanitization surface-aware per §5.13 |
| X7 | ~~Marketplace shipping before vertical depth~~ | **Resolved.** Marketplace removed; rules ship as Domain Packs. |
| X8 | Agent Governance is AI-agent specific | After Phase 11, generalize trust/mastery to apply to humans and business systems too |
| X9 | Phase 5 sub-phases (5a–5j) are deeply code-internal | Pause new 5x sub-phases until non-code packs are in production |

---

## 9. Risk and Considerations

### 9.1 Refactor Scope vs. Risk

The proposal preserves roughly 80% of the current implementation:

- The PostgreSQL schema gains columns but nothing is dropped.
- The Elasticsearch index gains fields.
- The Neo4j graph is unchanged in shape.
- The MCP server gains tools; the existing tools remain.
- The existing API endpoints retain their contracts.
- The Code Pack continues to function unchanged for current users.

The risk is concentrated in §5.1 (evaluation core re-layout) and §5.2 (introducing the `Subject` type). Both are testable with the existing test suite (212 tests) plus surface-specific test additions.

### 9.2 Communicating the Change

The repositioning in §7 will surprise users who installed the project as a coding-rules tool. Mitigations:

- The Code Pack is fully preserved and remains the most mature pack.
- The README explicitly notes that engineering use cases are first-class and well-supported, just no longer the center.
- A `MIGRATION.md` describes any behavior changes for existing users (there should be very few; the public API contract is stable).

### 9.3 Sequencing Discipline

The largest risk is sequencing discipline. The current trajectory adds features inside the code path (Phase 5j infrastructure tiers, more Agent Governance refinements). Each of these adds depth that has to be carried forward when the abstraction shifts in Phase 8. The recommended discipline:

- **Phase 7 freeze on non-essential code-path additions.** Hard freeze.
- **Phase 8 starts before Phase 5j or Phase 6c additions.**
- **No new sub-phase under 5x until Contract Pack ships.**

If sequencing is not held, the cost of the refactor grows month over month.

### 9.4 Team Composition

The Domain Packs have different expertise requirements. The Contract Pack benefits enormously from a legal-domain reviewer; the HR Pack from a labor-law-aware reviewer; the Finance Pack from a CPA. The repository's quality on these packs will be a function of bringing in those reviewers, not just shipping the code. Plan for at least one external domain reviewer per pack at the rules-curation stage.

---

## 10. Summary

The drift from "organization-wide normative management" to "AI-coding-agent rule manager" is **structural**, not cosmetic. It traces to one design choice — code change as the first-class evaluation input — and propagates throughout the system.

The fix is a phased refactor that:

1. Introduces `Subject` / `Surface` so code is one surface among many.
2. Promotes Norm Lineage to a first-class model alongside organizational Federation.
3. Ships work in **Domain Packs** (Contract, HR, Finance, ...) with Code becoming one pack among many.
4. Adds **persona-specific dashboards** for Legal, HR, Finance, and Compliance.
5. Generalizes the **MCP** so non-coding agents can be built on the same server.
6. Repositions the README and the GitHub About so the cross-organizational mission is the first impression.

The plan retains roughly 80% of the current implementation. The Code Pack remains the most mature pack; it is moved, not destroyed.

The sequencing matters: **Phase 7 (positioning, sample data) and Phase 8 (Surface abstraction) should run in parallel and start immediately**. Phase 9 (Contract Pack) is the first concrete proof that the project has reverted to its stated mission.

If sequencing is held, the project recovers its identity within one quarter, ships the first non-code pack within two quarters, and reaches three production domain packs within three quarters. At that point the Agent Governance investment — currently premature — becomes genuinely valuable, and the project occupies the cross-organizational normative-management space it was always meant to fill.

---

*This document is itself a proposal subject to review. It should be amended as design decisions are made, and superseded by the updated `PROJECT.md` and `CLAUDE.md` once the refactor lands.*
