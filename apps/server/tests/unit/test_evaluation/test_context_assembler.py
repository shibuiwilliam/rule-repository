"""Unit tests for the context assembler."""

import json

from rulerepo_server.domain.subject import EvaluationSubject, SubjectKind
from rulerepo_server.services.evaluation.context_assembler import (
    assemble_context,
    assemble_context_from_subject,
)


class TestAssembleContext:
    def test_diff_mode(self) -> None:
        diff = """\
diff --git a/main.py b/main.py
--- a/main.py
+++ b/main.py
@@ -1 +1,2 @@
 print("hello")
+print("world")
"""
        ctx = assemble_context(diff=diff)
        assert ctx.diff == diff
        assert len(ctx.files_changed) == 1
        assert ctx.files_changed[0].path == "main.py"
        assert "python" in ctx.languages

    def test_file_mode(self) -> None:
        ctx = assemble_context(
            files=[
                {"path": "src/api/handler.py", "content": "def main(): pass"},
                {"path": "lib/utils.ts", "content": "export const x = 1"},
            ],
            surface="code",
        )
        assert len(ctx.file_paths) == 2
        assert "python" in ctx.languages
        assert "typescript" in ctx.languages

    def test_facts_mode(self) -> None:
        ctx = assemble_context(
            facts={"employee_id": "E001", "overtime_hours": 50},
            intent="Register overtime",
        )
        assert ctx.facts["overtime_hours"] == 50
        assert ctx.intent == "Register overtime"
        assert ctx.narrative == "Register overtime"

    def test_hybrid_mode(self) -> None:
        diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new"
        ctx = assemble_context(
            diff=diff,
            facts={"reason": "refactor"},
            intent="Refactoring",
            repository="my-repo",
        )
        assert ctx.diff is not None
        assert ctx.facts["reason"] == "refactor"
        assert ctx.repository == "my-repo"

    def test_empty_input(self) -> None:
        ctx = assemble_context()
        assert ctx.diff is None
        assert ctx.files_changed == []
        assert ctx.facts == {}


class TestTransactionSurface:
    """Context assembly for TRANSACTION subjects."""

    def test_transaction_surface_no_diff_no_files(self) -> None:
        """Transaction surface should not produce diff or file_paths."""
        ctx = assemble_context(
            facts={"amount_jpy": 150000, "category": "travel", "employee_id": "E001"},
            intent="Expense claim submission",
            surface="transaction",
        )
        assert ctx.diff is None
        assert ctx.files_changed == []
        assert ctx.file_paths == []
        assert ctx.languages == []
        assert ctx.surface == "transaction"
        assert ctx.facts["amount_jpy"] == 150000

    def test_transaction_narrative_is_json(self) -> None:
        """Transaction narrative should include a JSON representation of facts."""
        facts = {"amount_jpy": 50000, "category": "supplies"}
        ctx = assemble_context(facts=facts, surface="transaction")
        assert ctx.narrative is not None
        # The narrative should contain the JSON-serialized facts.
        parsed = json.loads(ctx.narrative)
        assert parsed["amount_jpy"] == 50000

    def test_transaction_with_intent_includes_both(self) -> None:
        ctx = assemble_context(
            facts={"amount_jpy": 50000},
            intent="Expense claim",
            surface="transaction",
        )
        assert ctx.narrative is not None
        assert "Expense claim" in ctx.narrative
        assert "50000" in ctx.narrative


class TestDocumentSurface:
    """Context assembly for DOCUMENT subjects."""

    def test_document_surface_no_diff(self) -> None:
        """Document surface should not produce diff or file_paths."""
        ctx = assemble_context(
            facts={"document_text": "This agreement shall...", "title": "NDA"},
            surface="document",
        )
        assert ctx.diff is None
        assert ctx.files_changed == []
        assert ctx.surface == "document"
        assert "This agreement shall..." in (ctx.narrative or "")

    def test_document_narrative_uses_full_text(self) -> None:
        long_text = "Article 1. " * 100
        ctx = assemble_context(
            facts={"document_text": long_text},
            surface="document",
        )
        assert ctx.narrative is not None
        assert long_text in ctx.narrative


