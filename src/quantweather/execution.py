from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecutionOrder:
    order_id: str
    market_id: str
    side: str
    notional: float
    limit_price: float
    status: str
    mode: str
    reason_codes: list[str]
    created_at: str


def build_execution_orders(
    records: list[dict[str, Any]],
    *,
    mode: str = "paper",
) -> list[ExecutionOrder]:
    if mode != "paper":
        raise ValueError("Only paper execution is supported until a broker adapter is configured")

    orders: list[ExecutionOrder] = []
    for record in records:
        market_id = str(record["market_id"])
        final_status = record.get("final_status")
        notional = float(record.get("proposed_notional") or 0.0)
        side = str(record.get("signal_side") or "NONE")
        limit_price = float(record.get("market_probability_yes") or 0.0)

        if final_status == "approved" and notional > 0.0 and side != "NONE":
            status = "paper_filled"
            reason_codes = ["PAPER_EXECUTION_READY", "PAPER_FILL_RECORDED"]
        else:
            status = "skipped"
            reason_codes = ["RECOMMENDATION_NOT_APPROVED"]

        orders.append(
            ExecutionOrder(
                order_id=_build_order_id(market_id, side, mode),
                market_id=market_id,
                side=side,
                notional=round(notional, 2),
                limit_price=limit_price,
                status=status,
                mode=mode,
                reason_codes=reason_codes,
                created_at=_utc_now(),
            )
        )

    return orders


def execution_orders_to_dicts(orders: list[ExecutionOrder]) -> list[dict[str, Any]]:
    return [asdict(order) for order in orders]


def execution_orders_to_json(orders: list[ExecutionOrder], indent: int = 2) -> str:
    return json.dumps(execution_orders_to_dicts(orders), indent=indent, sort_keys=True)


def write_execution_orders(
    orders: list[ExecutionOrder],
    path: str | Path,
    *,
    indent: int = 2,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(execution_orders_to_json(orders, indent=indent) + "\n", encoding="utf-8")
    return output_path


def execution_summary(orders: list[ExecutionOrder]) -> dict[str, Any]:
    filled = [order for order in orders if order.status == "paper_filled"]
    skipped = [order for order in orders if order.status == "skipped"]
    return {
        "order_count": len(orders),
        "filled_count": len(filled),
        "skipped_count": len(skipped),
        "filled_notional": round(sum(order.notional for order in filled), 2),
    }


def _build_order_id(market_id: str, side: str, mode: str) -> str:
    sanitized = "".join(char if char.isalnum() or char in "-_" else "-" for char in market_id)
    return f"{mode}-{sanitized}-{side.lower()}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
