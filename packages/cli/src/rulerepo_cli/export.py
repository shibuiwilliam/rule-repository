"""rulerepo-export — export rules from the server to rules.yaml format.

Per PROJECT_IMPROVEMENT.md §3.4: bi-directional sync between server
and local rules.yaml files.
"""

from __future__ import annotations

import click
import httpx

from rulerepo_cli.rules_yaml import RuleEntry, RulesYaml, save_rules_yaml


@click.command()
@click.option(
    "--server-url",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
    help="Rule Repository server URL",
)
@click.option("--project-id", help="Project ID to export")
@click.option("--scope", help="Scope filter")
@click.option("--output", "-o", default="rules.yaml", help="Output file path")
def main(server_url: str, project_id: str | None, scope: str | None, output: str) -> None:
    """Export rules from the Rule Repository server to a rules.yaml file."""
    params: dict[str, str] = {"page_size": "200"}
    if project_id:
        params["project_id"] = project_id

    try:
        resp = httpx.get(f"{server_url}/api/v1/rules", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as exc:
        click.echo(f"Failed to fetch rules: {exc}", err=True)
        raise SystemExit(1) from exc

    items = data.get("items", [])

    # Filter by scope if provided
    if scope:
        items = [r for r in items if scope in (r.get("scope") or [])]

    rules = [
        RuleEntry(
            id=r["id"],
            statement=r["statement"],
            modality=r.get("modality", "MUST"),
            severity=r.get("severity", "MEDIUM"),
            scope=r.get("scope", []),
            tags=r.get("tags", []),
            rationale=r.get("rationale", ""),
        )
        for r in items
    ]

    rules_yaml = RulesYaml(
        version=1,
        project=project_id or "",
        rules=rules,
    )

    save_rules_yaml(rules_yaml, output)
    click.echo(f"Exported {len(rules)} rules to {output}")
