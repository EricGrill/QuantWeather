"""Aggregate daily risk budget enforcement in screen_markets (CHA-4345)."""

import unittest

from quantweather.domain import (
    ForecastSnapshot,
    Market,
    PositionProposal,
    RiskLimits,
    Side,
    SizingMethod,
    WeatherMetric,
)
from quantweather.engine import evaluate_market, screen_markets
from quantweather.risk import apply_daily_risk_budget


MAX_DAILY_RISK = 500.0

FORECAST = ForecastSnapshot(
    source="test",
    observed_at="2026-04-20T12:00:00Z",
    location="New York City",
    metrics={
        WeatherMetric.TEMPERATURE_HIGH_F: 84.0,
        WeatherMetric.PRECIPITATION_IN: 0.0,
        WeatherMetric.PRECIPITATION_PROBABILITY: 0.1,
    },
    uncertainty={WeatherMetric.TEMPERATURE_HIGH_F: 4.0},
)


def _limits(max_daily_risk: float = MAX_DAILY_RISK) -> RiskLimits:
    # Every individual position is sized at the full daily budget, so without
    # aggregate enforcement each market alone would consume all of it.
    return RiskLimits(
        max_trade_notional=max_daily_risk,
        max_market_exposure=max_daily_risk,
        max_daily_risk=max_daily_risk,
        min_confidence=0.45,
        min_edge=0.05,
        max_spread=0.05,
        min_liquidity=5000.0,
    )


def _market(market_id: str, yes_price: float) -> Market:
    # Lower YES price -> larger edge for the same forecast.
    return Market(
        market_id=market_id,
        title="New York City high at or above 80F?",
        yes_price=yes_price,
        no_price=round(1.03 - yes_price, 2),
        liquidity=20000.0,
        spread=0.02,
        expires_at="2026-04-22T00:00:00Z",
    )


def _screen(markets, limits=None, daily_risk_used=0.0, method=SizingMethod.FIXED):
    return screen_markets(
        markets=markets,
        forecasts=[FORECAST],
        risk_limits=limits or _limits(),
        account_balance=10000.0,
        daily_risk_used=daily_risk_used,
        sizing_method=method,
    )


def _approved_total(records) -> float:
    return round(
        sum(r.proposed_notional or 0.0 for r in records if r.final_status.value == "approved"),
        2,
    )


def _sequential_reference_total(markets, limits, daily_risk_used=0.0, method=SizingMethod.FIXED):
    """Backtest reference semantics: size one trade at a time, advancing the
    accumulator after each fill, in the same consumption order as screening."""
    results = [
        evaluate_market(m, FORECAST, limits, 10000.0, daily_risk_used=daily_risk_used, sizing_method=method)
        for m in markets
    ]
    order = sorted(
        range(len(markets)),
        key=lambda i: -(results[i].signal.edge if results[i].signal is not None else 0.0),
    )
    used = daily_risk_used
    for i in order:
        result = evaluate_market(
            markets[i], FORECAST, limits, 10000.0, daily_risk_used=used, sizing_method=method
        )
        if result.proposal.approved:
            used += result.proposal.notional
    return round(used - daily_risk_used, 2)


