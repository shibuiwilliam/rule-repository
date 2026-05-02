# CLAUDE.md Context Generator

## Overview

The `rulerepo-context` CLI maintains a `## Rules` section in your project's CLAUDE.md file. Since every AI coding agent reads CLAUDE.md at session start, this ensures rules reach agents automatically without any MCP configuration or hook setup.

## Installation

```bash
pip install rulerepo-cli
# or via uv workspace
uv sync
```

## Commands

### Generate (print to stdout)

```bash
rulerepo-context generate --server http://localhost:8000 --max-rules 50
```

### Update (modify file in-place)

```bash
rulerepo-context update --file ./CLAUDE.md --server http://localhost:8000 --project my-project
```

This reads the existing CLAUDE.md, finds the section between markers, replaces it with fresh rules, and writes back. All other content in the file is preserved.

### Watch (continuous regeneration)

```bash
rulerepo-context watch --file ./CLAUDE.md --server http://localhost:8000 --interval 60
```

Polls the server every 60 seconds and updates the file whenever rules change.

## Output Format

```markdown
<!-- rulerepo:rules:start -->
## Rules (auto-managed by Rule Repository)

### MUST
- All Python functions must have type annotations [HIGH]
- API endpoints must validate input with Pydantic models [HIGH]

### Never
- MUST NOT use bare except [CRITICAL]

### SHOULD
- Use dependency injection for services [MEDIUM]

_47 rules from project "backend-api" | Updated 2026-05-02T02:00:00Z_
<!-- rulerepo:rules:end -->
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RULEREPO_SERVER_URL` | `http://localhost:8000` | Default server URL (overridden by `--server`) |

## Integration

### Git Pre-Push Hook

Add to `.git/hooks/pre-push`:

```bash
#!/bin/sh
rulerepo-context update --file ./CLAUDE.md 2>/dev/null
git add CLAUDE.md 2>/dev/null
```

### CI Pipeline

```yaml
- name: Update CLAUDE.md rules
  run: |
    rulerepo-context update --file ./CLAUDE.md --server $RULEREPO_SERVER_URL
    git diff --quiet CLAUDE.md || git commit -m "chore: update rules section" CLAUDE.md
```
