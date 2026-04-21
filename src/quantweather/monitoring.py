from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def monitor_screen_run(
    records: list[dict[str, Any]],
    *,
    max_error_rate: float = 0.25,
    max_blocked_rate: float = 0.75,
) -> dict[str, Any]:
    total = len(records)
    error_count = _count(records, "error")
    blocked_count = _count(records, "blocked")
    approved_count = _count(records, "approved")
    error_rate = error_count / total if total else 0.0
    blocked_rate = blocked_count / total if total else 0.0

    alerts: list[dict[str, Any]] = []
    if total == 0:
        alerts.append({"severity": "warning", "code": "NO_RECORDS", "message": "No records were available to monitor."})
    if error_rate > max_error_rate:
        alerts.append({"severity": "critical", "code": "ERROR_RATE_HIGH", "message": "Screening error rate exceeded threshold."})
    if blocked_rate > max_blocked_rate:
        alerts.append({"severity": "warning", "code": "BLOCKED_RATE_HIGH", "message": "Blocked recommendation rate exceeded threshold."})

    return {
        "checked_at": _utc_now(),
        "record_count": total,
        "approved_count": approved_count,
        "blocked_count": blocked_count,
        "error_count": error_count,
        "error_rate": round(error_rate, 4),
        "blocked_rate": round(blocked_rate, 4),
        "alerts": alerts,
        "healthy": not any(alert["severity"] == "critical" for alert in alerts),
    }


def monitor_execution_orders(orders: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(orders)
    filled = sum(1 for order in orders if order.get("status") == "paper_filled")
    skipped = sum(1 for order in orders if order.get("status") == "skipped")
    alerts: list[dict[str, Any]] = []
    if total > 0 and filled == 0:
        alerts.append({"severity": "warning", "code": "NO_FILLS", "message": "Execution produced no filled paper orders."})

    return {
        "checked_at": _utc_now(),
        "order_count": total,
        "filled_count": filled,
        "skipped_count": skipped,
        "alerts": alerts,
        "healthy": True,
    }


def _count(records: list[dict[str, Any]], status: str) -> int:
    return sum(1 for record in records if record.get("final_status") == status)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
