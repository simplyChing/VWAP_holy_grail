from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    side: str
    entry_price: float
    exit_price: float
    quantity: int
    commission: float
    slippage: float
    tick_size: float
    tick_value: float
    highest_unrealized_profit: float = 0.0

    @property
    def pnl(self) -> float:
        direction = 1 if self.side == "long" else -1
        price_diff = self.exit_price - self.entry_price
        ticks = price_diff / self.tick_size
        return ticks * self.tick_value * self.quantity * direction - self.commission - self.slippage

    @property
    def duration(self) -> float:
        return (self.exit_time - self.entry_time).total_seconds() / 60.0
