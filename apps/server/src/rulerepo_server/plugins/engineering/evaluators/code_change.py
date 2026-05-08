"""Code change evaluator — evaluates code diffs against engineering rules.

Parses unified diffs, detects languages and file scopes, formats
context for LLM-backed rule evaluation. Delegates all LLM calls
through an injected callable -- never imports a specific LLM provider.

See: CLAUDE.md SS12.1
"""

from __future__ import annotations

import re
from collections.abc import Callable, Coroutine
from pathlib import PurePosixPath
from typing import Any

_LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".tf": "terraform",
    ".hcl": "terraform",
}

_SCOPE_MAP: dict[str, str] = {
    "python": "engineering/python",
    "typescript": "engineering/typescript",
    "javascript": "engineering/javascript",
    "go": "engineering/go",
    "rust": "engineering/rust",
    "java": "engineering/java",
    "kotlin": "engineering/kotlin",
    "ruby": "engineering/ruby",
    "sql": "engineering/database",
    "yaml": "engineering/config",
    "toml": "engineering/config",
    "json": "engineering/config",
    "terraform": "engineering/devops",
    "shell": "engineering/devops",
}

# Regex to extract file paths from unified diff headers
_DIFF_FILE_RE = re.compile(r"^(?:---|\+\+\+)\s+[ab]/(.+)$", re.MULTILINE)

# LLM callable type: takes a prompt string and returns a response string
LLMCallable = Callable[[str], Coroutine[Any, Any, str]]


def _detect_language(file_path: str) -> str | None:
    """Detect the programming language from a file extension.

    Args:
        file_path: Path to the file.

    Returns:
        Language identifier string, or None if unrecognized.
    """
    suffix = PurePosixPath(file_path).suffix.lower()
    return _LANGUAGE_EXTENSIONS.get(suffix)


def _extract_file_paths(diff: str) -> list[str]:
    """Extract file paths from unified diff headers.

    Args:
        diff: Unified diff text.

    Returns:
        Deduplicated list of file paths.
    """
    matches = _DIFF_FILE_RE.findall(diff)
    seen: set[str] = set()
    paths: list[str] = []
    for path in matches:
        if path not in seen and path != "/dev/null":
            seen.add(path)
            paths.append(path)
    return paths


def _resolve_scopes(file_paths: list[str], explicit_scopes: list[str] | None) -> list[str]:
    """Resolve evaluation scopes from file paths and explicit overrides.

    Args:
        file_paths: List of file paths from the diff.
        explicit_scopes: Explicitly provided scopes (override).

    Returns:
        Deduplicated, sorted list of scope strings.
    """
    scopes: set[str] = set()

    if explicit_scopes:
        scopes.update(explicit_scopes)

    for path in file_paths:
        lang = _detect_language(path)
        if lang and lang in _SCOPE_MAP:
            scopes.add(_SCOPE_MAP[lang])

        # Special path-based scopes
        lower_path = path.lower()
        if "test" in lower_path or "spec" in lower_path:
            scopes.add("engineering/testing")
        if ".github/" in lower_path or "ci" in lower_path:
            scopes.add("engineering/ci-cd")
        if "docker" in lower_path:
            scopes.add("engineering/devops")

    if not scopes:
        scopes.add("engineering")

    return sorted(scopes)


def _detect_languages(file_paths: list[str]) -> list[str]:
    """Detect unique languages across file paths.

    Args:
        file_paths: List of file paths.

    Returns:
        Sorted list of unique language identifiers.
    """
    languages: set[str] = set()
    for path in file_paths:
        lang = _detect_language(path)
        if lang:
            languages.add(lang)
    return sorted(languages)


def _build_evaluation_prompt(
    diff: str,
    file_paths: list[str],
    languages: list[str],
    scopes: list[str],
    rules: list[dict[str, Any]],
    context: dict[str, Any],
    prompt_template: str,
) -> str:
    """Build the full evaluation prompt from components.

    Args:
        diff: The code diff text.
        file_paths: Extracted file paths.
        languages: Detected languages.
        scopes: Resolved scopes.
        rules: Rules to evaluate against.
        context: Additional evaluation context.
        prompt_template: The prompt template text.

    Returns:
        The fully assembled prompt string.
    """
    rules_text = _format_rules_for_prompt(rules)
    context_text = _format_context(file_paths, languages, scopes, context)

    return prompt_template.format(
        diff=diff,
        context=context_text,
        rules=rules_text,
        intent=context.get("intent", "Not specified"),
    )


def _format_rules_for_prompt(rules: list[dict[str, Any]]) -> str:
    """Format rules into a prompt-friendly text block.

    Args:
        rules: List of rule dicts.

    Returns:
        Formatted rules text.
    """
    parts: list[str] = []
    for i, rule in enumerate(rules, 1):
        parts.append(
            f"Rule {i} (ID: {rule.get('id', 'unknown')}):\n"
            f"  Statement: {rule.get('statement', '')}\n"
            f"  Modality: {rule.get('modality', 'MUST')}\n"
            f"  Severity: {rule.get('severity', 'MEDIUM')}"
        )
    return "\n\n".join(parts)


def _format_context(
    file_paths: list[str],
    languages: list[str],
    scopes: list[str],
    context: dict[str, Any],
) -> str:
    """Format evaluation context metadata.

    Args:
        file_paths: Extracted file paths.
        languages: Detected languages.
        scopes: Resolved scopes.
        context: Additional context dict.

    Returns:
        Formatted context text.
    """
    parts = [
        f"Files changed: {', '.join(file_paths[:20])}",
        f"Languages: {', '.join(languages)}",
        f"Scopes: {', '.join(scopes)}",
    ]
    if context.get("repository"):
        parts.append(f"Repository: {context['repository']}")
    if context.get("base_branch"):
        parts.append(f"Base branch: {context['base_branch']}")
    if context.get("actor"):
        parts.append(f"Actor: {context['actor']}")
    return "\n".join(parts)


