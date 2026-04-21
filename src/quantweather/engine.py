from __future__ import annotations

from .audit import build_error_recommendation_record, build_recommendation_record
from .domain import (
    EvaluationResult,
    ForecastSnapshot,
    Market,
    RecommendationRecord,
    RiskLimits,
    SizingMethod,
)
from .market_rules import parse_event_rule
from .modeling import estimate_probability
from .risk import size_position
from .signals import generate_signal


def evaluate_market(
    market: Market,
    forecast: ForecastSnapshot,
    risk_limits: RiskLimits,
    account_balance: float,
    daily_risk_used: float = 0.0,
    sizing_method: SizingMethod = SizingMethod.PROPORTIONAL,
) -> EvaluationResult:
    rule = parse_event_rule(market)
    estimate = estimate_probability(rule, forecast)
    signal = generate_signal(market, estimate, min_edge=risk_limits.min_edge)
    proposal = size_position(
        signal=signal,
        market=market,
        risk_limits=risk_limits,
        account_balance=account_balance,
        daily_risk_used=daily_risk_used,
        method=sizing_method,
    )
    recommendation = build_recommendation_record(
        market=market,
        rule=rule,
        estimate=estimate,
        signal=signal,
        proposal=proposal,
        forecast_source=forecast.source,
        forecast_observed_at=forecast.observed_at,
    )
    return EvaluationResult(
        market=market,
        rule=rule,
        estimate=estimate,
        signal=signal,
        proposal=proposal,
        recommendation=recommendation,
    )


def screen_markets(
    markets: list[Market],
    forecasts: list[ForecastSnapshot],
    risk_limits: RiskLimits,
    account_balance: float,
    daily_risk_used: float = 0.0,
    sizing_method: SizingMethod = SizingMethod.PROPORTIONAL,
) -> list[RecommendationRecord]:
    forecasts_by_location = {forecast.location.lower(): forecast for forecast in forecasts}
    recommendations: list[RecommendationRecord] = []

    for market in markets:
        try:
            rule = parse_event_rule(market)
        except ValueError as exc:
            recommendations.append(
                build_error_recommendation_record(
                    market=market,
                    reason_code="UNSUPPORTED_MARKET_TITLE",
                    error_message=str(exc),
                )
            )
            continue

        forecast = forecasts_by_location.get(rule.location.lower())
        if forecast is None:
            recommendations.append(
                build_error_recommendation_record(
                    market=market,
                    reason_code="MISSING_FORECAST",
                    error_message=f"No forecast found for location: {rule.location}",
                    location=rule.location,
                )
            )
            continue

        try:
            result = evaluate_market(
                market=market,
                forecast=forecast,
                risk_limits=risk_limits,
                account_balance=account_balance,
                daily_risk_used=daily_risk_used,
                sizing_method=sizing_method,
            )
        except KeyError as exc:
            recommendations.append(
                build_error_recommendation_record(
                    market=market,
                    reason_code="MISSING_FORECAST_METRIC",
                    error_message=f"Forecast metric missing: {exc}",
                    forecast_source=forecast.source,
                    forecast_observed_at=forecast.observed_at,
                    location=rule.location,
                )
            )
            continue
        except ValueError as exc:
            reason_code = (
                "FORECAST_LOCATION_MISMATCH"
                if "location does not match" in str(exc).lower()
                else "EVALUATION_ERROR"
            )
            recommendations.append(
                build_error_recommendation_record(
                    market=market,
                    reason_code=reason_code,
                    error_message=str(exc),
                    forecast_source=forecast.source,
                    forecast_observed_at=forecast.observed_at,
                    location=rule.location,
                )
            )
            continue

        recommendations.append(result.recommendation)

    return sorted(recommendations, key=_recommendation_sort_key)


def _recommendation_sort_key(record: RecommendationRecord) -> tuple[int, float]:
    status_rank = {
        "approved": 0,
        "blocked": 1,
        "error": 2,
    }
    return (
        status_rank[record.final_status.value],
        -(record.edge if record.edge is not None else -1.0),
    )
