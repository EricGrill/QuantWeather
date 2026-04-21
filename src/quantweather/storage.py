from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from .domain import DecisionStatus, RecommendationRecord
from .dashboard import render_dashboard_html, write_dashboard_html
from .report import render_run_comparison_report, render_screen_run_report
from .serialize import recommendations_to_json


def persist_screen_run(
    records: list[RecommendationRecord],
    directory: str | Path,
    label: str = "screen",
    metadata: dict[str, Any] | None = None,
) -> Path:
    base_dir = Path(directory)
    base_dir.mkdir(parents=True, exist_ok=True)

    run_id = _build_run_id(label)
    run_path = base_dir / f"{run_id}.json"
    run_path.write_text(recommendations_to_json(records) + "\n", encoding="utf-8")

    manifest_path = base_dir / "manifest.json"
    manifest = _read_manifest(manifest_path)
    run_entry = {
        "run_id": run_id,
        "label": label,
        "created_at": _utc_now(),
        "path": run_path.name,
        "record_count": len(records),
        "approved_count": _count_status(records, DecisionStatus.APPROVED),
        "blocked_count": _count_status(records, DecisionStatus.BLOCKED),
        "error_count": _count_status(records, DecisionStatus.ERROR),
    }
    if metadata:
        run_entry["metadata"] = metadata
    manifest["runs"].append(run_entry)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return run_path


def list_screen_runs(directory: str | Path) -> list[dict[str, Any]]:
    manifest_path = Path(directory) / "manifest.json"
    manifest = _read_manifest(manifest_path)
    return list(manifest["runs"])


