# Rule Playground Enhancement — Multi-Mode Input Support

> Status: **COMPLETED**
> Date: 2026-04-29

---

## 1. Problem Statement

The Rule Playground frontend only supports code-based evaluation — a single "Sample Code" textarea that sends the `sample_code` parameter to the backend. However, the Rule Repository manages rules that go far beyond code: HR policies, contract clauses, expense rules, safety regulations, and business procedures.

The **backend already fully supports** scenario-based evaluation via the `sample_facts` parameter (which feeds into the `evaluate_facts.txt` prompt with both narrative and structured facts). The test runner also handles `input_type != "code"` correctly. The gap is entirely in the frontend.

This means users cannot test rules like "Monthly overtime MUST NOT exceed 45 hours" or "Travel expenses over $500 MUST have manager approval" in the playground, even though the backend handles them correctly.

---

## 2. Design

### Input Modes

Two tabs on the right panel:

| Mode | What the user enters | Backend parameter | Evaluation prompt |
|---|---|---|---|
| **Code** | Code snippet or diff | `sample_code` | `evaluate_code_change.txt` |
| **Scenario** | Narrative text + optional structured facts (key-value pairs) | `sample_facts: { narrative, ...facts }` | `evaluate_facts.txt` |

### Scenario Mode UX

- **Narrative** textarea: free-text description of the situation (e.g., "Employee John submitted 52 overtime hours for April 2026")
- **Facts** section: dynamic key-value pair editor with add/remove buttons (e.g., `employee_id: E001`, `overtime_hours: 52`, `month: 2026-04`)
- Facts are optional — narrative alone is sufficient for evaluation

### Why not three tabs?

Considered separating "Narrative" and "Structured Facts" into separate tabs, but:
- The backend `evaluate_facts.txt` prompt uses both narrative AND facts together
- Most real scenarios benefit from both: a natural-language description plus structured data points
- Two tabs keeps the UI clean and the mental model simple

---

## 3. Changes Required

### Frontend only — zero backend changes

| File | Change |
|---|---|
| `apps/frontend/lib/api.ts` | Add `sample_facts` to `playgroundEvaluate` parameter type |
| `apps/frontend/app/(dashboard)/playground/page.tsx` | Add input mode tabs, scenario mode with narrative + facts editor |

### What stays the same

- Backend API (`/api/v1/playground/evaluate`) — already accepts both params
- Backend service (`PlaygroundService.evaluate_sandbox`) — already handles both
- Evaluation engine — already selects the right prompt
- Schemas — `PlaygroundEvalRequest` already has both fields
- Test runner — already handles `input_type` routing

---

## 4. UX Details

### Tab Selector
- Positioned at the top of the right panel (replacing the "Sample Code" heading)
- Two buttons: "Code" and "Scenario"
- Active tab has blue background, inactive has gray border

### Code Tab (current behavior, preserved)
- Monospace textarea with "Paste code or diff here..." placeholder
- Sends `sample_code` to API

### Scenario Tab (new)
- **Narrative** section: regular textarea with placeholder "Describe the situation... e.g., An employee submitted 52 hours of overtime for April 2026."
- **Facts** section below: 
  - Header "Structured Facts (optional)" with an "Add Fact" button
  - Each fact is a row: key input + value input + remove button
  - Empty by default (facts are optional)
- Sends `sample_facts: { narrative: "...", key1: "val1", ... }` to API

### Result Panel
- Works identically for both modes
- Code locations section may be empty for scenario evaluations (expected)

---

## 5. Non-Goals

- No changes to the test case creation UI on rule detail pages (separate concern)
- No new backend endpoints or schema changes
- No changes to evaluation prompts
- No new dependencies
