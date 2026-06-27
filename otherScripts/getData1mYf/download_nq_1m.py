import os
import pandas as pd

try:
    import yfinance as yf
except Exception as exc:
    raise RuntimeError(
        "yfinance is incompatible with Python 3.8 in this environment. "
        "Install yfinance==0.2.27 or upgrade Python to 3.10+"
    ) from exc


def download_nq_1m(output_path: str) -> pd.DataFrame:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    symbol = "NQ=F"
    data = yf.download(symbol, period="7d", interval="1m", progress=False)

    if data.empty:
        raise ValueError(f"No 1m data downloaded for {symbol}.")

    data = data.rename_axis("datetime").reset_index()
    data = data[["datetime", "Open", "High", "Low", "Close", "Volume"]]
    data.columns = ["datetime", "open", "high", "low", "close", "volume"]
    data.to_csv(output_path, index=False)
    return data


if __name__ == "__main__":
    output_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "NQ", "1m", "nq_1m.csv")
    output_path = os.path.abspath(output_path)
    print(f"Downloading NQ 1m data to {output_path}")
    df = download_nq_1m(output_path)
    print(f"Saved {len(df)} rows.")
