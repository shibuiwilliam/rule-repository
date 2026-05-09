"""Subject-Aware Evaluation Engine — the core product differentiator.

Evaluates any Subject (code change, contract clause, HR event, transaction,
document, message) against natural-language rules via LLM-as-Judge.

Layout:
  - core/     — surface-agnostic evaluation logic (must not import from surfaces/)
  - surfaces/ — per-surface adapters and prompt hints
  - *.py      — legacy flat modules (backwards-compatible, delegated to by core/)

See CLAUDE.md §7.2, §14.2.
"""
