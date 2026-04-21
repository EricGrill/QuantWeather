import unittest

from quantweather_execution.domain import ApprovalDecision, ApprovalStatus, SignalEnvelope, Side
from quantweather_execution.repository import InMemoryRepository
from quantweather_execution.risk import RiskLimits
from quantweather_execution.service import ExecutionService


class ExecutionServicePaperTradeTests(unittest.TestCase):
    def test_ingest_signal_persists_signal_and_event(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        signal = SignalEnvelope(
            signal_id="sig-1",
            market_id="mkt-1",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-1",
        )

        stored = service.ingest_signal(signal, created_at="2026-04-20T18:20:00Z")

        self.assertEqual(stored.signal_id, "sig-1")
        self.assertEqual(len(repository.list_signals()), 1)
        self.assertEqual(repository.list_events()[-1].event_type, "signal_ingested")

    def test_paper_trade_approval_persists_order_fill_and_position(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        signal = SignalEnvelope(
            signal_id="sig-2",
            market_id="mkt-2",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-2",
        )
        decision = ApprovalDecision(
            signal_id="sig-2",
            status=ApprovalStatus.APPROVED,
            decided_at="2026-04-20T17:50:00Z",
            actor="eric",
            rationale="go",
        )

        result = service.paper_trade_approval(
            signal=signal,
            decision=decision,
            created_at="2026-04-20T17:50:00Z",
            intent_id="intent-2",
            order_id="order-2",
            fill_id="fill-2",
            risk_limits=RiskLimits(max_order_notional=500.0),
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(repository.list_order_intents()), 1)
        self.assertEqual(len(repository.list_orders()), 1)
        self.assertEqual(len(repository.list_fills()), 1)
        self.assertEqual(len(repository.list_positions()), 1)
        self.assertEqual(repository.list_positions()[0].size, 100.0)
        self.assertEqual(repository.list_events()[-1].event_type, "paper_trade_filled")

    def test_paper_trade_blocked_by_kill_switch_creates_no_order(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        signal = SignalEnvelope(
            signal_id="sig-3",
            market_id="mkt-3",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-3",
        )
        decision = ApprovalDecision(
            signal_id="sig-3",
            status=ApprovalStatus.APPROVED,
            decided_at="2026-04-20T17:51:00Z",
            actor="eric",
            rationale="go",
        )

        result = service.paper_trade_approval(
            signal=signal,
            decision=decision,
            created_at="2026-04-20T17:51:00Z",
            intent_id="intent-3",
            order_id="order-3",
            fill_id="fill-3",
            risk_limits=RiskLimits(max_order_notional=500.0, kill_switch_active=True),
        )

        self.assertIsNone(result)
        self.assertEqual(len(repository.list_order_intents()), 0)
        self.assertEqual(len(repository.list_orders()), 0)
        self.assertEqual(repository.list_events()[-1].event_type, "risk_blocked")

    def test_reconcile_state_reports_healthy_paper_trade(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        signal = SignalEnvelope(
            signal_id="sig-4",
            market_id="mkt-4",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-4",
        )
        decision = ApprovalDecision(
            signal_id="sig-4",
            status=ApprovalStatus.APPROVED,
            decided_at="2026-04-20T17:52:00Z",
            actor="eric",
            rationale="go",
        )

        service.paper_trade_approval(
            signal=signal,
            decision=decision,
            created_at="2026-04-20T17:52:00Z",
            intent_id="intent-4",
            order_id="order-4",
            fill_id="fill-4",
            risk_limits=RiskLimits(max_order_notional=500.0),
        )

        report = service.reconcile_state()

        self.assertTrue(report["healthy"])
        self.assertEqual(report["intent_count"], 1)
        self.assertEqual(report["order_count"], 1)
        self.assertEqual(report["fill_count"], 1)
        self.assertEqual(report["position_count"], 1)
        self.assertEqual(report["orphan_orders"], [])
        self.assertEqual(report["orphan_fills"], [])

    def test_settle_market_records_realized_pnl(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        signal = SignalEnvelope(
            signal_id="sig-6",
            market_id="mkt-6",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-6",
        )
        decision = ApprovalDecision(
            signal_id="sig-6",
            status=ApprovalStatus.APPROVED,
            decided_at="2026-04-20T18:22:00Z",
            actor="eric",
        )
        service.paper_trade_approval(
            signal=signal,
            decision=decision,
            created_at="2026-04-20T18:22:00Z",
            intent_id="intent-6",
            order_id="order-6",
            fill_id="fill-6",
            risk_limits=RiskLimits(max_order_notional=500.0),
        )

        settled = service.settle_market(
            market_id="mkt-6",
            winning_side="YES",
            created_at="2026-04-20T19:00:00Z",
        )

        self.assertEqual(len(settled), 1)
        self.assertTrue(settled[0].settled)
        self.assertEqual(settled[0].realized_pnl, 50.0)
        self.assertEqual(repository.list_events()[-1].event_type, "market_settled")

    def test_approve_signal_uses_persisted_signal(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        signal = SignalEnvelope(
            signal_id="sig-5",
            market_id="mkt-5",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-5",
        )
        service.ingest_signal(signal, created_at="2026-04-20T18:21:00Z")
        decision = ApprovalDecision(
            signal_id="sig-5",
            status=ApprovalStatus.APPROVED,
            decided_at="2026-04-20T18:21:01Z",
            actor="eric",
        )

        result = service.approve_signal(
            signal_id="sig-5",
            decision=decision,
            created_at="2026-04-20T18:21:01Z",
            intent_id="intent-5",
            order_id="order-5",
            fill_id="fill-5",
            risk_limits=RiskLimits(max_order_notional=500.0),
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(repository.list_order_intents()), 1)
        self.assertEqual(repository.list_order_intents()[0].signal_id, "sig-5")

    def test_auto_trade_signals_trades_matching_signal_and_skips_weak_signal(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        strong = SignalEnvelope(
            signal_id="sig-auto-strong",
            market_id="mkt-auto-1",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-auto",
        )
        weak = SignalEnvelope(
            signal_id="sig-auto-weak",
            market_id="mkt-auto-2",
            title="Chicago high at or above 70F?",
            side=Side.YES,
            edge=0.01,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-auto",
        )
        service.ingest_signal(strong, created_at="2026-04-20T18:30:00Z")
        service.ingest_signal(weak, created_at="2026-04-20T18:30:00Z")

        result = service.auto_trade_signals(
            created_at="2026-04-20T18:35:00Z",
            min_edge=0.05,
            min_confidence=0.45,
            max_notional=250.0,
            max_order_notional=500.0,
        )

        self.assertEqual(result["evaluated"], 2)
        self.assertEqual(result["paper_traded"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(len(repository.list_orders()), 1)
        self.assertEqual(repository.list_orders()[0].market_id, "mkt-auto-1")

    def test_cleanup_duplicate_execution_rows(self) -> None:
        repository = InMemoryRepository()
        service = ExecutionService(repository=repository)
        signal = SignalEnvelope(
            signal_id="sig-clean",
            market_id="mkt-clean",
            title="NYC high at or above 80F?",
            side=Side.YES,
            edge=0.12,
            confidence=0.75,
            proposed_notional=100.0,
            source_run_id="run-clean",
        )
        decision = ApprovalDecision(
            signal_id="sig-clean",
            status=ApprovalStatus.APPROVED,
            decided_at="2026-04-20T18:40:00Z",
            actor="eric",
        )
        for _ in range(2):
            service.paper_trade_approval(
                signal=signal,
                decision=decision,
                created_at="2026-04-20T18:40:00Z",
                intent_id="intent-clean",
                order_id="order-clean",
                fill_id="fill-clean",
                risk_limits=RiskLimits(max_order_notional=500.0),
            )

        result = service.cleanup_duplicate_execution_rows()

        self.assertEqual(result["after"]["orders"], 1)
        self.assertEqual(result["after"]["fills"], 1)
        self.assertEqual(result["after"]["intents"], 1)


if __name__ == "__main__":
    unittest.main()
