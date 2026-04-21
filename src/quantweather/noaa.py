from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

from .domain import ForecastSnapshot, WeatherMetric


JsonFetcher = Callable[[str], dict[str, Any]]


def fetch_noaa_forecast(
    latitude: float,
    longitude: float,
    location: str,
    *,
    user_agent: str,
    fetch_json: JsonFetcher | None = None,
) -> ForecastSnapshot:
    if not user_agent.strip():
        raise ValueError("NOAA requests require a descriptive User-Agent")

    fetcher = fetch_json or _urlopen_json(user_agent)
    point_url = f"https://api.weather.gov/points/{latitude:.4f},{longitude:.4f}"
    point_payload = fetcher(point_url)
    forecast_url = point_payload.get("properties", {}).get("forecast")
    if not isinstance(forecast_url, str) or not forecast_url:
        raise ValueError("NOAA points response did not include a forecast URL")

    forecast_payload = fetcher(forecast_url)
    return normalize_noaa_forecast_payload(forecast_payload, location=location)


def load_noaa_forecasts_from_fixture(path: str | Path) -> list[ForecastSnapshot]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "locations" in payload:
        locations = payload["locations"]
        if not isinstance(locations, list):
            raise ValueError("NOAA fixture locations must be a list")
        return [
            normalize_noaa_forecast_payload(item["forecast"], location=item["location"])
            for item in locations
        ]
    if isinstance(payload, dict):
        location = payload.get("location")
        forecast_payload = payload.get("forecast", payload)
        if not isinstance(location, str):
            raise ValueError("NOAA fixture must include a location")
        return [normalize_noaa_forecast_payload(forecast_payload, location=location)]
    raise ValueError("NOAA fixture must be an object")


def normalize_noaa_forecast_payload(payload: dict[str, Any], *, location: str) -> ForecastSnapshot:
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("NOAA forecast payload missing properties")

    periods = properties.get("periods")
    if not isinstance(periods, list) or not periods:
        raise ValueError("NOAA forecast payload missing periods")

    daytime_periods = [period for period in periods if period.get("isDaytime") is True]
    selected = daytime_periods[0] if daytime_periods else periods[0]
    if not isinstance(selected, dict):
        raise ValueError("NOAA forecast period must be an object")

    temperature = selected.get("temperature")
    if not isinstance(temperature, (int, float)):
        raise ValueError("NOAA forecast period missing numeric temperature")

    metrics = {WeatherMetric.TEMPERATURE_HIGH_F: float(temperature)}
    precip_probability = _nested_value(selected, "probabilityOfPrecipitation", "value")
    if isinstance(precip_probability, (int, float)):
        metrics[WeatherMetric.PRECIPITATION_PROBABILITY] = float(precip_probability) / 100.0

    precip_inches = _precip_inches(selected)
    if precip_inches is not None:
        metrics[WeatherMetric.PRECIPITATION_IN] = precip_inches

    observed_at = selected.get("startTime") or properties.get("generatedAt") or properties.get("updateTime")
    if not isinstance(observed_at, str) or not observed_at:
        raise ValueError("NOAA forecast payload missing period start time")

    return ForecastSnapshot(
        source="noaa-nws",
        observed_at=_to_utc_z(observed_at),
        location=location,
        metrics=metrics,
        uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 5.0},
    )


def _urlopen_json(user_agent: str) -> JsonFetcher:
    def fetch(url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={
                "Accept": "application/geo+json, application/json",
                "User-Agent": user_agent,
            },
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    return fetch


def _nested_value(payload: dict[str, Any], key: str, child_key: str) -> Any:
    value = payload.get(key)
    if not isinstance(value, dict):
        return None
    return value.get(child_key)


def _precip_inches(period: dict[str, Any]) -> float | None:
    amount = _nested_value(period, "quantitativePrecipitation", "value")
    if not isinstance(amount, (int, float)):
        return None
    unit = str(_nested_value(period, "quantitativePrecipitation", "unitCode") or "")
    if "mm" in unit.lower():
        return round(float(amount) / 25.4, 4)
    return float(amount)


def _to_utc_z(value: str) -> str:
    if value.endswith("Z") and "T" in value:
        return value
    if "+" in value:
        return value.split("+", 1)[0] + "Z"
    if value.count("-") >= 3:
        prefix, _, _offset = value.rpartition("-")
        return prefix + "Z"
    return value
