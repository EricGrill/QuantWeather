from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def render_dashboard_html(
    runs: list[dict[str, Any]],
    latest_records: list[dict[str, Any]],
    latest_summary: dict[str, Any],
    latest_comparison: dict[str, Any] | None = None,
) -> str:
    latest_run = runs[-1] if runs else None

    lines = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "<meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        "<title>QuantWeather Dashboard</title>",
        "<style>",
        "body { font-family: Georgia, 'Times New Roman', serif; margin: 0; background: #f5f1e8; color: #1b1b1b; }",
        ".wrap { max-width: 1100px; margin: 0 auto; padding: 32px 24px 64px; }",
        "h1, h2, h3 { margin-bottom: 0.35em; }",
        ".hero { background: linear-gradient(135deg, #183a37, #34675c); color: #f8f4ea; padding: 24px; border-radius: 18px; }",
        ".grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 24px 0; }",
        ".card { background: #fffdf8; border: 1px solid #d7cfbf; border-radius: 16px; padding: 18px; box-shadow: 0 4px 14px rgba(0,0,0,0.04); }",
        ".section { margin-top: 28px; }",
        ".pill { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; background: #e8e1cf; margin-right: 6px; margin-top: 6px; }",
        ".approved { border-left: 6px solid #3f7d20; }",
        ".blocked { border-left: 6px solid #ad7a22; }",
        ".error { border-left: 6px solid #8f2d2d; }",
        "table { width: 100%; border-collapse: collapse; background: #fffdf8; border-radius: 14px; overflow: hidden; }",
        "th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid #e8e1cf; vertical-align: top; }",
        "th { background: #ece4d4; }",
        "code { background: #efe8d8; padding: 2px 5px; border-radius: 6px; }",
        "</style>",
        "</head>",
        "<body>",
        "<div class=\"wrap\">",
        "<section class=\"hero\">",
        "<h1>QuantWeather Manual Review Dashboard</h1>",
        "<p>Saved-run overview for local operator review.</p>",
    ]

    if latest_run:
        lines.append(f"<p><strong>Latest run:</strong> <code>{escape(latest_run['run_id'])}</code></p>")
    lines.extend(["</section>", "<section class=\"grid\">"])

    for label, value in [
        ("Saved Runs", len(runs)),
        ("Records", latest_summary["record_count"]),
        ("Approved", latest_summary["approved_count"]),
        ("Blocked", latest_summary["blocked_count"]),
        ("Errors", latest_summary["error_count"]),
    ]:
        lines.append("<div class=\"card\">")
        lines.append(f"<h3>{escape(str(value))}</h3>")
        lines.append(f"<p>{escape(label)}</p>")
        lines.append("</div>")
    lines.append("</section>")

    if latest_summary.get("top_edge_market_id") is not None:
        lines.extend(
            [
                "<section class=\"section card\">",
                "<h2>Top Edge</h2>",
                f"<p><code>{escape(latest_summary['top_edge_market_id'])}</code> at <strong>{latest_summary['top_edge']:.4f}</strong></p>",
                "</section>",
            ]
        )

    lines.extend(_render_records_section("Approved Opportunities", latest_records, "approved"))
    lines.extend(_render_records_section("Blocked Opportunities", latest_records, "blocked"))
    lines.extend(_render_records_section("Errors", latest_records, "error"))

    lines.extend(["<section class=\"section\">", "<h2>Run History</h2>", "<table>", "<thead><tr><th>Run</th><th>Created</th><th>Counts</th><th>Artifacts</th></tr></thead>", "<tbody>"])
    for run in reversed(runs):
        artifacts: list[str] = []
        if run.get("screen_report_path"):
            artifacts.append(f"report: <code>{escape(run['screen_report_path'])}</code>")
        if run.get("comparison_report_path"):
            artifacts.append(f"compare: <code>{escape(run['comparison_report_path'])}</code>")
        if run.get("dashboard_path"):
            artifacts.append(f"dashboard: <code>{escape(run['dashboard_path'])}</code>")
        lines.append("<tr>")
        lines.append(f"<td><code>{escape(run['run_id'])}</code></td>")
        lines.append(f"<td>{escape(run['created_at'])}</td>")
        lines.append(f"<td>A {run['approved_count']} / B {run['blocked_count']} / E {run['error_count']}</td>")
        lines.append(f"<td>{'<br>'.join(artifacts) if artifacts else '&mdash;'}</td>")
        lines.append("</tr>")
    lines.extend(["</tbody>", "</table>", "</section>"])

    if latest_comparison is not None:
        lines.extend(["<section class=\"section\">", "<h2>Latest Comparison</h2>"])
        changed = latest_comparison.get("changed_markets", [])
        if not changed:
            lines.append("<div class=\"card\"><p>No changed markets between the latest two runs.</p></div>")
        else:
            lines.append("<table>")
            lines.append("<thead><tr><th>Market</th><th>Status</th><th>Edge</th><th>Reasons</th></tr></thead><tbody>")
            for item in changed:
                lines.append("<tr>")
                lines.append(f"<td><code>{escape(item['market_id'])}</code></td>")
                lines.append(f"<td><code>{escape(item['old_status'])}</code> → <code>{escape(item['new_status'])}</code></td>")
                lines.append(f"<td>{escape(str(item['old_edge']))} → {escape(str(item['new_edge']))}</td>")
                lines.append(
                    f"<td><code>{escape(','.join(item['old_reason_codes']))}</code> → "
                    f"<code>{escape(','.join(item['new_reason_codes']))}</code></td>"
                )
                lines.append("</tr>")
            lines.extend(["</tbody>", "</table>"])
        lines.append("</section>")

    lines.extend(["</div>", "</body>", "</html>"])
    return "\n".join(lines) + "\n"


def write_dashboard_html(
    html: str,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _render_records_section(
    heading: str,
    records: list[dict[str, Any]],
    final_status: str,
) -> list[str]:
    matching = [record for record in records if record["final_status"] == final_status]
    css_class = final_status
    lines = [f"<section class=\"section\"><h2>{escape(heading)}</h2>"]
    if not matching:
        lines.append(f"<div class=\"card {css_class}\"><p>None</p></div>")
        lines.append("</section>")
        return lines

    for record in matching:
        lines.append(f"<div class=\"card {css_class}\">")
        lines.append(f"<h3><code>{escape(record['market_id'])}</code></h3>")
        lines.append(f"<p>{escape(record['market_title'])}</p>")
        if record.get("edge") is not None:
            lines.append(f"<p><strong>Edge:</strong> {record['edge']:.4f}</p>")
        if record.get("error_message"):
            lines.append(f"<p><strong>Error:</strong> {escape(record['error_message'])}</p>")
        lines.append("<p>")
        for reason in record["reason_codes"]:
            lines.append(f"<span class=\"pill\">{escape(reason)}</span>")
        lines.append("</p>")
        lines.append("</div>")
    lines.append("</section>")
    return lines
