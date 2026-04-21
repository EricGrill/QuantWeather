from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .domain import (
    ApprovalState,
    DecisionStatus,
    EventRule,
    Market,
    PositionProposal,
    ProbabilityEstimate,
    RecommendationRecord,
    TradingSignal,
)


MODEL_VERSION = "heuristic-v1"
SCHEMA_VERSION = "v1"


def build_recommendation_record(
    market: Market,
    rule: EventRule,
    estimate: ProbabilityEstimate,
    signal: TradingSignal | None,
    proposal: PositionProposal,
    forecast_source: str,
    forecast_observed_at: str,
) -> RecommendationRecord:
    reason_codes = ["RULE_PARSED"]
    if signal is None:
        reason_codes.append("NO_EDGE")
        edge = 0.0
        signal_side = None
    else:
        reason_codes.append("SIGNAL_GENERATED")
        edge = signal.edge
        signal_side = signal.side

    if proposal.approved:
        approval_state = ApprovalState.REVIEW_REQUIRED
        final_status = DecisionStatus.APPROVED
        reason_codes.append("PROPOSAL_READY_FOR_REVIEW")
    else:
        approval_state = ApprovalState.BLOCKED
        final_status = DecisionStatus.BLOCKED
        reason_codes.extend(_reason_codes_from_blockers(proposal.blocked_reasons))

    return RecommendationRecord(
        schema_version=SCHEMA_VERSION,
        evaluation_id=_build_evaluation_id(
            market.market_id,
            forecast_source,
            forecast_observed_at,
            MODEL_VERSION,
        ),
        evaluated_at=_utc_now(),
        market_id=market.market_id,
        market_title=market.title,
        forecast_source=forecast_source,
        forecast_observed_at=forecast_observed_at,
        location=rule.location,
        rule_metric=rule.metric.value,
        rule_threshold=rule.threshold,
        rule_comparator=rule.comparator.value,
        model_version=MODEL_VERSION,
        model_probability_yes=estimate.probability_yes,
        market_probability_yes=market.yes_price,
        edge=edge,
        confidence=estimate.confidence,
        signal_side=signal_side,
        proposed_notional=proposal.notional,
        approval_state=approval_state,
        final_status=final_status,
        reason_codes=reason_codes,
    )


def build_error_recommendation_record(
    market: Market,
    reason_code: str,
    error_message: str,
    forecast_source: str | None = None,
    forecast_observed_at: str | None = None,
    location: str | None = None,
) -> RecommendationRecord:
    return RecommendationRecord(
        schema_version=SCHEMA_VERSION,
        evaluation_id=_build_evaluation_id(
            market.market_id,
            forecast_source or "none",
            forecast_observed_at or "none",
            MODEL_VERSION,
        ),
        evaluated_at=_utc_now(),
        market_id=market.market_id,
        market_title=market.title,
        forecast_source=forecast_source,
        forecast_observed_at=forecast_observed_at,
        location=location,
        rule_metric=None,
        rule_threshold=None,
        rule_comparator=None,
        model_version=MODEL_VERSION,
        model_probability_yes=None,
        market_probability_yes=market.yes_price,
        edge=None,
        confidence=None,
        signal_side=None,
        proposed_notional=None,
        approval_state=ApprovalState.BLOCKED,
        final_status=DecisionStatus.ERROR,
        reason_codes=[reason_code],
        error_message=error_message,
    )


def _reason_codes_from_blockers(blocked_reasons: list[str]) -> list[str]:
    reason_codes: list[str] = []
    for reason in blocked_reasons:
        if "confidence" in reason.lower():
            reason_codes.append("CONFIDENCE_BELOW_MIN")
        elif "edge" in reason.lower():
            reason_codes.append("EDGE_BELOW_MIN")
        elif "spread" in reason.lower():
            reason_codes.append("SPREAD_TOO_WIDE")
        elif "liquidity" in reason.lower():
            reason_codes.append("LIQUIDITY_TOO_LOW")
        elif "daily risk" in reason.lower():
            reason_codes.append("DAILY_RISK_EXHAUSTED")
        elif "no signal" in reason.lower():
            reason_codes.append("NO_EDGE")
        elif "zero" in reason.lower():
            reason_codes.append("POSITION_SIZE_ZERO_AFTER_CAPS")
    return reason_codes


def _build_evaluation_id(
    market_id: str,
    forecast_source: str,
    forecast_observed_at: str,
    model_version: str,
) -> str:
    raw = f"{market_id}:{forecast_source}:{forecast_observed_at}:{model_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
