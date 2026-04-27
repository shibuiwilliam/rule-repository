"""GitHub Repository Importer — fetches repo files for rule discovery.

Per PROJECT_IMPROVEMENT.md Proposal 1: one-click GitHub import that fetches
CLAUDE.md, linter configs, and key code files from a repository, then feeds
them into the existing discovery analyzers.
"""

from __future__ import annotations

import re

import httpx

from rulerepo_server.core.config import get_settings
from rulerepo_server.core.logging import get_logger

logger = get_logger(__name__)

# Files to attempt fetching from a repository
INTERESTING_FILES = [
    "CLAUDE.md",
    ".claude/settings.json",
    "pyproject.toml",
    "package.json",
    ".eslintrc.json",
    ".eslintrc.js",
    "eslint.config.mjs",
    "eslint.config.js",
    "tsconfig.json",
    "ruff.toml",
    ".prettierrc",
    ".prettierrc.json",
    "biome.json",
    ".github/CODEOWNERS",
]


def _parse_repo(github_url: str) -> str:
    """Parse owner/repo from various GitHub URL formats.

    Accepts: "org/repo", "https://github.com/org/repo", "github.com/org/repo"
    """
    # Strip protocol and domain
    url = github_url.strip().rstrip("/")
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^github\.com/", "", url)
    # Remove .git suffix
    url = re.sub(r"\.git$", "", url)
    return url


class GitHubImporter:
    """Imports repository contents via GitHub API for rule discovery.

    Uses the GitHub Contents API to fetch specific files without cloning.
    """

    def __init__(self, token: str | None = None) -> None:
        settings = get_settings()
        self._token = token or getattr(settings, "github_token", "") or ""

    async def import_repository(
        self,
        github_url: str,
        branch: str = "main",
    ) -> dict[str, str]:
        """Fetch interesting files from a GitHub repository.

        Args:
            github_url: Repository in "org/repo" or full URL format.
            branch: Branch to fetch from (default: main).

        Returns:
            Dictionary of {filename: content} for successfully fetched files.
        """
        repo = _parse_repo(github_url)
        logger.info("github_import_start", repo=repo, branch=branch)

        headers: dict[str, str] = {"Accept": "application/vnd.github.v3.raw"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        file_contents: dict[str, str] = {}

        async with httpx.AsyncClient(timeout=30) as client:
            for file_path in INTERESTING_FILES:
                url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
                try:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code == 200:
                        file_contents[file_path] = resp.text
                        logger.debug("github_file_fetched", file=file_path)
                    # 404 = file doesn't exist, skip silently
                except Exception as exc:
                    logger.debug("github_file_fetch_error", file=file_path, error=str(exc))

        logger.info(
            "github_import_complete",
            repo=repo,
            files_fetched=len(file_contents),
        )
        return file_contents
