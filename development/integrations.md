# Development Workflow Integrations

This guide covers all workflow integrations that connect the Rule Repository to development tools: GitHub PR review, CI pipelines, coding agent hooks, and rule ingestion.

---

## GitHub PR Review

**Source code**: `apps/server/src/rulerepo_server/integrations/github/`

### Webhook Endpoint

`POST /api/v1/integrations/webhooks/github`

### Supported Events

| Event | Action | Behavior |
|---|---|---|
| `pull_request` | `opened` | Fetches diff, runs evaluation, returns review comment |
| `pull_request` | `synchronize` | Same as opened (re-evaluates on push) |
| `pull_request` | other actions | Skipped with `{"status": "skipped"}` |
| `ping` | -- | Returns `{"status": "ok"}` (for webhook setup verification) |
| other events | -- | Skipped |

### Flow

1. **Receive webhook**: GitHub sends POST with event payload.
2. **Verify signature**: HMAC-SHA256 verification using `X-Hub-Signature-256` header and `GITHUB_WEBHOOK_SECRET` env var. Uses `hmac.compare_digest()` for constant-time comparison.
3. **Fetch diff**: Downloads the diff from the PR's `diff_url` using `httpx` with a 30-second timeout.
4. **Evaluate**: Runs the full evaluation pipeline via `EvaluationService.evaluate()` with `mode="posthoc"`, passing the diff text and PR title as intent.
5. **Format review comment**: Converts the `EvaluationResult` to a markdown review comment via `format_review_comment()`.
6. **Return result**: Returns verdict, rules_evaluated, violation count, and the formatted review comment.

### Review Comment Format

The `review_formatter.py` module produces structured markdown:

**All rules pass:**
```
**Rule Repository**: All applicable rules pass. :white_check_mark:
```

**Violations found:**
```markdown
**Rule Repository**: 2 violation(s), 1 suggestion(s) found

### :x: DENY -- All API handlers must validate input with Pydantic
:round_pushpin: `src/api/handler.py:42`
**Issue**: Raw dict access without Pydantic validation
**Fix**: Define a ProcessRefundRequest Pydantic model

### :x: DENY -- Type hints are mandatory on all public functions
:round_pushpin: `src/services/refund.py:15`
**Issue**: Missing return type annotation
**Fix**: Add -> RefundResult return type

### :warning: SUGGESTION -- Functions should have docstrings
Missing docstring on new public function
```

The violations section includes file:line locations (from `CodeLocation`), issue descriptions, and fix suggestions. The warnings section shows suggestions without location pinpointing.

### Signature Verification

**File**: `integrations/github/signature.py`

The `verify_github_signature()` function:
- Reads `GITHUB_WEBHOOK_SECRET` from settings.
- If no secret is configured, verification is **skipped** (for local development). A debug log is emitted.
- If a secret is configured but the `X-Hub-Signature-256` header is missing, returns `False`.
- Computes `sha256=` HMAC of the raw request body and compares using `hmac.compare_digest()`.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_WEBHOOK_SECRET` | No (dev) / Yes (prod) | Secret for HMAC-SHA256 signature verification. If unset, signature verification is skipped. |

### GitHub Repository Setup

1. Go to repository Settings > Webhooks > Add webhook
2. Payload URL: `https://your-server/api/v1/integrations/webhooks/github`
3. Content type: `application/json`
4. Secret: same value as `GITHUB_WEBHOOK_SECRET`
5. Events: select "Pull requests"

### NOT IMPLEMENTED

- **GitHub Check Run creation**: The server does not create GitHub Check Runs. PR merge blocking via required checks is not available.
- **Review comment posting**: The endpoint returns the formatted review comment but does not currently POST it back to GitHub via the API. The caller (or a GitHub Action wrapper) must handle posting.

---

## CI Pipeline: rulerepo-check

**Source code**: `packages/cli/src/rulerepo_cli/check.py`

A CLI tool that checks code changes against organizational rules. Designed for use in CI pipelines (GitHub Actions, GitLab CI, etc.).

### Installation

```bash
cd packages/cli
uv sync
```

The tool is registered as `rulerepo-check` via the package's entry points.

### Usage

```bash
# Basic usage with inline diff
rulerepo-check --diff "$(git diff origin/main...HEAD)" --scope engineering/python

# Using diff command (default: git diff origin/main...HEAD)
rulerepo-check --diff-cmd "git diff origin/main...HEAD" --format github-actions

# Custom server URL
rulerepo-check --diff "$(git diff)" --server-url https://rulerepo.internal.com
```

### Options

| Option | Default | Description |
|---|---|---|
| `--diff` | -- | Unified diff text. If omitted, `--diff-cmd` is executed. |
| `--diff-cmd` | `git diff origin/main...HEAD` | Shell command to generate the diff. |
| `--scope` | -- | Rule scope filter (e.g., `engineering/python`). |
| `--repository` | -- | Repository identifier. |
| `--server-url` | `http://localhost:8000` | Rule Repository server URL. Also reads `RULEREPO_SERVER_URL` env var. |
| `--fail-on-deny / --no-fail-on-deny` | `--fail-on-deny` | Whether to exit 1 on DENY verdict. |
| `--format` | `text` | Output format: `text`, `json`, `github-actions`. |

### Exit Codes

| Code | Meaning |
|---|---|
| 0 | ALLOW -- all rules pass |
| 1 | DENY -- at least one rule violated (with `--fail-on-deny`) |
| 2 | NEEDS_CONFIRMATION -- human review needed, or evaluation failed |

### Output Formats

