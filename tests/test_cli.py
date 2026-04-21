import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "quantweather.cli", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def write_profile(path: Path, profile: dict) -> Path:
    path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    return path


class CliTests(unittest.TestCase):
    def test_screen_command_outputs_json(self) -> None:
        result = run_cli(
            "screen",
            "--format",
            "json",
            "--markets",
            str(REPO_ROOT / "tests" / "fixtures" / "markets_mixed.json"),
            "--forecasts",
            str(REPO_ROOT / "tests" / "fixtures" / "forecasts.json"),
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload), 3)
        self.assertEqual(payload[0]["final_status"], "approved")
        self.assertEqual(payload[1]["final_status"], "error")

    def test_save_run_persists_metadata(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = run_cli(
                "save-run",
                "--run-dir",
                tmpdir,
                "--label",
                "cli-test",
                "--markets",
                "tests/fixtures/markets_mixed.json",
                "--forecasts",
                "tests/fixtures/forecasts.json",
                "--account-balance",
                "7777",
                "--min-edge",
                "0.07",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            run_path = Path(result.stdout.strip())
            manifest = json.loads((Path(tmpdir) / "manifest.json").read_text(encoding="utf-8"))

            self.assertTrue(run_path.exists())
            self.assertEqual(manifest["runs"][-1]["label"], "cli-test")
            self.assertEqual(manifest["runs"][-1]["metadata"]["account_balance"], 7777.0)
            self.assertEqual(manifest["runs"][-1]["metadata"]["risk_limits"]["min_edge"], 0.07)
            self.assertEqual(
                manifest["runs"][-1]["metadata"]["markets_path"],
                str((REPO_ROOT / "tests" / "fixtures" / "markets_mixed.json").resolve()),
            )
            self.assertEqual(
                manifest["runs"][-1]["metadata"]["forecasts_path"],
                str((REPO_ROOT / "tests" / "fixtures" / "forecasts.json").resolve()),
            )

    def test_save_run_sanitizes_hostile_label(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = run_cli(
                "save-run",
                "--run-dir",
                tmpdir,
                "--label",
                "../escape",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            run_path = Path(result.stdout.strip())
            manifest = json.loads((Path(tmpdir) / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(run_path.parent.resolve(), Path(tmpdir).resolve())
            self.assertNotIn("..", run_path.name)
            self.assertEqual(manifest["runs"][-1]["path"], run_path.name)

    def test_screen_command_loads_arguments_from_json_config(self) -> None:
        with TemporaryDirectory() as tmpdir:
            profile_path = write_profile(
                Path(tmpdir) / "profile.json",
                {
                    "version": 1,
                    "name": "baseline",
                    "screen": {
                        "markets": str(REPO_ROOT / "tests" / "fixtures" / "markets_mixed.json"),
                        "forecasts": str(REPO_ROOT / "tests" / "fixtures" / "forecasts.json"),
                        "format": "json",
                        "account_balance": 5000.0,
                        "sizing_method": "proportional",
                        "risk_limits": {
                            "min_edge": 0.05,
                            "min_confidence": 0.45,
                            "max_spread": 0.05,
                            "max_trade_notional": 250.0,
                            "max_market_exposure": 400.0,
                            "max_daily_risk": 500.0,
                            "min_liquidity": 5000.0,
                        },
                    },
                },
            )

            result = run_cli("screen", "--config", str(profile_path))

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload), 3)
            self.assertEqual(payload[0]["final_status"], "approved")

    def test_cli_flags_override_json_config_values(self) -> None:
        with TemporaryDirectory() as tmpdir:
            profile_path = write_profile(
                Path(tmpdir) / "profile.json",
                {
                    "version": 1,
                    "name": "high-edge",
                    "screen": {
                        "markets": str(REPO_ROOT / "tests" / "fixtures" / "markets_mixed.json"),
                        "forecasts": str(REPO_ROOT / "tests" / "fixtures" / "forecasts.json"),
                        "risk_limits": {
                            "min_edge": 0.99,
                            "min_confidence": 0.45,
                            "max_spread": 0.05,
                            "max_trade_notional": 250.0,
                            "max_market_exposure": 400.0,
                            "max_daily_risk": 500.0,
                            "min_liquidity": 5000.0,
                        },
                    },
                    "save_run": {"label": "profile-label"},
                },
            )

            result = run_cli(
                "save-run",
                "--config",
                str(profile_path),
                "--run-dir",
                tmpdir,
                "--min-edge",
                "0.07",
                "--label",
                "override-label",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            manifest = json.loads((Path(tmpdir) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["runs"][-1]["label"], "override-label")
            self.assertEqual(manifest["runs"][-1]["metadata"]["risk_limits"]["min_edge"], 0.07)
            self.assertEqual(manifest["runs"][-1]["metadata"]["config_path"], str(profile_path.resolve()))

    def test_screen_fails_cleanly_when_config_is_invalid(self) -> None:
        with TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "bad.json"
            profile_path.write_text("{not json}\n", encoding="utf-8")

            result = run_cli("screen", "--config", str(profile_path))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Expecting property name enclosed in double quotes", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_screen_fails_cleanly_when_config_file_is_missing(self) -> None:
        missing_path = REPO_ROOT / "tests" / "fixtures" / "missing-profile.json"

        result = run_cli("screen", "--config", str(missing_path))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unable to read config file", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_screen_rejects_invalid_config_probability(self) -> None:
        with TemporaryDirectory() as tmpdir:
            profile_path = write_profile(
                Path(tmpdir) / "profile.json",
                {
                    "version": 1,
                    "screen": {
                        "markets": str(REPO_ROOT / "tests" / "fixtures" / "markets_mixed.json"),
                        "forecasts": str(REPO_ROOT / "tests" / "fixtures" / "forecasts.json"),
                        "risk_limits": {"min_confidence": 2.0},
                    },
                },
            )

            result = run_cli("screen", "--config", str(profile_path))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("between 0 and 1", result.stderr)

    def test_summary_uses_run_dir_from_config(self) -> None:
        with TemporaryDirectory() as tmpdir:
            profile_path = write_profile(
                Path(tmpdir) / "profile.json",
                {
                    "version": 1,
                    "run_dir": "./runs",
                    "screen": {
                        "markets": str(REPO_ROOT / "tests" / "fixtures" / "markets_mixed.json"),
                        "forecasts": str(REPO_ROOT / "tests" / "fixtures" / "forecasts.json"),
                    },
                },
            )

            save_result = run_cli("save-run", "--config", str(profile_path))
            summary_result = run_cli("summary", "--config", str(profile_path))

            self.assertEqual(save_result.returncode, 0, msg=save_result.stderr)
            self.assertEqual(summary_result.returncode, 0, msg=summary_result.stderr)

            payload = json.loads(summary_result.stdout)
            self.assertEqual(payload["record_count"], 3)
            self.assertEqual(payload["approved_count"], 1)

    def test_compare_command_fails_cleanly_with_one_run(self) -> None:
        with TemporaryDirectory() as tmpdir:
            save_result = run_cli("save-run", "--run-dir", tmpdir)
            self.assertEqual(save_result.returncode, 0, msg=save_result.stderr)

            compare_result = run_cli("compare", "--run-dir", tmpdir)

            self.assertNotEqual(compare_result.returncode, 0)
            self.assertIn("Need at least two saved screen runs to compare", compare_result.stderr)

    def test_screen_rejects_invalid_probability_arguments(self) -> None:
        result = run_cli("screen", "--min-confidence", "2.0")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("between 0 and 1", result.stderr)

    def test_report_commands_render_and_save_reports(self) -> None:
        with TemporaryDirectory() as tmpdir:
            self.assertEqual(run_cli("save-run", "--run-dir", tmpdir).returncode, 0)
            self.assertEqual(run_cli("save-run", "--run-dir", tmpdir).returncode, 0)

            report_result = run_cli("report", "--run-dir", tmpdir)
            compare_result = run_cli("comparison-report", "--run-dir", tmpdir)
            save_report_result = run_cli("report-save", "--run-dir", tmpdir)
            save_compare_result = run_cli("comparison-report-save", "--run-dir", tmpdir)

            self.assertEqual(report_result.returncode, 0, msg=report_result.stderr)
            self.assertEqual(compare_result.returncode, 0, msg=compare_result.stderr)
            self.assertEqual(save_report_result.returncode, 0, msg=save_report_result.stderr)
            self.assertEqual(save_compare_result.returncode, 0, msg=save_compare_result.stderr)

            saved_report = Path(save_report_result.stdout.strip())
            saved_compare = Path(save_compare_result.stdout.strip())

            self.assertIn("# QuantWeather Screen Report", report_result.stdout)
            self.assertIn("# QuantWeather Run Comparison", compare_result.stdout)
            self.assertTrue(saved_report.exists())
            self.assertTrue(saved_compare.exists())

    def test_dashboard_save_writes_html_artifact(self) -> None:
        with TemporaryDirectory() as tmpdir:
            self.assertEqual(run_cli("save-run", "--run-dir", tmpdir).returncode, 0)
            self.assertEqual(run_cli("save-run", "--run-dir", tmpdir).returncode, 0)

            dashboard_result = run_cli("dashboard-save", "--run-dir", tmpdir)

            self.assertEqual(dashboard_result.returncode, 0, msg=dashboard_result.stderr)
            dashboard_path = Path(dashboard_result.stdout.strip())
            self.assertTrue(dashboard_path.exists())
            html = dashboard_path.read_text(encoding="utf-8")
            self.assertIn("QuantWeather Manual Review Dashboard", html)
            self.assertIn("Latest Comparison", html)


if __name__ == "__main__":
    unittest.main()
