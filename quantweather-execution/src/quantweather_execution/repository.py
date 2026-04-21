from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import sqlite3
from typing import Protocol

from .domain import (
    ApprovalDecision,
    ApprovalStatus,
    Fill,
    Order,
    OrderIntent,
    OrderStatus,
    Position,
    SignalEnvelope,
    Side,
)
from .events import ExecutionEvent


class ExecutionRepository(Protocol):
    def save_signal(self, signal: SignalEnvelope) -> None: ...

    def save_approval(self, decision: ApprovalDecision) -> None: ...

    def save_order_intent(self, intent: OrderIntent) -> None: ...

    def save_order(self, order: Order) -> None: ...

    def save_fill(self, fill: Fill) -> None: ...

    def save_position(self, position: Position) -> None: ...

    def append_event(self, event: ExecutionEvent) -> None: ...

    def list_approvals(self) -> list[ApprovalDecision]: ...

    def list_signals(self) -> list[SignalEnvelope]: ...

    def get_signal(self, signal_id: str) -> SignalEnvelope | None: ...

    def list_order_intents(self) -> list[OrderIntent]: ...

    def list_orders(self) -> list[Order]: ...

    def list_fills(self) -> list[Fill]: ...

    def list_positions(self) -> list[Position]: ...

    def list_events(self) -> list[ExecutionEvent]: ...

    def cleanup_duplicate_execution_rows(self) -> dict: ...


@dataclass
class InMemoryRepository:
    signals: list[SignalEnvelope] = field(default_factory=list)
    approvals: list[ApprovalDecision] = field(default_factory=list)
    order_intents: list[OrderIntent] = field(default_factory=list)
    orders: list[Order] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    positions: list[Position] = field(default_factory=list)
    events: list[ExecutionEvent] = field(default_factory=list)

    def save_signal(self, signal: SignalEnvelope) -> None:
        self.signals = [s for s in self.signals if s.signal_id != signal.signal_id]
        self.signals.append(signal)

    def save_approval(self, decision: ApprovalDecision) -> None:
        self.approvals.append(decision)

    def save_order_intent(self, intent: OrderIntent) -> None:
        self.order_intents = [item for item in self.order_intents if item.intent_id != intent.intent_id]
        self.order_intents.append(intent)

    def save_order(self, order: Order) -> None:
        self.orders = [item for item in self.orders if item.order_id != order.order_id]
        self.orders.append(order)

    def save_fill(self, fill: Fill) -> None:
        self.fills = [item for item in self.fills if item.fill_id != fill.fill_id]
        self.fills.append(fill)

    def save_position(self, position: Position) -> None:
        self.positions = [p for p in self.positions if not (p.market_id == position.market_id and p.side == position.side)]
        self.positions.append(position)

    def append_event(self, event: ExecutionEvent) -> None:
        self.events.append(event)

    def list_signals(self) -> list[SignalEnvelope]:
        return list(self.signals)

    def get_signal(self, signal_id: str) -> SignalEnvelope | None:
        return next((signal for signal in self.signals if signal.signal_id == signal_id), None)

    def list_approvals(self) -> list[ApprovalDecision]:
        return list(self.approvals)

    def list_order_intents(self) -> list[OrderIntent]:
        return list(self.order_intents)

    def list_orders(self) -> list[Order]:
        return list(self.orders)

    def list_fills(self) -> list[Fill]:
        return list(self.fills)

    def list_positions(self) -> list[Position]:
        return list(self.positions)

    def list_events(self) -> list[ExecutionEvent]:
        return list(self.events)

    def cleanup_duplicate_execution_rows(self) -> dict:
        before = {
            "orders": len(self.orders),
            "fills": len(self.fills),
            "intents": len(self.order_intents),
        }
        self.order_intents = list({item.intent_id: item for item in self.order_intents}.values())
        self.orders = list({item.order_id: item for item in self.orders}.values())
        self.fills = list({item.fill_id: item for item in self.fills}.values())
        after = {
            "orders": len(self.orders),
            "fills": len(self.fills),
            "intents": len(self.order_intents),
        }
        return {"before": before, "after": after}


