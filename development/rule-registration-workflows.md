# Rule Registration Workflows

How rules enter the system — three primary paths, each with a sequence diagram showing interactions across all data stores.

**Source files:** `services/rule_service.py`, `api/v1/rules.py`, `api/v1/extraction.py`, `api/v1/discovery.py`, `api/v1/feedback.py`

---

## Workflow 1: Manual Rule Creation

A user creates a rule directly via the REST API or frontend form.

```mermaid
sequenceDiagram
    participant Client
    participant API as api/v1/rules.py
    participant Svc as RuleService
    participant Gemini
    participant PG as PostgreSQL
    participant ES as Elasticsearch
    participant Neo as Neo4j
    participant Audit as AuditLog

    Client->>API: POST /api/v1/rules {statement, modality, severity, ...}
    API->>Svc: create_rule(data, actor)

    Note over Svc: Step 1: Generate embedding
    Svc->>Gemini: generate_embedding(statement)
    Gemini-->>Svc: embedding[768]

    Note over Svc: Step 2: Persist rule (source of truth)
    Svc->>PG: INSERT INTO rules (id, statement, modality, severity, scope, tags, embedding, ...)
    PG-->>Svc: RuleModel

    Note over Svc: Step 3: Create revision #1
    Svc->>PG: INSERT INTO rule_revisions (rule_id, revision_number=1, change_note="Initial creation")
    PG-->>Svc: RuleRevisionModel

    Note over Svc: Step 4: Index for search (best-effort)
    Svc->>ES: INDEX rules/{rule_id} {statement, modality, severity, embedding, ...}
    ES-->>Svc: ok (or warning logged on failure)

    Note over Svc: Step 5: Create graph node (best-effort)
    Svc->>Neo: MERGE (r:Rule {id: rule_id}) SET r.modality, r.severity, r.status
    Neo-->>Svc: ok (or warning logged on failure)

    Note over Svc: Step 6: Audit log (append-only, hash-chained)
    Svc->>Audit: append(action="rule_created", actor, resource_id=rule_id)
    Audit->>PG: INSERT INTO audit_log (previous_hash, entry_hash, ...)

    Svc-->>API: RuleModel
    API-->>Client: 201 Created {id, statement, modality, ...}
```

**Key properties:**
- PostgreSQL write MUST succeed — if it fails, the entire operation fails
- Elasticsearch and Neo4j writes are best-effort — failures are logged but don't roll back Postgres
- Embedding generation is optional — if Gemini is unavailable, the rule is created without an embedding
- The audit log append computes a SHA-256 hash chain linking to the previous entry

---

## Workflow 2: Document Extraction Pipeline

A user uploads a document (PDF, markdown, text), the system extracts candidate rules via Gemini, and a human reviews/approves them.

```mermaid
sequenceDiagram
    participant User
    participant API as api/v1/extraction.py
    participant Storage as LocalFileStorage
    participant PG as PostgreSQL
    participant Pipeline as ExtractionPipeline
    participant Gemini
    participant Audit as AuditLog
    participant Svc as RuleService
    participant ES as Elasticsearch
    participant Neo as Neo4j

    Note over User,Neo: Phase 1: Upload
    User->>API: POST /documents/upload (multipart file)
    API->>Storage: store(file_bytes, filename, mime_type) → doc_id
    Storage-->>API: doc_id (UUID)
    API->>PG: INSERT INTO documents (id, filename, mime_type, size_bytes, storage_path)
    PG-->>API: DocumentModel
    API-->>User: {document_id, filename, size_bytes}

    Note over User,Neo: Phase 2: Extract
    User->>API: POST /documents/{document_id}/extract
    API->>PG: SELECT FROM documents WHERE id = document_id
    PG-->>API: DocumentModel
    API->>Storage: retrieve(document_id) → file_bytes

    API->>Pipeline: extract_from_document(file_bytes, mime_type, filename)
    
    alt PDF > 50KB
        Pipeline->>Gemini: Files API upload(file_bytes)
        Gemini-->>Pipeline: file_uri
        Pipeline->>Gemini: generate_content(file_uri + extract_rules.txt prompt)
    else PDF ≤ 50KB or text/markdown
        Pipeline->>Gemini: generate_content(inline_content + extract_rules.txt prompt)
    end
    
    Gemini-->>Pipeline: JSON [{statement, modality, severity, scope, tags, confidence}, ...]
    Pipeline->>Audit: append(action="llm_extraction_call", model_id, latency_ms)

    Pipeline-->>API: {extraction_id, candidates[], model_id}
    API->>PG: INSERT INTO extractions (id, document_id, candidates, model_id, status="PENDING_REVIEW")
    API-->>User: {extraction_id, candidates[]}

    Note over User,Neo: Phase 3: Review & Approve
    User->>API: POST /extractions/{extraction_id}/review {approved_indices: [0, 2, 3]}
    API->>PG: SELECT FROM extractions WHERE id = extraction_id

    loop For each approved candidate
        API->>Svc: create_rule(candidate_as_RuleCreate, actor="extraction_pipeline")
        Note over Svc,Neo: [Full Workflow 1 sequence]
        Svc->>PG: INSERT INTO rules
        Svc->>PG: INSERT INTO rule_revisions
        Svc->>ES: INDEX rules/{id}
        Svc->>Neo: MERGE (:Rule {id})
        Svc->>Audit: append("rule_created")
        Svc-->>API: RuleModel
    end

    API->>PG: UPDATE extractions SET status = "REVIEWED"
    API-->>User: {rules_created: 3, rule_ids: [...]}
```