def load_screen_run(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_latest_screen_run(directory: str | Path) -> list[dict[str, Any]]:
    runs = list_screen_runs(directory)
    if not runs:
        raise ValueError("No saved screen runs found")
    latest = runs[-1]
    return load_screen_run(Path(directory) / latest["path"])


def load_latest_run_metadata(directory: str | Path) -> dict[str, Any]:
    runs = list_screen_runs(directory)
    if not runs:
        raise ValueError("No saved screen runs found")
    return runs[-1]


def summarize_screen_run(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {
        "approved": 0,
        "blocked": 0,
        "error": 0,
    }
    reason_counts: dict[str, int] = {}
    top_edge_market_id: str | None = None
    top_edge: float | None = None

    for record in records:
        status = record["final_status"]
        status_counts[status] += 1

        for reason_code in record["reason_codes"]:
            reason_counts[reason_code] = reason_counts.get(reason_code, 0) + 1

        edge = record.get("edge")
        if edge is not None and (top_edge is None or edge > top_edge):
            top_edge = edge
            top_edge_market_id = record["market_id"]

    return {
        "record_count": len(records),
        "approved_count": status_counts["approved"],
        "blocked_count": status_counts["blocked"],
        "error_count": status_counts["error"],
        "top_edge_market_id": top_edge_market_id,
        "top_edge": top_edge,
        "reason_counts": reason_counts,
    }


def summarize_latest_screen_run(directory: str | Path) -> dict[str, Any]:
    return summarize_screen_run(load_latest_screen_run(directory))


def compare_screen_runs(
    older_records: list[dict[str, Any]],
    newer_records: list[dict[str, Any]],
) -> dict[str, Any]:
    older_by_market = {record["market_id"]: record for record in older_records}
    newer_by_market = {record["market_id"]: record for record in newer_records}

    added_market_ids = sorted(set(newer_by_market) - set(older_by_market))
    removed_market_ids = sorted(set(older_by_market) - set(newer_by_market))
    changed_markets: list[dict[str, Any]] = []

    for market_id in sorted(set(older_by_market) & set(newer_by_market)):
        older = older_by_market[market_id]
        newer = newer_by_market[market_id]
        older_status = older["final_status"]
        newer_status = newer["final_status"]
        older_edge = older.get("edge")
        newer_edge = newer.get("edge")

        if (
            older_status != newer_status
            or older_edge != newer_edge
            or older["reason_codes"] != newer["reason_codes"]
        ):
            changed_markets.append(
                {
                    "market_id": market_id,
                    "old_status": older_status,
                    "new_status": newer_status,
                    "old_edge": older_edge,
                    "new_edge": newer_edge,
                    "old_reason_codes": older["reason_codes"],
                    "new_reason_codes": newer["reason_codes"],
                }
            )

    return {
        "older_record_count": len(older_records),
        "newer_record_count": len(newer_records),
        "added_market_ids": added_market_ids,
        "removed_market_ids": removed_market_ids,
        "changed_markets": changed_markets,
    }


def compare_latest_two_runs(directory: str | Path) -> dict[str, Any]:
    runs = list_screen_runs(directory)
    if len(runs) < 2:
        raise ValueError("Need at least two saved screen runs to compare")
    older = load_screen_run(Path(directory) / runs[-2]["path"])
    newer = load_screen_run(Path(directory) / runs[-1]["path"])
    return compare_screen_runs(older, newer)


def save_latest_screen_report(directory: str | Path) -> Path:
    base_dir = Path(directory)
    manifest_path = base_dir / "manifest.json"
    manifest = _read_manifest(manifest_path)
    if not manifest["runs"]:
        raise ValueError("No saved screen runs found")

    latest_metadata = manifest["runs"][-1]
    records = load_screen_run(base_dir / latest_metadata["path"])
    summary = summarize_screen_run(records)
    report_text = render_screen_run_report(records, summary, latest_metadata)

    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{latest_metadata['run_id']}.md"
    report_path.write_text(report_text, encoding="utf-8")

    latest_metadata["screen_report_path"] = str(report_path.relative_to(base_dir))
    _write_manifest(manifest_path, manifest)
    return report_path


def save_latest_comparison_report(directory: str | Path) -> Path:
    base_dir = Path(directory)
    manifest_path = base_dir / "manifest.json"
    manifest = _read_manifest(manifest_path)
    if len(manifest["runs"]) < 2:
        raise ValueError("Need at least two saved screen runs to compare")

    older_metadata = manifest["runs"][-2]
    newer_metadata = manifest["runs"][-1]
    older = load_screen_run(base_dir / older_metadata["path"])
    newer = load_screen_run(base_dir / newer_metadata["path"])
    comparison = compare_screen_runs(older, newer)
    report_text = render_run_comparison_report(comparison, older_metadata, newer_metadata)

    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_filename = f"{older_metadata['run_id']}--{newer_metadata['run_id']}.md"
    report_path = reports_dir / report_filename
    report_path.write_text(report_text, encoding="utf-8")

    newer_metadata["comparison_report_path"] = str(report_path.relative_to(base_dir))
    _write_manifest(manifest_path, manifest)
    return report_path


def save_latest_dashboard(directory: str | Path) -> Path:
    base_dir = Path(directory)
    manifest_path = base_dir / "manifest.json"
    manifest = _read_manifest(manifest_path)
    if not manifest["runs"]:
        raise ValueError("No saved screen runs found")

    runs = manifest["runs"]
    latest_metadata = runs[-1]
    latest_records = load_screen_run(base_dir / latest_metadata["path"])
    latest_summary = summarize_screen_run(latest_records)
    comparison = None
    if len(runs) >= 2:
        older = load_screen_run(base_dir / runs[-2]["path"])
        comparison = compare_screen_runs(older, latest_records)

    dashboards_dir = base_dir / "dashboards"
    dashboards_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = dashboards_dir / f"{latest_metadata['run_id']}.html"
    latest_metadata["dashboard_path"] = str(dashboard_path.relative_to(base_dir))
    dashboard_html = render_dashboard_html(runs, latest_records, latest_summary, comparison)
    write_dashboard_html(dashboard_html, dashboard_path)

    _write_manifest(manifest_path, manifest)
    return dashboard_path


def _read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"runs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _build_run_id(label: str) -> str:
    sanitized_label = _sanitize_label(label)
    return f"{sanitized_label}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"


def _count_status(records: list[RecommendationRecord], status: DecisionStatus) -> int:
    return sum(1 for record in records if record.final_status == status)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_label(label: str) -> str:
    sanitized = re.sub(r"[^a-z0-9_-]+", "-", label.strip().lower().replace(" ", "-"))
    sanitized = sanitized.strip(".-_")
    return sanitized or "screen"
