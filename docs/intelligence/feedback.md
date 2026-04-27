# Feedback Loop

The correction feedback loop captures how developers modify AI-suggested or rule-evaluated code, analyzes those corrections, and uses them to improve the rule corpus over time.

## How Corrections Are Captured

Corrections enter the system through two paths:

### PR-based capture

When a developer modifies code that was originally suggested by a rule evaluation (e.g., accepting an AI-generated fix but then adjusting it), the diff between the original suggestion and the final committed code is recorded as a correction.

### Hook-based capture

Agent hooks and CI integrations can submit corrections directly via the Feedback API when they detect that evaluated code was changed after evaluation.

## Analysis Types

Each correction is analyzed by Gemini to classify the type of improvement needed:

| Type | Description | Action |
|---|---|---|
| **new_rule** | The correction reveals a pattern not covered by any existing rule. | Proposes a new candidate rule for review. |
| **improve_existing** | The correction suggests an existing rule is too broad, too narrow, or imprecise. | Proposes an update to the matched rule's statement or metadata. |
| **adjust_scope** | The correction indicates a rule is being applied to the wrong files or contexts. | Proposes a scope adjustment (file patterns, tags, severity). |

## Flywheel Effect

The feedback loop creates a self-improving cycle:

1. Rules are evaluated against code changes.
2. Developers correct the evaluation results where needed.
3. Corrections are analyzed and classified.
4. Approved corrections create new rules or improve existing ones.
5. Improved rules produce better evaluations, reducing future corrections.

Over time, the rule corpus becomes more precise and generates fewer false positives.

## Stats and Monitoring

Feedback effectiveness is tracked at `GET /api/v1/feedback/stats`:

- **Total corrections** submitted and their breakdown by type and status.
- **Rules created** from feedback (new rules born from corrections).
- **Rules improved** from feedback (existing rules refined).
- **Top violated rules** -- rules that generate the most corrections, indicating they may need attention.

The [Intelligence Dashboard](dashboard.md) incorporates feedback metrics into the overall corpus health view.

## See Also

- [Feedback API](../api/feedback.md) -- endpoint details and request/response examples
- [Rule Discovery](../architecture/discovery.md) -- another path for new rule creation
- [Background Workers](../integrations/workers.md) -- scheduled feedback analysis job
