# Structured Auto-Remediation

When the evaluation engine detects a violation, it returns **machine-readable `Remediation` objects** alongside the traditional `fix_suggestion` text. These structured objects specify the exact file, line, and code change needed to fix the violation, enabling agents and CI pipelines to apply fixes automatically.

## Remediation Object

Each remediation specifies:

| Field | Type | Description |
|---|---|---|
| `type` | string | `replace`, `insert`, or `delete` |
| `file_path` | string | Target file path |
| `start_line` | int | Line to modify (1-indexed) |
| `end_line` | int or null | End line for multi-line changes |
| `original` | string or null | Current code (for replace/delete) |
| `replacement` | string or null | New code (for replace/insert) |
| `description` | string | Human-readable explanation of the fix |
| `auto_applicable` | boolean | True if safe to apply without human review |

## Auto-Applicable Flag

The `auto_applicable` flag is set to `true` only when:
- The rule modality is SHOULD (not MUST or MUST_NOT)
- The fix is unambiguous (single clear change)
- The change is low-risk (adding annotations, imports, docstrings)

MUST-level violations always require human review (`auto_applicable=false`).

## How It Works

### LLM Prompt

The `evaluate_code_change.txt` prompt instructs Gemini to return structured remediations in the JSON schema:

```json
{
  "verdict": "DENY",
  "remediations": [
    {
      "type": "replace",
      "file_path": "src/api/handler.py",
      "start_line": 42,
      "original": "def process(data):",
      "replacement": "def process(data: RequestModel) -> ResponseModel:",
      "description": "Add type annotations",
      "auto_applicable": true
    }
  ]
}
```

### Parsing

`evaluation_core.py` extracts remediations from the LLM response and constructs `Remediation` dataclass instances on each `RuleVerdict`.

### API Response

The `POST /api/v1/evaluate` response includes:

```json
{
  "overall_verdict": "DENY",
  "rule_verdicts": [
    {
      "rule_id": "...",
      "verdict": "DENY",
      "remediations": [{ "type": "replace", "file_path": "...", ... }]
    }
  ],
  "remediations": [...],
  "auto_fixable_count": 3
}
```

The top-level `remediations` array aggregates all remediations across all rule verdicts. `auto_fixable_count` is the number with `auto_applicable=true`.

## Domain Model

`domain/evaluation.py`:

```python
@dataclass(frozen=True)
class Remediation:
    type: str
    file_path: str
    start_line: int
    end_line: int | None = None
    original: str | None = None
    replacement: str | None = None
    description: str = ""
    auto_applicable: bool = False
```

`RuleVerdict` includes `remediations: list[Remediation]`.

## See Also

- [Evaluation Engine](evaluation-engine.md) -- the full evaluation pipeline
- [CLI Tools](../sdks/cli.md) -- future `--auto-fix` flag for `rulerepo-check`
