"""Generate and update a Rules section in CLAUDE.md files.

Maintains a rules section between HTML comment markers in any CLAUDE.md,
enabling automatic rule delivery to every AI coding agent that reads it.

Usage:
    rulerepo-context generate --server http://localhost:8000
    rulerepo-context update --file ./CLAUDE.md --server http://localhost:8000
    rulerepo-context watch --file ./CLAUDE.md --server http://localhost:8000
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

START_MARKER = "<!-- rulerepo:rules:start -->"
END_MARKER = "<!-- rulerepo:rules:end -->"

MODALITY_ORDER = ["MUST", "MUST_NOT", "SHOULD", "MAY", "INFO"]
MODALITY_LABELS = {
    "MUST": "MUST",
    "MUST_NOT": "Never",
    "SHOULD": "SHOULD",
    "MAY": "MAY",
    "INFO": "INFO",
}


def fetch_rules_section(
    server_url: str,
    project: str | None = None,
    max_rules: int = 50,
) -> str:
    """Fetch active rules from the server and format as a CLAUDE.md section.

    Args:
        server_url: Base URL of the Rule Repository server.
        project: Optional project ID to filter rules.
        max_rules: Maximum number of rules to include.

    Returns:
        Formatted markdown section with start/end markers.
    """
    params: dict[str, str | int] = {"page_size": max_rules}
    if project:
        params["project_id"] = project

    resp = httpx.get(
        f"{server_url.rstrip('/')}/api/v1/rules",
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    rules = data.get("items", [])
    if not rules:
        return _wrap_section("_No active rules found._", 0, project)

    # Group by modality
    groups: dict[str, list[str]] = {m: [] for m in MODALITY_ORDER}
    for r in rules:
        mod = r.get("modality", "MUST")
        sev = r.get("severity", "MEDIUM")
        stmt = r.get("statement", "").strip()
        if mod in groups:
            groups[mod].append(f"- {stmt} [{sev}]")
        else:
            groups.setdefault(mod, []).append(f"- {stmt} [{sev}]")

    lines: list[str] = []
    for mod in MODALITY_ORDER:
        items = groups.get(mod, [])
        if items:
            label = MODALITY_LABELS.get(mod, mod)
            lines.append(f"\n### {label}\n")
            lines.extend(items)

    body = "\n".join(lines)
    return _wrap_section(body, len(rules), project)


def _wrap_section(body: str, count: int, project: str | None) -> str:
    """Wrap the rules body with markers and metadata footer."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    proj_label = f' from project "{project}"' if project else ""
    return (
        f"{START_MARKER}\n"
        f"## Rules (auto-managed by Rule Repository)\n"
        f"{body}\n\n"
        f"_{count} rules{proj_label} | Updated {now}_\n"
        f"{END_MARKER}"
    )


def update_file(file_path: str, section: str) -> None:
    """Update a file in-place, replacing only the rules section.

    If markers exist, replaces the content between them.
    If no markers exist, appends the section at the end.
    Creates the file if it doesn't exist.

    Args:
        file_path: Path to the file to update.
        section: The complete rules section with markers.
    """
    path = Path(file_path)
    if path.exists():
        content = path.read_text()
        start_idx = content.find(START_MARKER)
        end_idx = content.find(END_MARKER)
        if start_idx != -1 and end_idx != -1:
            # Replace existing section
            content = content[:start_idx] + section + content[end_idx + len(END_MARKER) :]
        else:
            # Append section at the end
            content = content.rstrip() + "\n\n" + section + "\n"
    else:
        content = section + "\n"

    path.write_text(content)


def main() -> None:
    """CLI entry point for rulerepo-context."""
    parser = argparse.ArgumentParser(
        description="Manage a Rules section in CLAUDE.md files",
        prog="rulerepo-context",
    )
    sub = parser.add_subparsers(dest="command")

    # generate
    gen = sub.add_parser("generate", help="Print rules section to stdout")
    gen.add_argument(
        "--server",
        default=os.environ.get("RULEREPO_SERVER_URL", "http://localhost:8000"),
        help="Rule Repository server URL",
    )
    gen.add_argument("--project", default=None, help="Project ID to filter")
    gen.add_argument("--max-rules", type=int, default=50)

    # update
    upd = sub.add_parser("update", help="Update a CLAUDE.md file in-place")
    upd.add_argument("--file", default="CLAUDE.md", help="Path to CLAUDE.md")
    upd.add_argument(
        "--server",
        default=os.environ.get("RULEREPO_SERVER_URL", "http://localhost:8000"),
    )
    upd.add_argument("--project", default=None)

    # watch
    watch = sub.add_parser("watch", help="Watch and re-generate periodically")
    watch.add_argument("--file", default="CLAUDE.md")
    watch.add_argument(
        "--server",
        default=os.environ.get("RULEREPO_SERVER_URL", "http://localhost:8000"),
    )
    watch.add_argument("--project", default=None)
    watch.add_argument("--interval", type=int, default=60, help="Poll interval in seconds")

    args = parser.parse_args()

    if args.command == "generate":
        try:
            section = fetch_rules_section(args.server, args.project, args.max_rules)
            print(section)  # noqa: T201
        except httpx.HTTPError as exc:
            print(f"Error fetching rules: {exc}", file=sys.stderr)  # noqa: T201
            sys.exit(1)

    elif args.command == "update":
        try:
            section = fetch_rules_section(args.server, args.project)
            update_file(args.file, section)
            print(f"Updated {args.file}")  # noqa: T201
        except httpx.HTTPError as exc:
            print(f"Error fetching rules: {exc}", file=sys.stderr)  # noqa: T201
            sys.exit(1)

    elif args.command == "watch":
        print(f"Watching {args.file} (poll every {args.interval}s, Ctrl+C to stop)")  # noqa: T201
        while True:
            try:
                section = fetch_rules_section(args.server, args.project)
                update_file(args.file, section)
                rule_count = section.count("\n- ")
                print(f"  Updated ({rule_count} rules)")  # noqa: T201
            except Exception as exc:
                print(f"  Error: {exc}", file=sys.stderr)  # noqa: T201
            time.sleep(args.interval)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
