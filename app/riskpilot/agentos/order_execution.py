"""
Order execution interface for Binance AgentOS.

`OrderExecutor` is an abstraction only. `DryRunOrderExecutor` is the
ONLY implementation shipped in this vertical slice, and it never sends
a real order anywhere — it returns a clearly labelled simulated result.
A real implementation backed by the connected Binance AgentOS execution
tools is a separate, explicit later step and must not be assumed to
exist just because this interface does.
"""

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class OrderExecutionResult:
    status: str  # e.g. "SIMULATED", "FAILED" — "SUBMITTED"/"FILLED" only from a real executor
    symbol: str
    side: str
    requested_quote_amount: float
    message: str
    is_live: bool
    raw_response: Optional[dict] = None


class OrderExecutor(Protocol):
    def place_market_order(self, symbol: str, side: str, quote_amount: float) -> OrderExecutionResult:
        ...


class DryRunOrderExecutor:
    """
    Safe default OrderExecutor. Never places a real order. Exists so the
    full trading flow (state machine, preview, confirmation gate,
    verification) can be exercised end-to-end before any live execution
    capability is wired in.
    """

    def place_market_order(self, symbol: str, side: str, quote_amount: float) -> OrderExecutionResult:
        return OrderExecutionResult(
            status="SIMULATED",
            symbol=symbol,
            side=side,
            requested_quote_amount=quote_amount,
            message=(
                "No live AgentOS execution capability is wired in. "
                "This is a simulated (dry-run) result only — no real order was sent."
            ),
            is_live=False,
            raw_response=None,
        )
