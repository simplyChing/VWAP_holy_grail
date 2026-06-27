import os
from typing import List

import pandas as pd
import plotly.graph_objects as go

from indicators.vwap import calculate_vwap
from portfolio.trade import Trade


def generate_trade_chart_html(
    candles: pd.DataFrame,
    trades: List[Trade],
    output_path: str,
    title: str = "VWAP NQ Trend Strategy",
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df = candles.copy()
    if "vwap" not in df.columns:
        df["vwap"] = calculate_vwap(df)

    # Convert Timestamps to ISO strings for kaleido JSON serialization
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S%z")

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["datetime"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Price",
            ),
            go.Scatter(
                x=df["datetime"],
                y=df["vwap"],
                mode="lines",
                line=dict(color="blue", width=1.5),
                name="VWAP",
            ),
        ]
    )

    long_entry_x = []
    long_entry_y = []
    short_entry_x = []
    short_entry_y = []
    long_exit_x = []
    long_exit_y = []
    short_exit_x = []
    short_exit_y = []
    long_entry_text = []
    short_entry_text = []
    long_exit_text = []
    short_exit_text = []

    strftime = "%Y-%m-%d %H:%M:%S%z"
    for trade in trades:
        entry_t = trade.entry_time.strftime(strftime) if hasattr(trade.entry_time, "strftime") else trade.entry_time
        exit_t = trade.exit_time.strftime(strftime) if hasattr(trade.exit_time, "strftime") else trade.exit_time
        if trade.side == "long":
            long_entry_x.append(entry_t)
            long_entry_y.append(trade.entry_price)
            long_entry_text.append(f"LONG ENTRY\n{trade.entry_price:.2f}")
            long_exit_x.append(exit_t)
            long_exit_y.append(trade.exit_price)
            long_exit_text.append(f"LONG EXIT\n{trade.exit_price:.2f}\nPnL {trade.pnl:.2f}")
        else:
            short_entry_x.append(entry_t)
            short_entry_y.append(trade.entry_price)
            short_entry_text.append(f"SHORT ENTRY\n{trade.entry_price:.2f}")
            short_exit_x.append(exit_t)
            short_exit_y.append(trade.exit_price)
            short_exit_text.append(f"SHORT EXIT\n{trade.exit_price:.2f}\nPnL {trade.pnl:.2f}")

    if long_entry_x:
        fig.add_trace(
            go.Scatter(
                x=long_entry_x,
                y=long_entry_y,
                mode="markers",
                marker=dict(symbol="triangle-up", color="green", size=12),
                hovertext=long_entry_text,
                hovertemplate="%{text}<extra></extra>",
                name="Long Entry",
            )
        )
    if short_entry_x:
        fig.add_trace(
            go.Scatter(
                x=short_entry_x,
                y=short_entry_y,
                mode="markers",
                marker=dict(symbol="triangle-down", color="red", size=12),
                hovertext=short_entry_text,
                hovertemplate="%{text}<extra></extra>",
                name="Short Entry",
            )
        )
    if long_exit_x:
        fig.add_trace(
            go.Scatter(
                x=long_exit_x,
                y=long_exit_y,
                mode="markers",
                marker=dict(symbol="circle", color="darkgreen", size=10),
                hovertext=long_exit_text,
                hovertemplate="%{text}<extra></extra>",
                name="Long Exit",
            )
        )
    if short_exit_x:
        fig.add_trace(
            go.Scatter(
                x=short_exit_x,
                y=short_exit_y,
                mode="markers",
                marker=dict(symbol="circle", color="darkred", size=10),
                hovertext=short_exit_text,
                hovertemplate="%{text}<extra></extra>",
                name="Short Exit",
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Datetime",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        dragmode="pan",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )

    fig.update_xaxes(fixedrange=False)
    fig.update_yaxes(fixedrange=False)

    if output_path.endswith(".html"):
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
    else:
        fig.write_image(output_path, width=1400, height=700, scale=2, engine="kaleido")
    return output_path


def generate_trade_chart_for_report(
    candles: pd.DataFrame,
    trades: List[Trade],
    report_folder: str,
    filename: str = "trade_chart.html",
) -> str:
    output_path = os.path.join(report_folder, filename)
    return generate_trade_chart_html(candles, trades, output_path)
