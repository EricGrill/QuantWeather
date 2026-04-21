from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quantweather.cli import save_fixture_screen_run
from quantweather.dashboard import render_dashboard_html, write_dashboard_html
from quantweather.storage import compare_latest_two_runs, list_screen_runs, load_latest_screen_run, summarize_latest_screen_run


class DashboardTests(unittest.TestCase):
    def test_render_dashboard_html_includes_key_sections(self) -> None:
        with TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "runs"
            save_fixture_screen_run(run_dir)
            save_fixture_screen_run(run_dir)
            runs = list_screen_runs(run_dir)
            latest_records = load_latest_screen_run(run_dir)
            latest_summary = summarize_latest_screen_run(run_dir)
            comparison = compare_latest_two_runs(run_dir)

            html = render_dashboard_html(runs, latest_records, latest_summary, comparison)

        self.assertIn("QuantWeather Manual Review Dashboard", html)
        self.assertIn("Approved Opportunities", html)
        self.assertIn("Errors", html)
        self.assertIn("Latest Comparison", html)
        self.assertIn("fixture-nyc-high-80", html)

    def test_write_dashboard_html_persists_file(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "dashboard.html"
            written = write_dashboard_html("<html><body>ok</body></html>\n", output_path)

            self.assertEqual(written, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("ok", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
