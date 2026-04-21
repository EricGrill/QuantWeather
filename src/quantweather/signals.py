from __future__ import annotations

from .domain import Market, ProbabilityEstimate, Side, TradingSignal


def generate_signal(
    market: Market,
    estimate: ProbabilityEstimate,
    min_edge: float,
) -> TradingSignal | None:
    yes_edge = estimate.probability_yes - market.yes_price
    no_probability = 1.0 - estimate.probability_yes
    no_edge = no_probability - market.no_price

    if yes_edge < min_edge and no_edge < min_edge:
        return None

    if yes_edge >= no_edge:
        side = Side.YES
        model_probability = estimate.probability_yes
        market_probability = market.yes_price
        edge = yes_edge
    else:
        side = Side.NO
        model_probability = no_probability
        market_probability = market.no_price
        edge = no_edge

    return TradingSignal(
        market_id=market.market_id,
        side=side,
        model_probability=model_probability,
        market_probability=market_probability,
        edge=edge,
        confidence=estimate.confidence,
        rationale=estimate.rationale,
    )
