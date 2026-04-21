from __future__ import annotations

from dataclasses import dataclass

from .domain import OrderIntent, RiskEvent


@dataclass(frozen=True)
class RiskLimits:
    max_order_notional: float
    kill_switch_active: bool = False


def check_order_intent(intent: OrderIntent, limits: RiskLimits, created_at: str) -> RiskEvent | None:
    if limits.kill_switch_active:
        return RiskEvent(
            event_id=f"risk-{intent.intent_id}",
            created_at=created_at,
            message="Kill switch active.",
            blocking=True,
        )
    if intent.notional > limits.max_order_notional:
        return RiskEvent(
            event_id=f"risk-{intent.intent_id}",
            created_at=created_at,
            message="Order notional exceeds configured maximum.",
            blocking=True,
        )
    return None
