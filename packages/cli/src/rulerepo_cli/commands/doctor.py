"""rulerepo doctor — validate environment and connectivity.

Implementation lives in rulerepo_cli.main:doctor. This module re-exports
the command for backwards compatibility with the commands/ layout.
"""

from rulerepo_cli.main import doctor as main

__all__ = ["main"]