class TestEventSurface:
    """Context assembly for EVENT / human_action subjects."""

    def test_event_surface_uses_action(self) -> None:
        ctx = assemble_context(
            facts={"action": "register_overtime", "hours": 50, "employee_id": "E001"},
            surface="human_action",
        )
        assert ctx.diff is None
        assert ctx.surface == "human_action"
        assert ctx.narrative is not None
        assert "register_overtime" in ctx.narrative

    def test_event_surface_no_code_artifacts(self) -> None:
        ctx = assemble_context(
            facts={"action": "approve_leave"},
            surface="human_action",
        )
        assert ctx.files_changed == []
        assert ctx.file_paths == []
        assert ctx.languages == []


class TestContractSurface:
    """Context assembly for CLAUSE_SET / contract subjects."""

    def test_contract_surface_uses_clause_text(self) -> None:
        ctx = assemble_context(
            facts={"clause_text": "The indemnifying party shall...", "clause_type": "indemnity"},
            surface="contract",
        )
        assert ctx.diff is None
        assert ctx.surface == "contract"
        assert "indemnifying party" in (ctx.narrative or "")


class TestCodeSurfaceExplicit:
    """Explicit code surface still works as before."""

    def test_code_surface_parses_diff(self) -> None:
        diff = "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new"
        ctx = assemble_context(diff=diff, surface="code")
        assert ctx.diff == diff
        assert len(ctx.files_changed) >= 1

    def test_non_code_surface_ignores_diff_parsing(self) -> None:
        """Even if diff text is passed with a non-code surface, it should not
        be parsed into file_paths/languages (the diff is irrelevant)."""
        ctx = assemble_context(
            diff="some random text",
            surface="transaction",
            facts={"amount": 100},
        )
        assert ctx.diff is None
        assert ctx.files_changed == []


class TestAssembleContextFromSubject:
    """Tests for the polymorphic assemble_context_from_subject entry point."""

    def test_code_diff_subject(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.CODE_DIFF,
            payload={"diff": "diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-old\n+new"},
        )
        ctx = assemble_context_from_subject(subject)
        assert ctx.diff is not None
        assert ctx.surface == "code"

    def test_transaction_subject(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.TRANSACTION,
            payload={"amount_jpy": 200000, "category": "entertainment"},
        )
        ctx = assemble_context_from_subject(subject)
        assert ctx.diff is None
        assert ctx.surface == "transaction"
        assert ctx.facts["amount_jpy"] == 200000

    def test_document_subject(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.DOCUMENT,
            payload={"text": "This contract states..."},
        )
        ctx = assemble_context_from_subject(subject)
        assert ctx.diff is None
        assert ctx.surface == "document"
        assert "This contract states..." in (ctx.narrative or "")

    def test_event_subject(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.EVENT,
            payload={"action": "overtime_registration", "hours": 60},
        )
        ctx = assemble_context_from_subject(subject)
        assert ctx.diff is None
        assert ctx.surface == "human_action"
        assert "overtime_registration" in (ctx.narrative or "")

    def test_clause_set_subject(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.CLAUSE_SET,
            payload={"text": "The vendor shall indemnify..."},
        )
        ctx = assemble_context_from_subject(subject)
        assert ctx.diff is None
        assert ctx.surface == "contract"

    def test_creative_subject(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.CREATIVE,
            payload={"body": "Dear customer, we recommend..."},
        )
        ctx = assemble_context_from_subject(subject)
        assert ctx.surface == "message"

    def test_decision_subject(self) -> None:
        subject = EvaluationSubject(
            kind=SubjectKind.DECISION,
            payload={"decision": "approve_merger", "rationale": "synergy"},
        )
        ctx = assemble_context_from_subject(subject)
        assert ctx.surface == "generic"
