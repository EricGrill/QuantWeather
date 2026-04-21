from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quantweather.cli import save_fixture_screen_run
from quantweather.report import render_run_comparison_report, render_screen_run_report
from quantweather.storage import (
    compare_latest_two_runs,
    list_screen_runs,
    load_latest_screen_run,
    summarize_latest_screen_run,
)


class ReportTests(unittest.TestCase):
    def test_render_screen_run_report_includes_core_sections(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            save_fixture_screen_run(output_dir)
            runs = list_screen_runs(output_dir)
            records = load_latest_screen_run(output_dir)
            summary = summarize_latest_screen_run(output_dir)

            report = render_screen_run_report(records, summary, runs[-1])

        self.assertIn("# QuantWeather Screen Report", report)
        self.assertIn("## Approved Opportunities", report)
        self.assertIn("fixture-nyc-high-80", report)
        self.assertIn("## Errors", report)
        self.assertIn("MISSING_FORECAST", report)

    def test_render_run_comparison_report_lists_changed_markets(self) -> None:
        comparison = {
            "older_record_count": 2,
            "newer_record_count": 2,
            "added_market_ids": [],
            "removed_market_ids": [],
            "changed_markets": [
                {
                    "market_id": "m1",
                    "old_status": "error",
                    "new_status": "approved",
                    "old_edge": None,
                    "new_edge": 0.2,
                    "old_reason_codes": ["MISSING_FORECAST"],
                    "new_reason_codes": ["RULE_PARSED", "SIGNAL_GENERATED"],
                }
            ],
        }

        report = render_run_comparison_report(
            comparison,
            {"run_id": "older-run"},
            {"run_id": "newer-run"},
        )

        self.assertIn("# QuantWeather Run Comparison", report)
        self.assertIn("`m1`: `error` -> `approved`", report)
        self.assertIn("MISSING_FORECAST", report)

    def test_render_run_comparison_report_handles_empty_changes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            save_fixture_screen_run(output_dir)
            save_fixture_screen_run(output_dir)
            comparison = compare_latest_two_runs(output_dir)
            runs = list_screen_runs(output_dir)

            report = render_run_comparison_report(
                comparison,
                runs[-2],
                runs[-1],
            )

        self.assertIn("## Changed Markets", report)
        self.assertIn("- None", report)


if __name__ == "__main__":
    unittest.main()
