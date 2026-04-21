from __future__ import annotations

from typing import Any


def render_screen_run_report(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    run_metadata: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = ["# QuantWeather Screen Report", ""]

    if run_metadata:
        lines.append(f"- Run ID: `{run_metadata['run_id']}`")
        lines.append(f"- Created At: `{run_metadata['created_at']}`")
        lines.append(f"- Label: `{run_metadata['label']}`")
        lines.append("")

    lines.extend(
        [
            "## Overview",
            "",
            f"- Records: {summary['record_count']}",
            f"- Approved: {summary['approved_count']}",
            f"- Blocked: {summary['blocked_count']}",
            f"- Errors: {summary['error_count']}",
        ]
    )
    if summary["top_edge_market_id"] is not None:
        lines.append(
            f"- Top Edge: `{summary['top_edge_market_id']}` at `{summary['top_edge']:.4f}`"
        )
    lines.append("")

    lines.extend(_render_record_section("Approved Opportunities", records, "approved"))
    lines.extend(_render_record_section("Blocked Opportunities", records, "blocked"))
    lines.extend(_render_record_section("Errors", records, "error"))

    if summary["reason_counts"]:
        lines.extend(["## Reason Counts", ""])
        for reason_code, count in sorted(summary["reason_counts"].items()):
            lines.append(f"- `{reason_code}`: {count}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_run_comparison_report(
    comparison: dict[str, Any],
    older_run_metadata: dict[str, Any] | None = None,
    newer_run_metadata: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = ["# QuantWeather Run Comparison", ""]

    if older_run_metadata and newer_run_metadata:
        lines.append(f"- Older Run: `{older_run_metadata['run_id']}`")
        lines.append(f"- Newer Run: `{newer_run_metadata['run_id']}`")
        lines.append("")

    lines.extend(
        [
            "## Overview",
            "",
            f"- Older Records: {comparison['older_record_count']}",
            f"- Newer Records: {comparison['newer_record_count']}",
            f"- Added Markets: {len(comparison['added_market_ids'])}",
            f"- Removed Markets: {len(comparison['removed_market_ids'])}",
            f"- Changed Markets: {len(comparison['changed_markets'])}",
            "",
        ]
    )

    lines.extend(_render_market_id_section("Added Markets", comparison["added_market_ids"]))
    lines.extend(_render_market_id_section("Removed Markets", comparison["removed_market_ids"]))

    lines.extend(["## Changed Markets", ""])
    if not comparison["changed_markets"]:
        lines.append("- None")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    for change in comparison["changed_markets"]:
        lines.append(f"- `{change['market_id']}`: `{change['old_status']}` -> `{change['new_status']}`")
        if change["old_edge"] != change["new_edge"]:
            lines.append(f"  edge: `{change['old_edge']}` -> `{change['new_edge']}`")
        if change["old_reason_codes"] != change["new_reason_codes"]:
            lines.append(
                f"  reasons: `{','.join(change['old_reason_codes'])}` -> "
                f"`{','.join(change['new_reason_codes'])}`"
            )
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_record_section(
    heading: str,
    records: list[dict[str, Any]],
    final_status: str,
) -> list[str]:
    lines = [f"## {heading}", ""]
    matching_records = [record for record in records if record["final_status"] == final_status]
    if not matching_records:
        lines.append("- None")
        lines.append("")
        return lines

    for record in matching_records:
        description = f"- `{record['market_id']}`: {record['market_title']}"
        if record.get("edge") is not None:
            description += f" | edge `{record['edge']:.4f}`"
        lines.append(description)
        lines.append(f"  reasons: `{','.join(record['reason_codes'])}`")
        if record.get("error_message"):
            lines.append(f"  error: `{record['error_message']}`")
    lines.append("")
    return lines


def _render_market_id_section(heading: str, market_ids: list[str]) -> list[str]:
    lines = [f"## {heading}", ""]
    if not market_ids:
        lines.append("- None")
        lines.append("")
        return lines
    for market_id in market_ids:
        lines.append(f"- `{market_id}`")
    lines.append("")
    return lines
