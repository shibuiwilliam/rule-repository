"""rulerepo — unified CLI for the Rule Repository.

Consolidates all CLI tools under a single entry point:

    rulerepo check ...     (was rulerepo-check)
    rulerepo hook ...      (was rulerepo-hook)
    rulerepo ingest ...    (was rulerepo-ingest)
    rulerepo export ...    (was rulerepo-export)
    rulerepo context ...   (was rulerepo-context)
    rulerepo init          (new — Tier 1)
    rulerepo doctor        (new — Tier 1)
    rulerepo audit verify  (new — Tier 1)

The old entry points (rulerepo-check, etc.) remain as console_scripts
with deprecation warnings for one release cycle.
"""

from __future__ import annotations

import click

from rulerepo_cli.check import main as check_cmd
from rulerepo_cli.check_action import main as check_action_cmd
from rulerepo_cli.export import main as export_cmd
from rulerepo_cli.hook import main as hook_cmd
from rulerepo_cli.ingest import main as ingest_cmd
from rulerepo_cli.review_contract import main as review_contract_cmd


@click.group()
@click.version_option(version="0.1.0", prog_name="rulerepo")
def cli() -> None:
    """Rule Repository CLI — manage, evaluate, and enforce organizational rules."""


# --- Register existing commands ---

cli.add_command(check_cmd, name="check")
cli.add_command(hook_cmd, name="hook")
cli.add_command(ingest_cmd, name="ingest")
cli.add_command(export_cmd, name="export")
cli.add_command(review_contract_cmd, name="review-contract")
cli.add_command(check_action_cmd, name="check-action")


# --- Context subcommand (wraps argparse-based module) ---


@cli.group()
def context() -> None:
    """Generate and manage CLAUDE.md rules sections."""


@context.command()
@click.option(
    "--server",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
    help="Rule Repository server URL",
)
@click.option("--project", default=None, help="Project ID to filter")
@click.option("--max-rules", type=int, default=50, help="Maximum rules to include")
def generate(server: str, project: str | None, max_rules: int) -> None:
    """Print rules section to stdout."""
    import sys

    import httpx

    from rulerepo_cli.context import fetch_rules_section

    try:
        section = fetch_rules_section(server, project, max_rules)
        click.echo(section)
    except httpx.HTTPError as exc:
        click.echo(f"Error fetching rules: {exc}", err=True)
        sys.exit(1)


@context.command()
@click.option("--file", "file_path", default="CLAUDE.md", help="Path to CLAUDE.md")
@click.option(
    "--server",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
    help="Rule Repository server URL",
)
@click.option("--project", default=None, help="Project ID to filter")
def update(file_path: str, server: str, project: str | None) -> None:
    """Update a CLAUDE.md file in-place."""
    import sys

    import httpx

    from rulerepo_cli.context import fetch_rules_section, update_file

    try:
        section = fetch_rules_section(server, project)
        update_file(file_path, section)
        click.echo(f"Updated {file_path}")
    except httpx.HTTPError as exc:
        click.echo(f"Error fetching rules: {exc}", err=True)
        sys.exit(1)


@context.command()
@click.option("--file", "file_path", default="CLAUDE.md", help="Path to CLAUDE.md")
@click.option(
    "--server",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
    help="Rule Repository server URL",
)
@click.option("--project", default=None, help="Project ID to filter")
@click.option("--interval", type=int, default=60, help="Poll interval in seconds")
def watch(file_path: str, server: str, project: str | None, interval: int) -> None:
    """Watch and re-generate rules section periodically."""
    import time

    from rulerepo_cli.context import fetch_rules_section, update_file

    click.echo(f"Watching {file_path} (poll every {interval}s, Ctrl+C to stop)")
    while True:
        try:
            section = fetch_rules_section(server, project)
            update_file(file_path, section)
            rule_count = section.count("\n- ")
            click.echo(f"  Updated ({rule_count} rules)")
        except Exception as exc:
            click.echo(f"  Error: {exc}", err=True)
        time.sleep(interval)


# --- New stub commands (Tier 1) ---


@cli.command()
@click.option(
    "--server",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
    help="Rule Repository server URL",
)
@click.option("--name", default=None, help="Project name (default: current directory name)")
@click.option("--scope", default=None, help="Default scope (e.g. engineering/python)")
def init(server: str, name: str | None, scope: str | None) -> None:
    """Zero-config bootstrap for a new project.

    Creates a project on the server, writes a starter .rulerepo.yaml config,
    and optionally discovers rules from existing files.
    """
    import os
    from pathlib import Path

    import httpx

    project_name = name or os.path.basename(os.getcwd())
    click.echo(f"Initializing Rule Repository for project: {project_name}")

    # 1. Create project on server
    try:
        resp = httpx.post(
            f"{server}/api/v1/projects",
            json={"name": project_name, "description": "Auto-created by rulerepo init"},
            timeout=10,
        )
        if resp.status_code == 201:
            project = resp.json()
            click.echo(f"  Created project: {project['id']}")
        elif resp.status_code == 409:
            click.echo("  Project already exists on server.")
        else:
            click.echo(f"  Warning: could not create project (HTTP {resp.status_code})", err=True)
    except httpx.ConnectError:
        click.echo(f"  Warning: server not reachable at {server}. Continuing offline.", err=True)

    # 2. Write config file
    config_path = Path(".rulerepo.yaml")
    if config_path.exists():
        click.echo(f"  {config_path} already exists, skipping.")
    else:
        config_content = f"# Rule Repository configuration\nserver: {server}\nproject: {project_name}\n"
        if scope:
            config_content += f"default_scope: {scope}\n"
        config_path.write_text(config_content)
        click.echo(f"  Created {config_path}")

    # 3. Check for discoverable sources
    discoverable = []
    if Path("CLAUDE.md").exists():
        discoverable.append("CLAUDE.md")
    for p in [".ruff.toml", "pyproject.toml", ".eslintrc.json", ".eslintrc.js", "tsconfig.json"]:
        if Path(p).exists():
            discoverable.append(p)
    if discoverable:
        click.echo(f"  Discoverable sources found: {', '.join(discoverable)}")
        click.echo("  Run 'rulerepo ingest' to extract rules from these files.")
    else:
        click.echo("  No discoverable rule sources found in current directory.")

    click.echo("Done. Run 'rulerepo doctor' to validate your environment.")


