import unittest
from typing import Dict

from riskpilot.leverage.types import RiskStatus, TradeIntent, MarketType
from riskpilot.leverage.snapshot import LeverageMarketSnapshot
from riskpilot.leverage.engine import LeverageRiskEngine
from riskpilot.mitigation.types import MitigationAction, MitigationStatus
from riskpilot.mitigation.simulation import ProjectedPositionState
from riskpilot.trading.mitigation_workflow import evaluate_mitigation_workflow


class FixtureSimulator:
    def __init__(self, mapping: Dict[float, RiskStatus]):
        self._mapping = mapping

    def simulate(self, reduction_quantity: float) -> ProjectedPositionState:
        status = self._mapping.get(round(reduction_quantity, 10), RiskStatus.UNKNOWN)
        return ProjectedPositionState(quantity=reduction_quantity, risk_status=status)


REALISTIC_010_BTC_SIMULATOR = FixtureSimulator({
    0.01: RiskStatus.CRITICAL,
    0.02: RiskStatus.CRITICAL,
    0.04: RiskStatus.WARNING,
    0.06: RiskStatus.LOW,
    0.08: RiskStatus.LOW,
})


class TestMitigationRecommendationWithoutExecution(unittest.TestCase):
    """Test 1 — CRITICAL position produces a recommendation, never executes."""

    def test_critical_produces_partial_close_mapped_to_reduce_no_execution(self):
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertEqual(result.mitigation.status, MitigationStatus.RECOMMENDED)
        self.assertEqual(result.mitigation.recommended_action, MitigationAction.PARTIAL_CLOSE)
        self.assertEqual(result.mapped_trade_intent, TradeIntent.REDUCE)
        self.assertFalse(result.execution_performed)


class TestProjectedImprovementNotHardcoded(unittest.TestCase):
    """Test 2 — 0.10 BTC CRITICAL -> WARNING via the real, unmodified Phase 3 engine."""

    def test_010_btc_critical_to_warning_via_real_engine(self):
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertEqual(result.mitigation.current_risk, RiskStatus.CRITICAL)
        self.assertEqual(result.mitigation.projected_risk, RiskStatus.WARNING)
        self.assertEqual(result.mitigation.quantity, 0.04)

    def test_different_simulator_produces_different_result_not_hardcoded(self):
        # Proves the integration layer doesn't hard-code 0.04/WARNING —
        # it genuinely depends on the simulator passed in.
        harsher_simulator = FixtureSimulator({
            0.01: RiskStatus.CRITICAL,
            0.02: RiskStatus.CRITICAL,
            0.04: RiskStatus.CRITICAL,
            0.06: RiskStatus.CRITICAL,
            0.08: RiskStatus.WARNING,
        })
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=harsher_simulator,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertEqual(result.mitigation.quantity, 0.08)
        self.assertEqual(result.mitigation.projected_risk, RiskStatus.WARNING)


class TestPhase2RemainsAuthoritative(unittest.TestCase):
    """Test 3 — the integration cannot bypass Phase 2's existing hard-block rules."""

    def test_critical_open_still_blocked_via_direct_phase2_check(self):
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, post_trade_risk_status=RiskStatus.CRITICAL)
        result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.OPEN)
        self.assertTrue(result.hard_block)

    def test_critical_add_still_blocked_via_direct_phase2_check(self):
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, post_trade_risk_status=RiskStatus.CRITICAL)
        result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.ADD)
        self.assertTrue(result.hard_block)

    def test_critical_reduce_allowed_through_existing_gate(self):
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, current_risk_status=RiskStatus.CRITICAL)
        result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.REDUCE)
        self.assertFalse(result.hard_block)

    def test_workflow_reports_mitigation_action_not_hard_blocked(self):
        # The recommended mitigation itself (PARTIAL_CLOSE -> REDUCE) must
        # never be hard-blocked, since REDUCE is exempt in Phase 2.
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertFalse(result.would_be_hard_blocked)

    def test_workflow_never_sets_execution_performed_true(self):
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertIs(result.execution_performed, False)


class TestNoMitigationNormalFlowUnchanged(unittest.TestCase):
    """Test 4 — when mitigation is not applicable, behavior is exactly as before."""

    def test_low_risk_produces_not_needed_and_no_mapped_intent(self):
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.LOW,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        self.assertEqual(result.mitigation.status, MitigationStatus.NOT_NEEDED)
        self.assertIsNone(result.mapped_trade_intent)
        self.assertIsNone(result.would_be_hard_blocked)
        self.assertFalse(result.execution_performed)

    def test_no_market_type_skips_leverage_check_but_still_returns_mitigation(self):
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=None,
        )
        self.assertEqual(result.mitigation.status, MitigationStatus.RECOMMENDED)
        self.assertIsNone(result.would_be_hard_blocked)

    def test_as_dict_shape(self):
        result = evaluate_mitigation_workflow(
            current_risk=RiskStatus.CRITICAL,
            position_quantity=0.10,
            simulator=REALISTIC_010_BTC_SIMULATOR,
            market_type=MarketType.USD_M_FUTURES,
        )
        d = result.as_dict()
        self.assertEqual(d["status"], "RECOMMENDED")
        self.assertEqual(d["mapped_trade_intent"], "REDUCE")
        self.assertEqual(d["would_be_hard_blocked"], False)
        self.assertEqual(d["execution_performed"], False)


if __name__ == "__main__":
    unittest.main()
