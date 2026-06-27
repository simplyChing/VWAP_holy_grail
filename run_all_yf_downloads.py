import os

from otherScripts.getData1mYf.download_nq_1m import download_nq_1m
from otherScripts.getData5mYf.download_nq_5m import download_nq_5m
from otherScripts.getData1hYf.download_nq_1h import download_nq_1h


def get_default_output_path(interval: str) -> str:
    root = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root, "data", "raw", "NQ", interval, f"nq_{interval}.csv")


def main() -> None:
    print("Starting Yahoo Finance downloads for NQ futures...")
    outputs = {
        "1m": get_default_output_path("1m"),
        "5m": get_default_output_path("5m"),
        "1h": get_default_output_path("1h"),
    }

    try:
        print(f"Downloading 1m data to {outputs['1m']}")
        download_nq_1m(outputs["1m"])
        print("1m download completed.")
    except Exception as exc:
        print(f"1m download failed: {exc}")

    try:
        print(f"Downloading 5m data to {outputs['5m']}")
        download_nq_5m(outputs["5m"])
        print("5m download completed.")
    except Exception as exc:
        print(f"5m download failed: {exc}")

    try:
        print(f"Downloading 1h data to {outputs['1h']}")
        download_nq_1h(outputs["1h"])
        print("1h download completed.")
    except Exception as exc:
        print(f"1h download failed: {exc}")

    print("All download tasks finished.")


if __name__ == "__main__":
    main()
