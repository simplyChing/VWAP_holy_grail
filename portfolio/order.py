from dataclasses import dataclass
from datetime import datetime


@dataclass
class Order:
    timestamp: datetime
    side: str
    quantity: int
    price: float
    commission: float
    slippage: float
