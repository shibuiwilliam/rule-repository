"""Unit tests for the unified diff parser."""

from rulerepo_server.services.evaluation.diff_parser import (
    detect_functions,
    detect_language,
    parse_unified_diff,
)

SAMPLE_DIFF = """\
diff --git a/src/api/handlers/payment.py b/src/api/handlers/payment.py
new file mode 100644
--- /dev/null
+++ b/src/api/handlers/payment.py
@@ -0,0 +1,15 @@
+from fastapi import APIRouter
+
+router = APIRouter()
+
+async def process_refund(data: dict):
+    amount = data["amount"]
+    if amount <= 0:
+        raise ValueError("Invalid amount")
+    return {"status": "refunded", "amount": amount}
diff --git a/tests/test_payment.py b/tests/test_payment.py
--- a/tests/test_payment.py
+++ b/tests/test_payment.py
@@ -1,4 +1,8 @@
 def test_payment():
     pass
+
+def test_refund():
+    result = process_refund({"amount": 100})
+    assert result["status"] == "refunded"
"""


class TestParseUnifiedDiff:
    def test_parses_multiple_files(self) -> None:
        files = parse_unified_diff(SAMPLE_DIFF)
        assert len(files) == 2

    def test_detects_new_file(self) -> None:
        files = parse_unified_diff(SAMPLE_DIFF)
        payment = next(f for f in files if "payment.py" in f.path and "test" not in f.path)
        assert payment.change_type == "added"

    def test_detects_modified_file(self) -> None:
        files = parse_unified_diff(SAMPLE_DIFF)
        test_file = next(f for f in files if "test_payment" in f.path)
        assert test_file.change_type == "modified"

    def test_extracts_file_paths(self) -> None:
        files = parse_unified_diff(SAMPLE_DIFF)
        paths = {f.path for f in files}
        assert "src/api/handlers/payment.py" in paths
        assert "tests/test_payment.py" in paths

    def test_detects_language(self) -> None:
        files = parse_unified_diff(SAMPLE_DIFF)
        for f in files:
            assert f.language == "python"

    def test_detects_functions(self) -> None:
        files = parse_unified_diff(SAMPLE_DIFF)
        payment = next(f for f in files if "payment.py" in f.path and "test" not in f.path)
        assert "process_refund" in payment.functions_touched

    def test_has_diff_hunks(self) -> None:
        files = parse_unified_diff(SAMPLE_DIFF)
        for f in files:
            assert len(f.diff_hunks) > 0

    def test_empty_diff(self) -> None:
        assert parse_unified_diff("") == []
        assert parse_unified_diff("   ") == []


class TestDetectLanguage:
    def test_python(self) -> None:
        assert detect_language("src/main.py") == "python"

    def test_typescript(self) -> None:
        assert detect_language("app/page.tsx") == "typescript"

    def test_unknown(self) -> None:
        assert detect_language("Makefile") is None


class TestDetectFunctions:
    def test_python_def(self) -> None:
        diff = "+def process_refund(data):\n+    pass"
        assert "process_refund" in detect_functions(diff)

    def test_python_async_def(self) -> None:
        diff = "+async def handle_request(req):\n+    pass"
        assert "handle_request" in detect_functions(diff)

    def test_class(self) -> None:
        diff = "+class PaymentHandler:\n+    pass"
        assert "PaymentHandler" in detect_functions(diff)

    def test_no_functions(self) -> None:
        assert detect_functions("+ x = 1\n+ y = 2") == []
