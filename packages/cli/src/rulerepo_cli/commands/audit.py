"""rulerepo audit — audit log inspection and chain verification.

Implementation lives in rulerepo_cli.main:audit. This module re-exports
the command group for backwards compatibility with the commands/ layout.
"""

from rulerepo_cli.main import audit as main

__all__ = ["main"]
