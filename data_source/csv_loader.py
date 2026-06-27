import os
from datetime import datetime
import pandas as pd


class CSVDataSource:
    def __init__(self, path: str, timezone: str = "UTC") -> None:
        self.path = path
        self.timezone = timezone

    def load(self) -> pd.DataFrame:
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"CSV file not found: {self.path}")

        df = pd.read_csv(self.path, parse_dates=["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)
        dt_series = df["datetime"]
        if dt_series.dt.tz is None:
            dt_series = dt_series.dt.tz_localize("UTC")
        else:
            dt_series = dt_series.dt.tz_convert("UTC")
        df["datetime"] = dt_series.dt.tz_convert(self.timezone)
        required_cols = {"datetime", "open", "high", "low", "close", "volume"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns from CSV: {missing}")

        return df
