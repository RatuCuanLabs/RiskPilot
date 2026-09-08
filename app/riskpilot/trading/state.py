"""
Deterministic conversational state machine for the trading flow.

Phase 1.5 additions on top of the Phase 1 machine:
    - OVERRIDE_REQUIRED: the "Trading anyway?" gate for a WAIT/HOLD
      recommendation. Distinct from, and prior to, the final trade
      confirmation.
    - FINAL_SAFETY_CHECK: a mandatory step between the user's final
      confirmation and actual execution, representing the fresh
      (snapshot #2) safety re-check. There is deliberately no direct
      WAITING_FOR_CONFIRMATION -> EXECUTING transition.
    - BLOCKED: terminal state for hard safety violations. No path leads
      from BLOCKED to execution.
    - VERIFICATION_FAILED: terminal state distinct from COMPLETE.

The machine is decision-aware only to the extent needed to prevent
bypassing the override gate: `set_analysis_result` records whether the
just-computed decision was actionable (EXECUTE/BUY WITH NOTE) or not
(WAIT/HOLD). TRADE_INTENT is only valid when actionable; OVERRIDE_REQUESTED
is only valid when not. This still performs no momentum/risk/decision
calculation itself — it only remembers which path is legal.
"""

from enum import Enum
from typing import Dict, Optional, Tuple


class TradeState(str, Enum):
    IDLE = "IDLE"
    WAITING_FOR_TOKEN = "WAITING_FOR_TOKEN"
    ANALYZING = "ANALYZING"
    ANALYSIS_READY = "ANALYSIS_READY"
    OVERRIDE_REQUIRED = "OVERRIDE_REQUIRED"
    WAITING_FOR_AMOUNT = "WAITING_FOR_AMOUNT"
    PREVIEW_READY = "PREVIEW_READY"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    FINAL_SAFETY_CHECK = "FINAL_SAFETY_CHECK"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"


class TradeEvent(str, Enum):
    ASK_TO_TRADE = "ASK_TO_TRADE"
    TOKEN_PROVIDED = "TOKEN_PROVIDED"
    ANALYSIS_COMPLETE = "ANALYSIS_COMPLETE"
    TRADE_INTENT = "TRADE_INTENT"                        # only valid when decision was actionable
    OVERRIDE_REQUESTED = "OVERRIDE_REQUESTED"             # only valid when decision was WAIT/HOLD
    OVERRIDE_ACCEPTED = "OVERRIDE_ACCEPTED"
    OVERRIDE_DECLINED = "OVERRIDE_DECLINED"
    AMOUNT_PROVIDED = "AMOUNT_PROVIDED"
    HARD_BLOCK_DETECTED = "HARD_BLOCK_DETECTED"
    PREVIEW_PRESENTED = "PREVIEW_PRESENTED"
    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"
    SAFETY_CHECK_PASSED = "SAFETY_CHECK_PASSED"
    EXECUTION_RESULT_RECEIVED = "EXECUTION_RESULT_RECEIVED"
    VERIFICATION_COMPLETE = "VERIFICATION_COMPLETE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    RESET = "RESET"


class InvalidTradeStateTransition(Exception):
    def __init__(self, state: TradeState, event: TradeEvent):
        super().__init__(f"Event {event.value} is not valid from state {state.value}.")
        self.state = state
        self.event = event


