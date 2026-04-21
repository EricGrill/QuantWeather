import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quantweather.cli import export_fixture_screen_json
from quantweather.domain import ForecastSnapshot, Market, RiskLimits, WeatherMetric
from quantweather.engine import evaluate_market, screen_markets
from quantweather.serialize import recommendation_to_dict, recommendations_to_json


class SerializeTests(unittest.TestCase):
    def test_recommendation_to_dict_converts_enums_to_strings(self) -> None:
        market = Market(
            market_id="m1",
            title="New York City high at or above 80F?",
            yes_price=0.40,
            no_price=0.63,
            liquidity=20000.0,
            spread=0.02,
            expires_at="2026-04-22T00:00:00Z",
        )
        forecast = ForecastSnapshot(
            source="test",
            observed_at="2026-04-20T12:00:00Z",
            location="New York City",
            metrics={
                WeatherMetric.TEMPERATURE_HIGH_F: 84.0,
                WeatherMetric.PRECIPITATION_IN: 0.0,
                WeatherMetric.PRECIPITATION_PROBABILITY: 0.1,
            },
            uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
        )
        limits = RiskLimits(
            max_trade_notional=200.0,
            max_market_exposure=300.0,
            max_daily_risk=500.0,
            min_confidence=0.45,
            min_edge=0.05,
            max_spread=0.05,
            min_liquidity=5000.0,
        )

        result = evaluate_market(
            market=market,
            forecast=forecast,
            risk_limits=limits,
            account_balance=4000.0,
        )

        payload = recommendation_to_dict(result.recommendation)

        self.assertEqual(payload["approval_state"], "review_required")
        self.assertEqual(payload["final_status"], "approved")
        self.assertEqual(payload["signal_side"], "YES")

    def test_recommendations_to_json_includes_error_records(self) -> None:
        markets = [
            Market(
                market_id="m2",
                title="Chicago high at or above 70F?",
                yes_price=0.35,
                no_price=0.68,
                liquidity=12000.0,
                spread=0.02,
                expires_at="2026-04-22T00:00:00Z",
            )
        ]
        forecasts = []
        limits = RiskLimits(
            max_trade_notional=200.0,
            max_market_exposure=300.0,
            max_daily_risk=500.0,
            min_confidence=0.45,
            min_edge=0.05,
            max_spread=0.05,
            min_liquidity=5000.0,
        )

        recommendations = screen_markets(
            markets=markets,
            forecasts=forecasts,
            risk_limits=limits,
            account_balance=4000.0,
        )
        payload = json.loads(recommendations_to_json(recommendations))

        self.assertEqual(payload[0]["final_status"], "error")
        self.assertEqual(payload[0]["reason_codes"], ["MISSING_FORECAST"])
        self.assertEqual(payload[0]["error_message"], "No forecast found for location: Chicago")

    def test_export_fixture_screen_json_writes_mixed_feed(self) -> None:
        with TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "fixture-screen.json"
            written_path = export_fixture_screen_json(output_path)

            self.assertEqual(written_path, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(payload), 3)
        self.assertEqual(payload[0]["final_status"], "approved")
        self.assertEqual(payload[1]["final_status"], "error")
        self.assertEqual(payload[1]["reason_codes"], ["UNSUPPORTED_MARKET_TITLE"])
        self.assertEqual(payload[2]["reason_codes"], ["MISSING_FORECAST"])


if __name__ == "__main__":
    unittest.main()