class SQLiteRepository:
    def __init__(self, database_url: str) -> None:
        self.path = _sqlite_path_from_url(database_url)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def save_approval(self, decision: ApprovalDecision) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO approvals (signal_id, status, decided_at, actor, rationale)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    decision.signal_id,
                    decision.status.value,
                    decision.decided_at,
                    decision.actor,
                    decision.rationale,
                ),
            )

    def save_signal(self, signal: SignalEnvelope) -> None:
        with self.connection:
            self.connection.execute(
                """
                DELETE FROM signals WHERE signal_id = ?
                """,
                (signal.signal_id,),
            )
            self.connection.execute(
                """
                INSERT INTO signals (signal_id, market_id, title, side, edge, confidence, proposed_notional, source_run_id, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.signal_id,
                    signal.market_id,
                    signal.title,
                    signal.side.value,
                    signal.edge,
                    signal.confidence,
                    signal.proposed_notional,
                    signal.source_run_id,
                    signal.expires_at,
                ),
            )

    def save_order_intent(self, intent: OrderIntent) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM order_intents WHERE intent_id = ?", (intent.intent_id,))
            self.connection.execute(
                """
                INSERT INTO order_intents (intent_id, signal_id, market_id, side, notional, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    intent.intent_id,
                    intent.signal_id,
                    intent.market_id,
                    intent.side.value,
                    intent.notional,
                    intent.created_at,
                ),
            )

    def save_order(self, order: Order) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM orders WHERE order_id = ?", (order.order_id,))
            self.connection.execute(
                """
                INSERT INTO orders (order_id, intent_id, market_id, side, status, price, size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.order_id,
                    order.intent_id,
                    order.market_id,
                    order.side.value,
                    order.status.value,
                    order.price,
                    order.size,
                    order.created_at,
                ),
            )

    def save_fill(self, fill: Fill) -> None:
        with self.connection:
            self.connection.execute("DELETE FROM fills WHERE fill_id = ?", (fill.fill_id,))
            self.connection.execute(
                """
                INSERT INTO fills (fill_id, order_id, price, size, filled_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    fill.fill_id,
                    fill.order_id,
                    fill.price,
                    fill.size,
                    fill.filled_at,
                ),
            )

    def save_position(self, position: Position) -> None:
        with self.connection:
            self.connection.execute(
                """
                DELETE FROM positions WHERE market_id = ? AND side = ?
                """,
                (position.market_id, position.side.value),
            )
            self.connection.execute(
                """
                INSERT INTO positions (market_id, side, size, average_price, realized_pnl, settled)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    position.market_id,
                    position.side.value,
                    position.size,
                    position.average_price,
                    position.realized_pnl,
                    int(position.settled),
                ),
            )

    def append_event(self, event: ExecutionEvent) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO execution_events (event_type, created_at, payload_json)
                VALUES (?, ?, ?)
                """,
                (
                    event.event_type,
                    event.created_at,
                    json.dumps(event.payload, sort_keys=True),
                ),
            )

    def list_approvals(self) -> list[ApprovalDecision]:
        rows = self.connection.execute(
            "SELECT signal_id, status, decided_at, actor, rationale FROM approvals ORDER BY rowid"
        ).fetchall()
        return [
            ApprovalDecision(
                signal_id=row["signal_id"],
                status=ApprovalStatus(row["status"]),
                decided_at=row["decided_at"],
                actor=row["actor"],
                rationale=row["rationale"],
            )
            for row in rows
        ]

    def list_signals(self) -> list[SignalEnvelope]:
        rows = self.connection.execute(
            "SELECT signal_id, market_id, title, side, edge, confidence, proposed_notional, source_run_id, expires_at FROM signals ORDER BY rowid"
        ).fetchall()
        return [
            SignalEnvelope(
                signal_id=row["signal_id"],
                market_id=row["market_id"],
                title=row["title"],
                side=Side(row["side"]),
                edge=row["edge"],
                confidence=row["confidence"],
                proposed_notional=row["proposed_notional"],
                source_run_id=row["source_run_id"],
                expires_at=row["expires_at"],
            )
            for row in rows
        ]

    def get_signal(self, signal_id: str) -> SignalEnvelope | None:
        row = self.connection.execute(
            """
            SELECT signal_id, market_id, title, side, edge, confidence, proposed_notional, source_run_id, expires_at
            FROM signals WHERE signal_id = ?
            """,
            (signal_id,),
        ).fetchone()
        if row is None:
            return None
        return SignalEnvelope(
            signal_id=row["signal_id"],
            market_id=row["market_id"],
            title=row["title"],
            side=Side(row["side"]),
            edge=row["edge"],
            confidence=row["confidence"],
            proposed_notional=row["proposed_notional"],
            source_run_id=row["source_run_id"],
            expires_at=row["expires_at"],
        )

    def list_order_intents(self) -> list[OrderIntent]:
        rows = self.connection.execute(
            "SELECT intent_id, signal_id, market_id, side, notional, created_at FROM order_intents ORDER BY rowid"
        ).fetchall()
        return [
            OrderIntent(
                intent_id=row["intent_id"],
                signal_id=row["signal_id"],
                market_id=row["market_id"],
                side=Side(row["side"]),
                notional=row["notional"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def list_orders(self) -> list[Order]:
        rows = self.connection.execute(
            "SELECT order_id, intent_id, market_id, side, status, price, size, created_at FROM orders ORDER BY rowid"
        ).fetchall()
        return [
            Order(
                order_id=row["order_id"],
                intent_id=row["intent_id"],
                market_id=row["market_id"],
                side=Side(row["side"]),
                status=OrderStatus(row["status"]),
                price=row["price"],
                size=row["size"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def list_fills(self) -> list[Fill]:
        rows = self.connection.execute(
            "SELECT fill_id, order_id, price, size, filled_at FROM fills ORDER BY rowid"
        ).fetchall()
        return [
            Fill(
                fill_id=row["fill_id"],
                order_id=row["order_id"],
                price=row["price"],
                size=row["size"],
                filled_at=row["filled_at"],
            )
            for row in rows
        ]

    def list_positions(self) -> list[Position]:
        rows = self.connection.execute(
            "SELECT market_id, side, size, average_price, realized_pnl, settled FROM positions ORDER BY rowid"
        ).fetchall()
        return [
            Position(
                market_id=row["market_id"],
                side=Side(row["side"]),
                size=row["size"],
                average_price=row["average_price"],
                realized_pnl=row["realized_pnl"],
                settled=bool(row["settled"]),
            )
            for row in rows
        ]

    def list_events(self) -> list[ExecutionEvent]:
        rows = self.connection.execute(
            "SELECT event_type, created_at, payload_json FROM execution_events ORDER BY rowid"
        ).fetchall()
        return [
            ExecutionEvent(
                event_type=row["event_type"],
                created_at=row["created_at"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        ]

    def cleanup_duplicate_execution_rows(self) -> dict:
        before = {
            "orders": self._count_rows("orders"),
            "fills": self._count_rows("fills"),
            "intents": self._count_rows("order_intents"),
        }
        with self.connection:
            self.connection.executescript(
                """
                DELETE FROM order_intents
                WHERE rowid NOT IN (
                    SELECT MAX(rowid) FROM order_intents GROUP BY intent_id
                );

                DELETE FROM orders
                WHERE rowid NOT IN (
                    SELECT MAX(rowid) FROM orders GROUP BY order_id
                );

                DELETE FROM fills
                WHERE rowid NOT IN (
                    SELECT MAX(rowid) FROM fills GROUP BY fill_id
                );
                """
            )
        after = {
            "orders": self._count_rows("orders"),
            "fills": self._count_rows("fills"),
            "intents": self._count_rows("order_intents"),
        }
        return {"before": before, "after": after}

    def close(self) -> None:
        self.connection.close()

    def _initialize_schema(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    signal_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decided_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    rationale TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signals (
                    signal_id TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    side TEXT NOT NULL,
                    edge REAL NOT NULL,
                    confidence REAL NOT NULL,
                    proposed_notional REAL NOT NULL,
                    source_run_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS order_intents (
                    intent_id TEXT NOT NULL,
                    signal_id TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    notional REAL NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT NOT NULL,
                    intent_id TEXT NOT NULL,
                    market_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    status TEXT NOT NULL,
                    price REAL NOT NULL,
                    size REAL NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS fills (
                    fill_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    size REAL NOT NULL,
                    filled_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS positions (
                    market_id TEXT NOT NULL,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    average_price REAL NOT NULL,
                    realized_pnl REAL NOT NULL DEFAULT 0,
                    settled INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS execution_events (
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )
            _add_column_if_missing(self.connection, "positions", "realized_pnl", "REAL NOT NULL DEFAULT 0")
            _add_column_if_missing(self.connection, "positions", "settled", "INTEGER NOT NULL DEFAULT 0")
            _add_column_if_missing(self.connection, "signals", "expires_at", "TEXT NOT NULL DEFAULT ''")

    def _count_rows(self, table: str) -> int:
        return int(self.connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])


def _sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// database URLs are supported in the starter repository")
    raw_path = database_url[len(prefix):]
    return Path(raw_path).expanduser()


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
