from pathlib import Path
import unittest

from quantweather.domain import WeatherMetric
from quantweather.noaa import fetch_noaa_forecast, load_noaa_forecasts_from_fixture


FIXTURES_DIR = Path(__file__).parent / "fixtures"


class NoaaTests(unittest.TestCase):
    def test_loads_noaa_forecast_fixture_as_forecast_snapshot(self) -> None:
        forecasts = load_noaa_forecasts_from_fixture(FIXTURES_DIR / "noaa_forecast.json")

        self.assertEqual(len(forecasts), 1)
        forecast = forecasts[0]
        self.assertEqual(forecast.source, "noaa-nws")
        self.assertEqual(forecast.location, "New York City")
        self.assertEqual(forecast.observed_at, "2026-04-20T06:00:00Z")
        self.assertEqual(forecast.metrics[WeatherMetric.TEMPERATURE_HIGH_F], 83.0)
        self.assertEqual(forecast.metrics[WeatherMetric.PRECIPITATION_PROBABILITY], 0.2)
        self.assertAlmostEqual(forecast.metrics[WeatherMetric.PRECIPITATION_IN], 0.1)

    def test_fetch_noaa_forecast_uses_points_endpoint_then_forecast_url(self) -> None:
        calls: list[str] = []

        def fetch_json(url: str):
            calls.append(url)
            if url.startswith("https://api.weather.gov/points/"):
                return {"properties": {"forecast": "https://api.weather.gov/gridpoints/OKX/33,37/forecast"}}
            return {
                "properties": {
                    "periods": [
                        {
                            "startTime": "2026-04-20T06:00:00-04:00",
                            "isDaytime": True,
                            "temperature": 81,
                        }
                    ]
                }
            }

        forecast = fetch_noaa_forecast(
            40.7128,
            -74.0060,
            "New York City",
            user_agent="QuantWeather tests",
            fetch_json=fetch_json,
        )

        self.assertEqual(calls[0], "https://api.weather.gov/points/40.7128,-74.0060")
        self.assertEqual(calls[1], "https://api.weather.gov/gridpoints/OKX/33,37/forecast")
        self.assertEqual(forecast.metrics[WeatherMetric.TEMPERATURE_HIGH_F], 81.0)


if __name__ == "__main__":
    unittest.main()
