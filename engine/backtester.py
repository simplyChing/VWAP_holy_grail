from typing import Dict
import pandas as pd
import os

from engine.event_loop import EventLoop
from engine.metrics import Metrics
from execution.fills import FillEngine


class BacktestReport:
    def __init__(self, trades, metrics):
        self.trades = trades
        self.metrics = metrics

    def summary(self) -> str:
        return self.metrics.summary()

    def save_trades(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not self.trades:
            raise ValueError("No trades available to save.")

        df = pd.DataFrame([
            {
                "entry_time": trade.entry_time,
                "exit_time": trade.exit_time,
                "side": trade.side,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "quantity": trade.quantity,
                "pnl": trade.pnl,
                "duration_min": trade.duration,
            }
            for trade in self.trades
        ])
        df.to_csv(path, index=False)


class Backtester:
    def __init__(self, candles: pd.DataFrame, strategy, instrument: Dict, backtest_settings: Dict) -> None:
        self.candles = candles
        self.strategy = strategy
        self.instrument = instrument["instrument"]
        self.backtest_settings = backtest_settings["backtest"]

    def _filter_candles(self, df: pd.DataFrame) -> pd.DataFrame:
        start = pd.to_datetime(self.backtest_settings["start_date"]).tz_localize(self.backtest_settings["timezone"])
        end = pd.to_datetime(self.backtest_settings["end_date"]).tz_localize(self.backtest_settings["timezone"])
        mask = (df["datetime"] >= start) & (df["datetime"] <= end)
        filtered = df.loc[mask].reset_index(drop=True)
        if filtered.empty:
            first = df["datetime"].min()
            last = df["datetime"].max()
            raise ValueError(
                f"No candles found between {start} and {end}. "
                f"Data range is {first} to {last}. "
                "Update config/backtest.yaml or your CSV timestamps."
            )
        return filtered

    def _run(self, df: pd.DataFrame) -> BacktestReport:
        signals = self.strategy.generate_signals(df)
        fill_engine = FillEngine(self.instrument, self.backtest_settings)

        def step(row):
            fill_engine.process_row(row)

        event_loop = EventLoop(signals, step)
        event_loop.run()
        fill_engine.finalize()

        setattr(self, "max_contracts_held", fill_engine.max_contracts_held)
        metrics = Metrics(fill_engine.trades)
        return BacktestReport(fill_engine.trades, metrics)

    def run(self) -> BacktestReport:
        filtered = self._filter_candles(self.candles)
        return self._run(filtered)
