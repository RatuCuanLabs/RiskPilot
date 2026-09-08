"""
Trade Preview — a plain, deterministic snapshot of exactly what a
potential trade would look like, built entirely from prior engine
outputs. It never performs a calculation itself; it only assembles one.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TradePreview:
    symbol: str
    allocation_usdt: float
    momentum: str
    momentum_score: int
    risk: str
    decision: str

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "allocation_usdt": self.allocation_usdt,
            "momentum": self.momentum,
            "momentum_score": self.momentum_score,
            "risk": self.risk,
            "decision": self.decision,
        }

    def render(self) -> str:
        return (
            "TRADE PREVIEW\n"
            f"Symbol: {self.symbol}\n"
            f"Allocation: {self.allocation_usdt} USDT\n"
            f"Momentum: {self.momentum} {self.momentum_score}/4\n"
            f"Risk: {self.risk}\n"
            f"Decision: {self.decision}"
        )


def build_trade_preview(
    symbol: str,
    allocation_usdt: float,
    momentum: str,
    momentum_score: int,
    risk: str,
    decision: str,
) -> TradePreview:
    return TradePreview(
        symbol=symbol,
        allocation_usdt=allocation_usdt,
        momentum=momentum,
        momentum_score=momentum_score,
        risk=risk,
        decision=decision,
    )
