from __future__ import annotations

from .domain import Market, PositionProposal, RiskLimits, Side, SizingMethod, TradingSignal


def size_position(
    signal: TradingSignal | None,
    market: Market,
    risk_limits: RiskLimits,
    account_balance: float,
    daily_risk_used: float = 0.0,
    method: SizingMethod = SizingMethod.PROPORTIONAL,
) -> PositionProposal:
    blocked_reasons: list[str] = []

    if signal is None:
        blocked_reasons.append("No signal exceeded the configured edge threshold.")
    else:
        if signal.confidence < risk_limits.min_confidence:
            blocked_reasons.append("Signal confidence below minimum threshold.")
        if signal.edge < risk_limits.min_edge:
            blocked_reasons.append("Signal edge below minimum threshold.")

    if market.spread > risk_limits.max_spread:
        blocked_reasons.append("Market spread exceeds configured maximum.")
    if market.liquidity < risk_limits.min_liquidity:
        blocked_reasons.append("Market liquidity below configured minimum.")
    if daily_risk_used >= risk_limits.max_daily_risk:
        blocked_reasons.append("Daily risk budget exhausted.")

    if blocked_reasons or signal is None:
        return PositionProposal(
            market_id=market.market_id,
            side=signal.side if signal else Side.YES,
            notional=0.0,
            sizing_method=method,
            blocked_reasons=blocked_reasons,
            approved=False,
        )

    if method == SizingMethod.FIXED:
        notional = risk_limits.max_trade_notional
    elif method == SizingMethod.PROPORTIONAL:
        notional = account_balance * min(signal.edge, 0.20) * signal.confidence
    elif method == SizingMethod.FRACTIONAL_KELLY:
        b = max(signal.market_probability, 0.01)
        q = 1.0 - signal.model_probability
        kelly_fraction = max(((signal.model_probability * (1.0 / b)) - q), 0.0)
        notional = account_balance * kelly_fraction * 0.25
    else:
        raise ValueError(f"Unsupported sizing method: {method}")

    capped_notional = min(
        notional,
        risk_limits.max_trade_notional,
        risk_limits.max_market_exposure,
        max(risk_limits.max_daily_risk - daily_risk_used, 0.0),
    )

    approved = capped_notional > 0.0
    if not approved:
        blocked_reasons.append("Computed position size is zero after risk caps.")

    return PositionProposal(
        market_id=market.market_id,
        side=signal.side,
        notional=round(capped_notional, 2),
        sizing_method=method,
        blocked_reasons=blocked_reasons,
        approved=approved,
    )
