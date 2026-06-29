from datetime import time
from typing import Dict
import pandas as pd

from indicators.vwap import calculate_vwap
from strategies.base_strategy import BaseStrategy


class VWAPTrendStrategy(BaseStrategy):
    @staticmethod
    def _signal_from_price(price: float, vwap: float) -> int:
        if price > vwap:
            return 1
        if price < vwap:
            return -1
        return 0

    def generate_signals(self, candles: pd.DataFrame) -> pd.DataFrame:
        df = candles.copy()
        df["signal"] = 0
        df["position"] = 0

        entry_time = time.fromisoformat(self.config["strategy"]["entry_time"])
        exit_time = time.fromisoformat(self.config["strategy"]["exit_time"])
        start_of_day = time.fromisoformat(self.config["strategy"]["start_of_day"])

        df["vwap"] = calculate_vwap(df, session_start=start_of_day)
        df["time"] = df["datetime"].dt.time
        df["date"] = df["datetime"].dt.date
        df["prev_close"] = df["close"].shift(1)
        df["prev_open"] = df["open"].shift(1)
        df["prev_vwap"] = df["vwap"].shift(1)
        df["prev_date"] = df["date"].shift(1)

        current_position = 0

        for idx, row in df.iterrows():
            # enforce session boundaries: before session start, after exit, or different date -> flat
            if row["time"] < start_of_day or row["time"] > exit_time or row["prev_date"] != row["date"]:
                current_position = 0
            elif row["time"] == exit_time:
                current_position = 0
            elif row["time"] == entry_time:
                if row["prev_close"] > row["prev_vwap"]:
                    current_position = 1
                elif row["prev_close"] < row["prev_vwap"]:
                    current_position = -1
                else:
                    current_position = 0
            else:
                if current_position == 1 and row["prev_close"] < row["prev_vwap"]:
                    current_position = 0
                elif current_position == -1 and row["prev_close"] > row["prev_vwap"]:
                    current_position = 0
                elif current_position == 0:
                    if row["prev_close"] > row["prev_vwap"]:
                        current_position = 1
                    elif row["prev_close"] < row["prev_vwap"]:
                        current_position = -1

            df.at[idx, "signal"] = current_position

        df["position"] = df["signal"].ffill().fillna(0).astype(int)
        return df
