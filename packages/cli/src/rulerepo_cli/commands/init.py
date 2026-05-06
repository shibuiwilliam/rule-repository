"""rulerepo init — zero-config bootstrap for a new project.

Implementation lives in rulerepo_cli.main:init. This module re-exports
the command for backwards compatibility with the commands/ layout.
"""

from rulerepo_cli.main import init as main

__all__ = ["main"]
