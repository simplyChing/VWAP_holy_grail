from typing import List
from portfolio.trade import Trade


class Metrics:
    def __init__(self, trades: List[Trade]) -> None:
        self.trades = trades

    def total_pnl(self) -> float:
        return sum(trade.pnl for trade in self.trades)

    def win_rate(self) -> float:
        wins = [trade for trade in self.trades if trade.pnl > 0]
        return len(wins) / len(self.trades) if self.trades else 0.0

    def profit_factor(self) -> float:
        gross_profit = sum(trade.pnl for trade in self.trades if trade.pnl > 0)
        gross_loss = -sum(trade.pnl for trade in self.trades if trade.pnl < 0)
        return gross_profit / gross_loss if gross_loss != 0 else float("inf")

    def average_trade(self) -> float:
        return self.total_pnl() / len(self.trades) if self.trades else 0.0

    def summary(self) -> str:
        return (
            f"Trades: {len(self.trades)}\n"
            f"Total PnL: {self.total_pnl():.2f}\n"
            f"Win Rate: {self.win_rate():.2%}\n"
            f"Profit Factor: {self.profit_factor():.2f}\n"
            f"Average Trade: {self.average_trade():.2f}\n"
        )
