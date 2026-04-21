from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class WeatherMetric(str, Enum):
    TEMPERATURE_HIGH_F = "temperature_high_f"
    TEMPERATURE_LOW_F = "temperature_low_f"
    PRECIPITATION_IN = "precipitation_in"
    PRECIPITATION_PROBABILITY = "precipitation_probability"


class Comparator(str, Enum):
    GREATER_EQUAL = ">="
    GREATER = ">"
    LESS_EQUAL = "<="
    LESS = "<"


class Side(str, Enum):
    YES = "YES"
    NO = "NO"


class SizingMethod(str, Enum):
    FIXED = "fixed"
    PROPORTIONAL = "proportional"
    FRACTIONAL_KELLY = "fractional_kelly"


class ApprovalState(str, Enum):
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class DecisionStatus(str, Enum):
    APPROVED = "approved"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass(frozen=True)
class EventRule:
    metric: WeatherMetric
    comparator: Comparator
    threshold: float
    location: str
    market_question: str


@dataclass(frozen=True)
class Market:
    market_id: str
    title: str
    yes_price: float
    no_price: float
    liquidity: float
    spread: float
    expires_at: str
    rules_text: str = ""


@dataclass(frozen=True)
class ForecastSnapshot:
    source: str
    observed_at: str
    location: str
    metrics: Dict[WeatherMetric, float]
    uncertainty: Dict[WeatherMetric, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ProbabilityEstimate:
    probability_yes: float
    confidence: float
    rationale: str
    inputs: Dict[str, float | str]


@dataclass(frozen=True)
class TradingSignal:
    market_id: str
    side: Side
    model_probability: float
    market_probability: float
    edge: float
    confidence: float
    rationale: str


@dataclass(frozen=True)
class RiskLimits:
    max_trade_notional: float
    max_market_exposure: float
    max_daily_risk: float
    min_confidence: float
    min_edge: float
    max_spread: float
    min_liquidity: float


@dataclass(frozen=True)
class PositionProposal:
    market_id: str
    side: Side
    notional: float
    sizing_method: SizingMethod
    blocked_reasons: List[str]
    approved: bool


@dataclass(frozen=True)
class RecommendationRecord:
    schema_version: str
    evaluation_id: str
    evaluated_at: str
    market_id: str
    market_title: str
    forecast_source: Optional[str]
    forecast_observed_at: Optional[str]
    location: Optional[str]
    rule_metric: Optional[str]
    rule_threshold: Optional[float]
    rule_comparator: Optional[str]
    model_version: str
    model_probability_yes: Optional[float]
    market_probability_yes: float
    edge: Optional[float]
    confidence: Optional[float]
    signal_side: Optional[Side]
    proposed_notional: Optional[float]
    approval_state: ApprovalState
    final_status: DecisionStatus
    reason_codes: List[str]
    error_message: Optional[str] = None


@dataclass(frozen=True)
class EvaluationResult:
    market: Market
    rule: EventRule
    estimate: ProbabilityEstimate
    signal: Optional[TradingSignal]
    proposal: PositionProposal
    recommendation: RecommendationRecord
