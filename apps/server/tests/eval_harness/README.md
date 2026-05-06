# Eval Harness

Golden test sets for evaluating LLM-driven features.

## Structure

```
eval_harness/
├── golden/
│   ├── rule_extraction/          # Input documents → expected extracted rules
│   │   ├── <name>.input.txt      # Source document
│   │   └── <name>.expected.json  # Expected extracted rules
│   └── verdict/                  # Evaluation inputs → expected verdicts
│       ├── <name>.input.json     # Evaluation context
│       └── <name>.expected.json  # Expected verdict
├── runner.py                     # Harness runner
├── baseline.json                 # Baseline accuracy metrics
└── README.md
```

## Running

```bash
# Dry run (no LLM calls)
uv run python -m tests.eval_harness.runner

# With live LLM (requires GEMINI_API_KEY)
RULEREPO_LIVE_LLM=1 uv run pytest tests/eval_harness/ -v
```

## Adding Cases

1. Add `<name>.input.*` and `<name>.expected.json` to the appropriate golden/ subdirectory.
2. Run the harness with `--live-llm` to verify.
3. Update `baseline.json` if metrics improve.

## CI Integration

The harness runs nightly with `RULEREPO_LIVE_LLM=1`. CI fails if accuracy
regresses more than 5 percentage points from baseline.
