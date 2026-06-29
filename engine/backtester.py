from typing import Dict, Optional
import pandas as pd
import os

from engine.event_loop import EventLoop
from engine.metrics import Metrics
from execution.fills import FillEngine
from risk.volatility_targeting import compute_vol_multiplier, estimate_periods_per_year


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
                "highest_unrealized_profit": trade.highest_unrealized_profit,
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

        # ── Volatility targeting overlay ──────────────────────────
        vol_enabled = bool(self.backtest_settings.get("vol_target_enabled", False))
        if vol_enabled:
            target_vol = float(self.backtest_settings.get("vol_target_annual", 0.20))
            method = str(self.backtest_settings.get("vol_method", "rolling"))
            window = int(self.backtest_settings.get("vol_window", 20))
            data_freq = str(self.backtest_settings.get("vol_data_freq", "1m"))
            min_mult = float(self.backtest_settings.get("vol_min_mult", 0.25))
            max_mult = float(self.backtest_settings.get("vol_max_mult", 4.0))
            vol_floor = float(self.backtest_settings.get("vol_floor", 0.05))
            round_func = str(self.backtest_settings.get("vol_round_func", "round"))
            periods_per_year = estimate_periods_per_year(data_freq)

            signals["vol_multiplier"] = compute_vol_multiplier(
                signals["close"],
                target_annual_vol=target_vol,
                method=method,
                window=window,
                min_mult=min_mult,
                max_mult=max_mult,
                periods_per_year=periods_per_year,
                vol_floor=vol_floor,
            )
        else:
            signals["vol_multiplier"] = 1.0
            round_func = "round"

        fill_engine = FillEngine(self.instrument, self.backtest_settings)
        fill_engine.configure_vol_targeting(enabled=vol_enabled, round_func=round_func)

        def step(row):
            fill_engine.process_row(row)

        event_loop = EventLoop(signals, step)
        event_loop.run()
        fill_engine.finalize()

        setattr(self, "max_contracts_held", fill_engine.max_contracts_held)
        # Store vol multiplier series for reporting
        setattr(self, "vol_multiplier_series", signals["vol_multiplier"])
        metrics = Metrics(fill_engine.trades)
        return BacktestReport(fill_engine.trades, metrics)

    def run(self) -> BacktestReport:
        filtered = self._filter_candles(self.candles)
        return self._run(filtered)
