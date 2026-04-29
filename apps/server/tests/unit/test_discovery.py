"""Unit tests for rule discovery analyzers and pattern detector."""

from __future__ import annotations

import pytest

from rulerepo_server.services.discovery.analyzers.base import (
    DiscoveryContext,
    RawPattern,
)
from rulerepo_server.services.discovery.analyzers.claude_md import ClaudeMdAnalyzer
from rulerepo_server.services.discovery.analyzers.code_patterns import (
    CodePatternsAnalyzer,
)
from rulerepo_server.services.discovery.analyzers.linter_config import (
    LinterConfigAnalyzer,
)
from rulerepo_server.services.discovery.pattern_detector import deduplicate_and_score


# ---------------------------------------------------------------------------
# ClaudeMdAnalyzer
# ---------------------------------------------------------------------------


class TestClaudeMdAnalyzerMustRules:
    async def test_parse_must_rules(self) -> None:
        content = (
            "# Rules\n"
            "- All code MUST be reviewed before merging.\n"
            "- Deployments MUST go through staging first.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["CLAUDE.md"],
            file_contents={"CLAUDE.md": content},
        )
        analyzer = ClaudeMdAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 2
        for p in patterns:
            assert p.modality == "MUST"
            assert p.confidence >= 0.8


class TestClaudeMdAnalyzerShouldRules:
    async def test_parse_should_rules(self) -> None:
        content = (
            "# Guidelines\n"
            "- Engineers should write tests for new features.\n"
            "- Teams should prefer small pull requests.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["CLAUDE.md"],
            file_contents={"CLAUDE.md": content},
        )
        analyzer = ClaudeMdAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 2
        for p in patterns:
            assert p.modality == "SHOULD"


class TestClaudeMdAnalyzerMustNotRules:
    async def test_parse_must_not_rules(self) -> None:
        content = (
            "# Constraints\n"
            "- You must not commit secrets to the repo.\n"
            "- Never use print() in production code.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["CLAUDE.md"],
            file_contents={"CLAUDE.md": content},
        )
        analyzer = ClaudeMdAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 2
        for p in patterns:
            assert p.modality == "MUST_NOT"


class TestClaudeMdAnalyzerHeadingScope:
    async def test_heading_as_scope(self) -> None:
        content = (
            "## Python Rules\n"
            "- All functions MUST have type hints.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["CLAUDE.md"],
            file_contents={"CLAUDE.md": content},
        )
        analyzer = ClaudeMdAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 1
        assert "python" in " ".join(patterns[0].scope).lower()


class TestClaudeMdAnalyzerEmptyFile:
    async def test_empty_file(self) -> None:
        ctx = DiscoveryContext(
            file_paths=["CLAUDE.md"],
            file_contents={"CLAUDE.md": ""},
        )
        analyzer = ClaudeMdAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert patterns == []


class TestClaudeMdAnalyzerNonClaudeFile:
    async def test_non_claude_file(self) -> None:
        ctx = DiscoveryContext(
            file_paths=["README.md"],
            file_contents={"README.md": "- You MUST read this document.\n"},
        )
        analyzer = ClaudeMdAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert patterns == []


# ---------------------------------------------------------------------------
# LinterConfigAnalyzer
# ---------------------------------------------------------------------------


class TestLinterConfigRuffToml:
    async def test_parse_ruff_toml(self) -> None:
        content = (
            'line-length = 120\n'
            '\n'
            '[lint]\n'
            'select = ["E", "F", "I"]\n'
        )
        ctx = DiscoveryContext(
            file_paths=["ruff.toml"],
            file_contents={"ruff.toml": content},
        )
        analyzer = LinterConfigAnalyzer()
        patterns = await analyzer.analyze(ctx)

        statements = [p.statement for p in patterns]
        # Should have a line-length pattern and a lint-rules pattern
        assert any("120" in s for s in statements)
        assert any("E" in s and "F" in s for s in statements)


class TestLinterConfigEslintErrorRules:
    async def test_parse_eslint_error_rules(self) -> None:
        content = '{"rules": {"no-unused-vars": "error", "semi": "error"}}'
        ctx = DiscoveryContext(
            file_paths=[".eslintrc.json"],
            file_contents={".eslintrc.json": content},
        )
        analyzer = LinterConfigAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 2
        for p in patterns:
            assert p.modality == "MUST_NOT"
            assert "ESLint" in p.statement


class TestLinterConfigTsconfigStrict:
    async def test_parse_tsconfig_strict(self) -> None:
        content = '{"compilerOptions": {"strict": true}}'
        ctx = DiscoveryContext(
            file_paths=["tsconfig.json"],
            file_contents={"tsconfig.json": content},
        )
        analyzer = LinterConfigAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) == 1
        assert "strict" in patterns[0].statement.lower()
        assert patterns[0].modality == "MUST"


