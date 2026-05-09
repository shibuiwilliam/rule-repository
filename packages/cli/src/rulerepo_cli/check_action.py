"""rulerepo-check-action — evaluate a human action against organizational rules.

Sends a business action (overtime registration, leave request, etc.) to the
Rule Repository server for compliance evaluation using the Human Action Surface.

Usage:
    rulerepo-check-action --action register_overtime --actor user:E001 --json '{"hours":50}'
    rulerepo-check-action --action submit_leave --actor user:E002 --json '{"days":5}' --format json
"""

from __future__ import annotations

import json as json_module
from typing import Any

import click
import httpx


@click.command()
@click.option(
    "--action",
    required=True,
    help="Action identifier (e.g., register_overtime, submit_leave_request)",
)
@click.option(
    "--actor",
    required=True,
    help="Actor identifier (e.g., user:E001, system:ci)",
)
@click.option(
    "--json",
    "facts_json",
    default="{}",
    help="JSON string with action facts (e.g., '{\"hours\":50}')",
)
@click.option("--scope", help="Rule scope filter (e.g., hr/overtime)")
@click.option(
    "--server-url",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
@click.option("--fail-on-deny/--no-fail-on-deny", default=False)
def main(
    action: str,
    actor: str,
    facts_json: str,
    scope: str | None,
    server_url: str,
    output_format: str,
    fail_on_deny: bool,
) -> None:
    """Check a human action against organizational rules."""
    try:
        facts: dict[str, Any] = json_module.loads(facts_json)
    except json_module.JSONDecodeError as exc:
        click.echo(f"Invalid JSON for --json: {exc}", err=True)
        raise SystemExit(2) from exc

    # Determine actor kind from prefix
    actor_kind = "human"
    actor_id = actor
    if ":" in actor:
        prefix, actor_id = actor.split(":", 1)
        if prefix in ("agent", "system"):
            actor_kind = prefix

    body: dict[str, Any] = {
        "subject": {
            "surface": "human_action",
            "identifier": f"action:{action}/{actor}",
            "payload": {
                "action": action,
                "actor_id": actor_id,
                "actor_kind": actor_kind,
                "facts": facts,
            },
            "facts": facts,
            "timestamp": None,
            "locale": "en",
        },
        "mode": "posthoc",
    }
    if scope:
        body["scope"] = scope

    try:
        resp = httpx.post(
            f"{server_url}/api/v1/evaluate/human_action",
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPError as exc:
        click.echo(f"Action check failed: {exc}", err=True)
        raise SystemExit(2) from exc

    match output_format:
        case "json":
            click.echo(json_module.dumps(result, indent=2, default=str))
        case _:
            verdict = result.get("overall_verdict", "?")
            click.echo(f"Action Check: {verdict}")
            click.echo(f"Action: {action} | Actor: {actor} | Rules evaluated: {result.get('rules_evaluated', 0)}")
            violations = result.get("violations", [])
            warnings = result.get("warnings", [])
            if violations:
                click.echo(f"\nViolations ({len(violations)}):")
                for v in violations:
                    click.echo(f"  - {v.get('issue_description', '')}")
            if warnings:
                click.echo(f"\nWarnings ({len(warnings)}):")
                for w in warnings:
                    click.echo(f"  - {w.get('issue_description', '')}")
            if result.get("fix_summary"):
                click.echo(f"\n{result['fix_summary']}")

    verdict = result.get("overall_verdict", "ALLOW")
    if fail_on_deny and verdict == "DENY":
        raise SystemExit(1)
    if verdict == "NEEDS_CONFIRMATION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
