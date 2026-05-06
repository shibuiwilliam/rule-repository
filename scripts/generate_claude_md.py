#!/usr/bin/env python3
"""Generate a CLAUDE.md rules section from the Rule Repository.

Fetches rules for a given scope/repo and formats them as a CLAUDE.md-compatible
markdown block that can be appended to a project's CLAUDE.md file.

Usage:
    uv run python scripts/generate_claude_md.py \\
        --scope engineering/python \\
        --repo payments-api \\
        --output ./CLAUDE_RULES.md

    # Then append to your CLAUDE.md:
    cat CLAUDE_RULES.md >> /path/to/project/CLAUDE.md
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "server", "src"))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a CLAUDE.md rules section from the Rule Repository")
    parser.add_argument("--scope", help="Rule scope filter (e.g., engineering/python)")
    parser.add_argument("--repo", help="Repository identifier")
    parser.add_argument("--format", default="instructions", choices=["instructions", "checklist", "detailed"])
    parser.add_argument("--max-rules", type=int, default=30)
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--server-url", default=os.environ.get("RULEREPO_SERVER_URL", "http://localhost:8000"))
    args = parser.parse_args()

    import httpx

    async with httpx.AsyncClient(base_url=args.server_url, timeout=30) as client:
        # Check server health
        try:
            resp = await client.get("/healthz")
            if resp.status_code != 200:
                print(f"Server not healthy: {resp.status_code}", file=sys.stderr)
                sys.exit(1)
        except httpx.ConnectError:
            print(f"Cannot connect to server at {args.server_url}", file=sys.stderr)
            sys.exit(1)

        # Fetch rules
        params: dict = {"page": 1, "page_size": args.max_rules}
        resp = await client.get("/api/v1/rules", params=params)
        if resp.status_code != 200:
            print(f"Failed to fetch rules: {resp.status_code}", file=sys.stderr)
            sys.exit(1)

        data = resp.json()
        rules = data.get("items", [])

        if not rules:
            print("No rules found.", file=sys.stderr)
            sys.exit(0)

        # Filter by scope if specified
        if args.scope:
            rules = [r for r in rules if any(args.scope.lower() in s.lower() for s in (r.get("scope") or []))]

    # Format using the formatter
    from rulerepo_server.services.context_delivery.formatter import format_rules

    label = args.scope or args.repo or "all rules"
    output = format_rules(
        rules,
        format_type=args.format,
        context_label=label,
    )

    # Add header
    header = f"""\
# Rules from Rule Repository
# Generated from: {args.server_url}
# Scope: {args.scope or "all"}
# Repository: {args.repo or "all"}
# Rules: {len(rules)}
#
# Append this to your CLAUDE.md to give coding agents access to organizational rules.
# Regenerate when rules change: uv run python scripts/generate_claude_md.py

"""
    content = header + output + "\n"

    if args.output:
        with open(args.output, "w") as f:
            f.write(content)
        print(f"Written {len(rules)} rules to {args.output}")
    else:
        print(content)


if __name__ == "__main__":
    asyncio.run(main())
