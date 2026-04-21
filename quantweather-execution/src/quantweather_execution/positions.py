from __future__ import annotations

from .domain import Fill, Order, Position


def apply_fill(position: Position | None, order: Order, fill: Fill) -> Position:
    if position is None:
        return Position(
            market_id=order.market_id,
            side=order.side,
            size=fill.size,
            average_price=fill.price,
            realized_pnl=0.0,
            settled=False,
        )

    total_cost = position.average_price * position.size + fill.price * fill.size
    total_size = position.size + fill.size
    return Position(
        market_id=position.market_id,
        side=position.side,
        size=total_size,
        average_price=total_cost / total_size,
        realized_pnl=position.realized_pnl,
        settled=position.settled,
    )


def settle_position(position: Position, winning_side: str) -> Position:
    payout = position.size if position.side.value == winning_side else 0.0
    cost = position.size * position.average_price
    return Position(
        market_id=position.market_id,
        side=position.side,
        size=position.size,
        average_price=position.average_price,
        realized_pnl=payout - cost,
        settled=True,
    )