class TestLinterConfigEmptyConfig:
    async def test_empty_config(self) -> None:
        ctx = DiscoveryContext(
            file_paths=["ruff.toml"],
            file_contents={"ruff.toml": ""},
        )
        analyzer = LinterConfigAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert patterns == []


# ---------------------------------------------------------------------------
# CodePatternsAnalyzer
# ---------------------------------------------------------------------------


def _make_py_file_with_docstring(name: str) -> str:
    """Return a small Python file with a public function that has a docstring."""
    return (
        f'def {name}(x: int) -> int:\n'
        f'    """Do something."""\n'
        f'    return x + 1\n'
    )


def _make_py_file_without_docstring(name: str) -> str:
    """Return a small Python file with a public function lacking a docstring."""
    return (
        f'def {name}(x: int) -> int:\n'
        f'    return x + 1\n'
    )


class TestCodePatternsTestNaming:
    async def test_detect_test_naming(self) -> None:
        files = {
            "tests/test_alpha.py": "# test file\nimport pytest\n# padding to count",
            "tests/test_beta.py": "# test file\nimport pytest\n# padding to count",
            "tests/test_gamma.py": "# test file\nimport pytest\n# padding to count",
            "tests/test_delta.py": "# test file\nimport pytest\n# padding to count",
        }
        ctx = DiscoveryContext(
            file_paths=list(files.keys()),
            file_contents=files,
        )
        analyzer = CodePatternsAnalyzer()
        patterns = await analyzer.analyze(ctx)

        naming_patterns = [p for p in patterns if "test_*.py" in p.statement]
        assert len(naming_patterns) == 1
        assert naming_patterns[0].modality == "SHOULD"


class TestCodePatternsDocstrings:
    async def test_detect_docstrings(self) -> None:
        # 4 files, each with a public function that has a docstring (>80% coverage)
        files = {
            f"src/mod_{i}.py": _make_py_file_with_docstring(f"func_{i}")
            for i in range(4)
        }
        ctx = DiscoveryContext(
            file_paths=list(files.keys()),
            file_contents=files,
        )
        analyzer = CodePatternsAnalyzer()
        patterns = await analyzer.analyze(ctx)

        doc_patterns = [p for p in patterns if "docstring" in p.statement.lower()]
        assert len(doc_patterns) == 1
        assert doc_patterns[0].modality == "SHOULD"


class TestCodePatternsBelowThreshold:
    async def test_below_threshold(self) -> None:
        # 4 files: only 1 with docstring (25% < 80% threshold)
        files = {
            "src/mod_0.py": _make_py_file_with_docstring("func_0"),
            "src/mod_1.py": _make_py_file_without_docstring("func_1"),
            "src/mod_2.py": _make_py_file_without_docstring("func_2"),
            "src/mod_3.py": _make_py_file_without_docstring("func_3"),
        }
        ctx = DiscoveryContext(
            file_paths=list(files.keys()),
            file_contents=files,
        )
        analyzer = CodePatternsAnalyzer()
        patterns = await analyzer.analyze(ctx)

        doc_patterns = [p for p in patterns if "docstring" in p.statement.lower()]
        assert len(doc_patterns) == 0


# ---------------------------------------------------------------------------
# PatternDetector (deduplicate_and_score)
# ---------------------------------------------------------------------------


def _make_pattern(statement: str, confidence: float, source_type: str = "test") -> RawPattern:
    return RawPattern(
        statement=statement,
        modality="MUST",
        severity="HIGH",
        scope=["python"],
        tags=["test"],
        source_type=source_type,
        source_evidence=statement,
        confidence=confidence,
    )


class TestPatternDetectorDeduplicateSimilar:
    def test_deduplicate_similar(self) -> None:
        # Two patterns with the same long prefix should collapse to one
        p1 = _make_pattern(
            "Python code MUST pass ruff linting with rule codes: E, F, I.",
            confidence=0.85,
            source_type="linter_config",
        )
        p2 = _make_pattern(
            "Python code MUST pass ruff linting with rule codes: E, F.",
            confidence=0.80,
            source_type="claude_md",
        )
        result = deduplicate_and_score([p1, p2])

        assert len(result) == 1
        # Should keep the higher-confidence variant
        assert "E, F, I" in result[0].statement
        # Confidence should be >= the original best
        assert result[0].confidence >= 0.85


class TestPatternDetectorKeepDifferent:
    def test_keep_different(self) -> None:
        p1 = _make_pattern("All code MUST be reviewed before merging.", confidence=0.9)
        p2 = _make_pattern("Test files SHOULD follow the test_*.py naming convention.", confidence=0.8)
        result = deduplicate_and_score([p1, p2])

        assert len(result) == 2


