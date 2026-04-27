"""Diff delta extraction -- compares original vs corrected diff to find what changed."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CorrectionDelta:
    """Represents what the human changed relative to the agent's output."""

    summary: str
    lines_added: list[str] = field(default_factory=list)
    lines_removed: list[str] = field(default_factory=list)
    affected_functions: list[str] = field(default_factory=list)
    file_paths: list[str] = field(default_factory=list)


_FUNC_PATTERN = re.compile(
    r"^\+?\s*(?:def |function |class |async def |export (?:default )?(?:function |class ))"
    r"(\w+)",
)


def _parse_diff_lines(diff: str) -> tuple[set[str], set[str], list[str], list[str]]:
    """Parse a unified diff, returning (additions, removals, file_paths, function_names).

    Args:
        diff: Unified diff text.

    Returns:
        Tuple of (added_lines, removed_lines, file_paths, function_names).
    """
    additions: set[str] = set()
    removals: set[str] = set()
    file_paths: list[str] = []
    function_names: list[str] = []

    for line in diff.splitlines():
        if line.startswith("+++"):
            # Extract file path from +++ b/path/to/file
            path = line[4:].strip()
            if path.startswith("b/"):
                path = path[2:]
            if path and path != "/dev/null":
                file_paths.append(path)
        elif line.startswith("+") and not line.startswith("+++"):
            additions.add(line[1:])
            match = _FUNC_PATTERN.match(line)
            if match:
                function_names.append(match.group(1))
        elif line.startswith("-") and not line.startswith("---"):
            removals.add(line[1:])

    return additions, removals, file_paths, function_names


def extract_correction_delta(original_diff: str, corrected_diff: str) -> CorrectionDelta:
    """Compare original agent diff vs human-corrected diff, return semantic delta.

    Args:
        original_diff: The diff produced by the agent.
        corrected_diff: The diff after human correction.

    Returns:
        A CorrectionDelta describing what the human changed.
    """
    orig_adds, orig_rems, orig_paths, orig_funcs = _parse_diff_lines(original_diff)
    corr_adds, corr_rems, corr_paths, corr_funcs = _parse_diff_lines(corrected_diff)

    # Lines the human added that the agent did not
    new_additions = sorted(corr_adds - orig_adds)
    # Lines the agent added that the human removed
    new_removals = sorted(orig_adds - corr_adds)

    # Combine file paths (deduplicated, order preserved)
    seen: set[str] = set()
    all_paths: list[str] = []
    for p in corr_paths + orig_paths:
        if p not in seen:
            seen.add(p)
            all_paths.append(p)

    # Combine affected functions (deduplicated, order preserved)
    seen_funcs: set[str] = set()
    all_funcs: list[str] = []
    for f in corr_funcs + orig_funcs:
        if f not in seen_funcs:
            seen_funcs.add(f)
            all_funcs.append(f)

    summary = f"Human added {len(new_additions)} lines, removed {len(new_removals)} lines."
    if all_funcs:
        summary += f" Modified functions: {', '.join(all_funcs)}."

    return CorrectionDelta(
        summary=summary,
        lines_added=new_additions,
        lines_removed=new_removals,
        affected_functions=all_funcs,
        file_paths=all_paths,
    )
