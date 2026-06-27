import os
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import yaml
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def load_backtest_initial_cap(config_path: str) -> float:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return float(cfg.get("backtest", {}).get("initial_capital", 0.0))
    except Exception:
        return 0.0


def run_monte_carlo(trade_pnls: pd.Series, n_sims: int = 1000, rng: np.random.Generator | None = None) -> Tuple[np.ndarray, np.ndarray]:
    if rng is None:
        rng = np.random.default_rng()

    n_trades = len(trade_pnls)
    final_pnls = np.zeros(n_sims)
    equity_paths = np.zeros((n_sims, n_trades))

    for i in range(n_sims):
        sample = rng.choice(trade_pnls.values, size=n_trades, replace=True)
        equity = sample.cumsum()
        equity_paths[i] = equity
        final_pnls[i] = equity[-1]

    return final_pnls, equity_paths


def generate_monte_carlo_report(
    trades_csv: str,
    backtest_config: str,
    output_folder: str,
    n_sims: int = 2000,
    sample_curve_count: int = 30,
    random_seed: int | None = 42,
    png_output_folder: Optional[str] = None,
) -> str:
    os.makedirs(output_folder, exist_ok=True)

    if not os.path.exists(trades_csv):
        raise FileNotFoundError(f"Trades CSV not found: {trades_csv}")

    trades = pd.read_csv(trades_csv, parse_dates=["exit_time", "entry_time"])  # removed deprecated infer_datetime_format
    if "pnl" not in trades.columns:
        raise ValueError("Trades CSV must contain a 'pnl' column.")

    initial_cap = load_backtest_initial_cap(backtest_config)

    rng = np.random.default_rng(random_seed)
    final_pnls, equity_paths = run_monte_carlo(trades["pnl"], n_sims=n_sims, rng=rng)

    # save final pnl distribution to reports/data/
    data_dir = os.path.join(os.path.dirname(output_folder), "data")
    os.makedirs(data_dir, exist_ok=True)
    final_df = pd.DataFrame({"final_pnl": final_pnls})
    final_df.to_csv(os.path.join(data_dir, "monte_carlo_final_pnls.csv"), index=False)

    # build figure with two rows: sample equity curves and histogram
    fig = make_subplots(rows=2, cols=1, row_heights=[0.6, 0.4], specs=[[{}], [{}]], shared_xaxes=False, vertical_spacing=0.12)

    # plot a subset of sample curves (shifted by initial capital) with distinct colors
    picks = rng.choice(equity_paths.shape[0], size=min(sample_curve_count, equity_paths.shape[0]), replace=False)

    def hsv_to_rgb(h: float, s: float, v: float) -> tuple:
        """Convert HSV in range [0,1] to RGB 0-255."""
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        i = i % 6
        if i == 0:
            r_, g_, b_ = v, t, p
        elif i == 1:
            r_, g_, b_ = q, v, p
        elif i == 2:
            r_, g_, b_ = p, v, t
        elif i == 3:
            r_, g_, b_ = p, q, v
        elif i == 4:
            r_, g_, b_ = t, p, v
        else:
            r_, g_, b_ = v, p, q
        return int(r_ * 255), int(g_ * 255), int(b_ * 255)

    n_pick = len(picks)
    for j, idx in enumerate(picks):
        y = initial_cap + equity_paths[idx]
        h = j / max(1, n_pick)
        r, g, b = hsv_to_rgb(h, 0.7, 0.8)
        color = f"rgba({r},{g},{b},0.25)"
        fig.add_trace(
            go.Scatter(
                x=list(range(1, y.size + 1)),
                y=y,
                mode="lines",
                line=dict(width=1, color=color),
                showlegend=False,
            ),
            row=1,
            col=1,
        )

    # median and percentiles
    median = initial_cap + np.median(equity_paths, axis=0)
    p10 = initial_cap + np.percentile(equity_paths, 10, axis=0)
    p90 = initial_cap + np.percentile(equity_paths, 90, axis=0)

    x_axis = list(range(1, median.size + 1))
    fig.add_trace(go.Scatter(x=x_axis, y=median, mode="lines", line=dict(color="purple", width=2), name="Median"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=p10, mode="lines", line=dict(color="grey", width=1, dash="dash"), name="10th pct"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=p90, mode="lines", line=dict(color="grey", width=1, dash="dash"), name="90th pct"), row=1, col=1)

    # Histogram of final PnLs
    fig.add_trace(go.Histogram(x=final_pnls, nbinsx=60, marker_color="teal", name="Final PnL Distribution"), row=2, col=1)

    fig.update_xaxes(title_text="Trade Index (resampled)", row=1, col=1)
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1)
    fig.update_xaxes(title_text="Final PnL ($)", row=2, col=1)
    fig.update_yaxes(title_text="Count", row=2, col=1)

    title = f"Monte Carlo ({n_sims} sims) — Final PnL percentiles: 10% {np.percentile(final_pnls,10):.2f}, 50% {np.median(final_pnls):.2f}, 90% {np.percentile(final_pnls,90):.2f}"
    fig.update_layout(title=title, height=800, showlegend=True, margin=dict(l=40, r=20, t=80, b=40))

    out_html = os.path.join(output_folder, "monte_carlo.html")
    fig.write_html(out_html, include_plotlyjs="cdn", config={"scrollZoom": True, "displayModeBar": True})

    # write PNG to separate folder if provided (keeps figures_html clean)
    if png_output_folder is not None:
        os.makedirs(png_output_folder, exist_ok=True)
        out_png = os.path.join(png_output_folder, "monte_carlo.png")
        fig.write_image(out_png, width=1400, height=900, scale=2, engine="kaleido")

    return out_html


if __name__ == "__main__":
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    trades_csv = os.path.join(root, "reports", "trades", "trades.csv")
    backtest_config = os.path.join(root, "config", "backtest.yaml")
    out_folder = os.path.join(root, "reports", "figures_html")
    try:
        html = generate_monte_carlo_report(trades_csv, backtest_config, out_folder, n_sims=2000, sample_curve_count=40, random_seed=42)
        print(f"Monte Carlo report saved to {html}")
    except Exception as e:
        print(f"Monte Carlo failed: {e}")
