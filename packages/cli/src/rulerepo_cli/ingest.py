"""rulerepo-ingest — import rules from external sources (CLAUDE.md, etc.).

Per CLAUDE_ENHANCE.md §3.6: uploads a CLAUDE.md as a document, triggers
extraction, and shows the user how to review candidates.

Usage:
    rulerepo-ingest --source claude-md --file ./CLAUDE.md --scope engineering/python
"""

from __future__ import annotations

import click
import httpx


@click.command()
@click.option(
    "--source",
    type=click.Choice(["claude-md"]),
    required=True,
    help="Source type",
)
@click.option("--file", "file_path", required=True, help="File to ingest")
@click.option("--scope", required=True, help="Rule scope to assign to extracted rules")
@click.option(
    "--server-url",
    envvar="RULEREPO_SERVER_URL",
    default="http://localhost:8000",
)
def main(source: str, file_path: str, scope: str, server_url: str) -> None:
    """Import rules from external sources into the Rule Repository."""
    if source == "claude-md":
        _ingest_claude_md(file_path, scope, server_url)


def _ingest_claude_md(file_path: str, scope: str, server_url: str) -> None:
    """Upload a CLAUDE.md and trigger extraction."""
    click.echo(f"Uploading {file_path}...")

    with open(file_path, "rb") as f:
        resp = httpx.post(
            f"{server_url}/api/v1/documents/upload",
            files={"file": (file_path, f, "text/markdown")},
            timeout=30,
        )

    if resp.status_code not in (200, 201):
        click.echo(f"Upload failed: {resp.status_code}", err=True)
        raise SystemExit(1)

    doc_data = resp.json()
    doc_id = doc_data.get("document_id", "")
    click.echo(f"Uploaded: {doc_id}")

    # Trigger extraction
    click.echo("Extracting rules...")
    resp = httpx.post(
        f"{server_url}/api/v1/documents/{doc_id}/extract",
        timeout=120,
    )

    if resp.status_code not in (200, 201):
        click.echo(f"Extraction failed: {resp.status_code}", err=True)
        raise SystemExit(1)

    result = resp.json()
    candidates = result.get("candidates", [])
    click.echo(f"Extracted {len(candidates)} candidate rules from {file_path}")

    if candidates:
        click.echo("\nCandidate rules:")
        for c in candidates[:10]:
            modality = c.get("modality", "?")
            stmt = c.get("statement", "")[:80]
            conf = c.get("confidence", 0)
            click.echo(f"  [{modality}] {stmt}... (confidence: {conf:.0%})")

        if len(candidates) > 10:
            click.echo(f"  ... and {len(candidates) - 10} more")

    frontend_url = server_url.replace("localhost:8000", "localhost:3000")
    click.echo(f"\nReview and approve at: {frontend_url}/documents")


if __name__ == "__main__":
    main()
