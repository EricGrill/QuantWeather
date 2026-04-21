from __future__ import annotations

from .domain import OrderIntent, SignalEnvelope


def build_order_intent(signal: SignalEnvelope, created_at: str, intent_id: str) -> OrderIntent:
    return OrderIntent(
        intent_id=intent_id,
        signal_id=signal.signal_id,
        market_id=signal.market_id,
        side=signal.side,
        notional=signal.proposed_notional,
        created_at=created_at,
    )
