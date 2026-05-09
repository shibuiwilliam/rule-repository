"""rulerepo-review-contract — evaluate a contract document against organizational rules.

Sends the contract to the Rule Repository server for clause-by-clause compliance
review using the Contract Surface adapter.

Usage:
    rulerepo-review-contract --file ./contracts/draft.docx
    rulerepo-review-contract --file ./contracts/nda.pdf --scope legal/contract/nda --format json
    rulerepo review-contract --file ./draft.docx --output redline.html
"""

from __future__ import annotations

import json
from pathlib import Path

import click
import httpx


def _read_contract_text(file_path: Path) -> str:
    """Read contract file content as text.

    Supports .txt, .md, and .docx (via python-docx if available).
    For .pdf and .docx without python-docx, sends as binary to the server.
    """
    suffix = file_path.suffix.lower()

    if suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8")

    if suffix == ".docx":
        try:
            from docx import Document  # type: ignore[import-untyped]

            doc = Document(str(file_path))
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            click.echo(
                "python-docx not installed; sending raw text extraction. Install with: uv add python-docx",
                err=True,
            )
            return file_path.read_text(encoding="utf-8", errors="replace")

    # Fallback: read as text
    return file_path.read_text(encoding="utf-8", errors="replace")


def _render_html_redline(result: dict, output_path: Path) -> None:
    """Render evaluation result as an HTML redline report."""
    violations = result.get("violations", [])
    warnings = result.get("warnings", [])
    verdict = result.get("overall_verdict", "UNKNOWN")

    verdict_color = {"ALLOW": "#16a34a", "DENY": "#dc2626", "NEEDS_CONFIRMATION": "#d97706"}.get(verdict, "#6b7280")

    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Contract Review — Redline Report</title>",
        "<style>",
        "body { font-family: system-ui, sans-serif; max-width: 800px;"
        " margin: 2rem auto; padding: 0 1rem; color: #1f2937; }",
        "h1 { font-size: 1.5rem; }",
        ".verdict { display: inline-block; padding: 0.25rem 0.75rem;"
        " border-radius: 9999px; font-weight: 600; font-size: 0.875rem; }",
        ".stats { display: flex; gap: 2rem; margin: 1rem 0; font-size: 0.875rem; color: #6b7280; }",
        ".section { margin-top: 1.5rem; }",
        ".item { border: 1px solid #e5e7eb; border-radius: 0.75rem; padding: 1rem; margin-bottom: 0.75rem; }",
        ".item.violation { border-left: 4px solid #dc2626; }",
        ".item.warning { border-left: 4px solid #d97706; }",
        ".rule-id { font-size: 0.75rem; color: #9ca3af; }",
        ".issue { margin-top: 0.5rem; font-size: 0.875rem; }",
        ".fix { margin-top: 0.5rem; font-size: 0.875rem; color: #16a34a; }",
        "</style></head><body>",
        "<h1>Contract Review — Redline Report</h1>",
        f'<span class="verdict" style="background:{verdict_color}20;color:{verdict_color}">{verdict}</span>',
        '<div class="stats">',
        f"<span>Rules evaluated: {result.get('rules_evaluated', 0)}</span>",
        f"<span>Violations: {len(violations)}</span>",
        f"<span>Warnings: {len(warnings)}</span>",
        "</div>",
    ]

    if violations:
        html_parts.append('<div class="section"><h2>Violations</h2>')
        for v in violations:
            html_parts.append('<div class="item violation">')
            html_parts.append(f'<div class="rule-id">{v.get("rule_id", "")}</div>')
            html_parts.append(f'<div class="issue">{v.get("issue_description", "")}</div>')
            if v.get("fix_suggestion"):
                html_parts.append(f'<div class="fix">{v["fix_suggestion"]}</div>')
            html_parts.append("</div>")
        html_parts.append("</div>")

    if warnings:
        html_parts.append('<div class="section"><h2>Warnings</h2>')
        for w in warnings:
            html_parts.append('<div class="item warning">')
            html_parts.append(f'<div class="rule-id">{w.get("rule_id", "")}</div>')
            html_parts.append(f'<div class="issue">{w.get("issue_description", "")}</div>')
            html_parts.append("</div>")
        html_parts.append("</div>")

    if result.get("fix_summary"):
        html_parts.append('<div class="section"><h2>Summary</h2>')
        html_parts.append(f"<p>{result['fix_summary']}</p></div>")

    html_parts.append("</body></html>")

    output_path.write_text("\n".join(html_parts), encoding="utf-8")
    click.echo(f"Redline report written to {output_path}")


@click.command()
@click.option(
    "--file",
    "contract_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to contract file (.txt, .md, .docx, .pdf)",
)
@click.option("--scope", help="Rule scope filter (e.g. legal/contract/nda)")
@click.option("--locale", default="en", help="Contract locale (en, ja)")
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
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    help="Write HTML redline report to this file",
)
@click.option("--fail-on-deny/--no-fail-on-deny", default=False)
def main(
    contract_path: Path,
    scope: str | None,
    locale: str,
    server_url: str,
    output_format: str,
    output_path: Path | None,
    fail_on_deny: bool,
) -> None:
    """Review a contract document against organizational rules."""
    contract_text = _read_contract_text(contract_path)

    if not contract_text.strip():
        click.echo("Contract file is empty or could not be read.", err=True)
        raise SystemExit(2)

    # Build subject payload for the contract surface
    subject_payload: dict = {
        "text": contract_text,
        "document_id": str(contract_path),
        "locale": locale,
    }

    body: dict = {
        "subject": {
            "surface": "contract",
            "identifier": str(contract_path.name),
            "payload": subject_payload,
            "facts": {},
            "timestamp": None,
            "locale": locale,
        },
        "mode": "posthoc",
    }
    if scope:
        body["scope"] = scope

    try:
        resp = httpx.post(
            f"{server_url}/api/v1/evaluate/contract",
            json=body,
            timeout=120,
        )
        resp.raise_for_status()
        result = resp.json()
    except httpx.HTTPError as exc:
        click.echo(f"Contract review failed: {exc}", err=True)
        raise SystemExit(2) from exc

    # Output
    if output_path:
        _render_html_redline(result, output_path)

    match output_format:
        case "json":
            click.echo(json.dumps(result, indent=2, default=str))
        case _:
            verdict = result.get("overall_verdict", "?")
            click.echo(f"Contract Review: {verdict}")
            click.echo(f"Rules evaluated: {result.get('rules_evaluated', 0)}")
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

    # Exit code
    verdict = result.get("overall_verdict", "ALLOW")
    if fail_on_deny and verdict == "DENY":
        raise SystemExit(1)
    if verdict == "NEEDS_CONFIRMATION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