**Key properties:**
- Document upload and extraction are separate steps (user controls when to extract)
- Extraction uses Gemini with structured JSON output — no regex parsing
- Candidates are stored as JSONB in the `extractions` table until reviewed
- Approved candidates flow through the same `RuleService.create_rule()` as manual creation — full 3-store sync
- The LLM call itself is logged to the audit table (model_id, prompt version, latency)

---

## Workflow 3: Automatic Discovery Scan

The system scans repository artifacts (CLAUDE.md, linter configs, code patterns) and proposes candidate rules.

```mermaid
sequenceDiagram
    participant User
    participant API as api/v1/discovery.py
    participant Svc as DiscoveryService
    participant Importer as GitHubImporter
    participant Analyzers as Source Analyzers
    participant Detector as PatternDetector
    participant Generator as CandidateGenerator
    participant Gemini
    participant PG as PostgreSQL

    Note over User,PG: Phase 1: Initiate Scan
    User->>API: POST /discover/scan {sources: [...], file_contents: {...}}
    API->>Svc: start_scan(sources, file_contents, repository)

    Svc->>PG: INSERT INTO discovery_scans (id, status="running", sources, repository)

    Note over Svc,PG: Phase 1b: GitHub Import (optional)
    alt GitHub URL provided
        Svc->>Importer: import_repository(github_url, branch)
        Importer->>Importer: GET /repos/{owner}/{repo}/contents/{file} (14 interesting files)
        Importer-->>Svc: {filename: content} dict
    end

    Note over Svc,PG: Phase 2: Analyze Sources (parallel)
    par CLAUDE.md Analyzer
        Svc->>Analyzers: ClaudeMdAnalyzer.analyze(context)
        Analyzers-->>Svc: raw_patterns[]
    and Linter Config Analyzer
        Svc->>Analyzers: LinterConfigAnalyzer.analyze(context)
        Analyzers-->>Svc: raw_patterns[]
    and Code Pattern Analyzer
        Svc->>Analyzers: CodePatternsAnalyzer.analyze(context)
        Analyzers-->>Svc: raw_patterns[]
    end

    Note over Svc,PG: Phase 3: Deduplicate & Score
    Svc->>Detector: deduplicate_and_score(all_patterns)
    Detector-->>Svc: scored_patterns[] (with confidence)

    Note over Svc,PG: Phase 4: Refine via LLM
    Svc->>Generator: generate_candidates(scored_patterns, gemini_client)
    Generator->>Gemini: generate_content(pattern + refinement prompt)
    Gemini-->>Generator: {statement, modality, severity, scope, tags, rationale}
    Generator-->>Svc: refined_candidates[]

    Note over Svc,PG: Phase 5: Persist Candidates
    loop For each candidate
        Svc->>PG: INSERT INTO discovery_candidates (scan_id, statement, modality, confidence, status="pending")
    end
    Svc->>PG: UPDATE discovery_scans SET status="completed", candidates_found=N

    Svc-->>API: {scan_id, status: "completed"}
    API-->>User: {scan_id}

    Note over User,PG: Phase 6: Review & Approve
    User->>API: GET /discover/candidates?scan_id=...
    API-->>User: candidates[] (pending)

    User->>API: POST /discover/candidates/{id}/approve
    API->>Svc: approve_candidate(candidate_id)
    Svc->>PG: INSERT INTO rules (from candidate fields)
    Svc->>PG: UPDATE discovery_candidates SET status="approved", created_rule_id=rule.id
    Svc-->>API: {rule_id}
    API-->>User: {rule_id}
```

**Key properties:**
- Three analyzers run in parallel for speed
- GitHubImporter fetches files via GitHub Contents API (no cloning)
- Pattern detector deduplicates across sources — patterns found by multiple analyzers get higher confidence
- Gemini refines raw patterns into well-formed rule statements with structured output

---

## Workflow 4: Correction Feedback → Rule

