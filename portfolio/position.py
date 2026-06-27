from dataclasses import dataclass


@dataclass
class Position:
    side: str = "flat"
    quantity: int = 0
    entry_price: float = 0.0

    def is_flat(self) -> bool:
        return self.side == "flat"

    def is_long(self) -> bool:
        return self.side == "long"

    def is_short(self) -> bool:
        return self.side == "short"

    def close(self) -> None:
        self.side = "flat"
        self.quantity = 0
        self.entry_price = 0.0
