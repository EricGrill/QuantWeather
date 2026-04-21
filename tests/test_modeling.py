import unittest

from quantweather.domain import Comparator, EventRule, ForecastSnapshot, WeatherMetric
from quantweather.modeling import estimate_probability


class EstimateProbabilityTests(unittest.TestCase):
    def test_temperature_probability_increases_above_threshold(self) -> None:
        rule = EventRule(
            metric=WeatherMetric.TEMPERATURE_HIGH_F,
            comparator=Comparator.GREATER_EQUAL,
            threshold=80.0,
            location="New York City",
            market_question="New York City high at or above 80F?",
        )
        forecast = ForecastSnapshot(
            source="test",
            observed_at="2026-04-20T12:00:00Z",
            location="New York City",
            metrics={WeatherMetric.TEMPERATURE_HIGH_F: 84.0},
            uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
        )

        estimate = estimate_probability(rule, forecast)

        self.assertGreater(estimate.probability_yes, 0.5)
        self.assertGreaterEqual(estimate.confidence, 0.2)

    def test_precipitation_probability_uses_precip_metrics(self) -> None:
        rule = EventRule(
            metric=WeatherMetric.PRECIPITATION_IN,
            comparator=Comparator.GREATER_EQUAL,
            threshold=0.5,
            location="Boston",
            market_question="Boston rainfall at or above 0.5 inches?",
        )
        forecast = ForecastSnapshot(
            source="test",
            observed_at="2026-04-20T12:00:00Z",
            location="Boston",
            metrics={
                WeatherMetric.PRECIPITATION_IN: 0.75,
                WeatherMetric.PRECIPITATION_PROBABILITY: 0.7,
            },
        )

        estimate = estimate_probability(rule, forecast)

        self.assertGreaterEqual(estimate.probability_yes, 0.7)
        self.assertIn("precip_probability", estimate.inputs)

    def test_location_mismatch_raises(self) -> None:
        rule = EventRule(
            metric=WeatherMetric.TEMPERATURE_HIGH_F,
            comparator=Comparator.GREATER_EQUAL,
            threshold=70.0,
            location="Chicago",
            market_question="Chicago high at or above 70F?",
        )
        forecast = ForecastSnapshot(
            source="test",
            observed_at="2026-04-20T12:00:00Z",
            location="New York City",
            metrics={WeatherMetric.TEMPERATURE_HIGH_F: 71.0},
        )

        with self.assertRaises(ValueError):
            estimate_probability(rule, forecast)


if __name__ == "__main__":
    unittest.main()
