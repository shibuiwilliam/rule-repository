# Rule Discovery

Rule Discovery automatically identifies implicit rules from existing project artifacts -- configuration files, linter configs, code patterns, and documentation -- and proposes them as candidate rules for human review.

## Pipeline

The discovery pipeline runs in four stages:

### 1. Source Analyzers

Source analyzers extract potential rules from different artifact types:

| Analyzer | Source | Examples |
|---|---|---|
| **CLAUDE.md Analyzer** | `CLAUDE.md` files | Coding conventions, naming rules, forbidden patterns |
| **Linter Config Analyzer** | `.eslintrc`, `ruff.toml`, `pyproject.toml` | Linting rules, formatting requirements, import ordering |
| **Code Pattern Analyzer** | Source code files | Recurring patterns, guard clauses, error handling conventions |

Each analyzer produces raw rule candidates with a source reference back to the originating file and line.

### 2. Pattern Detector

The pattern detector deduplicates and scores raw candidates:

- **Deduplication**: merges semantically similar candidates using embedding similarity.
- **Scoring**: assigns a confidence score based on how frequently the pattern appears and how explicitly it is stated.
- Candidates below the confidence threshold are discarded.

### 3. Candidate Generator

The candidate generator uses Gemini to refine raw candidates into well-formed rule statements:

- Converts informal patterns into clear, enforceable rule language.
- Assigns suggested metadata (scope, modality, severity, tags).
- Links candidates to their source evidence.

### 4. Human Review Queue

All candidates enter a review queue. Reviewers can:

- **Approve** a candidate, creating a rule through the standard creation flow.
- **Edit** a candidate before approval (adjust statement, metadata, or scope).
- **Dismiss** a candidate, marking it as not a rule.

No candidate becomes a rule without explicit human approval.

## API Flow

```
POST /api/v1/discover/scan
  Body: { sources, file_contents, repository }
  -> Returns: scan_id, status

GET /api/v1/discover/scans/{scan_id}
  -> Returns: scan status, progress

GET /api/v1/discover/scans/{scan_id}/candidates
  -> Returns: list of candidate rules with scores

POST /api/v1/discover/candidates/{candidate_id}/approve
  -> Creates rule, returns rule_id

POST /api/v1/discover/candidates/{candidate_id}/dismiss
  -> Marks candidate as dismissed
```

## MCP Integration

The `discover_rules` MCP tool allows AI agents to trigger discovery scans directly:

```
Tool: discover_rules
Input: {"file_paths": ["CLAUDE.md", ".eslintrc.json"], "repository": "my-project"}
Output: List of candidate rules discovered from the provided files
```

## See Also

- [REST API: Discovery](../api/discovery.md) -- endpoint details and request/response examples
- [Feedback Loop](../intelligence/feedback.md) -- how corrections feed back into rule creation
