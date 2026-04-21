import unittest

from quantweather.domain import ForecastSnapshot, Market, RiskLimits, WeatherMetric
from quantweather.engine import evaluate_market, screen_markets


class EvaluateMarketTests(unittest.TestCase):
    def test_generates_signal_and_position_for_eligible_market(self) -> None:
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

        self.assertIsNotNone(result.signal)
        self.assertTrue(result.proposal.approved)
        self.assertGreater(result.proposal.notional, 0.0)
        self.assertEqual(result.recommendation.schema_version, "v1")
        self.assertTrue(result.recommendation.evaluation_id)
        self.assertTrue(result.recommendation.evaluated_at.endswith("Z"))
        self.assertEqual(result.recommendation.approval_state.value, "review_required")
        self.assertEqual(result.recommendation.final_status.value, "approved")
        self.assertIn("SIGNAL_GENERATED", result.recommendation.reason_codes)
        self.assertIn("PROPOSAL_READY_FOR_REVIEW", result.recommendation.reason_codes)

    def test_blocks_trade_when_spread_is_too_wide(self) -> None:
        market = Market(
            market_id="m2",
            title="New York City high at or above 80F?",
            yes_price=0.40,
            no_price=0.63,
            liquidity=20000.0,
            spread=0.08,
            expires_at="2026-04-22T00:00:00Z",
        )
        forecast = ForecastSnapshot(
            source="test",
            observed_at="2026-04-20T12:00:00Z",
            location="New York City",
            metrics={WeatherMetric.TEMPERATURE_HIGH_F: 84.0},
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

        self.assertFalse(result.proposal.approved)
        self.assertIn("Market spread exceeds configured maximum.", result.proposal.blocked_reasons)
        self.assertEqual(result.recommendation.approval_state.value, "blocked")
        self.assertEqual(result.recommendation.final_status.value, "blocked")
        self.assertIn("SPREAD_TOO_WIDE", result.recommendation.reason_codes)

    def test_screen_markets_returns_error_record_when_forecast_is_missing(self) -> None:
        markets = [
            Market(
                market_id="m3",
                title="Chicago high at or above 70F?",
                yes_price=0.35,
                no_price=0.68,
                liquidity=12000.0,
                spread=0.02,
                expires_at="2026-04-22T00:00:00Z",
            )
        ]
        forecasts = [
            ForecastSnapshot(
                source="test",
                observed_at="2026-04-20T12:00:00Z",
                location="New York City",
                metrics={WeatherMetric.TEMPERATURE_HIGH_F: 84.0},
                uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
            )
        ]
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

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].final_status.value, "error")
        self.assertIn("MISSING_FORECAST", recommendations[0].reason_codes)
        self.assertEqual(recommendations[0].location, "Chicago")

    def test_screen_markets_returns_error_record_for_unsupported_title(self) -> None:
        markets = [
            Market(
                market_id="m4",
                title="Will there be a tornado warning in Dallas?",
                yes_price=0.20,
                no_price=0.83,
                liquidity=9000.0,
                spread=0.04,
                expires_at="2026-04-22T00:00:00Z",
            )
        ]
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
            forecasts=[],
            risk_limits=limits,
            account_balance=4000.0,
        )

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0].final_status.value, "error")
        self.assertIn("UNSUPPORTED_MARKET_TITLE", recommendations[0].reason_codes)
        self.assertIsNotNone(recommendations[0].error_message)

    def test_screen_markets_sorts_approved_before_blocked_and_errors(self) -> None:
        markets = [
            Market(
                market_id="m5",
                title="New York City high at or above 80F?",
                yes_price=0.40,
                no_price=0.63,
                liquidity=20000.0,
                spread=0.02,
                expires_at="2026-04-22T00:00:00Z",
            ),
            Market(
                market_id="m6",
                title="Boston rainfall at or above 0.5 inches?",
                yes_price=0.90,
                no_price=0.14,
                liquidity=12000.0,
                spread=0.07,
                expires_at="2026-04-22T00:00:00Z",
            ),
            Market(
                market_id="m7",
                title="Will there be a tornado warning in Dallas?",
                yes_price=0.20,
                no_price=0.83,
                liquidity=9000.0,
                spread=0.04,
                expires_at="2026-04-22T00:00:00Z",
            ),
        ]
        forecasts = [
            ForecastSnapshot(
                source="test",
                observed_at="2026-04-20T12:00:00Z",
                location="New York City",
                metrics={
                    WeatherMetric.TEMPERATURE_HIGH_F: 84.0,
                    WeatherMetric.PRECIPITATION_IN: 0.0,
                    WeatherMetric.PRECIPITATION_PROBABILITY: 0.1,
                },
                uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
            ),
            ForecastSnapshot(
                source="test",
                observed_at="2026-04-20T12:00:00Z",
                location="Boston",
                metrics={
                    WeatherMetric.PRECIPITATION_IN: 0.6,
                    WeatherMetric.PRECIPITATION_PROBABILITY: 0.7,
                },
            ),
        ]
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

        self.assertEqual([record.market_id for record in recommendations], ["m5", "m6", "m7"])
        self.assertEqual(recommendations[0].final_status.value, "approved")
        self.assertEqual(recommendations[1].final_status.value, "blocked")
        self.assertEqual(recommendations[2].final_status.value, "error")


if __name__ == "__main__":
    unittest.main()
