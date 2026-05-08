"""PR correction capture — captures human corrections from merged PR diffs.

When a developer modifies code that was previously evaluated, the diff
between the evaluation snapshot and the merged result represents a
correction signal. This feedback source detects such corrections and
produces feedback events for the rule improvement flywheel.

See: CLAUDE.md SS17
"""

from __future__ import annotations

import re
from typing import Any


def _extract_correction_pairs(
    original_diff: str,
    final_diff: str,
) -> list[dict[str, Any]]:
    """Compare original evaluated diff with final merged diff to find corrections.

    A correction is a hunk that was present in the original evaluation but
    was modified before merge -- indicating the developer disagreed with
    the original approach (and by extension, the evaluation verdict).

    Args:
        original_diff: The diff that was evaluated.
        final_diff: The diff that was actually merged.

    Returns:
        List of correction dicts with original/final hunks.
    """
    corrections: list[dict[str, Any]] = []

    original_files = _split_diff_by_file(original_diff)
    final_files = _split_diff_by_file(final_diff)

    for file_path, original_hunks in original_files.items():
        final_hunks = final_files.get(file_path)
        if final_hunks is None:
            # File was dropped entirely -- significant correction
            corrections.append(
                {
                    "file_path": file_path,
                    "correction_type": "file_removed",
                    "original_hunks": original_hunks,
                    "final_hunks": [],
                    "significance": "high",
                }
            )
            continue

        if original_hunks != final_hunks:
            corrections.append(
                {
                    "file_path": file_path,
                    "correction_type": "hunks_modified",
                    "original_hunks": original_hunks,
                    "final_hunks": final_hunks,
                    "significance": _assess_significance(original_hunks, final_hunks),
                }
            )

    # Files added in final that weren't in original
    for file_path in final_files:
        if file_path not in original_files:
            corrections.append(
                {
                    "file_path": file_path,
                    "correction_type": "file_added",
                    "original_hunks": [],
                    "final_hunks": final_files[file_path],
                    "significance": "medium",
                }
            )

    return corrections


def _split_diff_by_file(diff: str) -> dict[str, list[str]]:
    """Split a unified diff into per-file hunk lists.

    Args:
        diff: Unified diff text.

    Returns:
        Dict mapping file paths to lists of diff hunks.
    """
    files: dict[str, list[str]] = {}
    current_file: str | None = None
    current_hunks: list[str] = []

    for line in diff.split("\n"):
        file_match = re.match(r"^\+\+\+\s+b/(.+)$", line)
        if file_match:
            if current_file is not None:
                files[current_file] = current_hunks
            current_file = file_match.group(1)
            current_hunks = []
        elif current_file is not None:
            current_hunks.append(line)

    if current_file is not None:
        files[current_file] = current_hunks

    return files


def _assess_significance(
    original_hunks: list[str],
    final_hunks: list[str],
) -> str:
    """Assess the significance of a correction based on hunk differences.

    Args:
        original_hunks: Original diff hunks.
        final_hunks: Final diff hunks.

    Returns:
        Significance level: 'high', 'medium', or 'low'.
    """
    original_adds = sum(1 for h in original_hunks if h.startswith("+"))
    final_adds = sum(1 for h in final_hunks if h.startswith("+"))
    original_dels = sum(1 for h in original_hunks if h.startswith("-"))
    final_dels = sum(1 for h in final_hunks if h.startswith("-"))

    total_original = original_adds + original_dels
    total_final = final_adds + final_dels

    if total_original == 0:
        return "medium"

    change_ratio = abs(total_final - total_original) / max(total_original, 1)

    if change_ratio > 0.5:
        return "high"
    if change_ratio > 0.2:
        return "medium"
    return "low"


def _determine_feedback_kind(
    correction: dict[str, Any],
    review_comments: list[dict[str, Any]],
) -> str:
    """Determine the feedback kind based on the correction and review context.

    Args:
        correction: Correction dict from _extract_correction_pairs.
        review_comments: PR review comments, if available.

    Returns:
        Feedback kind string.
    """
    if correction["correction_type"] == "file_removed":
        return "code_correction"

    # Check review comments for explicit rule references
    for comment in review_comments:
        body = comment.get("body", "").lower()
        if "false positive" in body or "not applicable" in body:
            return "explicit_verdict_override"
        if "exception" in body or "waiver" in body:
            return "exception_granted"

    return "code_correction"


class PrCorrectionCapture:
    """Captures correction feedback from merged pull requests.

    Compares the diff snapshot at evaluation time with the final merged
    diff. Differences represent human corrections to the evaluated code,
    which are feedback signals for the rule improvement flywheel.
    """

    @property
    def name(self) -> str:
        return "pr_correction"

    @property
    def domain(self) -> str:
        return "engineering"

    async def capture(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Capture feedback events from a PR merge event.

        Args:
            event: PR merge event with keys:
                - pr_id: Pull request identifier.
                - original_diff: Diff at evaluation time.
                - final_diff: Diff at merge time.
                - evaluation_id: ID of the original evaluation.
                - evaluation_verdicts: List of verdict dicts from the original
                    evaluation.
                - review_comments: Optional list of review comment dicts.
                - repository: Repository identifier.
                - actor: The person who merged.

        Returns:
            List of feedback event dicts.
        """
        original_diff = event.get("original_diff", "")
        final_diff = event.get("final_diff", "")

        if not original_diff or not final_diff:
            return []

        if original_diff == final_diff:
            return []

        corrections = _extract_correction_pairs(original_diff, final_diff)
        if not corrections:
            return []

        review_comments = event.get("review_comments", [])
        evaluation_verdicts = event.get("evaluation_verdicts", [])
        feedback_events: list[dict[str, Any]] = []

        for correction in corrections:
            feedback_kind = _determine_feedback_kind(correction, review_comments)

            # Match corrections to verdicts by file path
            related_verdicts = [v for v in evaluation_verdicts if _verdict_relates_to_file(v, correction["file_path"])]

            feedback_events.append(
                {
                    "kind": feedback_kind,
                    "subject_kind": "code_diff",
                    "original_verdict": (
                        related_verdicts[0].get("verdict", "UNKNOWN") if related_verdicts else "UNKNOWN"
                    ),
                    "corrected_verdict": "ALLOW",
                    "reason": (
                        f"Code in {correction['file_path']} was modified between "
                        f"evaluation and merge ({correction['correction_type']}). "
                        f"Significance: {correction['significance']}."
                    ),
                    "correctness_evidence": [
                        {
                            "type": "pr_diff",
                            "pr_id": event.get("pr_id", ""),
                            "file_path": correction["file_path"],
                            "correction_type": correction["correction_type"],
                        }
                    ],
                    "metadata": {
                        "evaluation_id": event.get("evaluation_id", ""),
                        "pr_id": event.get("pr_id", ""),
                        "repository": event.get("repository", ""),
                        "actor": event.get("actor", ""),
                        "significance": correction["significance"],
                        "related_rule_ids": [v.get("rule_id", "") for v in related_verdicts],
                    },
                }
            )

        return feedback_events


def _verdict_relates_to_file(verdict: dict[str, Any], file_path: str) -> bool:
    """Check if a verdict is related to a specific file.

    Args:
        verdict: Verdict dict from the evaluation.
        file_path: File path to check against.

    Returns:
        True if the verdict mentions the file.
    """
    # Check locations in the verdict
    locations = verdict.get("locations", [])
    for loc in locations:
        if loc.get("file_path") == file_path:
            return True

    # Check if the reasoning mentions the file
    reasoning = verdict.get("reasoning", "")
    return file_path in reasoning
