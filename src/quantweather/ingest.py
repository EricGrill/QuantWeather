from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .domain import ForecastSnapshot, Market, WeatherMetric


_METRIC_ALIASES = {
    "temperature_high_f": WeatherMetric.TEMPERATURE_HIGH_F,
    "temperature_low_f": WeatherMetric.TEMPERATURE_LOW_F,
    "precipitation_in": WeatherMetric.PRECIPITATION_IN,
    "precipitation_probability": WeatherMetric.PRECIPITATION_PROBABILITY,
}


def _read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid string field: {key}")
    return value.strip()


def _require_probability(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"Missing or invalid numeric field: {key}")
    probability = float(value)
    if probability < 0.0 or probability > 1.0:
        raise ValueError(f"Probability field out of range: {key}")
    return probability


def _read_metrics(metrics: dict[str, Any]) -> dict[WeatherMetric, float]:
    normalized: dict[WeatherMetric, float] = {}
    for key, value in metrics.items():
        metric = _METRIC_ALIASES.get(key)
        if metric is None:
            continue
        if not isinstance(value, (int, float)):
            raise ValueError(f"Metric {key} must be numeric")
        normalized[metric] = float(value)
    if not normalized:
        raise ValueError("Forecast payload did not contain any supported metrics")
    return normalized


def _require_non_negative_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"Missing or invalid numeric field: {key}")
    number = float(value)
    if number < 0.0:
        raise ValueError(f"Numeric field must be non-negative: {key}")
    return number


def _require_utc_timestamp(payload: dict[str, Any], key: str) -> str:
    value = _require_string(payload, key)
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError(f"Invalid UTC timestamp field: {key}") from exc
    return value


def normalize_market_payload(payload: dict[str, Any]) -> Market:
    market_id = _require_string(payload, "market_id")
    title = _require_string(payload, "title")
    expires_at = _require_utc_timestamp(payload, "expires_at")
    yes_price = _require_probability(payload, "yes_price")
    no_price = _require_probability(payload, "no_price")

    liquidity = _require_non_negative_number(payload, "liquidity")
    spread = _require_non_negative_number(payload, "spread")
    rules_text = str(payload.get("rules_text", ""))
    return Market(
        market_id=market_id,
        title=title,
        yes_price=yes_price,
        no_price=no_price,
        liquidity=liquidity,
        spread=spread,
        expires_at=expires_at,
        rules_text=rules_text,
    )


def normalize_forecast_payload(payload: dict[str, Any]) -> ForecastSnapshot:
    source = _require_string(payload, "source")
    observed_at = _require_utc_timestamp(payload, "observed_at")
    location = _require_string(payload, "location")

    metrics_raw = payload.get("metrics")
    if not isinstance(metrics_raw, dict):
        raise ValueError("Missing or invalid metrics field")
    metrics = _read_metrics(metrics_raw)

    uncertainty_raw = payload.get("uncertainty", {})
    if not isinstance(uncertainty_raw, dict):
        raise ValueError("Uncertainty must be an object when provided")
    uncertainty = _read_metrics(uncertainty_raw) if uncertainty_raw else {}

    return ForecastSnapshot(
        source=source,
        observed_at=observed_at,
        location=location,
        metrics=metrics,
        uncertainty=uncertainty,
    )


def load_markets_from_fixture(path: str | Path) -> list[Market]:
    payload = _read_json(path)
    if isinstance(payload, dict):
        payload = payload.get("markets")
    if not isinstance(payload, list):
        raise ValueError("Market fixture must contain a list of market payloads")
    return [normalize_market_payload(item) for item in payload]


def load_forecasts_from_fixture(path: str | Path) -> list[ForecastSnapshot]:
    payload = _read_json(path)
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("Forecast fixture must contain a list of forecast payloads")
    return [normalize_forecast_payload(item) for item in payload]


def index_forecasts_by_location(
    forecasts: Iterable[ForecastSnapshot],
) -> dict[str, ForecastSnapshot]:
    return {forecast.location.lower(): forecast for forecast in forecasts}
