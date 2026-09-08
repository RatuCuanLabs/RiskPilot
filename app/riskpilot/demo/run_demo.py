from riskpilot.risk.portfolio import Position
from riskpilot.audit.auditor import audit_portfolio
from riskpilot.stress.stress_test import run_stress_test
from riskpilot.rebalance.proposal import create_rebalance_proposal
from riskpilot.confirmation.gate import create_confirmation_request, confirm_action
from riskpilot.execution.executor import create_execution_request, execute_request
from riskpilot.verification.verifier import verify_execution

from riskpilot.leverage.types import RiskStatus, MarketType
from riskpilot.mitigation.simulation import ProjectedPositionState
from riskpilot.trading.mitigation_workflow import evaluate_mitigation_workflow


class _DemoMitigationSimulator:
    """
    Demo-only fixture standing in for a real (not-yet-wired) provider.
    Fixed, hand-written quantity -> risk_status mapping — not a formula,
    not live data. Exists purely so this walkthrough is deterministic.
    """

    def __init__(self, mapping):
        self._mapping = mapping

    def simulate(self, reduction_quantity: float) -> ProjectedPositionState:
        status = self._mapping.get(round(reduction_quantity, 10), RiskStatus.UNKNOWN)
        return ProjectedPositionState(quantity=reduction_quantity, risk_status=status)


def run_phase3_mitigation_demo():
    print("\n[7] PHASE 3 — RISK MITIGATION (SIMULATED, NOT LIVE)")
    print("This section uses a hand-written demo fixture standing in for a")
    print("real exchange data provider. It is not live account data, and")
    print("nothing here places, modifies, or verifies a real order.")

    position_symbol = "BTC"
    position_quantity = 0.10
    current_risk = RiskStatus.CRITICAL

    # Fixture chosen to match the exact walkthrough requested: smallest
    # candidate that flips CRITICAL -> WARNING is 0.04, matching the
    # engine's real candidate set for a 0.10 position (0.01/0.02/0.04/0.06/0.08).
    simulator = _DemoMitigationSimulator({
        0.01: RiskStatus.CRITICAL,
        0.02: RiskStatus.CRITICAL,
        0.04: RiskStatus.WARNING,
        0.06: RiskStatus.LOW,
        0.08: RiskStatus.LOW,
    })

    print(f"\nPosition: {position_quantity} {position_symbol}")
    print(f"Current risk: {current_risk.value}")

    # Phase 4: route through the workflow integration layer rather than
    # calling MitigationEngine directly — this is the same underlying
    # engine call, plus the Phase 2 TradeIntent mapping and an
    # informational (non-gating) Phase 2 hard-block check, all in one place.
    workflow_result = evaluate_mitigation_workflow(
        current_risk=current_risk,
        position_quantity=position_quantity,
        simulator=simulator,
        market_type=MarketType.USD_M_FUTURES,
    )
    result = workflow_result.mitigation

    print(f"\nMitigation status: {result.status.value}")
    print(f"Recommended action: {result.recommended_action.value}")
    print(f"Proposed reduction: {result.quantity} {position_symbol}")
    print(f"Projected risk: {current_risk.value} -> {result.projected_risk.value}")
    print("\n(This is a proposal only — it is simulated, not executed.)")

    print(f"\nMaps to Phase 2 TradeIntent: {workflow_result.mapped_trade_intent.value}")
    print(f"Phase 2 hard_block for this action: {workflow_result.would_be_hard_blocked} "
          f"(risk-reducing actions remain allowed even under CRITICAL current risk)")
    print(f"Execution performed: {workflow_result.execution_performed}")
    print("No live Binance order was sent.")


def main():
    positions = [
        Position(symbol="BTC", value=6000),
        Position(symbol="ETH", value=2500),
        Position(symbol="SOL", value=1500),
    ]

    print("=== RiskPilot Demo ===")

    audit = audit_portfolio(positions)

    print("\n[1] RISK AUDIT")
    print(f"Total value: ${audit.total_value:,.2f}")
    print(f"Largest position: {audit.largest_position}")
    print(f"Largest weight: {audit.largest_weight:.2%}")
    print(f"Concentration risk: {audit.concentration_risk}")
    print(f"Action: {audit.action}")

    print("\n[2] STRESS TEST")
    stress = run_stress_test(positions, price_drop_percent=20)

    print(f"Scenario: {stress.scenario}")
    print(f"Original value: ${stress.original_value:,.2f}")
    print(f"Stressed value: ${stress.stressed_value:,.2f}")
    print(f"Loss: ${stress.loss:,.2f}")
    print(f"Loss percent: {stress.loss_percent:.2f}%")

    print("\n[3] REBALANCE PROPOSAL")
    proposals = create_rebalance_proposal(
        positions,
        target_max_weight=0.50,
    )

    for proposal in proposals:
        print(
            f"{proposal.symbol}: "
            f"{proposal.current_weight:.2%} -> "
            f"{proposal.target_weight:.2%}, "
            f"action={proposal.action}, "
            f"value_change=${proposal.value_change:,.2f}"
        )

    if not proposals:
        print("No rebalance required.")
        return

    proposal = proposals[0]

    print("\n[4] CONFIRMATION GATE")
    confirmation = create_confirmation_request(
        action=proposal.action,
        description=(
            f"Reduce {proposal.symbol} by "
            f"${abs(proposal.value_change):,.2f}"
        ),
    )

    print(f"Action: {confirmation.action}")
    print(f"Description: {confirmation.description}")
    print(f"Confirmed: {confirmation.confirmed}")

    confirmation = confirm_action(confirmation)

    print(f"Confirmed: {confirmation.confirmed}")

    print("\n[5] EXECUTION")
    execution = create_execution_request(
        symbol=proposal.symbol,
        action=proposal.action,
        value=proposal.value_change,
        reason="Reduce portfolio concentration risk.",
    )

    execution.confirmed = confirmation.confirmed

    result = execute_request(execution)

    print(f"Status: {result.status}")
    print(f"Message: {result.message}")

    print("\n[6] VERIFICATION")
    verification = verify_execution(
        symbol=proposal.symbol,
        expected_value=proposal.value_change,
        actual_value=proposal.value_change,
    )

    print(f"Status: {verification.status}")
    print(f"Expected value: ${verification.expected_value:,.2f}")
    print(f"Actual value: ${verification.actual_value:,.2f}")
    print(f"Difference: ${verification.difference:,.2f}")
    print(f"Message: {verification.message}")

    run_phase3_mitigation_demo()

    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
