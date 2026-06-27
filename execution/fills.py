from datetime import datetime
from typing import Dict, List, Optional

from portfolio.order import Order
from portfolio.trade import Trade
from portfolio.position import Position
from risk.volatility_targeting import compute_position_size


class FillEngine:
    def __init__(self, instrument: Dict, settings: Dict):
        self.instrument = instrument
        self.settings = settings
        self.position = Position()
        self.trades: List[Trade] = []
        self.current_order: Optional[Order] = None
        self.last_row = None
        self.max_contracts_held = 0

        # Volatility targeting config (set by backtester)
        self._vol_enabled: bool = False
        self._vol_round_func: str = "round"

    def _close_position(self, timestamp: datetime, price: float) -> None:
        if self.position.is_flat():
            return

        trade_side = "long" if self.position.is_long() else "short"
        trade = Trade(
            entry_time=self.current_order.timestamp if self.current_order else timestamp,
            exit_time=timestamp,
            side=trade_side,
            entry_price=self.position.entry_price,
            exit_price=price,
            quantity=self.position.quantity,
            commission=self.instrument["commission_per_trade"],
            slippage=self.instrument["slippage_per_trade"],
            tick_size=self.instrument["tick_size"],
            tick_value=self.instrument["tick_value"],
        )
        self.trades.append(trade)
        self.position.close()
        self.current_order = None

    def _open_position(self, side: str, timestamp: datetime, price: float, quantity: int) -> None:
        self.position.side = side
        self.position.quantity = quantity
        self.position.entry_price = price
        self.max_contracts_held = max(self.max_contracts_held, quantity)
        order_side = "buy" if side == "long" else "sell"
        self.current_order = Order(timestamp, order_side, quantity, price, self.instrument["commission_per_trade"], self.instrument["slippage_per_trade"])

    def configure_vol_targeting(self, enabled: bool, round_func: str = "round") -> None:
        """Enable or disable volatility-targeting position scaling."""
        self._vol_enabled = enabled
        self._vol_round_func = round_func

    def _resolve_quantity(self, row: Dict) -> int:
        """Return the contract quantity for this bar, scaled by volatility multiplier."""
        base = int(self.instrument.get("contract_size", 1))
        if not self._vol_enabled:
            return base
        mult = float(row.get("vol_multiplier", 1.0))
        return compute_position_size(base, mult, round_func=self._vol_round_func)

    def process_row(self, row: Dict) -> None:
        self.last_row = row
        signal = row["position"]
        price = float(row["open"])
        timestamp = row["datetime"]
        quantity = self._resolve_quantity(row)

        if signal == 1:
            # Long signal: allow close always, only open if long is allowed
            if self.position.is_flat():
                if self.instrument.get("long_allowed", True):
                    self._open_position("long", timestamp, price, quantity)
                else:
                    # opening longs disabled by instrument config
                    return
            elif self.position.is_short():
                # close existing short
                self._close_position(timestamp, price)
                # open long only if allowed
                if self.instrument.get("long_allowed", True):
                    self._open_position("long", timestamp, price, quantity)

        elif signal == -1:
            # Short signal: allow close always, only open if short is allowed
            if self.position.is_flat():
                if self.instrument.get("short_allowed", True):
                    self._open_position("short", timestamp, price, quantity)
                else:
                    # opening shorts disabled by instrument config
                    return
            elif self.position.is_long():
                # close existing long
                self._close_position(timestamp, price)
                # open short only if allowed
                if self.instrument.get("short_allowed", True):
                    self._open_position("short", timestamp, price, quantity)

        elif signal == 0 and not self.position.is_flat():
            self._close_position(timestamp, price)

    def finalize(self) -> None:
        if not self.position.is_flat() and self.last_row is not None:
            price = float(self.last_row["open"])
            timestamp = self.last_row["datetime"]
            self._close_position(timestamp, price)
