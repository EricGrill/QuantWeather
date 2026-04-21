import unittest

from quantweather.domain import Comparator, Market, WeatherMetric
from quantweather.market_rules import parse_event_rule


class ParseEventRuleTests(unittest.TestCase):
    def test_parses_temperature_threshold_market(self) -> None:
        market = Market(
            market_id="1",
            title="New York City high at or above 80F?",
            yes_price=0.45,
            no_price=0.57,
            liquidity=10000.0,
            spread=0.02,
            expires_at="2026-04-22T00:00:00Z",
        )

        rule = parse_event_rule(market)

        self.assertEqual(rule.location, "New York City")
        self.assertEqual(rule.metric, WeatherMetric.TEMPERATURE_HIGH_F)
        self.assertEqual(rule.comparator, Comparator.GREATER_EQUAL)
        self.assertEqual(rule.threshold, 80.0)

    def test_parses_precipitation_threshold_market(self) -> None:
        market = Market(
            market_id="2",
            title="Boston rainfall at or above 0.5 inches?",
            yes_price=0.34,
            no_price=0.69,
            liquidity=8000.0,
            spread=0.03,
            expires_at="2026-04-22T00:00:00Z",
        )

        rule = parse_event_rule(market)

        self.assertEqual(rule.location, "Boston")
        self.assertEqual(rule.metric, WeatherMetric.PRECIPITATION_IN)
        self.assertEqual(rule.threshold, 0.5)

    def test_rejects_unsupported_market_titles(self) -> None:
        market = Market(
            market_id="3",
            title="Will there be a tornado warning in Dallas?",
            yes_price=0.20,
            no_price=0.83,
            liquidity=9000.0,
            spread=0.05,
            expires_at="2026-04-22T00:00:00Z",
        )

        with self.assertRaises(ValueError):
            parse_event_rule(market)


if __name__ == "__main__":
    unittest.main()
