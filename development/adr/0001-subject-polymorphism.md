# ADR 0001: Subject Polymorphism

## Status

Accepted

## Context

The Rule Repository evaluation pipeline was originally built around code diffs. The `evaluation_core.py` module dispatches to subject-specific prompts via `_SUBJECT_PROMPT_MAP`, `diff_parser.py` and `context_assembler.py` assume code-shaped inputs, and the `EvaluationService.evaluate()` method does not accept a `subject_kind` parameter.

Phase 7b introduced `SubjectType` enum, `EvaluationSubject` dataclass, and four adapters (`code_change`, `hr_event`, `contract_clause`, `expense_claim`). However, these diverge from the PROJECT.md specification in naming, protocol shape, and registry pattern:

| Current | PROJECT.md target |
|---|---|
| `SubjectType.CODE_CHANGE` | `SubjectKind.CODE_DIFF` |
| `SubjectType.HR_EVENT` | `SubjectKind.EVENT` |
| `SubjectType.CONTRACT_CLAUSE` | `SubjectKind.CLAUSE_SET` |
| `SubjectType.EXPENSE_CLAIM` | `SubjectKind.TRANSACTION` |
| String-keyed registries | Enum-keyed `@register` decorator |
| `EvaluationSubject` (payload dict) | `Subject` Protocol with `render_for_llm()`, `extract_features()`, `parse_remediation()`, `pii_fields`, `locale`, `jurisdiction` |
| `_SUBJECT_PROMPT_MAP` in `evaluation_core.py` | Subject adapters own their prompts |

This ADR formalizes the alignment to PROJECT.md and the migration path.

## Decision

### 1. Rename `SubjectType` to `SubjectKind`

Adopt the PROJECT.md enum values:

```python
class SubjectKind(str, Enum):
    CODE_DIFF = "code_diff"
    CLAUSE_SET = "clause_set"
    EVENT = "event"
    TRANSACTION = "transaction"
    CREATIVE = "creative"
    DECISION = "decision"
    IDENTITY = "identity"
    DOCUMENT = "document"
```

An Alembic migration updates stored `applicable_subject_types` values.

### 2. Upgrade the Subject Protocol

The `Subject` Protocol gains the fields and methods specified in CLAUDE.md SS11.1:

```python
class Subject(Protocol):
    kind: SubjectKind
    identifier: str
    facts: dict[str, Any]
    attachments: list[Attachment]
    locale: str | None
    jurisdiction: str | None
    pii_fields: list[str]

    def render_for_llm(self, format: PromptFormat) -> str: ...
    def extract_features(self) -> dict[str, Any]: ...
    def parse_remediation(self, raw: dict) -> Remediation | None: ...
```

Each subject adapter implements this protocol. The orchestrator calls `subject.render_for_llm()` instead of assembling prompts itself.

### 3. Decorator-based registry

```python
_REGISTRY: dict[SubjectKind, type[SubjectAdapter]] = {}

def register(kind: SubjectKind):
    def decorator(cls):
        _REGISTRY[kind] = cls
        return cls
    return decorator

def resolve(kind: SubjectKind) -> SubjectAdapter:
    if kind not in _REGISTRY:
        raise UnsupportedSubjectKindError(kind)
    return _REGISTRY[kind]()
```

### 4. Subject-agnostic orchestrator

`evaluation_core.py` and `service.py` must contain no `if subject.kind == ...` branching. All domain-specific logic lives in `services/evaluation/subjects/<kind>_subject.py`. The `_SUBJECT_PROMPT_MAP` dict is removed; each adapter returns its prompt via `render_for_llm()` or owns prompt files that the adapter references internally.

### 5. Backward compatibility

- `EvaluateRequest.subject_kind` defaults to `CODE_DIFF`.
- The existing `EvaluationSubject.from_legacy_diff()` shim is preserved until all callers migrate.
- All 418 existing tests must pass after the refactor.

## Migration

1. Rename enum values in code and DB (Alembic migration).
2. Upgrade `Subject` protocol with new fields/methods.
3. Switch registries to decorator pattern.
4. Move domain logic from `evaluation_core.py` into subject adapters.
5. Wire `subject_kind` through API → service → rule_selector → evaluation_core.
6. Verify all tests pass.

## Consequences

- Adding a new domain means implementing one adapter class, not modifying the orchestrator.
- Prompt templates are owned by adapters, not the orchestrator.
- The registry pattern makes it impossible to accidentally bypass subject dispatch.
- DB migration required for existing `applicable_subject_types` values.
