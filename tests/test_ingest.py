from pathlib import Path
import unittest

from quantweather.domain import WeatherMetric
from quantweather.ingest import (
    index_forecasts_by_location,
    load_forecasts_from_fixture,
    load_markets_from_fixture,
    normalize_market_payload,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class IngestTests(unittest.TestCase):
    def test_loads_fixture_markets(self) -> None:
        markets = load_markets_from_fixture(FIXTURES_DIR / "markets.json")

        self.assertEqual(len(markets), 2)
        self.assertEqual(markets[0].market_id, "fixture-nyc-high-80")
        self.assertAlmostEqual(markets[0].yes_price, 0.41)

    def test_loads_fixture_forecasts_and_indexes_by_location(self) -> None:
        forecasts = load_forecasts_from_fixture(FIXTURES_DIR / "forecasts.json")
        forecast_index = index_forecasts_by_location(forecasts)

        self.assertEqual(len(forecasts), 2)
        self.assertIn("new york city", forecast_index)
        self.assertEqual(
            forecast_index["boston"].metrics[WeatherMetric.PRECIPITATION_IN],
            0.7,
        )

    def test_loads_single_forecast_object_fixture(self) -> None:
        forecasts = load_forecasts_from_fixture(FIXTURES_DIR / "forecast_single.json")

        self.assertEqual(len(forecasts), 1)
        self.assertEqual(forecasts[0].location, "New York City")

    def test_rejects_market_payload_without_required_id(self) -> None:
        with self.assertRaises(ValueError):
            normalize_market_payload(
                {
                    "title": "New York City high at or above 80F?",
                    "yes_price": 0.41,
                    "no_price": 0.62,
                    "expires_at": "2026-04-21T23:59:59Z",
                }
            )

    def test_normalizes_unsupported_market_titles_without_parsing_them(self) -> None:
        market = normalize_market_payload(
            {
                "market_id": "bad-market",
                "title": "Will there be a tornado warning in Dallas?",
                "yes_price": 0.20,
                "no_price": 0.83,
                "liquidity": 9000.0,
                "spread": 0.05,
                "expires_at": "2026-04-21T23:59:59Z",
            }
        )

        self.assertEqual(market.market_id, "bad-market")
        self.assertEqual(market.title, "Will there be a tornado warning in Dallas?")


if __name__ == "__main__":
    unittest.main()
