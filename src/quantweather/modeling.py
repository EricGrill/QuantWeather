from __future__ import annotations

from .domain import Comparator, EventRule, ForecastSnapshot, ProbabilityEstimate, WeatherMetric


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def estimate_probability(rule: EventRule, forecast: ForecastSnapshot) -> ProbabilityEstimate:
    if rule.location.lower() != forecast.location.lower():
        raise ValueError("Forecast location does not match market location")

    if rule.metric == WeatherMetric.TEMPERATURE_HIGH_F:
        mean = forecast.metrics[WeatherMetric.TEMPERATURE_HIGH_F]
        spread = forecast.uncertainty.get(WeatherMetric.TEMPERATURE_HIGH_F, 5.0)
        raw_probability = 0.5 + ((mean - rule.threshold) / max(spread, 1.0)) * 0.25
        probability_yes = _clamp(raw_probability)
        confidence = _clamp(1.0 - (spread / 20.0), 0.2, 0.95)
        rationale = "Temperature probability derived from forecast mean relative to threshold."
        inputs = {"mean_high_f": mean, "spread_f": spread, "threshold_f": rule.threshold}
    elif rule.metric == WeatherMetric.PRECIPITATION_IN:
        expected_precip = forecast.metrics[WeatherMetric.PRECIPITATION_IN]
        precip_chance = forecast.metrics.get(WeatherMetric.PRECIPITATION_PROBABILITY, 0.5)
        raw_probability = precip_chance * _clamp(expected_precip / max(rule.threshold, 0.01))
        probability_yes = _clamp(raw_probability)
        confidence = _clamp(0.4 + precip_chance * 0.5, 0.2, 0.95)
        rationale = "Precipitation probability combines expected precipitation and event chance."
        inputs = {
            "expected_precip_in": expected_precip,
            "precip_probability": precip_chance,
            "threshold_in": rule.threshold,
        }
    else:
        raise ValueError(f"Unsupported metric: {rule.metric}")

    if rule.comparator in {Comparator.LESS, Comparator.LESS_EQUAL}:
        probability_yes = 1.0 - probability_yes

    return ProbabilityEstimate(
        probability_yes=probability_yes,
        confidence=confidence,
        rationale=rationale,
        inputs=inputs,
    )
