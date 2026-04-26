"""Unit tests for the context assembler."""

from rulerepo_server.services.evaluation.context_assembler import assemble_context


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
            ]
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
