"""Backtest engine for Hyperliquid strategies."""

from __future__ import annotations

import json
import logging
from typing import Any

from .metrics import calculate_metrics

logger = logging.getLogger(__name__)


def run_backtest(
    strategy_rules: dict,
    candles: list[dict],
    initial_capital: float = 10000.0,
) -> dict:
    """Run a backtest against historical candle data.

    Args:
        strategy_rules: Strategy definition with entry/exit/risk rules
        candles: List of OHLCV candle dicts (must have 'o', 'h', 'l', 'c', 'v', 't' keys)
        initial_capital: Starting capital in USDC
    """
    if not candles or len(candles) < 20:
        return {"error": "Need at least 20 candles for backtest"}

    equity = initial_capital
    position = 0.0  # positive=long, negative=short
    entry_price = 0.0
    equity_curve = [equity]
    trades = []
    closes = [float(c["c"]) for c in candles]

    risk = strategy_rules.get("risk", {})
    stop_loss_pct = risk.get("stop_loss_pct", 5) / 100
    take_profit_pct = risk.get("take_profit_pct", 15) / 100
    max_pos_pct = risk.get("max_position_pct", 20) / 100

    entry_rule = strategy_rules.get("entry", {})
    exit_rule = strategy_rules.get("exit", {})
    indicator = entry_rule.get("indicator", "sma_crossover")
    period = entry_rule.get("period", 20)

    for i in range(period, len(closes)):
        price = closes[i]

        # Compute simple indicators
        sma = sum(closes[i - period:i]) / period
        high_n = max(closes[i - period:i])
        low_n = min(closes[i - period:i])

        # Check stop loss / take profit
        if position != 0:
            pnl_pct = (price - entry_price) / entry_price if position > 0 else (entry_price - price) / entry_price
            if pnl_pct <= -stop_loss_pct or pnl_pct >= take_profit_pct:
                pnl = position * (price - entry_price)
                equity += pnl
                trades.append({"type": "exit", "price": price, "size": abs(position), "pnl": pnl, "reason": "stop_loss" if pnl_pct <= -stop_loss_pct else "take_profit"})
                position = 0.0
                entry_price = 0.0

        # Entry signals
        if position == 0:
            signal = None
            if indicator == "sma_crossover":
                if closes[i - 1] < sma and price >= sma:
                    signal = "long"
                elif closes[i - 1] > sma and price <= sma:
                    signal = "short"
            elif indicator == "price_vs_high":
                if price > high_n:
                    signal = "long"
            elif indicator == "price_vs_low":
                if price < low_n:
                    signal = "short"
            elif indicator == "bb_lower_touch" or indicator == "bb_upper_touch":
                std_val = (sum((c - sma) ** 2 for c in closes[i - period:i]) / period) ** 0.5
                bb_upper = sma + 2 * std_val
                bb_lower = sma - 2 * std_val
                if price <= bb_lower:
                    signal = "long"
                elif price >= bb_upper:
                    signal = "short"

            if signal:
                max_size_usd = equity * max_pos_pct
                size = max_size_usd / price
                if signal == "long":
                    position = size
                else:
                    position = -size
                entry_price = price
                trades.append({"type": "entry", "side": signal, "price": price, "size": abs(position)})

        # Exit signals
        elif position != 0:
            exit_indicator = exit_rule.get("indicator", "")
            exit_period = exit_rule.get("period", period)
            if exit_indicator == "sma_cross":
                exit_sma = sum(closes[i - exit_period:i]) / exit_period
                if (position > 0 and price < exit_sma) or (position < 0 and price > exit_sma):
                    pnl = position * (price - entry_price)
                    equity += pnl
                    trades.append({"type": "exit", "price": price, "size": abs(position), "pnl": pnl, "reason": "signal"})
                    position = 0.0
                    entry_price = 0.0
            elif exit_indicator == "price_vs_low" and position > 0:
                exit_low = min(closes[i - exit_period:i])
                if price < exit_low:
                    pnl = position * (price - entry_price)
                    equity += pnl
                    trades.append({"type": "exit", "price": price, "size": abs(position), "pnl": pnl, "reason": "signal"})
                    position = 0.0

        # Mark to market
        if position != 0:
            mtm = equity + position * (price - entry_price)
            equity_curve.append(mtm)
        else:
            equity_curve.append(equity)

    # Close any remaining position at last price
    if position != 0:
        price = closes[-1]
        pnl = position * (price - entry_price)
        equity += pnl
        trades.append({"type": "exit", "price": price, "size": abs(position), "pnl": pnl, "reason": "end_of_backtest"})
        equity_curve[-1] = equity

    metrics = calculate_metrics(equity_curve, [t for t in trades if t["type"] == "exit"], initial_capital)
    metrics["equityCurve"] = [round(e, 2) for e in equity_curve[::max(1, len(equity_curve) // 100)]]  # sample ~100 points
    metrics["trades"] = trades

    return metrics