@cli.command()
@click.option(
    "--server",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
    help="Rule Repository server URL",
)
def doctor(server: str) -> None:
    """Validate environment and connectivity.

    Checks server reachability, API health, and local configuration.
    """
    from pathlib import Path

    import httpx

    checks_passed = 0
    checks_failed = 0

    def check(label: str, ok: bool, detail: str = "") -> None:
        nonlocal checks_passed, checks_failed
        if ok:
            checks_passed += 1
            click.echo(f"  [OK]   {label}" + (f" ({detail})" if detail else ""))
        else:
            checks_failed += 1
            click.echo(f"  [FAIL] {label}" + (f" ({detail})" if detail else ""))

    click.echo("Running environment checks...")

    # 1. Server connectivity
    try:
        resp = httpx.get(f"{server}/api/v1/health", timeout=5)
        check("Server reachable", resp.status_code == 200, server)
    except httpx.ConnectError:
        check("Server reachable", False, f"cannot connect to {server}")
    except Exception as exc:
        check("Server reachable", False, str(exc))

    # 2. Config file
    config_exists = Path(".rulerepo.yaml").exists()
    check("Config file (.rulerepo.yaml)", config_exists)

    # 3. GEMINI_API_KEY (common requirement)
    import os

    has_key = bool(os.environ.get("GEMINI_API_KEY"))
    check("GEMINI_API_KEY set", has_key, "required for LLM features")

    # 4. Python version
    import sys

    py_ok = sys.version_info >= (3, 12)
    check("Python >= 3.12", py_ok, f"found {sys.version_info.major}.{sys.version_info.minor}")

    # 5. Check if server has any rules
    try:
        resp = httpx.get(f"{server}/api/v1/rules?page_size=1", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            total = data.get("total", 0)
            check("Rules available", total > 0, f"{total} rules in server")
        else:
            check("Rules available", False, f"HTTP {resp.status_code}")
    except Exception:
        check("Rules available", False, "server not reachable")

    click.echo(f"\n{checks_passed} passed, {checks_failed} failed")
    if checks_failed > 0:
        raise SystemExit(1)


@cli.group()
def audit() -> None:
    """Audit log inspection and chain verification."""


@audit.command()
@click.option("--since", default="7d", help="Time window (e.g. 7d, 24h)")
@click.option(
    "--server",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
    help="Rule Repository server URL",
)
def verify(since: str, server: str) -> None:
    """Verify audit log integrity chain.

    Walks the audit log hash chain and checks that every entry's
    previous_hash matches the preceding entry's hash.
    """
    import re

    import httpx

    # Parse time window
    m = re.match(r"^(\d+)([dhm])$", since)
    if not m:
        click.echo(f"Invalid time window: {since}. Use format like 7d, 24h, 30m", err=True)
        raise SystemExit(1)

    click.echo(f"Verifying audit chain (window: {since})...")

    try:
        resp = httpx.get(f"{server}/api/v1/audit/verify?limit=10000", timeout=30)
        if resp.status_code != 200:
            click.echo(f"Error: server returned HTTP {resp.status_code}", err=True)
            raise SystemExit(2)

        result = resp.json()
        verified = result.get("verified", False)
        checked = result.get("entries_checked", 0)
        message = result.get("message", "")

        if verified:
            click.echo(f"  Chain OK: {checked} entries verified")
            click.echo(f"  {message}")
        else:
            broken_id = result.get("first_broken_entry_id", "unknown")
            click.echo(f"  CHAIN BROKEN at entry: {broken_id}", err=True)
            click.echo(f"  {message}", err=True)
            click.echo(f"  Entries checked before failure: {checked}")
            raise SystemExit(1)
    except httpx.ConnectError:
        click.echo(f"Error: cannot connect to {server}", err=True)
        raise SystemExit(3) from None


cli.add_command(audit)


# --- MCP subcommand (stub, for parity with CLAUDE.md §5) ---


@cli.command()
def mcp() -> None:
    """Start the MCP server."""
    click.echo("rulerepo mcp: MCP server (coming soon)")


def main() -> None:
    """Entry point for the unified CLI."""
    cli()


if __name__ == "__main__":
    main()
