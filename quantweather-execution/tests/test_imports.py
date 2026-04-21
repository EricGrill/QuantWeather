import unittest

from quantweather_execution import ExecutionService
from quantweather_execution.approvals import can_execute
from quantweather_execution.config import load_config
from quantweather_execution.domain import (
    ApprovalDecision,
    ApprovalStatus,
    SignalEnvelope,
    Side,
)
from quantweather_execution.risk import RiskLimits


class ExecutionSkeletonTests(unittest.TestCase):
    def test_config_loads(self) -> None:
        config = load_config()
        self.assertTrue(config.database_url)
        self.assertEqual(config.environment, "development")

    def test_rejected_approval_does_not_create_order_intent(self) -> None:
        service = ExecutionService()
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
        decision = ApprovalDecision(
            signal_id="sig-1",
            status=ApprovalStatus.REJECTED,
            decided_at="2026-04-20T17:39:29Z",
            actor="eric",
            rationale="not today",
        )

        intent = service.process_approval(
            signal=signal,
            decision=decision,
            created_at="2026-04-20T17:39:29Z",
            intent_id="intent-1",
            risk_limits=RiskLimits(max_order_notional=500.0),
        )

        self.assertIsNone(intent)
        self.assertFalse(can_execute(decision))


if __name__ == "__main__":
    unittest.main()