_TRANSITIONS: Dict[Tuple[TradeState, TradeEvent], TradeState] = {
    (TradeState.IDLE, TradeEvent.ASK_TO_TRADE): TradeState.WAITING_FOR_TOKEN,
    (TradeState.WAITING_FOR_TOKEN, TradeEvent.TOKEN_PROVIDED): TradeState.ANALYZING,
    (TradeState.ANALYZING, TradeEvent.ANALYSIS_COMPLETE): TradeState.ANALYSIS_READY,

    # Actionable decision (EXECUTE / BUY WITH NOTE): straight to amount collection.
    (TradeState.ANALYSIS_READY, TradeEvent.TRADE_INTENT): TradeState.WAITING_FOR_AMOUNT,

    # Non-actionable decision (WAIT/HOLD): must pass the override gate first.
    (TradeState.ANALYSIS_READY, TradeEvent.OVERRIDE_REQUESTED): TradeState.OVERRIDE_REQUIRED,
    (TradeState.OVERRIDE_REQUIRED, TradeEvent.OVERRIDE_ACCEPTED): TradeState.WAITING_FOR_AMOUNT,
    (TradeState.OVERRIDE_REQUIRED, TradeEvent.OVERRIDE_DECLINED): TradeState.CANCELLED,

    # A hard block can surface as soon as the token/amount is known.
    (TradeState.ANALYSIS_READY, TradeEvent.HARD_BLOCK_DETECTED): TradeState.BLOCKED,
    (TradeState.WAITING_FOR_AMOUNT, TradeEvent.HARD_BLOCK_DETECTED): TradeState.BLOCKED,

    (TradeState.WAITING_FOR_AMOUNT, TradeEvent.AMOUNT_PROVIDED): TradeState.PREVIEW_READY,
    (TradeState.PREVIEW_READY, TradeEvent.PREVIEW_PRESENTED): TradeState.WAITING_FOR_CONFIRMATION,
    (TradeState.PREVIEW_READY, TradeEvent.DECLINED): TradeState.CANCELLED,

    # Confirmation leads to a MANDATORY fresh safety check, never directly to execution.
    (TradeState.WAITING_FOR_CONFIRMATION, TradeEvent.CONFIRMED): TradeState.FINAL_SAFETY_CHECK,
    (TradeState.WAITING_FOR_CONFIRMATION, TradeEvent.DECLINED): TradeState.CANCELLED,

    (TradeState.FINAL_SAFETY_CHECK, TradeEvent.SAFETY_CHECK_PASSED): TradeState.EXECUTING,
    (TradeState.FINAL_SAFETY_CHECK, TradeEvent.HARD_BLOCK_DETECTED): TradeState.BLOCKED,

    (TradeState.EXECUTING, TradeEvent.EXECUTION_RESULT_RECEIVED): TradeState.VERIFYING,
    (TradeState.VERIFYING, TradeEvent.VERIFICATION_COMPLETE): TradeState.COMPLETE,
    (TradeState.VERIFYING, TradeEvent.VERIFICATION_FAILED): TradeState.VERIFICATION_FAILED,
}

# RESET is allowed from every state, including terminal ones, returning to IDLE.
for _state in TradeState:
    _TRANSITIONS[(_state, TradeEvent.RESET)] = TradeState.IDLE


class TradeConversation:
    """
    Wraps the raw transition table with current-state bookkeeping and a
    minimal decision-awareness guard (see module docstring). Every
    method either returns the new state or raises
    InvalidTradeStateTransition — it never silently no-ops.
    """

    def __init__(self, state: TradeState = TradeState.IDLE):
        self._state = state
        self._decision_actionable: Optional[bool] = None

    @property
    def state(self) -> TradeState:
        return self._state

    def set_analysis_result(self, decision_actionable: bool) -> None:
        """
        Record whether the most recently computed decision was
        actionable (True: EXECUTE/BUY WITH NOTE) or not (False:
        WAIT/HOLD). This does not itself change state; it only gates
        which of TRADE_INTENT / OVERRIDE_REQUESTED is legal next.
        """
        self._decision_actionable = decision_actionable

    def handle_event(self, event: TradeEvent) -> TradeState:
        if event == TradeEvent.TRADE_INTENT and self._state == TradeState.ANALYSIS_READY:
            if self._decision_actionable is not True:
                raise InvalidTradeStateTransition(self._state, event)
        if event == TradeEvent.OVERRIDE_REQUESTED and self._state == TradeState.ANALYSIS_READY:
            if self._decision_actionable is not False:
                raise InvalidTradeStateTransition(self._state, event)

        key = (self._state, event)
        if key not in _TRANSITIONS:
            raise InvalidTradeStateTransition(self._state, event)
        self._state = _TRANSITIONS[key]
        return self._state
