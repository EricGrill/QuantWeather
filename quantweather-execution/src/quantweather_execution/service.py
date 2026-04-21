from __future__ import annotations

from .approvals import can_execute
from .domain import ApprovalDecision, ApprovalStatus, Fill, Order, OrderStatus, SignalEnvelope
from .events import ExecutionEvent
from .orders import build_order_intent
from .positions import apply_fill, settle_position
from .repository import ExecutionRepository, InMemoryRepository
from .risk import RiskLimits, check_order_intent


DEFAULT_ACTOR = "auto-paper-trader"


class ExecutionService:
    def __init__(self, repository: ExecutionRepository | None = None) -> None:
        self.repository = repository or InMemoryRepository()

    def process_approval(
        self,
        signal: SignalEnvelope,
        decision: ApprovalDecision,
        created_at: str,
        intent_id: str,
        risk_limits: RiskLimits,
    ):
        self.repository.save_approval(decision)
        if not can_execute(decision):
            self.repository.append_event(
                ExecutionEvent(
                    event_type="approval_rejected",
                    created_at=created_at,
                    payload={"signal_id": signal.signal_id},
                )
            )
            return None

        intent = build_order_intent(signal=signal, created_at=created_at, intent_id=intent_id)
        risk_event = check_order_intent(intent, risk_limits, created_at)
        if risk_event is not None:
            self.repository.append_event(
                ExecutionEvent(
                    event_type="risk_blocked",
                    created_at=created_at,
                    payload={"signal_id": signal.signal_id, "message": risk_event.message},
                )
            )
            return None

        self.repository.save_order_intent(intent)
        self.repository.append_event(
            ExecutionEvent(
                event_type="order_intent_created",
                created_at=created_at,
                payload={"signal_id": signal.signal_id, "intent_id": intent.intent_id},
            )
        )
        return intent

    def ingest_signal(self, signal: SignalEnvelope, created_at: str) -> SignalEnvelope:
        self.repository.save_signal(signal)
        self.repository.append_event(
            ExecutionEvent(
                event_type="signal_ingested",
                created_at=created_at,
                payload={"signal_id": signal.signal_id, "source_run_id": signal.source_run_id},
            )
        )
        return signal

    def approve_signal(
        self,
        signal_id: str,
        decision: ApprovalDecision,
        created_at: str,
        intent_id: str,
        order_id: str,
        fill_id: str,
        risk_limits: RiskLimits,
    ):
        signal = self.repository.get_signal(signal_id)
        if signal is None:
            raise ValueError(f"Signal not found: {signal_id}")
        return self.paper_trade_approval(
            signal=signal,
            decision=decision,
            created_at=created_at,
            intent_id=intent_id,
            order_id=order_id,
            fill_id=fill_id,
            risk_limits=risk_limits,
        )

    def paper_trade_approval(
        self,
        signal: SignalEnvelope,
        decision: ApprovalDecision,
        created_at: str,
        intent_id: str,
        order_id: str,
        fill_id: str,
        risk_limits: RiskLimits,
    ):
        intent = self.process_approval(
            signal=signal,
            decision=decision,
            created_at=created_at,
            intent_id=intent_id,
            risk_limits=risk_limits,
        )
        if intent is None:
            return None

        order = Order(
            order_id=order_id,
            intent_id=intent.intent_id,
            market_id=intent.market_id,
            side=intent.side,
            status=OrderStatus.FILLED,
            price=0.5,
            size=intent.notional,
            created_at=created_at,
        )
        fill = Fill(
            fill_id=fill_id,
            order_id=order.order_id,
            price=order.price,
            size=order.size,
            filled_at=created_at,
        )

        current_position = next(
            (
                position
                for position in self.repository.list_positions()
                if position.market_id == order.market_id and position.side == order.side
            ),
            None,
        )
        position = apply_fill(current_position, order, fill)

        self.repository.save_order(order)
        self.repository.save_fill(fill)
        self.repository.save_position(position)
        self.repository.append_event(
            ExecutionEvent(
                event_type="paper_trade_filled",
                created_at=created_at,
                payload={
                    "signal_id": signal.signal_id,
                    "intent_id": intent.intent_id,
                    "order_id": order.order_id,
                    "fill_id": fill.fill_id,
                },
            )
        )
        return {
            "intent": intent,
            "order": order,
            "fill": fill,
            "position": position,
        }

    def reconcile_state(self) -> dict:
        approvals = self.repository.list_approvals()
        intents = self.repository.list_order_intents()
        orders = self.repository.list_orders()
        fills = self.repository.list_fills()
        positions = self.repository.list_positions()
        events = self.repository.list_events()

        intents_by_id = {intent.intent_id for intent in intents}
        orders_by_id = {order.order_id for order in orders}

        orphan_orders = [order.order_id for order in orders if order.intent_id not in intents_by_id]
        orphan_fills = [fill.fill_id for fill in fills if fill.order_id not in orders_by_id]

        return {
            "approval_count": len(approvals),
            "intent_count": len(intents),
            "order_count": len(orders),
            "fill_count": len(fills),
            "position_count": len(positions),
            "event_count": len(events),
            "orphan_orders": orphan_orders,
            "orphan_fills": orphan_fills,
            "healthy": not orphan_orders and not orphan_fills,
        }

    def list_trade_state(self) -> dict:
        orders = self.repository.list_orders()
        fills = self.repository.list_fills()
        positions = self.repository.list_positions()
        return {
            "orders": orders,
            "fills": fills,
            "positions": positions,
            "open_positions": [position for position in positions if not position.settled],
            "settled_positions": [position for position in positions if position.settled],
        }

    def performance_report(self) -> dict:
        state = self.list_trade_state()
        positions = state["positions"]
        settled_positions = state["settled_positions"]
        realized_pnl = sum(position.realized_pnl for position in settled_positions)
        wins = sum(1 for position in settled_positions if position.realized_pnl > 0)
        losses = sum(1 for position in settled_positions if position.realized_pnl < 0)
        pushes = sum(1 for position in settled_positions if position.realized_pnl == 0)
        open_exposure = sum(position.size * position.average_price for position in state["open_positions"])
        total_cost = sum(position.size * position.average_price for position in positions)

        return {
            "order_count": len(state["orders"]),
            "fill_count": len(state["fills"]),
            "open_position_count": len(state["open_positions"]),
            "settled_position_count": len(settled_positions),
            "open_exposure": round(open_exposure, 2),
            "total_cost": round(total_cost, 2),
            "realized_pnl": round(realized_pnl, 2),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "events": self.repository.list_events()[-10:],
        }

    def cleanup_duplicate_execution_rows(self) -> dict:
        result = self.repository.cleanup_duplicate_execution_rows()
        self.repository.append_event(
            ExecutionEvent(
                event_type="execution_rows_deduplicated",
                created_at="system",
                payload=result,
            )
        )
        return {
            **result,
            "reconcile": self.reconcile_state(),
        }

    def settle_market(self, market_id: str, winning_side: str, created_at: str) -> list:
        updated_positions = []
        for position in self.repository.list_positions():
            if position.market_id != market_id or position.settled:
                continue
            settled = settle_position(position, winning_side)
            self.repository.save_position(settled)
            updated_positions.append(settled)

        self.repository.append_event(
            ExecutionEvent(
                event_type="market_settled",
                created_at=created_at,
                payload={
                    "market_id": market_id,
                    "winning_side": winning_side,
                    "settled_positions": len(updated_positions),
                },
            )
        )
        return updated_positions

    def auto_trade_signals(
        self,
        *,
        created_at: str,
        min_edge: float,
        min_confidence: float,
        max_notional: float,
        max_order_notional: float,
        actor: str = DEFAULT_ACTOR,
    ) -> dict:
        results = []
        existing_intent_signal_ids = {intent.signal_id for intent in self.repository.list_order_intents()}

        for signal in self.repository.list_signals():
            reasons = []
            if signal.signal_id in existing_intent_signal_ids:
                reasons.append("already_traded")
            if signal.edge < min_edge:
                reasons.append("edge_below_min")
            if signal.confidence < min_confidence:
                reasons.append("confidence_below_min")
            if signal.proposed_notional > max_notional:
                reasons.append("notional_above_rule")

            if reasons:
                results.append(
                    {
                        "signal_id": signal.signal_id,
                        "action": "skipped",
                        "reasons": reasons,
                    }
                )
                continue

            decision = ApprovalDecision(
                signal_id=signal.signal_id,
                status=ApprovalStatus.APPROVED,
                decided_at=created_at,
                actor=actor,
                rationale="auto paper trade rules matched",
            )
            result = self.approve_signal(
                signal_id=signal.signal_id,
                decision=decision,
                created_at=created_at,
                intent_id=f"intent-{signal.signal_id}",
                order_id=f"order-{signal.signal_id}",
                fill_id=f"fill-{signal.signal_id}",
                risk_limits=RiskLimits(max_order_notional=max_order_notional),
            )
            results.append(
                {
                    "signal_id": signal.signal_id,
                    "action": "paper_traded" if result is not None else "blocked",
                    "reasons": [] if result is not None else ["risk_blocked"],
                }
            )

        self.repository.append_event(
            ExecutionEvent(
                event_type="auto_trade_evaluated",
                created_at=created_at,
                payload={
                    "evaluated": len(results),
                    "paper_traded": sum(1 for item in results if item["action"] == "paper_traded"),
                },
            )
        )
        return {
            "evaluated": len(results),
            "paper_traded": sum(1 for item in results if item["action"] == "paper_traded"),
            "skipped": sum(1 for item in results if item["action"] == "skipped"),
            "blocked": sum(1 for item in results if item["action"] == "blocked"),
            "results": results,
            "reconcile": self.reconcile_state(),
        }
