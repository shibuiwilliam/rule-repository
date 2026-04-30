"""rules.yaml — portable, version-controllable rule format.

Per PROJECT_IMPROVEMENT.md §3: a lightweight format that works without
a server, enabling zero-infrastructure rule evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class RuleEntry:
    """A single rule definition in rules.yaml."""

    id: str
    statement: str
    modality: str = "MUST"
    severity: str = "MEDIUM"
    scope: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class RulesYaml:
    """Top-level structure of a rules.yaml file."""

    version: int = 1
    project: str = ""
    rules: list[RuleEntry] = field(default_factory=list)


def load_rules_yaml(path: str | Path) -> RulesYaml:
    """Load and parse a rules.yaml file.

    Args:
        path: Path to the rules.yaml file.

    Returns:
        Parsed RulesYaml object.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the YAML is invalid.
    """
    p = Path(path)
    if not p.exists():
        msg = f"Rules file not found: {p}"
        raise FileNotFoundError(msg)

    with p.open() as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        msg = f"Invalid rules.yaml: expected a mapping, got {type(data).__name__}"
        raise ValueError(msg)

    rules = []
    for r in data.get("rules", []):
        if isinstance(r, dict) and "statement" in r:
            rules.append(
                RuleEntry(
                    id=r.get("id", ""),
                    statement=r["statement"],
                    modality=r.get("modality", "MUST"),
                    severity=r.get("severity", "MEDIUM"),
                    scope=r.get("scope", []),
                    tags=r.get("tags", []),
                    rationale=r.get("rationale", ""),
                )
            )

    return RulesYaml(
        version=data.get("version", 1),
        project=data.get("project", ""),
        rules=rules,
    )


def save_rules_yaml(data: RulesYaml, path: str | Path) -> None:
    """Write a RulesYaml object to a YAML file.

    Args:
        data: The rules data to write.
        path: Output file path.
    """
    output: dict[str, Any] = {
        "version": data.version,
        "project": data.project,
        "rules": [
            {
                "id": r.id,
                "statement": r.statement,
                "modality": r.modality,
                "severity": r.severity,
                **({"scope": r.scope} if r.scope else {}),
                **({"tags": r.tags} if r.tags else {}),
                **({"rationale": r.rationale} if r.rationale else {}),
            }
            for r in data.rules
        ],
    }

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
