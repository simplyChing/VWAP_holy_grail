import pandas as pd
from typing import Callable


class EventLoop:
    def __init__(self, candles: pd.DataFrame, callback: Callable[[pd.Series], None]) -> None:
        self.candles = candles
        self.callback = callback

    def run(self) -> None:
        for _, row in self.candles.iterrows():
            self.callback(row)
