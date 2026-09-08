"""
Post-trade exposure calculation.

Calculates what the projected exposure to a given base token WOULD be
after a proposed trade. This module does NOT define or enforce a
threshold — no existing hard post-trade exposure policy exists in the
repository, so per instruction, the value is calculated and exposed
for display, not silently gated against an invented limit.

A trade converts available USDT into an asset position; it does not by
itself change total trading capital, so total_trading_capital is held
constant in the projection (only the mix of positions changes).
"""

from .portfolio_snapshot import PortfolioSnapshot


def calculate_post_trade_exposure(
    base_token: str,
    snapshot: PortfolioSnapshot,
    amount: float,
) -> float:
    """
    Returns the projected weight (0.0-1.0+) that `base_token` would
    represent of total trading capital after adding `amount` USDT worth
    of it. Returns 0.0 if total trading capital is zero/unknown.
    """
    if snapshot.total_trading_capital <= 0:
        return 0.0

    current_value = next(
        (p.value for p in snapshot.positions if p.symbol.upper() == base_token.upper()),
        0.0,
    )
    projected_value = current_value + amount
    return projected_value / snapshot.total_trading_capital
