"""Type definitions for Hyperliquid client."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TradingMode(str, Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class MarketType(str, Enum):
    PERP = "perp"
    SPOT = "spot"


@dataclass
class HLConfig:
    private_key: str
    account_address: Optional[str] = None
    vault_address: Optional[str] = None
    testnet: bool = False

    @property
    def mode(self) -> TradingMode:
        return TradingMode.TESTNET if self.testnet else TradingMode.MAINNET


@dataclass
class PositionData:
    coin: str
    size: float
    entry_price: float
    unrealized_pnl: float
    leverage: float
    liquidation_price: Optional[float] = None
    margin_used: float = 0.0
    return_on_equity: float = 0.0


@dataclass
class AccountSummary:
    account_value: float
    total_margin_used: float
    total_ntl_pos: float
    withdrawable: float
    positions: list[PositionData] = field(default_factory=list)


@dataclass
class SpotBalance:
    coin: str
    total: float
    hold: float  # locked in orders
    available: float


@dataclass
class OrderInfo:
    status: str  # "resting", "filled", "error", "unknown"
    order_id: Optional[int] = None
    total_size: Optional[str] = None
    avg_price: Optional[str] = None
    error: Optional[str] = None
    message: str = ""
