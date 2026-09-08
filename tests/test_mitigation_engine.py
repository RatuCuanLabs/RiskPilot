import unittest
from typing import Dict

from riskpilot.leverage.types import RiskStatus, TradeIntent
from riskpilot.leverage.snapshot import LeverageMarketSnapshot
from riskpilot.leverage.engine import LeverageRiskEngine
from riskpilot.leverage.types import MarketType
from riskpilot.mitigation.types import MitigationAction, MitigationStatus
from riskpilot.mitigation.simulation import ProjectedPositionState
from riskpilot.mitigation.engine import MitigationEngine
from riskpilot.mitigation.candidates import generate_reduction_candidates
from riskpilot.mitigation.integration import mitigation_action_to_trade_intent


class FixtureSimulator:
    """
    Deterministic test double: a fixed quantity -> risk_status mapping,
    standing in for a real (future) provider-backed simulator.
    """

    def __init__(self, mapping: Dict[float, RiskStatus]):
        self._mapping = mapping

    def simulate(self, reduction_quantity: float) -> ProjectedPositionState:
        status = self._mapping.get(round(reduction_quantity, 10), RiskStatus.UNKNOWN)
        return ProjectedPositionState(quantity=reduction_quantity, risk_status=status)


class TestCandidateGeneration(unittest.TestCase):

    def test_candidates_match_example_for_010_btc(self):
        candidates = generate_reduction_candidates(0.10)
        self.assertEqual(candidates, [0.01, 0.02, 0.04, 0.06, 0.08])

    def test_no_candidates_for_zero_or_none_position(self):
        self.assertEqual(generate_reduction_candidates(0.0), [])
        self.assertEqual(generate_reduction_candidates(None), [])


class TestMitigationEngineReduction(unittest.TestCase):

    def test_critical_position_produces_candidates_and_recommendation(self):
        simulator = FixtureSimulator({
            0.01: RiskStatus.CRITICAL,
            0.02: RiskStatus.CRITICAL,
            0.04: RiskStatus.WARNING,
            0.06: RiskStatus.LOW,
            0.08: RiskStatus.LOW,
        })
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        self.assertEqual(result.status, MitigationStatus.RECOMMENDED)
        self.assertEqual(result.recommended_action, MitigationAction.PARTIAL_CLOSE)
        self.assertEqual(result.quantity, 0.04)
        self.assertEqual(result.projected_risk, RiskStatus.WARNING)

    def test_candidate_that_remains_critical_is_rejected(self):
        # Only the largest candidate ever improves things; smaller ones must be skipped.
        simulator = FixtureSimulator({
            0.01: RiskStatus.CRITICAL,
            0.02: RiskStatus.CRITICAL,
            0.04: RiskStatus.CRITICAL,
            0.06: RiskStatus.CRITICAL,
            0.08: RiskStatus.WARNING,
        })
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        self.assertEqual(result.status, MitigationStatus.RECOMMENDED)
        self.assertEqual(result.quantity, 0.08)  # not any of the rejected smaller ones

    def test_smallest_effective_candidate_is_selected_not_a_larger_one(self):
        simulator = FixtureSimulator({
            0.01: RiskStatus.CRITICAL,
            0.02: RiskStatus.CRITICAL,
            0.04: RiskStatus.WARNING,
            0.06: RiskStatus.LOW,
            0.08: RiskStatus.LOW,
        })
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        self.assertEqual(result.quantity, 0.04)
        self.assertNotEqual(result.quantity, 0.06)

    def test_low_current_risk_produces_none_action(self):
        simulator = FixtureSimulator({})
        result = MitigationEngine.evaluate_reduction(RiskStatus.LOW, 0.10, simulator)
        self.assertEqual(result.recommended_action, MitigationAction.NONE)
        self.assertEqual(result.status, MitigationStatus.NOT_NEEDED)
        self.assertIsNone(result.quantity)

    def test_not_applicable_current_risk_produces_none_action(self):
        simulator = FixtureSimulator({})
        result = MitigationEngine.evaluate_reduction(RiskStatus.NOT_APPLICABLE, 0.10, simulator)
        self.assertEqual(result.recommended_action, MitigationAction.NONE)
        self.assertEqual(result.status, MitigationStatus.NOT_NEEDED)

    def test_no_candidate_improves_risk_returns_no_effective_mitigation(self):
        simulator = FixtureSimulator({
            0.01: RiskStatus.CRITICAL,
            0.02: RiskStatus.CRITICAL,
            0.04: RiskStatus.CRITICAL,
            0.06: RiskStatus.CRITICAL,
            0.08: RiskStatus.CRITICAL,
        })
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        self.assertEqual(result.status, MitigationStatus.NO_EFFECTIVE_MITIGATION)
        self.assertIsNone(result.quantity)

    def test_unverifiable_unknown_candidates_are_not_treated_as_improvement(self):
        simulator = FixtureSimulator({
            0.01: RiskStatus.UNKNOWN,
            0.02: RiskStatus.UNKNOWN,
            0.04: RiskStatus.UNKNOWN,
            0.06: RiskStatus.UNKNOWN,
            0.08: RiskStatus.UNKNOWN,
        })
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        self.assertEqual(result.status, MitigationStatus.NO_EFFECTIVE_MITIGATION)

    def test_unknown_current_risk_does_not_fabricate_a_recommendation(self):
        simulator = FixtureSimulator({0.04: RiskStatus.LOW})
        result = MitigationEngine.evaluate_reduction(RiskStatus.UNKNOWN, 0.10, simulator)
        self.assertEqual(result.status, MitigationStatus.NO_EFFECTIVE_MITIGATION)
        self.assertIsNone(result.quantity)


