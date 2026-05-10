"""Tests for surface-based template routing in batch evaluator.

Verifies that the batch evaluator selects the correct prompt template
based on the surface field in EvaluationContext, rather than branching
on diff presence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rulerepo_server.domain.evaluation import EvaluationContext
from rulerepo_server.services.evaluation.batch_evaluator import _select_template

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "src" / "rulerepo_server" / "services" / "evaluation" / "prompts"


class TestSelectTemplate:
    """Tests for _select_template routing logic."""

    def test_code_surface_uses_code_template(self) -> None:
        ctx = EvaluationContext(diff="--- a/f.py\n+++ b/f.py", surface="code")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_code.txt").read_text()
        assert template == expected

    def test_contract_surface_uses_contract_template(self) -> None:
        ctx = EvaluationContext(facts={"clause": "test"}, surface="contract")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_contract.txt").read_text()
        assert template == expected

    def test_transaction_surface_uses_transaction_template(self) -> None:
        ctx = EvaluationContext(facts={"amount": 1000}, surface="transaction")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_transaction.txt").read_text()
        assert template == expected

    def test_document_surface_uses_document_template(self) -> None:
        ctx = EvaluationContext(facts={"text": "draft"}, surface="document")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_document.txt").read_text()
        assert template == expected

    def test_message_surface_uses_message_template(self) -> None:
        ctx = EvaluationContext(facts={"body": "hello"}, surface="message")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_message.txt").read_text()
        assert template == expected

    def test_human_action_surface_uses_human_action_template(self) -> None:
        ctx = EvaluationContext(facts={"action": "overtime"}, surface="human_action")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_human_action.txt").read_text()
        assert template == expected

    def test_generic_surface_uses_generic_template(self) -> None:
        ctx = EvaluationContext(facts={"key": "val"}, surface="generic")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_generic.txt").read_text()
        assert template == expected

    def test_unknown_surface_falls_back_to_generic(self) -> None:
        ctx = EvaluationContext(facts={"key": "val"}, surface="unknown_surface")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_generic.txt").read_text()
        assert template == expected

    def test_no_surface_with_diff_defaults_to_code(self) -> None:
        """Backward compat: no surface + diff present -> code template."""
        ctx = EvaluationContext(diff="--- a/f.py\n+++ b/f.py")
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_code.txt").read_text()
        assert template == expected

    def test_no_surface_no_diff_defaults_to_generic(self) -> None:
        """Backward compat: no surface + no diff -> generic template."""
        ctx = EvaluationContext(facts={"key": "val"})
        template = _select_template(ctx)
        expected = (PROMPTS_DIR / "evaluate_batch_generic.txt").read_text()
        assert template == expected


class TestTemplateContent:
    """Verify that surface-specific templates do NOT reference code concepts."""

    @pytest.mark.parametrize(
        "surface",
        ["contract", "transaction", "document", "message", "human_action", "generic"],
    )
    def test_non_code_templates_do_not_reference_code_concepts(self, surface: str) -> None:
        template_path = PROMPTS_DIR / f"evaluate_batch_{surface}.txt"
        content = template_path.read_text()
        assert "unified diff" not in content.lower()
        assert "{diff}" not in content
        assert "{file_paths}" not in content
        assert "line numbers" not in content.lower() or surface == "generic"
        assert "function names" not in content.lower()

    def test_code_template_references_diff(self) -> None:
        template_path = PROMPTS_DIR / "evaluate_batch_code.txt"
        content = template_path.read_text()
        assert "{diff}" in content
        assert "{file_paths}" in content

    def test_all_templates_have_rules_block(self) -> None:
        for surface in ["code", "contract", "transaction", "document", "message", "human_action", "generic"]:
            template_path = PROMPTS_DIR / f"evaluate_batch_{surface}.txt"
            content = template_path.read_text()
            assert "{rules_block}" in content, f"{surface} template missing {{rules_block}}"

    def test_all_templates_have_relationships_block(self) -> None:
        for surface in ["code", "contract", "transaction", "document", "message", "human_action", "generic"]:
            template_path = PROMPTS_DIR / f"evaluate_batch_{surface}.txt"
            content = template_path.read_text()
            assert "{relationships_block}" in content, f"{surface} template missing {{relationships_block}}"


class TestContextAssemblerSurface:
    """Verify that assemble_context threads surface through."""

    def test_assemble_context_with_surface(self) -> None:
        from rulerepo_server.services.evaluation.context_assembler import assemble_context

        ctx = assemble_context(
            facts={"amount": 30000},
            intent="expense claim",
            surface="transaction",
        )
        assert ctx.surface == "transaction"

    def test_assemble_context_without_surface(self) -> None:
        from rulerepo_server.services.evaluation.context_assembler import assemble_context

        ctx = assemble_context(diff="--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-old\n+new")
        assert ctx.surface is None

    def test_assemble_context_code_surface(self) -> None:
        from rulerepo_server.services.evaluation.context_assembler import assemble_context

        ctx = assemble_context(
            diff="--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-old\n+new",
            surface="code",
        )
        assert ctx.surface == "code"
