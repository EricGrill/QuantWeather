import unittest

from quantweather.analytics import analyze_run_history, analyze_screen_run


class AnalyticsTests(unittest.TestCase):
    def test_analyze_screen_run_reports_edge_and_expected_value(self) -> None:
        analytics = analyze_screen_run(
            [
                {
                    "final_status": "approved",
                    "edge": 0.2,
                    "proposed_notional": 100.0,
                    "reason_codes": ["SIGNAL_GENERATED"],
                },
                {
                    "final_status": "blocked",
                    "edge": 0.03,
                    "proposed_notional": 0.0,
                    "reason_codes": ["NO_EDGE"],
                },
            ]
        )

        self.assertEqual(analytics["approval_rate"], 0.5)
        self.assertEqual(analytics["average_edge"], 0.115)
        self.assertEqual(analytics["expected_edge_value"], 20.0)
        self.assertEqual(analytics["edge_buckets"]["15pct_plus"], 1)

    def test_analyze_run_history_totals_counts(self) -> None:
        analytics = analyze_run_history(
            [
                {"run_id": "a", "approved_count": 1, "blocked_count": 2, "error_count": 3},
                {"run_id": "b", "approved_count": 4, "blocked_count": 5, "error_count": 6},
            ]
        )

        self.assertEqual(analytics["latest_run_id"], "b")
        self.assertEqual(analytics["approved_count"], 5)
        self.assertEqual(analytics["error_count"], 9)


if __name__ == "__main__":
    unittest.main()