When a human corrects agent-generated code, the correction can become a new rule.

```mermaid
sequenceDiagram
    participant Agent
    participant Human
    participant GitHub
    participant API as api/v1/feedback.py
    participant Capture as PRCapture
    participant Analyzer as CorrectionAnalyzer
    participant Gemini
    participant PG as PostgreSQL

    Note over Agent,PG: Step 1: Agent writes code, evaluated
    Agent->>API: POST /evaluate {diff}
    API-->>Agent: {verdict: "ALLOW"}

    Note over Agent,PG: Step 2: Human corrects in PR review
    Human->>GitHub: Edit agent's code in PR
    GitHub->>GitHub: PR merged

    Note over Agent,PG: Step 3: Auto-capture correction
    GitHub->>API: Webhook: pull_request.closed (merged)
    API->>Capture: capture_from_pr_merge(repo, pr_number, merged_diff)
    Capture->>PG: Query audit_log for prior evaluations on this repo
    Capture->>PG: INSERT INTO corrections (original_diff, corrected_diff, source_type="github_pr_merge")

    Note over Agent,PG: Step 4: Analyze correction
    Analyzer->>Gemini: Classify correction (new_rule / improve_existing / adjust_scope)
    Gemini-->>Analyzer: {type: "new_rule", candidate_statement, confidence: 0.85}
    Analyzer->>PG: UPDATE corrections SET analysis_type, candidate_statement, confidence

    Note over Agent,PG: Step 5: Approve → create rule
    Human->>API: POST /feedback/corrections/{id}/approve
    API->>PG: INSERT INTO rules (statement=candidate_statement, status="DRAFT")
    API->>PG: UPDATE corrections SET status="approved", created_rule_id=rule.id
    API-->>Human: {rule_id}
```

**Key properties:**
- Corrections can be captured automatically (PR merge webhook) or manually (user submits diffs)
- The analyzer classifies corrections into three types to determine the right action
- Approved corrections create rules in DRAFT status (not immediately enforced)
- Rules from corrections are tagged `["auto-generated", "from-correction"]` for tracking

---

## Data Store Synchronization Matrix

| Workflow | PostgreSQL | Elasticsearch | Neo4j | Audit Log | Notes |
|---|---|---|---|---|---|
| **Manual create** | ✅ Insert | ✅ Index | ✅ Node | ✅ Entry | Full sync via `RuleService.create_rule()` |
| **Extraction review** | ✅ Insert | ✅ Index | ✅ Node | ✅ Entry | Uses `RuleService.create_rule()` |
| **Discovery approve** | ✅ Insert | ⚠️ Not indexed | ⚠️ No node | ⚠️ No entry | Direct PG insert — needs reconciler |
| **Feedback approve** | ✅ Insert | ⚠️ Not indexed | ⚠️ No node | ⚠️ No entry | Direct PG insert — needs reconciler |

**Recovery:** Run `scripts/reindex_elasticsearch.py` and `scripts/reconcile_graph.py` to sync derived stores from PostgreSQL.

---

## Rule Lifecycle After Registration

```
DRAFT ──────► REVIEW ──────► APPROVED ──────► EFFECTIVE ──────► RETIRED
  │              │                                │                  ▲
  └──────────────┴────────────────────────────────┴──────────────────┘
                         (can retire from any state)

Status transitions are validated in domain/rule.py — invalid jumps raise ValidationError.
RETIRED is terminal (rules are never deleted).
```

---

## Files Referenced

| File | Role |
|---|---|
| `api/v1/rules.py` | Manual rule creation endpoint |
| `services/rule_service.py` | Orchestrates writes to all 3 stores |
| `api/v1/extraction.py` | Document upload, extract, review endpoints |
| `services/extraction/pipeline.py` | Gemini-powered rule extraction |
| `api/v1/discovery.py` | Discovery scan, candidate approve endpoints |
| `services/discovery/service.py` | Scan orchestration, analyzer dispatch |
| `services/discovery/github_importer.py` | GitHub Contents API file fetcher |
| `api/v1/feedback.py` | Correction submission and approval |
| `services/feedback/pr_capture.py` | Auto-capture corrections from merged PRs |
| `services/feedback/correction_analyzer.py` | Classify corrections via Gemini |
| `adapters/postgres/rule_repo.py` | PostgreSQL CRUD operations |
| `adapters/elasticsearch/rule_index.py` | ES indexing and search |
| `adapters/neo4j/graph_repo.py` | Neo4j node and relationship operations |
| `adapters/postgres/audit_repo.py` | Append-only audit log with hash chain |
| `scripts/reindex_elasticsearch.py` | Rebuild ES index from Postgres |
| `scripts/reconcile_graph.py` | Rebuild Neo4j graph from Postgres |
