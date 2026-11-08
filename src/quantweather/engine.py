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
from .risk import apply_daily_risk_budget, size_position
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
    """Evaluate every market and enforce ``max_daily_risk`` across the whole run.

    Daily risk budget enforcement lives here, in screening, because this is
    where positions are sized and where ``proposed_notional`` is reported.
    Execution consumes those values as-is, so every approved notional in the
    output is one the budget can actually honor.

    Screening runs in two passes:

    1. Each market is evaluated and sized independently against the budget
       left at the start of the run (``max_daily_risk - daily_risk_used``).
       This applies the per-trade, per-market and other static caps.
    2. Approved proposals then consume the shared budget in **descending edge
       order** (ties keep input order). The first proposals take their full
       size, the one that crosses the limit is reduced to the remainder
       (reason code ``DAILY_RISK_AGGREGATE_REDUCED``), and the rest are
       refused (reason code ``DAILY_RISK_AGGREGATE_EXHAUSTED``).

    Highest-edge-first is deliberate: input order is an artifact of the market
    feed, and when budget is scarce it should go to the best opportunities.
    The sum of approved ``proposed_notional`` never exceeds
    ``max(max_daily_risk - daily_risk_used, 0)``.
    """
    forecasts_by_location = {forecast.location.lower(): forecast for forecast in forecasts}
    recommendations: list[RecommendationRecord] = []
    evaluated: list[tuple[EvaluationResult, ForecastSnapshot]] = []

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

        evaluated.append((result, forecast))

    recommendations.extend(
        _apply_aggregate_daily_risk_budget(
            evaluated,
            remaining_budget=risk_limits.max_daily_risk - daily_risk_used,
        )
    )
    return sorted(recommendations, key=_recommendation_sort_key)


def budget_consumption_order(
    evaluated: list[tuple[EvaluationResult, ForecastSnapshot]],
) -> list[tuple[EvaluationResult, ForecastSnapshot]]:
    """Order in which approved proposals draw on the daily risk budget.

    Descending signal edge; Python's stable sort keeps input order for ties.
    Exposed so a backtest can consume budget in exactly the same order.
    """
    return sorted(
        evaluated,
        key=lambda item: -(item[0].signal.edge if item[0].signal is not None else 0.0),
    )


def _apply_aggregate_daily_risk_budget(
    evaluated: list[tuple[EvaluationResult, ForecastSnapshot]],
    remaining_budget: float,
) -> list[RecommendationRecord]:
    records: list[RecommendationRecord] = []
    for result, forecast in budget_consumption_order(evaluated):
        proposal, remaining_budget = apply_daily_risk_budget(result.proposal, remaining_budget)
        if proposal is result.proposal:
            records.append(result.recommendation)
            continue
        records.append(
            build_recommendation_record(
                market=result.market,
                rule=result.rule,
                estimate=result.estimate,
                signal=result.signal,
                proposal=proposal,
                forecast_source=forecast.source,
                forecast_observed_at=forecast.observed_at,
            )
        )
    return records


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
