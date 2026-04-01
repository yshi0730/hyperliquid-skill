"""Performance metrics calculation."""

from __future__ import annotations

import math
from typing import List


def calculate_metrics(
    equity_curve: List[float],
    trades: List[dict],
    initial_capital: float,
    periods_per_year: int = 365,
) -> dict:
    """Calculate standard performance metrics from equity curve and trades."""

    if not equity_curve or len(equity_curve) < 2:
        return {"error": "Insufficient data"}

    final = equity_curve[-1]
    total_return = (final - initial_capital) / initial_capital

    # Daily returns
    returns = [(equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1] for i in range(1, len(equity_curve)) if equity_curve[i - 1] != 0]

    # Annualized return
    n_periods = len(equity_curve) - 1
    ann_return = (1 + total_return) ** (periods_per_year / max(n_periods, 1)) - 1

    # Sharpe ratio (assume 0 risk-free rate for crypto)
    if returns:
        avg_ret = sum(returns) / len(returns)
        std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / max(len(returns) - 1, 1))
        sharpe = (avg_ret / std_ret) * math.sqrt(periods_per_year) if std_ret > 0 else 0
    else:
        sharpe = 0

    # Max drawdown
    peak = equity_curve[0]
    max_dd = 0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)

    # Win rate & profit factor
    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) < 0]
    win_rate = len(wins) / len(trades) if trades else 0
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    return {
        "totalReturn": round(total_return * 100, 2),
        "annualizedReturn": round(ann_return * 100, 2),
        "sharpeRatio": round(sharpe, 3),
        "maxDrawdown": round(max_dd * 100, 2),
        "winRate": round(win_rate * 100, 2),
        "profitFactor": round(profit_factor, 3),
        "totalTrades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "grossProfit": round(gross_profit, 2),
        "grossLoss": round(gross_loss, 2),
        "finalEquity": round(final, 2),
        "initialCapital": initial_capital,
    }
