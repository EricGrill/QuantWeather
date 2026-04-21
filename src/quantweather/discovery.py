from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from .domain import Market
from .ingest import normalize_market_payload
from .market_rules import parse_event_rule


@dataclass(frozen=True)
class DiscoveryDecision:
    market: Market
    accepted: bool
    reason_codes: list[str]


def discover_weather_markets(
    payload: dict[str, Any] | list[dict[str, Any]],
    *,
    min_liquidity: float = 0.0,
    max_spread: float = 1.0,
    locations: Iterable[str] | None = None,
) -> list[DiscoveryDecision]:
    wanted_locations = {location.lower() for location in locations or []}
    decisions: list[DiscoveryDecision] = []

    for item in _market_payloads(payload):
        market = normalize_market_payload(item)
        reason_codes: list[str] = []
        accepted = True

        try:
            rule = parse_event_rule(market)
            reason_codes.append("RULE_PARSED")
        except ValueError:
            accepted = False
            reason_codes.append("UNSUPPORTED_MARKET_TITLE")
            rule = None

        if rule is not None and wanted_locations and rule.location.lower() not in wanted_locations:
            accepted = False
            reason_codes.append("LOCATION_NOT_REQUESTED")
        if market.liquidity < min_liquidity:
            accepted = False
            reason_codes.append("LIQUIDITY_TOO_LOW")
        if market.spread > max_spread:
            accepted = False
            reason_codes.append("SPREAD_TOO_WIDE")

        if accepted:
            reason_codes.append("DISCOVERED")
        decisions.append(DiscoveryDecision(market=market, accepted=accepted, reason_codes=reason_codes))

    return sorted(decisions, key=_decision_sort_key)


def load_market_discovery_payload(path: str | Path) -> dict[str, Any] | list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def discovery_decision_to_dict(decision: DiscoveryDecision) -> dict[str, Any]:
    payload = asdict(decision.market)
    payload["accepted"] = decision.accepted
    payload["reason_codes"] = decision.reason_codes
    return payload


def discovery_decisions_to_json(decisions: list[DiscoveryDecision], indent: int = 2) -> str:
    return json.dumps(
        [discovery_decision_to_dict(decision) for decision in decisions],
        indent=indent,
        sort_keys=True,
    )


def _market_payloads(payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        markets = payload.get("markets", payload.get("data"))
    else:
        markets = payload
    if not isinstance(markets, list):
        raise ValueError("Discovery payload must contain a list of markets")
    for item in markets:
        if not isinstance(item, dict):
            raise ValueError("Discovery market entries must be objects")
    return markets


def _decision_sort_key(decision: DiscoveryDecision) -> tuple[int, str]:
    return (0 if decision.accepted else 1, decision.market.market_id)
