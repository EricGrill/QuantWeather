from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class OrderStatus(str, Enum):
    PLANNED = "planned"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    SETTLED = "settled"


class Side(str, Enum):
    YES = "YES"
    NO = "NO"


@dataclass(frozen=True)
class SignalEnvelope:
    signal_id: str
    market_id: str
    title: str
    side: Side
    edge: float
    confidence: float
    proposed_notional: float
    source_run_id: str
    expires_at: str = ""


@dataclass(frozen=True)
class ApprovalDecision:
    signal_id: str
    status: ApprovalStatus
    decided_at: str
    actor: str
    rationale: str = ""


@dataclass(frozen=True)
class OrderIntent:
    intent_id: str
    signal_id: str
    market_id: str
    side: Side
    notional: float
    created_at: str


@dataclass(frozen=True)
class Order:
    order_id: str
    intent_id: str
    market_id: str
    side: Side
    status: OrderStatus
    price: float
    size: float
    created_at: str


@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    price: float
    size: float
    filled_at: str


@dataclass(frozen=True)
class Position:
    market_id: str
    side: Side
    size: float
    average_price: float
    realized_pnl: float = 0.0
    settled: bool = False


@dataclass(frozen=True)
class RiskEvent:
    event_id: str
    created_at: str
    message: str
    blocking: bool


@dataclass(frozen=True)
class PortfolioSnapshot:
    created_at: str
    cash: float
    reserved_cash: float
    positions: List[Position] = field(default_factory=list)
