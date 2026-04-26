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


@click.command()
@click.argument("mode", type=click.Choice(["preflight", "posthoc"]))
@click.option("--file", "file_path", help="File being edited")
@click.option("--diff", help="Diff of changes (for posthoc)")
@click.option("--format", "output_format", default="instructions")
@click.option(
    "--server-url",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
)
def main(
    mode: str,
    file_path: str | None,
    diff: str | None,
    output_format: str,
    server_url: str,
) -> None:
    """Hook for coding agent integration (preflight or posthoc)."""
    if mode == "preflight":
        # Get applicable rules for this file
        body: dict = {"file_paths": [file_path] if file_path else []}
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
        body = {
            "diff": diff,
            "mode": "posthoc",
        }
        if file_path:
            body["files"] = [{"path": file_path}]

        try:
            resp = httpx.post(f"{server_url}/api/v1/evaluate", json=body, timeout=30)
            if resp.status_code == 200:
                result = resp.json()
                verdict = result.get("overall_verdict", "ALLOW")
                if verdict != "ALLOW":
                    click.echo(f"\nRule Repository: {verdict}")
                    if result.get("fix_summary"):
                        click.echo(result["fix_summary"])
        except httpx.HTTPError:
            pass


if __name__ == "__main__":
    main()
