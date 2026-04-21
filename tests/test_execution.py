import unittest

from quantweather.execution import build_execution_orders, execution_summary


class ExecutionTests(unittest.TestCase):
    def test_builds_paper_order_for_approved_recommendation(self) -> None:
        records = [
            {
                "market_id": "m1",
                "final_status": "approved",
                "signal_side": "YES",
                "proposed_notional": 125.25,
                "market_probability_yes": 0.41,
            },
            {
                "market_id": "m2",
                "final_status": "blocked",
                "signal_side": None,
                "proposed_notional": 0.0,
                "market_probability_yes": 0.2,
            },
        ]

        orders = build_execution_orders(records)
        summary = execution_summary(orders)

        self.assertEqual(orders[0].status, "paper_filled")
        self.assertEqual(orders[0].side, "YES")
        self.assertEqual(orders[1].status, "skipped")
        self.assertEqual(summary["filled_count"], 1)
        self.assertEqual(summary["filled_notional"], 125.25)

    def test_rejects_non_paper_execution_without_adapter(self) -> None:
        with self.assertRaises(ValueError):
            build_execution_orders([], mode="live")


if __name__ == "__main__":
    unittest.main()