class TestPatternDetectorConfidenceBoost:
    def test_confidence_boost(self) -> None:
        # Same pattern from two different sources should get a confidence boost
        base_confidence = 0.85
        p1 = _make_pattern(
            "Python code MUST pass ruff linting for quality assurance.",
            confidence=base_confidence,
            source_type="linter_config",
        )
        p2 = _make_pattern(
            "Python code MUST pass ruff linting for quality assurance.",
            confidence=0.80,
            source_type="claude_md",
        )
        result = deduplicate_and_score([p1, p2])

        assert len(result) == 1
        # With 2 unique sources, boost = base * (1 + 0.1 * 2) = base * 1.2
        assert result[0].confidence > base_confidence


# ---------------------------------------------------------------------------
# PolicyDocumentAnalyzer
# ---------------------------------------------------------------------------

from rulerepo_server.services.discovery.analyzers.policy_document import (
    PolicyDocumentAnalyzer,
)


class TestPolicyDocumentMustStatements:
    async def test_detects_must_in_hr_policy(self) -> None:
        content = (
            "# Employee Handbook\n\n"
            "All employees must submit their timesheets by Friday 5pm.\n"
            "Managers must approve leave requests within 3 business days.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["employee_handbook.md"],
            file_contents={"employee_handbook.md": content},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 2
        for p in patterns:
            assert p.modality == "MUST"
            assert p.source_type == "policy_document"
            assert p.confidence >= 0.8


class TestPolicyDocumentShallNot:
    async def test_detects_shall_not_in_contract(self) -> None:
        content = (
            "## Confidentiality\n\n"
            "The contractor shall not disclose any confidential information "
            "to third parties without prior written consent.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["contractor_agreement.txt"],
            file_contents={"contractor_agreement.txt": content},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert patterns[0].modality == "MUST_NOT"
        assert "confidentiality" in patterns[0].scope[0]


class TestPolicyDocumentShouldRecommendations:
    async def test_detects_should_in_guidelines(self) -> None:
        content = (
            "# Expense Policy\n\n"
            "Employees should retain receipts for all expenses over $25.\n"
            "It is recommended to submit expense reports within 30 days.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["expense_policy.md"],
            file_contents={"expense_policy.md": content},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert any(p.modality == "SHOULD" for p in patterns)


class TestPolicyDocumentDomainTags:
    async def test_infers_hr_tags(self) -> None:
        content = "All employees must complete annual safety training.\n"
        ctx = DiscoveryContext(
            file_paths=["safety_training.txt"],
            file_contents={"safety_training.txt": content},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        tags = patterns[0].tags
        assert "policy_document" in tags
        assert "safety" in tags or "hr" in tags


class TestPolicyDocumentSeverityInference:
    async def test_critical_for_security_rules(self) -> None:
        content = "All users must enable two-factor authentication for security purposes.\n"
        ctx = DiscoveryContext(
            file_paths=["security_policy.txt"],
            file_contents={"security_policy.txt": content},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert len(patterns) >= 1
        assert patterns[0].severity == "CRITICAL"


class TestPolicyDocumentSkipsCodeFiles:
    async def test_skips_claude_md(self) -> None:
        content = "All code MUST be reviewed.\n"
        ctx = DiscoveryContext(
            file_paths=["CLAUDE.md"],
            file_contents={"CLAUDE.md": content},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        # CLAUDE.md is handled by ClaudeMdAnalyzer, not PolicyDocumentAnalyzer
        assert len(patterns) == 0


class TestPolicyDocumentEmptyFile:
    async def test_empty_returns_nothing(self) -> None:
        ctx = DiscoveryContext(
            file_paths=["empty.txt"],
            file_contents={"empty.txt": ""},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        assert patterns == []


class TestPolicyDocumentMixedContent:
    async def test_extracts_only_normative_sentences(self) -> None:
        content = (
            "# Company Overview\n\n"
            "Founded in 2020, our company has grown to 500 employees.\n"
            "We operate in 12 countries across three continents.\n\n"
            "# Workplace Rules\n\n"
            "All employees must wear identification badges at all times.\n"
            "Visitors should be escorted by a staff member.\n"
            "The cafeteria serves lunch from 12pm to 2pm.\n"
        )
        ctx = DiscoveryContext(
            file_paths=["company_handbook.md"],
            file_contents={"company_handbook.md": content},
        )
        analyzer = PolicyDocumentAnalyzer()
        patterns = await analyzer.analyze(ctx)

        # Should find the 2 normative statements but not the descriptive ones
        statements = [p.statement for p in patterns]
        assert any("identification badges" in s for s in statements)
        assert any("escorted" in s for s in statements)
        # Descriptive sentences should NOT be extracted
        assert not any("Founded in 2020" in s for s in statements)
        assert not any("cafeteria" in s for s in statements)