class TestHedgeNeverAssumedSafer(unittest.TestCase):

    def test_hedge_is_always_unsupported(self):
        result = MitigationEngine.evaluate_hedge(RiskStatus.CRITICAL)
        self.assertEqual(result.status, MitigationStatus.UNSUPPORTED)
        self.assertEqual(result.recommended_action, MitigationAction.HEDGE)
        self.assertIsNone(result.projected_risk)


class TestPhase2HardBlockUnaffected(unittest.TestCase):

    def test_critical_open_still_hard_blocks_after_phase3(self):
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, post_trade_risk_status=RiskStatus.CRITICAL)
        result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.OPEN)
        self.assertTrue(result.hard_block)

    def test_critical_add_still_hard_blocks_after_phase3(self):
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, post_trade_risk_status=RiskStatus.CRITICAL)
        result = LeverageRiskEngine.evaluate(snapshot, TradeIntent.ADD)
        self.assertTrue(result.hard_block)

    def test_partial_close_mitigation_maps_to_allowed_reduce_intent(self):
        intent = mitigation_action_to_trade_intent(MitigationAction.PARTIAL_CLOSE)
        self.assertEqual(intent, TradeIntent.REDUCE)
        snapshot = LeverageMarketSnapshot(market_type=MarketType.USD_M_FUTURES, current_risk_status=RiskStatus.CRITICAL)
        result = LeverageRiskEngine.evaluate(snapshot, intent)
        self.assertFalse(result.hard_block)  # risk-reducing action remains allowed


class TestMitigationResultShape(unittest.TestCase):

    def test_recommended_as_dict_matches_spec_shape(self):
        simulator = FixtureSimulator({0.04: RiskStatus.WARNING, 0.01: RiskStatus.CRITICAL, 0.02: RiskStatus.CRITICAL})
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        d = result.as_dict()["mitigation"]
        self.assertEqual(d["status"], "RECOMMENDED")
        self.assertEqual(d["recommended_action"], "PARTIAL_CLOSE")
        self.assertEqual(d["quantity"], 0.04)
        self.assertEqual(d["projected_risk"], "WARNING")

    def test_no_effective_mitigation_as_dict(self):
        simulator = FixtureSimulator({q: RiskStatus.CRITICAL for q in [0.01, 0.02, 0.04, 0.06, 0.08]})
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        d = result.as_dict()["mitigation"]
        self.assertEqual(d["status"], "NO_EFFECTIVE_MITIGATION")
        self.assertIsNone(d["quantity"])

    def test_unsupported_hedge_as_dict(self):
        result = MitigationEngine.evaluate_hedge(RiskStatus.CRITICAL)
        d = result.as_dict()["mitigation"]
        self.assertEqual(d["status"], "UNSUPPORTED")

    def test_render_proposal_contains_key_fields(self):
        simulator = FixtureSimulator({0.04: RiskStatus.WARNING, 0.01: RiskStatus.CRITICAL, 0.02: RiskStatus.CRITICAL})
        result = MitigationEngine.evaluate_reduction(RiskStatus.CRITICAL, 0.10, simulator)
        text = result.render_proposal(symbol="BTC")
        self.assertIn("CRITICAL", text)
        self.assertIn("WARNING", text)
        self.assertIn("0.04", text)
        self.assertIn("Confirm mitigation?", text)


if __name__ == "__main__":
    unittest.main()
