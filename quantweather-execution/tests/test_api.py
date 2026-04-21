import json
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen
import unittest

from quantweather_execution.api import ExecutionAPI, serve
from quantweather_execution.config import ExecutionConfig
from quantweather_execution.repository import InMemoryRepository


class ExecutionAPITests(unittest.TestCase):
    def test_health_and_reconcile(self) -> None:
        api = ExecutionAPI(repository=InMemoryRepository())

        self.assertEqual(api.health(), {"status": "ok"})
        self.assertTrue(api.reconcile()["healthy"])

    def test_paper_trade_returns_created_payload(self) -> None:
        api = ExecutionAPI(repository=InMemoryRepository())

        payload = {
            "signal": {
                "signal_id": "sig-api-1",
                "market_id": "mkt-api-1",
                "title": "NYC high at or above 80F?",
                "side": "YES",
                "edge": 0.12,
                "confidence": 0.75,
                "proposed_notional": 100.0,
                "source_run_id": "run-api-1",
            },
            "decision": {
                "signal_id": "sig-api-1",
                "status": "approved",
                "decided_at": "2026-04-20T18:10:00Z",
                "actor": "eric",
                "rationale": "go",
            },
            "risk_limits": {"max_order_notional": 500.0},
            "created_at": "2026-04-20T18:10:00Z",
            "intent_id": "intent-api-1",
            "order_id": "order-api-1",
            "fill_id": "fill-api-1",
        }

        result = api.paper_trade(payload)

        self.assertTrue(result["created"])
        self.assertEqual(result["intent"]["intent_id"], "intent-api-1")
        self.assertEqual(result["order"]["order_id"], "order-api-1")
        self.assertEqual(result["position"]["market_id"], "mkt-api-1")
        self.assertTrue(result["reconcile"]["healthy"])

    def test_signal_ingest_and_approval_flow(self) -> None:
        api = ExecutionAPI(repository=InMemoryRepository())

        signal_payload = {
            "signal_id": "sig-api-2",
            "market_id": "mkt-api-2",
            "title": "NYC high at or above 80F?",
            "side": "YES",
            "edge": 0.12,
            "confidence": 0.75,
            "proposed_notional": 100.0,
            "source_run_id": "run-api-2",
            "created_at": "2026-04-20T18:12:00Z",
        }
        ingest = api.ingest_signal(signal_payload)
        self.assertTrue(ingest["stored"])
        self.assertEqual(len(api.list_signals()["signals"]), 1)

        approval_payload = {
            "signal_id": "sig-api-2",
            "decision": {
                "signal_id": "sig-api-2",
                "status": "approved",
                "decided_at": "2026-04-20T18:12:01Z",
                "actor": "eric",
            },
            "risk_limits": {"max_order_notional": 500.0},
            "created_at": "2026-04-20T18:12:01Z",
            "intent_id": "intent-api-2",
            "order_id": "order-api-2",
            "fill_id": "fill-api-2",
        }
        approved = api.approve_signal(approval_payload)
        self.assertTrue(approved["created"])
        self.assertEqual(approved["order"]["order_id"], "order-api-2")

        trades = api.list_trades()
        self.assertEqual(len(trades["orders"]), 1)
        self.assertEqual(len(trades["open_positions"]), 1)

        settlement = api.settle_market(
            {
                "market_id": "mkt-api-2",
                "winning_side": "YES",
                "created_at": "2026-04-20T19:00:00Z",
            }
        )
        self.assertEqual(settlement["settled"], 1)
        self.assertEqual(settlement["positions"][0]["realized_pnl"], 50.0)

        report = api.performance_report()
        self.assertEqual(report["realized_pnl"], 50.0)
        self.assertEqual(report["wins"], 1)
        self.assertEqual(report["losses"], 0)

    def test_auto_trade_endpoint_trades_matching_stored_signal(self) -> None:
        api = ExecutionAPI(repository=InMemoryRepository())
        signal_payload = {
            "signal_id": "sig-api-auto",
            "market_id": "mkt-api-auto",
            "title": "NYC high at or above 80F?",
            "side": "YES",
            "edge": 0.12,
            "confidence": 0.75,
            "proposed_notional": 100.0,
            "source_run_id": "run-api-auto",
            "created_at": "2026-04-20T18:30:00Z",
        }
        api.ingest_signal(signal_payload)

        result = api.auto_trade(
            {
                "created_at": "2026-04-20T18:35:00Z",
                "min_edge": 0.05,
                "min_confidence": 0.45,
                "max_notional": 250.0,
                "max_order_notional": 500.0,
            }
        )

        self.assertEqual(result["paper_traded"], 1)
        self.assertEqual(len(api.list_trades()["orders"]), 1)

    def test_cleanup_duplicates_endpoint(self) -> None:
        api = ExecutionAPI(repository=InMemoryRepository())
        result = api.cleanup_duplicates()

        self.assertIn("before", result)
        self.assertIn("after", result)


class ExecutionHTTPServerTests(unittest.TestCase):
    def test_server_health_and_paper_trade(self) -> None:
        with TemporaryDirectory() as tmpdir:
            config = ExecutionConfig(database_url=f"sqlite:///{Path(tmpdir) / 'execution.db'}")
            server = serve(config, host="127.0.0.1", port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                health = json.loads(urlopen(f"{base}/health").read().decode("utf-8"))
                self.assertEqual(health["status"], "ok")

                html = urlopen(f"{base}/").read().decode("utf-8")
                self.assertIn("QuantWeather Execution Console", html)
                self.assertIn("Approve + Paper Trade", html)
                self.assertIn("Open Trades", html)
                self.assertIn("Settle Market", html)
                self.assertIn("Performance Report", html)
                self.assertIn("Auto Paper Trade Rules", html)

                signal_payload = {
                    "signal_id": "sig-http-1",
                    "market_id": "mkt-http-1",
                    "title": "NYC high at or above 80F?",
                    "side": "YES",
                    "edge": 0.12,
                    "confidence": 0.75,
                    "proposed_notional": 100.0,
                    "source_run_id": "run-http-1",
                    "created_at": "2026-04-20T18:11:00Z",
                }
                signal_req = Request(
                    f"{base}/signals",
                    data=json.dumps(signal_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                signal_response = json.loads(urlopen(signal_req).read().decode("utf-8"))
                self.assertTrue(signal_response["stored"])

                payload = {
                    "signal_id": "sig-http-1",
                    "decision": {
                        "signal_id": "sig-http-1",
                        "status": "approved",
                        "decided_at": "2026-04-20T18:11:00Z",
                        "actor": "eric",
                    },
                    "risk_limits": {"max_order_notional": 500.0},
                    "created_at": "2026-04-20T18:11:00Z",
                    "intent_id": "intent-http-1",
                    "order_id": "order-http-1",
                    "fill_id": "fill-http-1",
                }
                req = Request(
                    f"{base}/approvals",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response = json.loads(urlopen(req).read().decode("utf-8"))
                self.assertTrue(response["created"])
                self.assertEqual(response["order"]["order_id"], "order-http-1")

                report = json.loads(urlopen(f"{base}/report").read().decode("utf-8"))
                self.assertEqual(report["order_count"], 1)
                printable = urlopen(f"{base}/report.html").read().decode("utf-8")
                self.assertIn("QuantWeather Execution Report", printable)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