def _parse_verdict_response(response_text: str, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse LLM response text into per-rule verdict dicts.

    Expects the LLM to return one verdict block per rule, each containing
    rule_id, verdict, confidence, reasoning, and optional fix_suggestion.

    Falls back to a conservative NEEDS_CONFIRMATION verdict if parsing
    fails for any rule.

    Args:
        response_text: Raw LLM response text.
        rules: The rules that were evaluated (for fallback IDs).

    Returns:
        List of verdict dicts.
    """
    import json

    verdicts: list[dict[str, Any]] = []

    # Attempt JSON parsing first (structured output mode)
    try:
        parsed = json.loads(response_text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "verdicts" in parsed:
            return parsed["verdicts"]
    except (json.JSONDecodeError, TypeError, KeyError):
        pass

    # Fallback: generate conservative verdicts
    for rule in rules:
        verdicts.append(
            {
                "rule_id": rule.get("id", "unknown"),
                "verdict": "NEEDS_CONFIRMATION",
                "confidence": 0.5,
                "reasoning": ("Automated parsing of LLM response failed. Manual review required."),
                "raw_response": response_text[:500],
            }
        )

    return verdicts


class CodeChangeEvaluator:
    """Evaluator for code changes (diffs) against engineering rules.

    Parses unified diffs, detects programming languages, resolves scopes
    from file paths, and delegates rule evaluation to an LLM callable.

    The LLM callable is injected via the constructor -- this evaluator
    never imports or references a specific LLM provider.

    Args:
        llm_callable: Async function that takes a prompt string and
            returns a response string. Injected at construction.
        prompt_template: Optional custom prompt template. If not provided,
            loads from the default prompts directory.
    """

    def __init__(
        self,
        llm_callable: LLMCallable | None = None,
        prompt_template: str | None = None,
    ) -> None:
        self._llm_callable = llm_callable
        self._prompt_template = prompt_template or self._load_default_prompt()

    @property
    def name(self) -> str:
        return "code_change"

    @property
    def domain(self) -> str:
        return "engineering"

    @property
    def supported_subject_kinds(self) -> list[str]:
        return ["code_diff"]

    def set_llm_callable(self, llm_callable: LLMCallable) -> None:
        """Set the LLM callable after construction.

        Useful when the LLM provider is resolved at server startup time,
        after plugin instantiation.

        Args:
            llm_callable: Async function for LLM calls.
        """
        self._llm_callable = llm_callable

    async def evaluate(
        self,
        subject_payload: dict[str, Any],
        rules: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Evaluate a code diff against engineering rules.

        Args:
            subject_payload: Must contain 'diff' (unified diff text).
                Optional: 'file_paths', 'intent', 'scope'.
            rules: List of rule dicts to evaluate against.
            context: Additional context (repository, actor, base_branch, ...).

        Returns:
            List of verdict dicts, one per rule.

        Raises:
            PluginError: If no LLM callable is configured.
        """
        from rulerepo_server.plugins.base import PluginError

        if self._llm_callable is None:
            raise PluginError(
                "CodeChangeEvaluator requires an LLM callable. Call set_llm_callable() before evaluate()."
            )

        diff = subject_payload.get("diff", "")
        if not diff:
            return [
                {
                    "rule_id": rule.get("id", "unknown"),
                    "verdict": "ALLOW",
                    "confidence": 1.0,
                    "reasoning": "No code changes provided.",
                }
                for rule in rules
            ]

        explicit_scopes = subject_payload.get("scope")
        if isinstance(explicit_scopes, str):
            explicit_scopes = [explicit_scopes]

        file_paths = subject_payload.get("file_paths") or _extract_file_paths(diff)
        languages = _detect_languages(file_paths)
        scopes = _resolve_scopes(file_paths, explicit_scopes)

        prompt = _build_evaluation_prompt(
            diff=diff,
            file_paths=file_paths,
            languages=languages,
            scopes=scopes,
            rules=rules,
            context={**context, "intent": subject_payload.get("intent")},
            prompt_template=self._prompt_template,
        )

        response_text = await self._llm_callable(prompt)
        return _parse_verdict_response(response_text, rules)

    @staticmethod
    def _load_default_prompt() -> str:
        """Load the default code evaluation prompt template.

        Returns:
            The prompt template string.
        """
        prompt_path = PurePosixPath(__file__).parent.parent / "prompts" / "code_evaluation.md"
        # Convert to a real Path for reading
        from pathlib import Path

        real_path = Path(str(prompt_path))
        if real_path.exists():
            return real_path.read_text(encoding="utf-8")

        # Inline fallback if file not found
        return (
            "You are a code review assistant evaluating a code change against "
            "engineering rules.\n\n"
            "## Code Diff\n```\n{diff}\n```\n\n"
            "## Context\n{context}\n\n"
            "## Developer Intent\n{intent}\n\n"
            "## Rules to Evaluate\n{rules}\n\n"
            "For each rule, return a JSON object with:\n"
            '- "rule_id": the rule ID\n'
            '- "verdict": one of "ALLOW", "DENY", "NEEDS_CONFIRMATION"\n'
            '- "confidence": float between 0 and 1\n'
            '- "reasoning": explanation of your verdict\n'
            '- "fix_suggestion": optional suggestion for fixing violations\n\n'
            "Return a JSON array of verdict objects."
        )
