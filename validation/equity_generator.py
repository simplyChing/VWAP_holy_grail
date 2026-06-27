import os
from typing import List

import pandas as pd
import plotly.graph_objects as go

from portfolio.trade import Trade


def generate_equity_curve_html(
    trades: List[Trade],
    initial_capital: float,
    output_path: str,
    title: str = "Equity Curve",
    smooth_window: int = 1,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if not trades:
        # create an empty equity file with initial capital
        df_empty = pd.DataFrame([{"datetime": pd.NaT, "trade_pnl": 0.0, "equity": initial_capital}])
        df_empty.to_csv(os.path.join(os.path.dirname(output_path), "equity.csv"), index=False)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[], y=[], mode="lines", name="Equity"))
        fig.update_layout(title=title, xaxis_title="Datetime", yaxis_title="Equity")
        fig.write_html(output_path, include_plotlyjs="cdn")
        return output_path

    df = pd.DataFrame([
        {"datetime": trade.exit_time, "trade_pnl": trade.pnl} for trade in trades
    ])
    df = df.sort_values("datetime").reset_index(drop=True)
    df["equity"] = initial_capital + df["trade_pnl"].cumsum()

    # optional smoothing using centered rolling mean
    if smooth_window and smooth_window > 1:
        df["equity_smooth"] = df["equity"].rolling(window=smooth_window, min_periods=1, center=True).mean()
        plot_y = df["equity_smooth"]
    else:
        plot_y = df["equity"]

    # save csv
    csv_path = os.path.join(os.path.dirname(output_path), "equity.csv")
    df.to_csv(csv_path, index=False)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["datetime"],
            y=plot_y,
            mode="lines",
            line=dict(color="purple", width=2),
            name="Equity",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Datetime",
        yaxis_title="Equity",
        xaxis_rangeslider_visible=False,
        dragmode="pan",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )

    fig.update_xaxes(fixedrange=False)
    fig.update_yaxes(fixedrange=False)

    fig.write_html(
        output_path,
        include_plotlyjs="cdn",
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToAdd": [
                "zoomIn2d",
                "zoomOut2d",
                "autoScale2d",
                "resetScale2d",
            ],
        },
    )

    return output_path


def generate_equity_curve_for_report(
    trades: List[Trade], report_folder: str, initial_capital: float, filename: str = "equity_curve.html", smooth_window: int = 1
) -> str:
    output_path = os.path.join(report_folder, filename)
    return generate_equity_curve_html(trades, initial_capital, output_path, title="VWAP Strategy Equity Curve", smooth_window=smooth_window)
