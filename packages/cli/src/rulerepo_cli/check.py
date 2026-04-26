"""rulerepo-check — CI pipeline integration for code compliance checking.

Per CLAUDE_ENHANCE.md §3.4: checks code changes against organizational rules.
Exit code 0 = ALLOW, 1 = DENY, 2 = NEEDS_CONFIRMATION.

Usage:
    rulerepo-check --diff "$(git diff origin/main...HEAD)" --scope engineering/python
    rulerepo-check --diff-cmd "git diff origin/main...HEAD" --format github-actions
"""

from __future__ import annotations

import subprocess

import click
import httpx


@click.command()
@click.option("--diff", help="Unified diff text")
@click.option(
    "--diff-cmd",
    default="git diff origin/main...HEAD",
    help="Command to generate diff",
)
@click.option("--scope", help="Rule scope filter")
@click.option("--repository", help="Repository identifier")
@click.option(
    "--server-url",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
)
@click.option("--fail-on-deny/--no-fail-on-deny", default=True)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "github-actions"]),
    default="text",
)
def main(
    diff: str | None,
    diff_cmd: str,
    scope: str | None,
    repository: str | None,
    server_url: str,
    fail_on_deny: bool,
    output_format: str,
) -> None:
    """Check code changes against organizational rules."""
    if diff is None:
        try:
            diff = subprocess.check_output(diff_cmd, shell=True, text=True)
        except subprocess.CalledProcessError:
            click.echo("Failed to generate diff", err=True)
            raise SystemExit(2)

    if not diff.strip():
        click.echo("No changes to evaluate.")
        return

    body: dict = {"diff": diff, "mode": "posthoc"}
    if scope:
        body["scope"] = scope
    if repository:
        body["repository"] = repository

    try:
        resp = httpx.post(f"{server_url}/api/v1/evaluate", json=body, timeout=60)
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPError as exc:
        click.echo(f"Evaluation failed: {exc}", err=True)
        raise SystemExit(2)

    # Format output
    match output_format:
        case "json":
            import json

            click.echo(json.dumps(result, indent=2, default=str))
        case "github-actions":
            for v in result.get("violations", []):
                locs = v.get("locations", [])
                if locs:
                    loc = locs[0]
                    fp = loc.get("file_path", "")
                    ln = loc.get("start_line", "")
                    msg = v.get("issue_description", "")
                    click.echo(f"::error file={fp},line={ln}::{msg}")
                else:
                    click.echo(f"::error::{v.get('issue_description', '')}")
            for w in result.get("warnings", []):
                click.echo(f"::warning::{w.get('issue_description', '')}")
        case _:
            verdict = result.get("overall_verdict", "?")
            click.echo(f"Rule Repository: {verdict}")
            click.echo(f"Rules evaluated: {result.get('rules_evaluated', 0)}")
            if result.get("fix_summary"):
                click.echo(f"\n{result['fix_summary']}")

    # Exit code
    verdict = result.get("overall_verdict", "ALLOW")
    if fail_on_deny and verdict == "DENY":
        raise SystemExit(1)
    if verdict == "NEEDS_CONFIRMATION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
