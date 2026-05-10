"""rulerepo-hook — agent hook integration for preflight/posthoc rule checks.

Per CLAUDE_ENHANCE.md §3.5: lightweight wrapper for coding agent integration.
- preflight: Before the agent edits a file, inject applicable rules
- posthoc: After the agent edits a file, evaluate the change

Usage in Claude Code .claude/settings.json:
    {
      "hooks": {
        "PreToolUse": [{
          "matcher": "Edit|Write",
          "command": "rulerepo-hook preflight --file \"$TOOL_INPUT_FILE_PATH\""
        }]
      }
    }
"""

from __future__ import annotations

import click
import httpx


@click.group(invoke_without_command=True)
@click.argument("mode", type=click.Choice(["preflight", "posthoc"]), required=False)
@click.option("--file", "file_path", help="File being edited")
@click.option("--diff", help="Diff of changes (for posthoc)")
@click.option("--format", "output_format", default="instructions")
@click.option("--prompt", "prompt_text", default=None, help="Agent prompt context (for preflight)")
@click.option(
    "--server-url",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
)
@click.option(
    "--agent-id",
    envvar="RULEREPO_AGENT_ID",
    default=None,
    help="Agent identifier (e.g., 'claude-code', 'cursor')",
)
@click.pass_context
def main(
    ctx: click.Context,
    mode: str | None,
    file_path: str | None,
    diff: str | None,
    output_format: str,
    prompt_text: str | None,
    server_url: str,
    agent_id: str | None,
) -> None:
    """Hook for coding agent integration (preflight or posthoc)."""
    if ctx.invoked_subcommand is not None:
        return

    if mode is None:
        click.echo(ctx.get_help())
        return

    if mode == "preflight":
        # Get applicable rules for this file
        body: dict = {"file_paths": [file_path] if file_path else []}
        if prompt_text:
            body["intent"] = prompt_text
        try:
            resp = httpx.post(
                f"{server_url}/api/v1/evaluate/applicable-rules",
                json=body,
                timeout=15,
            )
            if resp.status_code == 200:
                rules = resp.json()
                if rules:
                    click.echo(f"\n## Rules for {file_path or 'your files'}")
                    for r in rules:
                        mod = r.get("modality", "")
                        prefix = "MUST" if mod in ("MUST", "MUST_NOT") else mod
                        click.echo(f"  [{prefix}] {r.get('statement', '')}")
        except httpx.HTTPError:
            pass  # Don't block the agent on hook failure

    elif mode == "posthoc":
        if not diff:
            return
        body_post: dict = {
            "diff": diff,
            "mode": "posthoc",
        }
        if file_path:
            body_post["files"] = [{"path": file_path}]
        if agent_id:
            body_post["agent_id"] = agent_id

        try:
            resp = httpx.post(f"{server_url}/api/v1/evaluate", json=body_post, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                verdict = result.get("overall_verdict", "ALLOW")
                if verdict != "ALLOW":
                    click.echo(f"\nRule Repository: {verdict}")
                    if result.get("fix_summary"):
                        click.echo(result["fix_summary"])
        except httpx.HTTPError:
            pass


@main.command()
@click.option(
    "--server-url",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
)
@click.option(
    "--agent-id",
    envvar="RULEREPO_AGENT_ID",
    default="claude-code",
)
def install(server_url: str, agent_id: str) -> None:
    """Install hooks into .claude/settings.json for Claude Code integration.

    Writes PreToolUse and PostToolUse hooks that invoke rulerepo-hook
    for preflight and posthoc rule checks respectively.
    """
    import json
    from pathlib import Path

    settings_dir = Path(".claude")
    settings_dir.mkdir(exist_ok=True)
    settings_path = settings_dir / "settings.json"

    hooks_config = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write|MultiEdit",
                    "command": f'rulerepo-hook preflight --file "$TOOL_INPUT_FILE_PATH" --server-url {server_url}',
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Edit|Write|MultiEdit",
                    "command": (
                        f'rulerepo-hook posthoc --file "$TOOL_INPUT_FILE_PATH" '
                        f'--diff "$(git diff HEAD)" --agent-id {agent_id} '
                        f"--server-url {server_url}"
                    ),
                }
            ],
        }
    }

    if settings_path.exists():
        existing = json.loads(settings_path.read_text())
        existing.setdefault("hooks", {})
        existing["hooks"].update(hooks_config["hooks"])
        settings_path.write_text(json.dumps(existing, indent=2) + "\n")
        click.echo(f"Updated {settings_path} with rulerepo hooks.")
    else:
        settings_path.write_text(json.dumps(hooks_config, indent=2) + "\n")
        click.echo(f"Created {settings_path} with rulerepo hooks.")

    click.echo("Hooks installed. Restart your Claude Code session to activate.")


if __name__ == "__main__":
    main()
