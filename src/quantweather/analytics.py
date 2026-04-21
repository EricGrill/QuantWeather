from __future__ import annotations

from typing import Any


def analyze_screen_run(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    approved = [record for record in records if record.get("final_status") == "approved"]
    edges = [float(record["edge"]) for record in records if record.get("edge") is not None]
    proposed_notional = sum(float(record.get("proposed_notional") or 0.0) for record in approved)
    expected_edge_value = sum(
        float(record.get("edge") or 0.0) * float(record.get("proposed_notional") or 0.0)
        for record in approved
    )

    return {
        "record_count": total,
        "approval_rate": round(len(approved) / total, 4) if total else 0.0,
        "average_edge": round(sum(edges) / len(edges), 4) if edges else None,
        "max_edge": max(edges) if edges else None,
        "proposed_notional": round(proposed_notional, 2),
        "expected_edge_value": round(expected_edge_value, 2),
        "edge_buckets": _edge_buckets(edges),
        "reason_counts": _reason_counts(records),
    }


def analyze_run_history(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {"run_count": 0, "latest_run_id": None, "approved_count": 0, "error_count": 0}
    return {
        "run_count": len(runs),
        "latest_run_id": runs[-1]["run_id"],
        "approved_count": sum(int(run.get("approved_count", 0)) for run in runs),
        "blocked_count": sum(int(run.get("blocked_count", 0)) for run in runs),
        "error_count": sum(int(run.get("error_count", 0)) for run in runs),
    }


def _edge_buckets(edges: list[float]) -> dict[str, int]:
    buckets = {
        "negative": 0,
        "0_to_5pct": 0,
        "5_to_15pct": 0,
        "15pct_plus": 0,
    }
    for edge in edges:
        if edge < 0:
            buckets["negative"] += 1
        elif edge < 0.05:
            buckets["0_to_5pct"] += 1
        elif edge < 0.15:
            buckets["5_to_15pct"] += 1
        else:
            buckets["15pct_plus"] += 1
    return buckets


def _reason_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        for reason in record.get("reason_codes", []):
            counts[reason] = counts.get(reason, 0) + 1
    return counts
