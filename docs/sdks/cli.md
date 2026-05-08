# CLI Tools

The Rule Repository ships three command-line tools for integrating rule evaluation into development workflows.

## rulerepo-check

CI integration tool. Evaluates a diff against the rule corpus and reports violations.

### Usage

```bash
rulerepo-check --diff "$(git diff origin/main...HEAD)" \
    --scope engineering \
    --format github-actions \
    --fail-on-deny
```

### Options

| Option | Description | Default |
|---|---|---|
| `--diff TEXT` | The diff content to evaluate | Required (or use `--diff-cmd`) |
| `--diff-cmd TEXT` | Shell command that produces the diff | Alternative to `--diff` |
| `--scope TEXT` | Limit evaluation to rules in this scope | All scopes |
| `--repository TEXT` | Repository identifier for context matching | Auto-detected from git |
| `--server-url URL` | Rule Repository server URL | `$RULEREPO_SERVER_URL` |
| `--fail-on-deny` | Exit with code 1 if any rule returns DENY | Off |
| `--format TEXT` | Output format: `text`, `json`, `github-actions` | `text` |

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | All rules passed (or warnings only without `--fail-on-deny`) |
| `1` | One or more rules returned DENY (with `--fail-on-deny`) |
| `2` | Error communicating with the server or invalid arguments |

### Output Formats

- **text** -- Human-readable output for terminal use. Shows violations with file paths and line numbers.
- **json** -- Machine-readable JSON array of evaluation results. Suitable for piping into other tools.
- **github-actions** -- Emits `::error` and `::warning` annotations that GitHub Actions renders as inline comments on the PR diff.

### Example: GitHub Actions Workflow

```yaml
name: Rule Check
on: [pull_request]

jobs:
  rule-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install rulerepo CLI
        run: pip install rulerepo-agentic

      - name: Check rules
        env:
          RULEREPO_SERVER_URL: ${{ secrets.RULEREPO_SERVER_URL }}
        run: |
          rulerepo-check \
            --diff "$(git diff origin/main...HEAD)" \
            --format github-actions \
            --scope engineering \
            --fail-on-deny
```

---

## rulerepo-hook

Agent hooks tool. Designed for use with AI coding agent hook systems (e.g., Claude Code hooks). Provides two subcommands for pre-edit and post-edit rule integration.

### Subcommands

#### `rulerepo-hook preflight`

Runs before a file edit. Returns applicable rules so the agent can incorporate them before making changes.

```bash
rulerepo-hook preflight --file src/main.py --server-url http://localhost:8000
```

#### `rulerepo-hook posthot`

Runs after a file edit. Evaluates the change against applicable rules and reports violations.

```bash
rulerepo-hook posthot --file src/main.py --diff "..." --server-url http://localhost:8000
```

### Options

| Option | Description | Default |
|---|---|---|
| `--file PATH` | File path being edited | Required |
| `--diff TEXT` | Diff content (posthot only) | Auto-generated if omitted |
| `--format TEXT` | Output format: `text`, `json` | `text` |
| `--server-url URL` | Rule Repository server URL | `$RULEREPO_SERVER_URL` |
| `--agent-id TEXT` | Agent identifier for tracking | `$RULEREPO_AGENT_ID` |

### Error Behavior

Both subcommands are **non-blocking on errors**. If the server is unreachable or returns an error, the hook prints a warning to stderr and exits with code 0. This prevents rule evaluation failures from blocking the agent's workflow.

---

## rulerepo-ingest

Rule import tool. Uploads a document to the Rule Repository and triggers rule extraction.

### Usage

```bash
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering
```

### Options

| Option | Description | Default |
|---|---|---|
| `--source TEXT` | Source type: `claude-md`, `pdf`, `markdown`, `text` | Required |
| `--file PATH` | Path to the document to ingest | Required |
| `--scope TEXT` | Scope to assign to extracted rules | Required |
| `--server-url URL` | Rule Repository server URL | `$RULEREPO_SERVER_URL` |

### What Happens

1. The document is uploaded to the server.
2. The extraction pipeline processes the document (using Gemini for PDFs and structured documents).
3. Candidate rules are extracted and stored for review.
4. The command prints the number of candidate rules found.

```
$ rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering
Uploaded document: CLAUDE.md (doc_abc123)
Extraction complete: 15 candidate rules found
```

Candidates must be reviewed and approved through the frontend or API before they become active rules.

## rulerepo-export

Exports rules from the server to a portable `rules.yaml` file.

### Usage

```bash
rulerepo-export --output rules.yaml --project-id abc-123
```

### Options

| Option | Description | Default |
|---|---|---|
| `--output PATH` | Output file path | `rules.yaml` |
| `--project-id TEXT` | Filter by project | All projects |
| `--scope TEXT` | Filter by scope tag | All scopes |
| `--server-url URL` | Rule Repository server URL | `$RULEREPO_SERVER_URL` |

### Output Format

```yaml
version: 1
project: abc-123
rules:
  - id: rule-abc
    statement: "All API endpoints MUST validate input with Pydantic models"
    modality: MUST
    severity: HIGH
    scope: [src/api/**]
```

The `rules.yaml` file is version-controllable and works with the planned `rulerepo-lite` local evaluator.

---

---

## rulerepo context

Generates or updates a CLAUDE.md rules section from rules in the Rule Repository.

### Usage

```bash
rulerepo context generate --server http://localhost:8000 --project my-project
rulerepo context update --file CLAUDE.md
```

---

## rulerepo init

Initializes a new project with default configuration.

### Usage

```bash
rulerepo init
```

---

## rulerepo doctor

Runs health checks against the Rule Repository server.

### Usage

```bash
rulerepo doctor --server-url http://localhost:8000
```

---

## rulerepo audit verify

Verifies the integrity of the audit chain.

### Usage

```bash
rulerepo audit verify --server-url http://localhost:8000
```

---

## Environment

All commands read `RULEREPO_SERVER_URL` from the environment if `--server-url` is not provided. `rulerepo-hook` also reads `RULEREPO_AGENT_ID` for agent identity tracking.

## See Also

- [CI Pipeline Integration](../integrations/ci.md) -- using `rulerepo-check` in CI
- [Agent Hooks](../integrations/agent-hooks.md) -- configuring `rulerepo-hook` with Claude Code
- [Agentic Client SDK](agentic-client.md) -- Python API for programmatic access
