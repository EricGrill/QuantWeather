import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quantweather.cli import save_fixture_screen_run
from quantweather.domain import ForecastSnapshot, Market, RiskLimits, WeatherMetric
from quantweather.engine import screen_markets
from quantweather.storage import (
    compare_latest_two_runs,
    list_screen_runs,
    load_latest_screen_run,
    load_screen_run,
    save_latest_dashboard,
    save_latest_comparison_report,
    save_latest_execution,
    save_latest_screen_report,
    persist_screen_run,
    summarize_latest_screen_run,
)


class StorageTests(unittest.TestCase):
    def test_save_fixture_screen_run_writes_run_and_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            run_path = save_fixture_screen_run(output_dir)

            self.assertTrue(run_path.exists())
            self.assertEqual(run_path.parent, output_dir)

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["runs"]), 1)
            self.assertEqual(manifest["runs"][0]["record_count"], 3)
            self.assertEqual(manifest["runs"][0]["approved_count"], 1)
            self.assertEqual(manifest["runs"][0]["error_count"], 2)

    def test_load_latest_screen_run_returns_latest_saved_payload(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            first = save_fixture_screen_run(output_dir)
            second = save_fixture_screen_run(output_dir)

            runs = list_screen_runs(output_dir)
            latest_payload = load_latest_screen_run(output_dir)
            loaded_first = load_screen_run(first)
            loaded_second = load_screen_run(second)

            self.assertEqual(len(runs), 2)
            self.assertEqual(latest_payload, loaded_second)
            self.assertNotEqual(loaded_first, [])

    def test_summarize_latest_screen_run_reports_top_edge_and_counts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            save_fixture_screen_run(output_dir)

            summary = summarize_latest_screen_run(output_dir)

            self.assertEqual(summary["record_count"], 3)
            self.assertEqual(summary["approved_count"], 1)
            self.assertEqual(summary["error_count"], 2)
            self.assertEqual(summary["top_edge_market_id"], "fixture-nyc-high-80")
            self.assertIn("MISSING_FORECAST", summary["reason_counts"])

    def test_compare_latest_two_runs_reports_market_changes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            limits = RiskLimits(
                max_trade_notional=200.0,
                max_market_exposure=300.0,
                max_daily_risk=500.0,
                min_confidence=0.45,
                min_edge=0.05,
                max_spread=0.05,
                min_liquidity=5000.0,
            )
            markets = [
                Market(
                    market_id="m1",
                    title="New York City high at or above 80F?",
                    yes_price=0.40,
                    no_price=0.63,
                    liquidity=20000.0,
                    spread=0.02,
                    expires_at="2026-04-22T00:00:00Z",
                ),
                Market(
                    market_id="m2",
                    title="Chicago high at or above 70F?",
                    yes_price=0.35,
                    no_price=0.68,
                    liquidity=12000.0,
                    spread=0.02,
                    expires_at="2026-04-22T00:00:00Z",
                ),
            ]
            forecasts_run_one = [
                ForecastSnapshot(
                    source="test",
                    observed_at="2026-04-20T12:00:00Z",
                    location="New York City",
                    metrics={WeatherMetric.TEMPERATURE_HIGH_F: 84.0},
                    uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
                )
            ]
            forecasts_run_two = [
                ForecastSnapshot(
                    source="test",
                    observed_at="2026-04-20T12:00:00Z",
                    location="New York City",
                    metrics={WeatherMetric.TEMPERATURE_HIGH_F: 81.0},
                    uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
                ),
                ForecastSnapshot(
                    source="test",
                    observed_at="2026-04-20T12:00:00Z",
                    location="Chicago",
                    metrics={WeatherMetric.TEMPERATURE_HIGH_F: 73.0},
                    uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
                ),
            ]

            run_one = screen_markets(
                markets=markets,
                forecasts=forecasts_run_one,
                risk_limits=limits,
                account_balance=4000.0,
            )
            run_two = screen_markets(
                markets=markets,
                forecasts=forecasts_run_two,
                risk_limits=limits,
                account_balance=4000.0,
            )

            persist_screen_run(run_one, output_dir, label="comparison")
            persist_screen_run(run_two, output_dir, label="comparison")

            comparison = compare_latest_two_runs(output_dir)

            self.assertEqual(comparison["older_record_count"], 2)
            self.assertEqual(comparison["newer_record_count"], 2)
            self.assertEqual(comparison["added_market_ids"], [])
            self.assertEqual(comparison["removed_market_ids"], [])
            self.assertEqual(len(comparison["changed_markets"]), 2)
            self.assertEqual(comparison["changed_markets"][0]["market_id"], "m1")
            self.assertEqual(comparison["changed_markets"][1]["market_id"], "m2")
            self.assertEqual(comparison["changed_markets"][1]["old_status"], "error")
            self.assertEqual(comparison["changed_markets"][1]["new_status"], "approved")

    def test_save_latest_screen_report_writes_markdown_and_updates_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            save_fixture_screen_run(output_dir)

            report_path = save_latest_screen_report(output_dir)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertTrue(report_path.exists())
            self.assertIn("## Approved Opportunities", report_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["runs"][-1]["screen_report_path"],
                str(report_path.relative_to(output_dir)),
            )

    def test_save_latest_comparison_report_writes_markdown_and_updates_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            save_fixture_screen_run(output_dir)
            save_fixture_screen_run(output_dir)

            report_path = save_latest_comparison_report(output_dir)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertTrue(report_path.exists())
            self.assertIn("# QuantWeather Run Comparison", report_path.read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["runs"][-1]["comparison_report_path"],
                str(report_path.relative_to(output_dir)),
            )

    def test_save_latest_dashboard_writes_html_and_updates_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            save_fixture_screen_run(output_dir)
            save_fixture_screen_run(output_dir)

            dashboard_path = save_latest_dashboard(output_dir)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertTrue(dashboard_path.exists())
            dashboard_html = dashboard_path.read_text(encoding="utf-8")
            self.assertIn("QuantWeather Manual Review Dashboard", dashboard_html)
            self.assertEqual(
                manifest["runs"][-1]["dashboard_path"],
                str(dashboard_path.relative_to(output_dir)),
            )
            self.assertIn(str(dashboard_path.relative_to(output_dir)), dashboard_html)
            self.assertIn("Analytics", dashboard_html)
            self.assertIn("Monitoring", dashboard_html)

    def test_save_latest_execution_writes_orders_and_updates_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "screen-runs"
            save_fixture_screen_run(output_dir)

            execution_path = save_latest_execution(output_dir)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            orders = json.loads(execution_path.read_text(encoding="utf-8"))

            self.assertTrue(execution_path.exists())
            self.assertEqual(manifest["runs"][-1]["execution_path"], str(execution_path.relative_to(output_dir)))
            self.assertEqual(manifest["runs"][-1]["execution_summary"]["filled_count"], 1)
            self.assertEqual(orders[0]["status"], "paper_filled")


if __name__ == "__main__":
    unittest.main()
