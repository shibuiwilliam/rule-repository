"""Unit tests for GitHub integration components."""

from rulerepo_server.integrations.github.review_formatter import format_review_comment


class TestReviewFormatter:
    def test_all_allow(self) -> None:
        result = format_review_comment(
            {
                "overall_verdict": "ALLOW",
                "violations": [],
                "warnings": [],
            }
        )
        assert "pass" in result.lower()
        assert "white_check_mark" in result

    def test_violations_shown(self) -> None:
        result = format_review_comment(
            {
                "overall_verdict": "DENY",
                "violations": [
                    {
                        "rule_id": "r1",
                        "rule_statement": "Must validate input",
                        "issue_description": "Raw dict access",
                        "fix_suggestion": "Add Pydantic model",
                        "locations": [{"file_path": "api.py", "start_line": 42}],
                    }
                ],
                "warnings": [],
            }
        )
        assert "DENY" in result
        assert "Must validate input" in result
        assert "api.py" in result
        assert "Add Pydantic model" in result

    def test_warnings_shown(self) -> None:
        result = format_review_comment(
            {
                "overall_verdict": "NEEDS_CONFIRMATION",
                "violations": [],
                "warnings": [
                    {
                        "rule_id": "r2",
                        "rule_statement": "Should add docstrings",
                        "issue_description": "Missing docstring",
                    }
                ],
            }
        )
        assert "SUGGESTION" in result
        assert "Should add docstrings" in result

    def test_violation_count_in_header(self) -> None:
        result = format_review_comment(
            {
                "overall_verdict": "DENY",
                "violations": [
                    {"rule_id": "r1", "rule_statement": "V1", "locations": []},
                    {"rule_id": "r2", "rule_statement": "V2", "locations": []},
                ],
                "warnings": [],
            }
        )
        assert "2 violation(s)" in result
