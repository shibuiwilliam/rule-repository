# CI Pipeline Integration

Use the `rulerepo-check` CLI tool to enforce rules in any CI system. The tool evaluates a diff against the rule corpus and can fail the build when violations are found.

## Quick Start

```bash
rulerepo-check \
    --diff "$(git diff origin/main...HEAD)" \
    --scope engineering \
    --format github-actions \
    --fail-on-deny
```

## Environment

Set `RULEREPO_SERVER_URL` in your CI environment to point to the Rule Repository server:

```
RULEREPO_SERVER_URL=https://rules.your-company.com
```

## GitHub Actions

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

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

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

When `--format github-actions` is used, violations are emitted as `::error` and `::warning` annotations. GitHub renders these as inline comments on the PR diff.

## GitLab CI

```yaml
rule-check:
  stage: test
  image: python:3.13
  script:
    - pip install rulerepo-agentic
    - rulerepo-check
        --diff "$(git diff origin/main...HEAD)"
        --format text
        --scope engineering
        --fail-on-deny
  variables:
    RULEREPO_SERVER_URL: $RULEREPO_SERVER_URL
```

## Output Formats

| Format | Best For | Description |
|---|---|---|
| `text` | Terminal / local dev | Human-readable output with file paths, line numbers, and violation details |
| `json` | Machine processing | JSON array of evaluation results, suitable for piping into `jq` or other tools |
| `github-actions` | GitHub Actions | Emits `::error file=...` and `::warning file=...` annotations for inline PR comments |

### Example: text output

```
DENY  src/api/auth.py:42  SEC-001  Missing input validation on user-supplied token
WARN  src/config.py:15    ENG-003  Bare Exception raised; use project exception hierarchy
```

### Example: json output

```json
[
  {
    "verdict": "DENY",
    "file": "src/api/auth.py",
    "line": 42,
    "rule_id": "SEC-001",
    "message": "Missing input validation on user-supplied token",
    "suggestion": "Add validate_token() call before processing"
  }
]
```

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | All rules passed, or only warnings were found (without `--fail-on-deny`) |
| `1` | One or more DENY verdicts (when `--fail-on-deny` is set) |
| `2` | Error: server unreachable, invalid arguments, or other failures |

## Tips

- Use `--scope` to limit evaluation to a specific rule scope. Without it, all scopes are evaluated.
- Use `--diff-cmd` instead of `--diff` if your diff command is complex: `--diff-cmd "git diff origin/main...HEAD"`.
- For monorepos, run `rulerepo-check` per changed directory with different scopes.

## See Also

- [CLI Tools Reference](../sdks/cli.md) -- full CLI documentation
- [GitHub PR Review](github.md) -- automatic PR review via webhooks (no CI config needed)
