import unittest

from quantweather.monitoring import monitor_execution_orders, monitor_screen_run


class MonitoringTests(unittest.TestCase):
    def test_monitor_screen_run_flags_high_error_rate(self) -> None:
        report = monitor_screen_run(
            [
                {"final_status": "approved"},
                {"final_status": "error"},
                {"final_status": "error"},
            ],
            max_error_rate=0.25,
        )

        self.assertFalse(report["healthy"])
        self.assertEqual(report["alerts"][0]["code"], "ERROR_RATE_HIGH")
        self.assertEqual(report["error_rate"], 0.6667)

    def test_monitor_execution_orders_warns_when_no_orders_fill(self) -> None:
        report = monitor_execution_orders([{"status": "skipped"}])

        self.assertTrue(report["healthy"])
        self.assertEqual(report["alerts"][0]["code"], "NO_FILLS")


if __name__ == "__main__":
    unittest.main()
