import os
import pandas as pd
import yaml
from engine.backtester import Backtester
from strategies.vwap_trend_strategy import VWAPTrendStrategy
from data_source.csv_loader import CSVDataSource
from validation.chart_generator import generate_trade_chart_for_report
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
        chart_path = generate_trade_chart_for_report(
            filtered_candles,
            report.trades,
            os.path.join(root, "reports", "figures_html"),
            filename="trade_chart.html",
        )
        # generate equity curve using initial capital from backtest config
        try:
            initial_cap = backtest_config["backtest"]["initial_capital"]
        except Exception:
            initial_cap = 0.0
        try:
            smooth_w = backtest_config["backtest"].get("equity_smooth_window", 5)
        except Exception:
            smooth_w = 5
        equity_path = generate_equity_curve_for_report(
            report.trades,
            os.path.join(root, "reports", "figures_html"),
            initial_cap,
            filename="equity_curve.html",
            smooth_window=smooth_w,
        )
        # optionally run Monte Carlo report if enabled in backtest config
        try:
            run_mc = bool(backtest_config["backtest"].get("run_monte_carlo", False))
        except Exception:
            run_mc = False
        if run_mc:
            try:
                mc_sims = int(backtest_config["backtest"].get("monte_carlo_sims", 2000))
            except Exception:
                mc_sims = 2000
            mc_path = generate_monte_carlo_report(
                os.path.join(root, "reports", "trades", "trades.csv"),
                os.path.join(root, "config", "backtest.yaml"),
                os.path.join(root, "reports", "figures_html"),
                n_sims=mc_sims,
            )
            print(f"Saved Monte Carlo report to {mc_path}")
        print(f"Saved interactive chart to {chart_path}")
        print(f"Saved equity chart to {equity_path}")
    else:
        print("No trades generated; skipping trade save and chart generation.")


if __name__ == "__main__":
    main()
