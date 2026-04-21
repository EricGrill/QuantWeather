from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from typing import Any

from .config import ExecutionConfig, load_config
from .domain import ApprovalDecision, ApprovalStatus, Side, SignalEnvelope
from .repository import ExecutionRepository, InMemoryRepository, SQLiteRepository
from .risk import RiskLimits
from .service import ExecutionService
from .ui import render_operator_ui


class ExecutionAPI:
    def __init__(self, repository: ExecutionRepository | None = None) -> None:
        self.repository = repository or InMemoryRepository()
        self.service = ExecutionService(repository=self.repository)

    def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    def reconcile(self) -> dict[str, Any]:
        return self.service.reconcile_state()

    def list_signals(self) -> dict[str, Any]:
        return {"signals": [_to_jsonable(signal) for signal in self.repository.list_signals()]}

    def list_trades(self) -> dict[str, Any]:
        state = self.service.list_trade_state()
        return {
            "orders": [_to_jsonable(order) for order in state["orders"]],
            "fills": [_to_jsonable(fill) for fill in state["fills"]],
            "positions": [_to_jsonable(position) for position in state["positions"]],
            "open_positions": [_to_jsonable(position) for position in state["open_positions"]],
            "settled_positions": [_to_jsonable(position) for position in state["settled_positions"]],
        }

    def performance_report(self) -> dict[str, Any]:
        report = self.service.performance_report()
        return {
            **{key: value for key, value in report.items() if key != "events"},
            "events": [_to_jsonable(event) for event in report["events"]],
        }

    def cleanup_duplicates(self) -> dict[str, Any]:
        return self.service.cleanup_duplicate_execution_rows()

    def ingest_signal(self, payload: dict[str, Any]) -> dict[str, Any]:
        signal = SignalEnvelope(
            signal_id=payload["signal_id"],
            market_id=payload["market_id"],
            title=payload["title"],
            side=Side(payload["side"]),
            edge=float(payload["edge"]),
            confidence=float(payload["confidence"]),
            proposed_notional=float(payload["proposed_notional"]),
            source_run_id=payload["source_run_id"],
            expires_at=payload.get("expires_at", ""),
        )
        stored = self.service.ingest_signal(signal, payload["created_at"])
        return {"stored": True, "signal": _to_jsonable(stored)}

    def approve_signal(self, payload: dict[str, Any]) -> dict[str, Any]:
        decision = ApprovalDecision(
            signal_id=payload["decision"]["signal_id"],
            status=ApprovalStatus(payload["decision"]["status"]),
            decided_at=payload["decision"]["decided_at"],
            actor=payload["decision"]["actor"],
            rationale=payload["decision"].get("rationale", ""),
        )
        limits = RiskLimits(
            max_order_notional=float(payload["risk_limits"]["max_order_notional"]),
            kill_switch_active=bool(payload["risk_limits"].get("kill_switch_active", False)),
        )
        result = self.service.approve_signal(
            signal_id=payload["signal_id"],
            decision=decision,
            created_at=payload["created_at"],
            intent_id=payload["intent_id"],
            order_id=payload["order_id"],
            fill_id=payload["fill_id"],
            risk_limits=limits,
        )
        if result is None:
            return {"created": False, "reconcile": self.reconcile()}
        return {
            "created": True,
            "intent": _to_jsonable(result["intent"]),
            "order": _to_jsonable(result["order"]),
            "fill": _to_jsonable(result["fill"]),
            "position": _to_jsonable(result["position"]),
            "reconcile": self.reconcile(),
        }

    def settle_market(self, payload: dict[str, Any]) -> dict[str, Any]:
        positions = self.service.settle_market(
            market_id=payload["market_id"],
            winning_side=payload["winning_side"],
            created_at=payload["created_at"],
        )
        return {
            "settled": len(positions),
            "positions": [_to_jsonable(position) for position in positions],
            "reconcile": self.reconcile(),
        }

    def auto_trade(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.service.auto_trade_signals(
            created_at=payload["created_at"],
            min_edge=float(payload["min_edge"]),
            min_confidence=float(payload["min_confidence"]),
            max_notional=float(payload["max_notional"]),
            max_order_notional=float(payload["max_order_notional"]),
            actor=payload.get("actor", "auto-paper-trader"),
        )

    def paper_trade(self, payload: dict[str, Any]) -> dict[str, Any]:
        signal = SignalEnvelope(
            signal_id=payload["signal"]["signal_id"],
            market_id=payload["signal"]["market_id"],
            title=payload["signal"]["title"],
            side=Side(payload["signal"]["side"]),
            edge=float(payload["signal"]["edge"]),
            confidence=float(payload["signal"]["confidence"]),
            proposed_notional=float(payload["signal"]["proposed_notional"]),
            source_run_id=payload["signal"]["source_run_id"],
            expires_at=payload["signal"].get("expires_at", ""),
        )
        decision = ApprovalDecision(
            signal_id=payload["decision"]["signal_id"],
            status=ApprovalStatus(payload["decision"]["status"]),
            decided_at=payload["decision"]["decided_at"],
            actor=payload["decision"]["actor"],
            rationale=payload["decision"].get("rationale", ""),
        )
        limits = RiskLimits(
            max_order_notional=float(payload["risk_limits"]["max_order_notional"]),
            kill_switch_active=bool(payload["risk_limits"].get("kill_switch_active", False)),
        )
        result = self.service.paper_trade_approval(
            signal=signal,
            decision=decision,
            created_at=payload["created_at"],
            intent_id=payload["intent_id"],
            order_id=payload["order_id"],
            fill_id=payload["fill_id"],
            risk_limits=limits,
        )
        if result is None:
            return {"created": False, "reconcile": self.reconcile()}
        return {
            "created": True,
            "intent": _to_jsonable(result["intent"]),
            "order": _to_jsonable(result["order"]),
            "fill": _to_jsonable(result["fill"]),
            "position": _to_jsonable(result["position"]),
            "reconcile": self.reconcile(),
        }


def create_api(config: ExecutionConfig) -> ExecutionAPI:
    repository = SQLiteRepository(config.database_url)
    return ExecutionAPI(repository=repository)


def serve(config: ExecutionConfig, host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    api = create_api(config)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/ui"):
                self._send_html(render_operator_ui())
                return
            if self.path == "/health":
                self._send_json(api.health())
                return
            if self.path == "/reconcile":
                self._send_json(api.reconcile())
                return
            if self.path == "/signals":
                self._send_json(api.list_signals())
                return
            if self.path == "/trades":
                self._send_json(api.list_trades())
                return
            if self.path == "/report":
                self._send_json(api.performance_report())
                return
            if self.path == "/report.html":
                self._send_html(_render_report_html(api.performance_report()))
                return
            self.send_error(404)

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
            if self.path == "/paper-trade":
                self._send_json(api.paper_trade(payload))
                return
            if self.path == "/signals":
                self._send_json(api.ingest_signal(payload))
                return
            if self.path == "/approvals":
                self._send_json(api.approve_signal(payload))
                return
            if self.path == "/settlements":
                self._send_json(api.settle_market(payload))
                return
            if self.path == "/auto-trade":
                self._send_json(api.auto_trade(payload))
                return
            if self.path == "/cleanup-duplicates":
                self._send_json(api.cleanup_duplicates())
                return
            self.send_error(404)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _send_json(self, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer((host, port), Handler)
    return server


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    return value


def _render_report_html(report: dict[str, Any]) -> str:
    rows = [
        ("Orders", report["order_count"]),
        ("Fills", report["fill_count"]),
        ("Open Positions", report["open_position_count"]),
        ("Settled Positions", report["settled_position_count"]),
        ("Open Exposure", f"${report['open_exposure']:.2f}"),
        ("Total Cost", f"${report['total_cost']:.2f}"),
        ("Realized PnL", f"${report['realized_pnl']:.2f}"),
        ("Wins", report["wins"]),
        ("Losses", report["losses"]),
        ("Pushes", report["pushes"]),
    ]
    events = "".join(
        f"<li><code>{event['event_type']}</code> {event['created_at']} {event['payload']}</li>"
        for event in report["events"]
    )
    metrics = "".join(f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QuantWeather Execution Report</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; margin: 0; background: #f5f1e8; color: #17211f; }}
    main {{ max-width: 900px; margin: 0 auto; padding: 36px 22px; }}
    h1 {{ font-size: 44px; margin-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fffdf7; border: 1px solid #d9cfbb; }}
    th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #d9cfbb; }}
    code {{ background: #efe6d3; padding: 2px 5px; border-radius: 6px; }}
  </style>
</head>
<body>
  <main>
    <h1>QuantWeather Execution Report</h1>
    <p>Paper trading performance snapshot.</p>
    <table>{metrics}</table>
    <h2>Recent Events</h2>
    <ul>{events or '<li>No events yet.</li>'}</ul>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QuantWeather execution API/UI server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    server = serve(load_config(), host=args.host, port=args.port)
    print(f"QuantWeather Execution UI: http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
