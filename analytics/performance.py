from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from portfolio.trade import Trade


def calculate_performance_summary(
    trades: List[Trade],
    candles: pd.DataFrame,
    initial_capital: float = 0.0,
    max_contracts_held: int | None = None,
) -> Dict[str, float | int]:
    if not candles.empty and "close" in candles.columns:
        close_series = pd.to_numeric(candles["close"], errors="coerce").dropna()
    else:
        close_series = pd.Series(dtype=float)

    if trades:
        trade_pnls = [trade.pnl for trade in trades]
        cumulative_pnl = np.cumsum(trade_pnls)
        equity_curve = initial_capital + cumulative_pnl
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = running_max - equity_curve
        max_strategy_drawdown = float(drawdown.max()) if len(drawdown) else 0.0

        buy_and_hold_return = 0.0
        if not close_series.empty:
            first_close = float(close_series.iloc[0])
            last_close = float(close_series.iloc[-1])
            if first_close != 0.0:
                buy_and_hold_return = (last_close / first_close - 1.0) * 100.0

        if not close_series.empty:
            close_to_close_returns = close_series.pct_change().fillna(0.0)
            running_equity = 1.0 + close_to_close_returns.cumsum()
            running_max_close = np.maximum.accumulate(running_equity)
            close_drawdown = running_max_close - running_equity
            max_close_to_close_drawdown = float(close_drawdown.max()) if len(close_drawdown) else 0.0
        else:
            max_close_to_close_drawdown = 0.0

        # Separate trades by side
        long_trades_list = [trade for trade in trades if trade.side == "long"]
        short_trades_list = [trade for trade in trades if trade.side == "short"]

        # Calculate net profit and gross profit for each position type
        net_profit_long = float(sum(trade.pnl for trade in long_trades_list))
        net_profit_short = float(sum(trade.pnl for trade in short_trades_list))
        net_profit_all = float(sum(trade.pnl for trade in trades))

        gross_profit_long = float(sum(trade.pnl for trade in long_trades_list if trade.pnl > 0))
        gross_profit_short = float(sum(trade.pnl for trade in short_trades_list if trade.pnl > 0))
        gross_profit_all = float(sum(trade.pnl for trade in trades if trade.pnl > 0))

        long_trades = len(long_trades_list)
        short_trades = len(short_trades_list)
        all_trades = len(trades)
    else:
        max_strategy_drawdown = 0.0
        max_close_to_close_drawdown = 0.0
        buy_and_hold_return = 0.0
        net_profit_long = 0.0
        net_profit_short = 0.0
        net_profit_all = 0.0
        gross_profit_long = 0.0
        gross_profit_short = 0.0
        gross_profit_all = 0.0
        long_trades = 0
        short_trades = 0
        all_trades = 0

    return {
        "net_profit_long": net_profit_long,
        "net_profit_short": net_profit_short,
        "net_profit_all": net_profit_all,
        "gross_profit_long": gross_profit_long,
        "gross_profit_short": gross_profit_short,
        "gross_profit_all": gross_profit_all,
        "long_trades": long_trades,
        "short_trades": short_trades,
        "all_trades": all_trades,
        "max_strategy_drawdown": max_strategy_drawdown,
        "max_close_to_close_drawdown": max_close_to_close_drawdown,
        "buy_and_hold_return": buy_and_hold_return,
        "max_contracts_held": max_contracts_held if max_contracts_held is not None else 0,
    }


def format_performance_summary(summary: Dict[str, float | int]) -> str:
    return "\n".join(
        [
            "Long Positions:",
            f"  Net profit: ${summary['net_profit_long']:.2f}",
            f"  Gross profit: ${summary['gross_profit_long']:.2f}",
            f"  Trades: {summary['long_trades']}",
            "",
            "Short Positions:",
            f"  Net profit: ${summary['net_profit_short']:.2f}",
            f"  Gross profit: ${summary['gross_profit_short']:.2f}",
            f"  Trades: {summary['short_trades']}",
            "",
            "All Positions:",
            f"  Net profit: ${summary['net_profit_all']:.2f}",
            f"  Gross profit: ${summary['gross_profit_all']:.2f}",
            f"  Trades: {summary['all_trades']}",
            f"  Max strategy drawdown ($): ${summary['max_strategy_drawdown']:.2f}",
            f"  Max Close to close drawdown: {summary['max_close_to_close_drawdown']:.2f}",
            f"  Buy and Hold return: {summary['buy_and_hold_return']:.2f}%",
            f"  Max contract held: {summary['max_contracts_held']}",
        ]
    )
