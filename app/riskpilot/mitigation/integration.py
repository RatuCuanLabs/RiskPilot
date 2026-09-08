"""
Integration glue between the Phase 3 Mitigation Engine and the Phase 2
Leverage Risk Engine.

This module does not change any Phase 2 behavior — it only maps a
mitigation action onto the existing Phase 2 TradeIntent so that a
proposed mitigation can be run back through the unmodified Phase 2
hard-block gate for confirmation that risk-reducing actions remain
allowed even under CRITICAL current risk.
"""

from typing import Optional

from riskpilot.leverage.types import TradeIntent
from .types import MitigationAction

_ACTION_TO_INTENT = {
    MitigationAction.REDUCE_POSITION: TradeIntent.REDUCE,
    MitigationAction.PARTIAL_CLOSE: TradeIntent.REDUCE,
    MitigationAction.HEDGE: TradeIntent.HEDGE,
}


def mitigation_action_to_trade_intent(action: MitigationAction) -> Optional[TradeIntent]:
    """Returns None for MitigationAction.NONE, since there is no trade to check."""
    return _ACTION_TO_INTENT.get(action)
