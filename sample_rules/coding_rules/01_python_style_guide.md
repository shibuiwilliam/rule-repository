# Python Style Guide

**YourExampleSoftware** — SNS Web Backend

**Document ID:** ENG-001  
**Version:** 3.0  
**Effective Date:** 2025-04-01  
**Owner:** Backend Engineering Team  
**Review Cycle:** Quarterly

---

## 1. Language Version

- MUST use Python 3.13 or later.
- MUST use modern syntax: built-in generics (`list[str]`, `dict[str, int]`), union types with `|`, `match` statements where they improve clarity.
- MUST NOT use `from __future__ import annotations` in new code — use runtime-evaluable types instead.

## 2. Formatting

- MUST use `ruff` for both linting and formatting. No `black`, no `isort` — ruff covers both.
- MUST set line length to 100 characters in `pyproject.toml`.
- MUST NOT disable ruff rules without a justification comment.
- SHOULD keep files under 400 lines. If a module exceeds 400 lines, split it by responsibility.

## 3. Naming

- MUST use `snake_case` for functions, methods, and variables.
- MUST use `PascalCase` for classes and type aliases.
- MUST use `SCREAMING_SNAKE_CASE` for module-level constants.
- MUST use lowercase for module and package names (no hyphens, no underscores in package names).
- MUST NOT use single-letter variable names except in comprehensions (`[x for x in items]`) and loop counters (`for i, item in enumerate(...)` ).
- SHOULD use descriptive names that reveal intent: `user_timeline` over `ut`, `is_blocked` over `blocked`.

## 4. Type Hints

- MUST add type annotations on all public function signatures (arguments and return type).
- MUST pass `mypy --strict` on the `src/` directory.
- MUST NOT use `Any` without a justification comment explaining why a more specific type is impossible.
- SHOULD use `TypeAlias` for complex types used in more than two places.
- SHOULD prefer `Sequence[T]` over `list[T]` in function parameters when mutation is not needed.

## 5. Docstrings

- MUST write Google-style docstrings for all public functions, classes, and modules.
- MUST include `Args:`, `Returns:`, and `Raises:` sections when applicable.
- MUST NOT write docstrings that just restate the function name: `def get_user` → `"""Get user."""` is not acceptable.
- SHOULD include a usage example in docstrings for complex utility functions.

## 6. Imports

- MUST order imports: standard library → third-party → local application (ruff enforces this).
- MUST use absolute imports for cross-module references.
- MUST NOT use wildcard imports (`from module import *`).
- MUST NOT import from `__init__.py` of sibling packages — import from the specific module.
- SHOULD prefer explicit imports over module-level imports for large packages.

## 7. Functions and Methods

- MUST keep functions under 50 lines of executable code (excluding docstrings and blank lines).
- MUST keep cyclomatic complexity under 10 per function. Refactor with early returns or extraction.
- MUST NOT use mutable default arguments (`def f(items=[])` → use `def f(items: list[str] | None = None)`).
- SHOULD limit function parameters to 5. Use a dataclass or Pydantic model for more.
- SHOULD prefer pure functions (no side effects) for business logic.

## 8. Classes

- MUST prefer composition over inheritance. Use inheritance only for genuine "is-a" relationships.
- MUST NOT create God classes (> 10 public methods). Split by responsibility.
- SHOULD use `@dataclass` or Pydantic `BaseModel` instead of plain classes for data containers.
- SHOULD use `__slots__` on classes that will have many instances (e.g., domain models in hot paths).

## 9. String Formatting

- MUST use f-strings for string formatting in application code.
- MUST NOT use `%` formatting or `.format()` in new code.
- MUST use `.join()` for concatenating lists of strings, not `+` in a loop.
- MUST NOT embed f-strings in log calls — use structlog's native formatting: `logger.info("user_created", user_id=uid)`.

## 10. Exceptions

- Refer to ENG-006 (Error Handling & Logging) for the exception hierarchy.
- MUST NOT use bare `except:` or `except Exception:` without re-raising or logging.
- MUST NOT use exceptions for control flow in normal execution paths.

---

*Last reviewed: 2025-04-01 | Next review: 2025-07-01*
