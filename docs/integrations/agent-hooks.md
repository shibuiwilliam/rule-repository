# Agent Hooks

Agent hooks integrate the Rule Repository directly into AI coding agents, providing rules before edits and evaluating changes after edits. This guide covers configuration for Claude Code.

## Overview

The hook system uses two checkpoints:

- **Preflight** (before edit): Injects applicable rules into the agent's context so it can follow them while making changes.
- **Posthot** (after edit): Evaluates the change against rules and reports any violations.

Both hooks are non-blocking -- if the Rule Repository server is unreachable, the hooks print a warning and exit cleanly so the agent can continue working.

## Claude Code Configuration

Add the following to your Claude Code settings (`.claude/settings.json` or project-level `.claude/settings.local.json`):

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
        "command": "rulerepo-hook posthot --file \"$TOOL_INPUT_FILE_PATH\""
      }
    ]
  }
}
```

### How It Works

1. When Claude Code is about to call the `Edit` or `Write` tool, the `PreToolUse` hook fires.
2. `rulerepo-hook preflight` sends the file path to the server, which returns applicable rules.
3. The rules are printed to stdout, which Claude Code incorporates into its context.
4. Claude Code makes the edit with awareness of the rules.
5. After the edit, the `PostToolUse` hook fires.
6. `rulerepo-hook posthot` sends the file path (and optionally the diff) to the server for evaluation.
7. Any violations are printed to stdout for the agent to see and address.

### Environment

The hooks read `RULEREPO_SERVER_URL` from the environment. Set it in your shell profile or `.envrc`:

```bash
export RULEREPO_SERVER_URL=http://localhost:8000
```

## Preflight Output Example

```
Applicable rules for src/api/routes.py:
- [ENG-001] All public API functions must have type hints and Google-style docstrings.
- [ENG-003] Never raise bare Exception; use the project exception hierarchy.
- [SEC-005] API endpoints handling user input must validate with Pydantic models.
```

## Posthot Output Example

```
Evaluation of src/api/routes.py:
  NEEDS_CONFIRMATION  ENG-001  Function `create_rule` is missing a docstring.
  OK    ENG-003  No bare exceptions found.
  OK    SEC-005  Pydantic model used for request validation.
```

## Error Handling

Both hooks are designed to be **non-blocking on failure**:

- If the server is unreachable, the hook prints a warning to stderr and exits with code 0.
- If the server returns an error, the hook prints the error message to stderr and exits with code 0.
- The agent's workflow is never interrupted by hook failures.

This ensures that network issues or server downtime do not prevent the agent from completing its work.

## Using with Other Agents

The `rulerepo-hook` CLI is not specific to Claude Code. Any agent framework that supports pre/post-edit hooks or shell command execution can use it. The key requirements are:

- The hook command receives the file path being edited.
- The hook's stdout is fed back to the agent as context.
- The hook should be non-blocking (exit code 0) on failure.

## See Also

- [CLI Tools Reference](../sdks/cli.md) -- full `rulerepo-hook` options
- [MCP Server](mcp.md) -- alternative agent integration via MCP protocol
- [CI Pipeline Integration](ci.md) -- rule checking in CI (complements hooks)
