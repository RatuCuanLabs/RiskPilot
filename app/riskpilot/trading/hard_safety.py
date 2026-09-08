"""
Hard safety constraints.

These are NOT overrideable, unlike a WAIT/HOLD momentum recommendation.
If any hard violation is present, the trade must be blocked outright —
there is no "trading anyway?" path for these.

ASSUMPTION FLAGGED: MIN_TRADE_USDT below is a placeholder minimum-notional
value (no real Binance symbol filter data has been wired in yet). It is
called out explicitly rather than silently invented as a "real" exchange
rule — replace it once real spot symbol filters are available.

The 20%-of-total-trading-capital per-trade allocation limit IS an
explicit rule from the spec, not invented here.

No new post-trade *exposure* threshold is invented: exposure is
calculated and exposed (see exposure.py) but is not, by itself, hard
blocked, per instruction not to invent a threshold that doesn't exist
in the existing policy.
"""

from dataclasses import dataclass
from typing import List

from .portfolio_snapshot import PortfolioSnapshot

MIN_TRADE_USDT = 10.0  # ASSUMPTION: placeholder minimum notional, not sourced from a real Binance filter yet.
MAX_PER_TRADE_ALLOCATION_RATIO = 0.20  # 20% of TOTAL trading capital, per spec.

_FLOAT_TOLERANCE = 1e-9


@dataclass(frozen=True)
class HardSafetyResult:
    hard_block: bool
    override_allowed: bool
    violations: List[str]
    reason: str

    def as_dict(self) -> dict:
        return {
            "hard_block": self.hard_block,
            "override_allowed": self.override_allowed,
            "violations": self.violations,
            "reason": self.reason,
        }


class HardSafetyEngine:

    @classmethod
    def check(
        cls,
        symbol_supported: bool,
        amount: float,
        snapshot: PortfolioSnapshot,
    ) -> HardSafetyResult:
        violations: List[str] = []

        if not symbol_supported:
            violations.append("Unsupported symbol.")

        if amount is None or amount <= 0:
            violations.append("Invalid order amount.")
        else:
            if amount < MIN_TRADE_USDT:
                violations.append(
                    f"Order amount ({amount} USDT) is below the minimum trade size of {MIN_TRADE_USDT} USDT."
                )
            if amount > snapshot.available_balance:
                violations.append(
                    f"Insufficient available balance: requested {amount} USDT, "
                    f"available {snapshot.available_balance} USDT."
                )
            if snapshot.total_trading_capital > 0:
                allocation_ratio = amount / snapshot.total_trading_capital
                if allocation_ratio > MAX_PER_TRADE_ALLOCATION_RATIO + _FLOAT_TOLERANCE:
                    violations.append(
                        f"Requested allocation ({allocation_ratio:.2%} of total trading capital) "
                        f"exceeds the hard per-trade allocation limit of "
                        f"{MAX_PER_TRADE_ALLOCATION_RATIO:.0%}."
                    )
            else:
                violations.append("Total trading capital is zero or unknown; cannot validate allocation limit.")

        hard_block = len(violations) > 0
        reason = "; ".join(violations) if violations else "No hard safety violations detected."

        return HardSafetyResult(
            hard_block=hard_block,
            override_allowed=not hard_block,
            violations=violations,
            reason=reason,
        )
