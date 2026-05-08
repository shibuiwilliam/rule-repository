"""JSON reporter — serializes a HarnessReport to a JSON file."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..models import HarnessReport


class JsonReporter:
    """Writes a HarnessReport as a JSON file for downstream consumption."""

    def write_report(
        self,
        report: HarnessReport,
        output_path: str | Path,
    ) -> None:
        """Serialize the report to a JSON file.

        Args:
            report: The HarnessReport to serialize.
            output_path: Filesystem path for the output JSON file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = asdict(report)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def to_json_string(self, report: HarnessReport) -> str:
        """Return the report as a JSON string.

        Args:
            report: The HarnessReport to serialize.

        Returns:
            JSON string representation.
        """
        return json.dumps(asdict(report), indent=2, default=str)
