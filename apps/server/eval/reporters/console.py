"""Console reporter — prints eval harness results as a formatted table."""

from __future__ import annotations

import sys
from typing import IO

from ..models import HarnessReport


class ConsoleReporter:
    """Prints a HarnessReport as a human-readable table to a stream."""

    def print_report(self, report: HarnessReport, *, stream: IO[str] | None = None) -> None:
        """Print the harness report as a formatted table.

        Args:
            report: The HarnessReport to render.
            stream: Output stream (defaults to sys.stdout).
        """
        out = stream or sys.stdout
        header = f"{'Domain':<16} {'Total':>6} {'Correct':>8} {'Prec':>7} {'Recall':>7} {'F1':>7} {'Avg ms':>9}"
        separator = "-" * len(header)

        out.write("\n")
        out.write(f"  Eval Harness Run: {report.run_id}\n")
        out.write(f"  Timestamp:        {report.timestamp}\n")
        if report.model_ids:
            out.write(f"  Models:           {', '.join(report.model_ids)}\n")
        out.write("\n")
        out.write(f"  {header}\n")
        out.write(f"  {separator}\n")

        for domain_report in report.domains:
            row = (
                f"{domain_report.domain:<16} "
                f"{domain_report.total:>6} "
                f"{domain_report.correct_verdict:>8} "
                f"{domain_report.precision:>7.4f} "
                f"{domain_report.recall:>7.4f} "
                f"{domain_report.f1:>7.4f} "
                f"{domain_report.avg_latency_ms:>9.2f}"
            )
            out.write(f"  {row}\n")

        out.write(f"  {separator}\n")
        total_cases = sum(d.total for d in report.domains)
        total_correct = sum(d.correct_verdict for d in report.domains)
        out.write(f"  {'OVERALL':<16} {total_cases:>6} {total_correct:>8} {'':>7} {'':>7} {report.overall_f1:>7.4f}\n")
        out.write("\n")

        # Per-domain failure details
        for domain_report in report.domains:
            failures = [r for r in domain_report.cases if not r.match_verdict]
            errors = [r for r in domain_report.cases if r.error is not None]

            if failures or errors:
                out.write(f"  [{domain_report.domain}] Failures ({len(failures)}):\n")
                for f in failures[:10]:
                    out.write(f"    - {f.case_id}: expected != {f.actual_verdict}\n")
                if len(failures) > 10:
                    out.write(f"    ... and {len(failures) - 10} more\n")

                if errors:
                    out.write(f"  [{domain_report.domain}] Errors ({len(errors)}):\n")
                    for e in errors[:5]:
                        out.write(f"    - {e.case_id}: {e.error}\n")
                out.write("\n")