class AggregateDailyRiskBudgetTests(unittest.TestCase):
    def test_each_market_alone_is_sized_at_the_full_budget(self) -> None:
        # Guard on the fixture: otherwise the aggregate test proves nothing.
        for market in [_market(f"m{i}", 0.30 + 0.02 * i) for i in range(10)]:
            result = evaluate_market(market, FORECAST, _limits(), 10000.0, sizing_method=SizingMethod.FIXED)
            self.assertTrue(result.proposal.approved)
            self.assertEqual(result.proposal.notional, MAX_DAILY_RISK)

    def test_total_approved_notional_never_exceeds_max_daily_risk(self) -> None:
        markets = [_market(f"m{i}", 0.30 + 0.02 * i) for i in range(10)]

        records = _screen(markets)

        self.assertEqual(len(records), 10)
        self.assertLessEqual(_approved_total(records), MAX_DAILY_RISK)
        self.assertEqual(_approved_total(records), MAX_DAILY_RISK)
        self.assertEqual(sum(r.final_status.value == "approved" for r in records), 1)

    def test_total_respects_budget_already_used_today(self) -> None:
        markets = [_market(f"m{i}", 0.30 + 0.02 * i) for i in range(5)]

        records = _screen(markets, daily_risk_used=350.0)

        self.assertEqual(_approved_total(records), 150.0)

    def test_budget_holds_for_proportional_and_kelly_sizing(self) -> None:
        markets = [_market(f"m{i}", 0.30 + 0.02 * i) for i in range(10)]
        for method in (SizingMethod.PROPORTIONAL, SizingMethod.FRACTIONAL_KELLY):
            with self.subTest(method=method):
                records = _screen(markets, method=method)
                self.assertLessEqual(_approved_total(records), MAX_DAILY_RISK)

    def test_reduced_and_refused_positions_carry_distinct_reason_codes(self) -> None:
        # 200 per trade against a 500 budget: 200 + 200 full, third reduced to
        # 100, fourth and fifth refused.
        limits = RiskLimits(
            max_trade_notional=200.0,
            max_market_exposure=200.0,
            max_daily_risk=500.0,
            min_confidence=0.45,
            min_edge=0.05,
            max_spread=0.05,
            min_liquidity=5000.0,
        )
        markets = [_market(f"m{i}", 0.30 + 0.02 * i) for i in range(5)]

        by_id = {r.market_id: r for r in _screen(markets, limits=limits)}

        self.assertEqual([by_id[m].proposed_notional for m in ("m0", "m1", "m2")], [200.0, 200.0, 100.0])
        for market_id in ("m0", "m1"):
            self.assertNotIn("DAILY_RISK_AGGREGATE_REDUCED", by_id[market_id].reason_codes)
        self.assertEqual(by_id["m2"].final_status.value, "approved")
        self.assertIn("DAILY_RISK_AGGREGATE_REDUCED", by_id["m2"].reason_codes)
        for market_id in ("m3", "m4"):
            record = by_id[market_id]
            self.assertEqual(record.final_status.value, "blocked")
            self.assertEqual(record.proposed_notional, 0.0)
            self.assertIn("DAILY_RISK_AGGREGATE_EXHAUSTED", record.reason_codes)
            # Distinct from the pre-existing whole-day code and the zero-size code.
            self.assertNotIn("DAILY_RISK_EXHAUSTED", record.reason_codes)
            self.assertNotIn("EDGE_BELOW_MIN", record.reason_codes)

    def test_budget_is_consumed_highest_edge_first_regardless_of_input_order(self) -> None:
        # Input order is lowest edge first; the highest edge must still win.
        markets = [_market(f"m{i}", 0.48 - 0.04 * i) for i in range(4)]

        records = _screen(markets)
        by_id = {r.market_id: r for r in records}
        winner = max(records, key=lambda r: r.edge or 0.0)

        self.assertEqual(winner.market_id, "m3")
        self.assertEqual(by_id["m3"].final_status.value, "approved")
        self.assertEqual(by_id["m3"].proposed_notional, MAX_DAILY_RISK)
        for market_id in ("m0", "m1", "m2"):
            self.assertIn("DAILY_RISK_AGGREGATE_EXHAUSTED", by_id[market_id].reason_codes)

    def test_consumption_order_does_not_depend_on_input_order(self) -> None:
        markets = [_market(f"m{i}", 0.30 + 0.03 * i) for i in range(6)]
        limits = RiskLimits(
            max_trade_notional=180.0,
            max_market_exposure=180.0,
            max_daily_risk=500.0,
            min_confidence=0.45,
            min_edge=0.05,
            max_spread=0.05,
            min_liquidity=5000.0,
        )

        forward = {r.market_id: r.proposed_notional for r in _screen(markets, limits=limits)}
        backward = {r.market_id: r.proposed_notional for r in _screen(list(reversed(markets)), limits=limits)}

        self.assertEqual(forward, backward)

    def test_screen_matches_sequential_backtest_reference_total(self) -> None:
        markets = [_market(f"m{i}", 0.30 + 0.02 * i) for i in range(8)]
        cases = [
            (_limits(), 0.0, SizingMethod.FIXED),
            (_limits(), 120.0, SizingMethod.FIXED),
            (
                RiskLimits(200.0, 200.0, 500.0, 0.45, 0.05, 0.05, 5000.0),
                0.0,
                SizingMethod.FIXED,
            ),
            (_limits(), 0.0, SizingMethod.PROPORTIONAL),
        ]
        for limits, used, method in cases:
            with self.subTest(limits=limits, used=used, method=method):
                self.assertEqual(
                    _approved_total(_screen(markets, limits=limits, daily_risk_used=used, method=method)),
                    _sequential_reference_total(markets, limits, used, method),
                )


class ApplyDailyRiskBudgetTests(unittest.TestCase):
    def _proposal(self, notional: float, approved: bool = True) -> PositionProposal:
        return PositionProposal(
            market_id="m",
            side=Side.YES,
            notional=notional,
            sizing_method=SizingMethod.FIXED,
            blocked_reasons=[] if approved else ["Market spread exceeds configured maximum."],
            approved=approved,
        )

    def test_fits_within_budget(self) -> None:
        proposal, remaining = apply_daily_risk_budget(self._proposal(100.0), 300.0)
        self.assertEqual((proposal.notional, proposal.approved, remaining), (100.0, True, 200.0))
        self.assertEqual(proposal.adjustments, [])

    def test_reduced_to_remainder(self) -> None:
        proposal, remaining = apply_daily_risk_budget(self._proposal(100.0), 40.0)
        self.assertEqual((proposal.notional, proposal.approved, remaining), (40.0, True, 0.0))
        self.assertEqual(len(proposal.adjustments), 1)

    def test_refused_when_exhausted(self) -> None:
        proposal, remaining = apply_daily_risk_budget(self._proposal(100.0), 0.0)
        self.assertEqual((proposal.notional, proposal.approved, remaining), (0.0, False, 0.0))

    def test_blocked_proposal_consumes_nothing(self) -> None:
        original = self._proposal(0.0, approved=False)
        proposal, remaining = apply_daily_risk_budget(original, 300.0)
        self.assertIs(proposal, original)
        self.assertEqual(remaining, 300.0)


if __name__ == "__main__":
    unittest.main()
