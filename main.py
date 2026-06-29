import os
import pandas as pd
import yaml
from engine.backtester import Backtester
from strategies.vwap_trend_strategy import VWAPTrendStrategy
from data_source.csv_loader import CSVDataSource
from validation.chart_generator import generate_trade_chart_for_report, generate_daily_trade_charts
from validation.equity_generator import generate_equity_curve_for_report
from analytics.monte_carlo import generate_monte_carlo_report
from analytics.performance import calculate_performance_summary, format_performance_summary


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    root = os.path.dirname(__file__)
    config_dir = os.path.join(root, "config")
    data_dir = os.path.join(root, "data")

    strategy_config = load_yaml(os.path.join(config_dir, "strategy.yaml"))
    instrument_config = load_yaml(os.path.join(config_dir, "instrument.yaml"))
    backtest_config = load_yaml(os.path.join(config_dir, "backtest.yaml"))

    csv_path = os.path.join(data_dir, "raw", "NQ", "1m", "nq_1m.csv")
    data_source = CSVDataSource(csv_path, timezone="America/New_York")
    candles = data_source.load()

    strategy = VWAPTrendStrategy(strategy_config)
    engine = Backtester(
        candles=candles,
        strategy=strategy,
        instrument=instrument_config,
        backtest_settings=backtest_config,
    )

    filtered_candles = engine._filter_candles(candles)
    report = engine._run(filtered_candles)

    print(report.summary())

    performance_summary = calculate_performance_summary(
        report.trades,
        filtered_candles,
        initial_capital=float(backtest_config["backtest"].get("initial_capital", 0.0)),
        max_contracts_held=getattr(engine, "max_contracts_held", None),
        vol_multiplier_series=getattr(engine, "vol_multiplier_series", None),
    )
    print(format_performance_summary(performance_summary))

    if report.trades:
        report.save_trades(os.path.join(root, "reports", "trades", "trades.csv"))

        figures_html_dir = os.path.join(root, "reports", "figures_html")
        figures_png_dir = os.path.join(root, "reports", "figures_png")
        os.makedirs(figures_png_dir, exist_ok=True)

        # ── Trade chart ──────────────────────────────────────────
        chart_html = generate_trade_chart_for_report(
            filtered_candles,
            report.trades,
            figures_html_dir,
            filename="trade_chart.html",
        )
        chart_png = generate_trade_chart_for_report(
            filtered_candles,
            report.trades,
            figures_png_dir,
            filename="trade_chart.png",
        )

        # ── Daily trade charts (first 5 trading days) ────────────
        daily_results = generate_daily_trade_charts(
            filtered_candles,
            report.trades,
            figures_html_dir,
            figures_png_dir,
            max_days=5,
        )

        # ── Equity curve ─────────────────────────────────────────
        try:
            initial_cap = backtest_config["backtest"]["initial_capital"]
        except Exception:
            initial_cap = 0.0
        try:
            smooth_w = backtest_config["backtest"].get("equity_smooth_window", 5)
        except Exception:
            smooth_w = 5
        equity_html = generate_equity_curve_for_report(
            report.trades,
            figures_html_dir,
            initial_cap,
            filename="equity_curve.html",
            smooth_window=smooth_w,
        )
        equity_png = generate_equity_curve_for_report(
            report.trades,
            figures_png_dir,
            initial_cap,
            filename="equity_curve.png",
            smooth_window=smooth_w,
        )

        # ── Monte Carlo (expensive — compute once, copy PNG) ─────
        try:
            run_mc = bool(backtest_config["backtest"].get("run_monte_carlo", False))
        except Exception:
            run_mc = False
        if run_mc:
            try:
                mc_sims = int(backtest_config["backtest"].get("monte_carlo_sims", 2000))
            except Exception:
                mc_sims = 2000
            mc_html = generate_monte_carlo_report(
                os.path.join(root, "reports", "trades", "trades.csv"),
                os.path.join(root, "config", "backtest.yaml"),
                figures_html_dir,
                n_sims=mc_sims,
                png_output_folder=figures_png_dir,
            )
            print(f"Saved Monte Carlo report to {mc_html}")

        print(f"Saved interactive chart (HTML) to {chart_html}")
        print(f"Saved interactive chart (PNG)  to {chart_png}")
        print(f"Saved equity chart (HTML) to {equity_html}")
        print(f"Saved equity chart (PNG)  to {equity_png}")
    else:
        print("No trades generated; skipping trade save and chart generation.")


if __name__ == "__main__":
    main()
