from __future__ import annotations

import re

from .domain import Comparator, EventRule, Market, WeatherMetric


TEMPERATURE_PATTERN = re.compile(
    r"(?P<location>.+?)\s+(?:high|temperature)\s+(?:at\s+or\s+above|above|at\s+least)\s+\$?(?P<threshold>-?\d+(?:\.\d+)?)f",
    re.IGNORECASE,
)

PRECIP_PATTERN = re.compile(
    r"(?P<location>.+?)\s+(?:rainfall|precipitation)\s+(?:at\s+or\s+above|above|at\s+least)\s+\$?(?P<threshold>\d+(?:\.\d+)?)\s*(?:in|inch|inches)",
    re.IGNORECASE,
)


def parse_event_rule(market: Market) -> EventRule:
    title = market.title.strip().rstrip("?")

    temperature_match = TEMPERATURE_PATTERN.fullmatch(title)
    if temperature_match:
        return EventRule(
            metric=WeatherMetric.TEMPERATURE_HIGH_F,
            comparator=Comparator.GREATER_EQUAL,
            threshold=float(temperature_match.group("threshold")),
            location=temperature_match.group("location").strip(),
            market_question=market.title,
        )

    precip_match = PRECIP_PATTERN.fullmatch(title)
    if precip_match:
        return EventRule(
            metric=WeatherMetric.PRECIPITATION_IN,
            comparator=Comparator.GREATER_EQUAL,
            threshold=float(precip_match.group("threshold")),
            location=precip_match.group("location").strip(),
            market_question=market.title,
        )

    raise ValueError(f"Unsupported market title format: {market.title}")
