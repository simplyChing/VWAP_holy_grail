import pandas as pd
from datetime import time


def calculate_vwap(
    candles: pd.DataFrame,
    session_start: time = time(9, 30),
    session_end: time | None = None,
) -> pd.Series:
    if candles.empty:
        return pd.Series([], dtype=float)

    df = candles.copy()
    df["time"] = df["datetime"].dt.time
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0

    def compute_group(group: pd.DataFrame) -> pd.Series:
        mask = group["time"] >= session_start
        if session_end is not None:
            mask &= group["time"] <= session_end

        group_tp = typical_price.loc[group.index]
        group_vol = group["volume"]
        cum_vp = (group_tp * group_vol).where(mask, 0).cumsum()
        cum_vol = group_vol.where(mask, 0).cumsum()
        vwap = pd.Series(index=group.index, dtype=float)
        vwap.loc[mask] = cum_vp.loc[mask] / cum_vol.loc[mask]
        return vwap

    daily = df.groupby(df["datetime"].dt.date, group_keys=False)
    return daily.apply(compute_group)
