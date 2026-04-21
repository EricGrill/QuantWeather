from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from quantweather_execution.domain import ApprovalDecision, ApprovalStatus, OrderIntent, Side, SignalEnvelope
from quantweather_execution.events import ExecutionEvent
from quantweather_execution.repository import SQLiteRepository


class SQLiteRepositoryTests(unittest.TestCase):
    def test_persists_approval_order_intent_and_event(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo = SQLiteRepository(f"sqlite:///{Path(tmpdir) / 'execution.db'}")

            repo.save_signal(
                SignalEnvelope(
                    signal_id="sig-1",
                    market_id="mkt-1",
                    title="NYC high at or above 80F?",
                    side=Side.YES,
                    edge=0.12,
                    confidence=0.75,
                    proposed_notional=100.0,
                    source_run_id="run-1",
                )
            )
            repo.save_approval(
                ApprovalDecision(
                    signal_id="sig-1",
                    status=ApprovalStatus.APPROVED,
                    decided_at="2026-04-20T17:39:29Z",
                    actor="eric",
                    rationale="looks good",
                )
            )
            repo.save_order_intent(
                OrderIntent(
                    intent_id="intent-1",
                    signal_id="sig-1",
                    market_id="mkt-1",
                    side=Side.YES,
                    notional=100.0,
                    created_at="2026-04-20T17:39:29Z",
                )
            )
            repo.append_event(
                ExecutionEvent(
                    event_type="order_intent_created",
                    created_at="2026-04-20T17:39:29Z",
                    payload={"intent_id": "intent-1"},
                )
            )

            approvals = repo.list_approvals()
            signals = repo.list_signals()
            intents = repo.list_order_intents()
            events = repo.list_events()
            repo.close()

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].signal_id, "sig-1")
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0].status, ApprovalStatus.APPROVED)
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].side, Side.YES)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["intent_id"], "intent-1")

    def test_rejects_non_sqlite_url(self) -> None:
        with self.assertRaises(ValueError):
            SQLiteRepository("postgres://not-supported")


if __name__ == "__main__":
    unittest.main()
