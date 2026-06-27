from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd


class BaseStrategy(ABC):
    def __init__(self, config: Dict) -> None:
        self.config = config

    @abstractmethod
    def generate_signals(self, candles: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
