"""Parse unified diffs into structured FileChange objects.

Per CLAUDE_ENHANCE.md §1.4: simple state machine, no external dependency.
Unified diff format is well-defined — ~50 lines of parsing logic.
"""

from __future__ import annotations

import re

from rulerepo_server.domain.evaluation import FileChange

# File extension → language mapping (simple, no library)
_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".sh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
}

# Patterns for detecting function/class definitions in diff context
_FUNC_PATTERNS = [
    re.compile(r"^\s*(?:async\s+)?def\s+(\w+)"),  # Python
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)"),  # JS/TS
    re.compile(r"^\s*func\s+(\w+)"),  # Go
    re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)"),  # Rust
    re.compile(r"^\s*class\s+(\w+)"),  # Python/Java/TS
]


def detect_language(file_path: str) -> str | None:
    """Infer language from file extension.

    Args:
        file_path: Path to the file.

    Returns:
        Language name or None if unknown.
    """
    for ext, lang in _LANG_MAP.items():
        if file_path.endswith(ext):
            return lang
    return None


def detect_functions(diff_text: str) -> list[str]:
    """Best-effort extraction of function/class names from diff text.

    Looks for def/function/class declarations in diff context and added lines.

    Args:
        diff_text: A single file's diff hunks concatenated.

    Returns:
        List of detected function/class names.
    """
    functions: list[str] = []
    for line in diff_text.splitlines():
        stripped = line.lstrip("+").lstrip(" ")
        for pattern in _FUNC_PATTERNS:
            m = pattern.match(stripped)
            if m:
                name = m.group(1)
                if name not in functions:
                    functions.append(name)
    return functions


def parse_unified_diff(diff_text: str) -> list[FileChange]:
    """Parse a unified diff into structured FileChange objects.

    Handles standard unified diff format (git diff output).

    Args:
        diff_text: Full unified diff text (may contain multiple files).

    Returns:
        List of FileChange objects, one per file.
    """
    if not diff_text or not diff_text.strip():
        return []

    files: list[FileChange] = []
    current_path: str | None = None
    current_hunks: list[str] = []
    current_hunk_lines: list[str] = []
    change_type = "modified"

    for line in diff_text.splitlines():
        # New file header
        if line.startswith("diff --git"):
            # Save previous file
            if current_path is not None:
                if current_hunk_lines:
                    current_hunks.append("\n".join(current_hunk_lines))
                all_hunks = "\n".join(current_hunks)
                files.append(
                    FileChange(
                        path=current_path,
                        change_type=change_type,
                        language=detect_language(current_path),
                        diff_hunks=current_hunks[:],
                        functions_touched=detect_functions(all_hunks),
                    )
                )
            # Reset for new file
            current_hunks = []
            current_hunk_lines = []
            change_type = "modified"
            # Extract path from "diff --git a/path b/path"
            parts = line.split(" b/", 1)
            current_path = parts[1] if len(parts) > 1 else None

        elif line.startswith("new file"):
            change_type = "added"
        elif line.startswith("deleted file"):
            change_type = "deleted"
        elif line.startswith("rename from"):
            change_type = "renamed"
        elif line.startswith("--- ") or line.startswith("+++ "):
            # File path headers — extract path if we didn't get it from diff --git
            if current_path is None and line.startswith("+++ b/"):
                current_path = line[6:]
        elif line.startswith("@@"):
            # New hunk — save previous hunk
            if current_hunk_lines:
                current_hunks.append("\n".join(current_hunk_lines))
                current_hunk_lines = []
            current_hunk_lines.append(line)
        elif current_path is not None:
            current_hunk_lines.append(line)

    # Save final file
    if current_path is not None:
        if current_hunk_lines:
            current_hunks.append("\n".join(current_hunk_lines))
        all_hunks = "\n".join(current_hunks)
        files.append(
            FileChange(
                path=current_path,
                change_type=change_type,
                language=detect_language(current_path),
                diff_hunks=current_hunks[:],
                functions_touched=detect_functions(all_hunks),
            )
        )

    return files
