"""
Volatility Targeting Module

Computes a dynamic position-sizing multiplier that scales exposure
inversely with recent realized volatility. The goal is to keep
portfolio volatility near a constant target level.

    position_multiplier = target_vol / forecast_vol

The multiplier is clipped to a configurable range to prevent
extreme leverage or excessively tiny positions.
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd


def estimate_periods_per_year(freq: str) -> float:
    """Return an approximate number of bars per year for different data frequencies."""
    freq = freq.lower().strip()
    if freq in ("1min", "1m", "minute"):
        return 390 * 252  # ~98 280
    if freq in ("5min", "5m"):
        return 78 * 252  # ~19 656
    if freq in ("15min", "15m"):
        return 26 * 252
    if freq in ("30min", "30m"):
        return 13 * 252
    if freq in ("60min", "60m", "1h", "hourly"):
        return 6.5 * 252
    if freq in ("daily", "1d", "day"):
        return 252
    if freq in ("weekly", "1w"):
        return 52
    return 252  # fallback


def _compute_returns(close: pd.Series) -> pd.Series:
    """Compute fractional returns from a close price series."""
    return close.astype(float).pct_change().fillna(0.0)


def compute_rolling_vol(
    close: pd.Series,
    window: int = 20,
    periods_per_year: float = 98_280,
) -> pd.Series:
    """
    Compute rolling annualized realized volatility.

    Parameters
    ----------
    close : pd.Series
        Close price series.
    window : int
        Rolling window length in bars.
    periods_per_year : float
        Number of bars in one year (for annualization).

    Returns
    -------
    pd.Series
        Annualized volatility estimate for each bar.
    """
    returns = _compute_returns(close)
    rolling_std = returns.rolling(window=window, min_periods=max(window // 2, 5)).std()
    annualized_vol = rolling_std * np.sqrt(periods_per_year)
    return annualized_vol.bfill().fillna(0.0)


def compute_ewma_vol(
    close: pd.Series,
    span: int = 20,
    periods_per_year: float = 98_280,
) -> pd.Series:
    """
    Compute EWMA (exponentially weighted) annualized volatility.
    Responds faster to changing conditions than a simple rolling estimate.

    Parameters
    ----------
    close : pd.Series
        Close price series.
    span : int
        EWMA span in bars (equivalent to approx *2* halflife).
    periods_per_year : float
        Number of bars in one year.

    Returns
    -------
    pd.Series
        Annualized EWMA volatility estimate.
    """
    returns = _compute_returns(close)
    ewma_var = returns.ewm(span=span, min_periods=max(span // 2, 5)).var()
    annualized_vol = np.sqrt(ewma_var) * np.sqrt(periods_per_year)
    return annualized_vol.bfill().fillna(0.0)


def compute_vol_multiplier(
    close: pd.Series,
    target_annual_vol: float = 0.20,
    method: str = "rolling",
    window: int = 20,
    min_mult: float = 0.25,
    max_mult: float = 4.0,
    periods_per_year: Optional[float] = None,
    data_freq: str = "1m",
    vol_floor: float = 0.05,
) -> pd.Series:
    """
    Compute the volatility-targeting position multiplier for every bar.

    multiplier = clamp(target_vol / forecast_vol, min_mult, max_mult)

    Parameters
    ----------
    close : pd.Series
        Close price series.
    target_annual_vol : float
        Desired annualized portfolio volatility (e.g. 0.20 = 20 %).
    method : str
        Volatility estimator — ``"rolling"`` (simple rolling std) or
        ``"ewma"`` (exponentially weighted).
    window : int
        Lookback window / EWMA span in bars.
    min_mult : float
        Lower clamp on the multiplier.
    max_mult : float
        Upper clamp on the multiplier.
    periods_per_year : float, optional
        Annualization factor. Auto-estimated from *data_freq* if not given.
    data_freq : str
        Data frequency label (``"1m"``, ``"5m"``, ``"1h"``, ``"daily"`` …).
        Only used when *periods_per_year* is None.
    vol_floor : float
        Minimum annualized vol used in the denominator to avoid division
        by extremely small numbers.

    Returns
    -------
    pd.Series
        Position multiplier for each bar.  A value of 1.0 means
        normal sizing; 0.5 means half-size; 2.0 means double.
    """
    if periods_per_year is None:
        periods_per_year = estimate_periods_per_year(data_freq)

    if method == "ewma":
        forecast_vol = compute_ewma_vol(close, span=window, periods_per_year=periods_per_year)
    else:
        forecast_vol = compute_rolling_vol(close, window=window, periods_per_year=periods_per_year)

    # Avoid division by zero or unrealistically small vol
    safe_vol = np.maximum(forecast_vol, vol_floor)

    multiplier = target_annual_vol / safe_vol
    multiplier = multiplier.clip(lower=min_mult, upper=max_mult)

    return multiplier


def compute_position_size(
    base_quantity: int,
    vol_multiplier: float,
    round_func: str = "round",
) -> int:
    """
    Scale a base contract quantity by the volatility multiplier.

    Parameters
    ----------
    base_quantity : int
        Nominal contract quantity (e.g. ``contract_size``).
    vol_multiplier : float
        Volatility targeting multiplier for this bar.
    round_func : str
        ``"round"``, ``"floor"``, or ``"ceil"`` — how to convert the
        scaled float to an integer.

    Returns
    -------
    int
        Scaled integer position size.
    """
    scaled = base_quantity * vol_multiplier
    if round_func == "floor":
        return max(int(np.floor(scaled)), 0)
    if round_func == "ceil":
        return max(int(np.ceil(scaled)), 0)
    return max(int(round(scaled)), 0)
