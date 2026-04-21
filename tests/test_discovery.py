from pathlib import Path
import unittest

from quantweather.discovery import (
    discover_weather_markets,
    discovery_decisions_to_json,
    load_market_discovery_payload,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DiscoveryTests(unittest.TestCase):
    def test_discovers_only_parseable_markets_that_pass_filters(self) -> None:
        payload = load_market_discovery_payload(FIXTURES_DIR / "markets_mixed.json")

        decisions = discover_weather_markets(
            payload,
            min_liquidity=10000.0,
            max_spread=0.03,
            locations=["New York City", "Chicago"],
        )

        self.assertEqual([decision.market.market_id for decision in decisions], [
            "fixture-chicago-high-70",
            "fixture-nyc-high-80",
            "fixture-dallas-tornado",
        ])
        self.assertTrue(decisions[0].accepted)
        self.assertTrue(decisions[1].accepted)
        self.assertFalse(decisions[2].accepted)
        self.assertIn("UNSUPPORTED_MARKET_TITLE", decisions[2].reason_codes)

    def test_discovery_json_marks_rejected_markets(self) -> None:
        payload = load_market_discovery_payload(FIXTURES_DIR / "markets_mixed.json")

        output = discovery_decisions_to_json(discover_weather_markets(payload))

        self.assertIn('"accepted": false', output)
        self.assertIn("fixture-dallas-tornado", output)


if __name__ == "__main__":
    unittest.main()