**text** (default):
```
Rule Repository: DENY
Rules evaluated: 8

Fix 1 violation(s):
  1. Add Pydantic model for input validation
```

**json**: Raw JSON response from the evaluation API.

**github-actions**: GitHub Actions annotation format:
```
::error file=src/api/handler.py,line=42::Raw dict access without Pydantic validation
::warning::Missing docstring on new public function
```

These annotations appear inline in the GitHub PR diff view.

### GitHub Actions Example

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

      - name: Check rules
        run: |
          rulerepo-check \
            --diff "$(git diff origin/main...HEAD)" \
            --scope engineering/python \
            --format github-actions \
            --server-url ${{ secrets.RULEREPO_SERVER_URL }}
```

### API Call

The tool sends a POST to `/api/v1/evaluate` with:
```json
{
  "diff": "<unified diff>",
  "mode": "posthoc",
  "scope": "<if provided>",
  "repository": "<if provided>"
}
```

---

## Agent Hooks: rulerepo-hook

**Source code**: `packages/cli/src/rulerepo_cli/hook.py`

A lightweight wrapper for coding agent integration. Supports two modes: preflight (before edit) and posthoc (after edit).

### Installation

```bash
cd packages/cli
uv sync
```

Registered as `rulerepo-hook` via entry points.

### Modes

**preflight**: Before the agent edits a file, fetch applicable rules and inject them into the agent's context.

```bash
rulerepo-hook preflight --file src/api/handler.py
```

Output (printed to stdout for agent consumption):
```
## Rules for src/api/handler.py
  [MUST] All API handlers must validate input with Pydantic
  [MUST] Type hints are mandatory on all public functions
  [SHOULD] Functions should have docstrings
```

Calls `POST /api/v1/evaluate/applicable-rules` with the file path.

**posthoc**: After the agent edits a file, evaluate the change and report violations.

```bash
rulerepo-hook posthoc --file src/api/handler.py --diff "$(git diff src/api/handler.py)"
```

Output (only shown if verdict is not ALLOW):
```
Rule Repository: DENY
Fix 1 violation(s):
  1. Add Pydantic model for input validation
```

Calls `POST /api/v1/evaluate` with the diff and file path.

### Options

| Option | Description |
|---|---|
| `--file` | File being edited |
| `--diff` | Diff of changes (for posthoc mode) |
| `--format` | Output format (default: `instructions`) |
| `--server-url` | Server URL (default: `http://localhost:8000`, also reads `RULEREPO_SERVER_URL`) |

### Error Handling

Both modes are **non-blocking on HTTP errors**. If the server is unreachable or returns an error, the hook silently passes (catches `httpx.HTTPError` and continues). This ensures the agent is never blocked by Rule Repository downtime.

### Claude Code Hooks Configuration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "rulerepo-hook preflight --file \"$TOOL_INPUT_FILE_PATH\""
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "rulerepo-hook posthoc --file \"$TOOL_INPUT_FILE_PATH\""
      }
    ]
  }
}
```

This configuration runs the preflight hook before every Edit or Write tool call (injecting applicable rules), and the posthoc hook after every Edit or Write (checking the result for violations).

---

## Rule Ingestion: rulerepo-ingest

**Source code**: `packages/cli/src/rulerepo_cli/ingest.py`

Import rules from external sources (currently CLAUDE.md files) into the Rule Repository.

### Usage

```bash
rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
```

### Options

| Option | Required | Description |
|---|---|---|
| `--source` | Yes | Source type. Currently only `claude-md` is supported. |
| `--file` | Yes | Path to the file to ingest. |
| `--scope` | Yes | Rule scope to assign to extracted rules. |
| `--server-url` | No | Server URL (default: `http://localhost:8000`, also reads `RULEREPO_SERVER_URL`). |

### Flow

1. **Upload**: Sends the file to `POST /api/v1/documents/upload` as multipart form data with `text/markdown` MIME type.
2. **Extract**: Triggers extraction via `POST /api/v1/documents/{doc_id}/extract` with a 120-second timeout (extraction can be slow for large documents).
3. **Display**: Prints the number of candidate rules and the first 10 candidates with modality, statement preview (80 chars), and confidence score.
4. **Review**: Directs the user to the frontend at `/documents` for reviewing and approving candidates.

### Example Output

```
Uploading ./CLAUDE.md...
Uploaded: a1b2c3d4-...
Extracting rules...
Extracted 15 candidate rules from ./CLAUDE.md

Candidate rules:
  [MUST] Type hints are mandatory on all public functions. mypy m... (confidence: 92%)
  [MUST_NOT] Never commit secrets. No API keys, no DB passwords, ... (confidence: 95%)
  [SHOULD] Prefer fewer dependencies. Every added library is a lo... (confidence: 78%)
  ... and 12 more

Review and approve at: http://localhost:3000/documents
```

---

## Gateway Action Execution

### NOT IMPLEMENTED

The gateway (`gateway/router.py`) receives webhooks, normalizes events, matches policies, and runs the real evaluation engine to produce verdicts. However, **action execution on DENY is not implemented**:

- The `actions_taken` field on `GatewayEvaluationModel` is always an empty list `[]`.
- Configured `response_actions` and `on_deny` policy fields are stored but not executed.
- Webhook callbacks (notifying the source system of a DENY) are not sent.
- Slack message notifications on DENY are not sent.

To implement: add action executors in `gateway/actions/` that read the policy's `response_actions` config and dispatch to the appropriate channel (webhook callback, Slack API, email, etc.) when the verdict is DENY.
