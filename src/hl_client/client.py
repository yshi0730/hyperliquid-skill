"""Hyperliquid API client wrapping the official Python SDK."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import eth_account
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.types import Cloid

from .types import HLConfig, OrderInfo

logger = logging.getLogger(__name__)

# Singleton
_shared_client: Optional["HyperliquidClient"] = None


def get_shared_client() -> "HyperliquidClient":
    global _shared_client
    if _shared_client is None:
        config = HLConfig(
            private_key=os.getenv("HYPERLIQUID_PRIVATE_KEY", ""),
            account_address=os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS"),
            vault_address=os.getenv("HYPERLIQUID_VAULT_ADDRESS"),
            testnet=os.getenv("HYPERLIQUID_TESTNET", "").lower() == "true",
        )
        _shared_client = HyperliquidClient(config)
    return _shared_client


def reset_shared_client() -> None:
    global _shared_client
    _shared_client = None


class HyperliquidClient:
    """Wraps hyperliquid-python-sdk Exchange and Info classes."""

    def __init__(self, config: HLConfig):
        self.config = config
        self.wallet: Optional[LocalAccount] = None
        self.info: Optional[Info] = None
        self.exchange: Optional[Exchange] = None
        self._meta_cache: Optional[dict] = None
        self._spot_meta_cache: Optional[dict] = None

        if config.private_key:
            self._init()

    def _init(self):
        self.wallet = eth_account.Account.from_key(self.config.private_key)
        if not self.config.account_address:
            self.config.account_address = self.wallet.address

        base_url = constants.TESTNET_API_URL if self.config.testnet else constants.MAINNET_API_URL
        logger.info(f"Connecting to {base_url} as {self.config.account_address}")

        self.info = Info(base_url, skip_ws=True)
        self.exchange = Exchange(
            wallet=self.wallet,
            base_url=base_url,
            account_address=self.config.account_address,
            vault_address=self.config.vault_address,
        )

    @property
    def address(self) -> str:
        return self.config.account_address or ""

    @property
    def is_testnet(self) -> bool:
        return self.config.testnet

    # ── Meta helpers ──

    def get_perp_meta(self) -> dict:
        if self._meta_cache is None:
            self._meta_cache = self.info.meta()
        return self._meta_cache

    def get_spot_meta(self) -> dict:
        if self._spot_meta_cache is None:
            self._spot_meta_cache = self.info.spot_meta()
        return self._spot_meta_cache

    def coin_to_asset_index(self, coin: str) -> int:
        meta = self.get_perp_meta()
        for idx, asset in enumerate(meta["universe"]):
            if asset["name"].upper() == coin.upper():
                return idx
        raise ValueError(f"Unknown perp asset: {coin}")

    def get_spot_token_index(self, coin: str) -> Optional[int]:
        """Get spot token index for a coin name."""
        spot_meta = self.get_spot_meta()
        for token in spot_meta.get("tokens", []):
            if token["name"].upper() == coin.upper():
                return token["index"]
        return None

    # ── Account ──

    def get_user_state(self, address: str = None) -> dict:
        addr = address or self.address
        return self.info.user_state(addr)

    def get_spot_user_state(self, address: str = None) -> dict:
        addr = address or self.address
        return self.info.spot_user_state(addr)

    # ── Market data ──

    def get_all_mids(self) -> dict:
        return self.info.all_mids()

    def get_l2_snapshot(self, coin: str) -> dict:
        return self.info.l2_snapshot(coin)

    def get_recent_trades(self, coin: str) -> list:
        return self.info.recent_trades(coin)

    def get_candles(self, coin: str, interval: str, start_time: int, end_time: int = None) -> list:
        return self.info.candles_snapshot(coin=coin, interval=interval, start_time=start_time, end_time=end_time)

    def get_funding_history(self, coin: str, start_time: int, end_time: int = None) -> list:
        return self.info.funding_history(coin=coin, start_time=start_time, end_time=end_time)

    def get_open_orders(self, address: str = None) -> list:
        return self.info.open_orders(address or self.address)

    def get_user_fills(self, start_time: int, end_time: int = None, address: str = None) -> list:
        return self.info.user_fills_by_time(
            user=address or self.address,
            start_time=start_time,
            end_time=end_time,
        )

    def get_user_funding(self, start_time: int, end_time: int = None, address: str = None) -> list:
        return self.info.user_funding(
            user=address or self.address,
            start_time=start_time,
            end_time=end_time,
        )

    def query_order(self, oid: int, address: str = None) -> dict:
        return self.info.query_order_by_oid(address or self.address, oid)

    def get_vault_details(self, vault_address: str) -> dict:
        return self.info.vault_details(vault_address)

    # ── Perp trading ──

    def place_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float = 0.0,
        reduce_only: bool = False,
        order_type: dict = None,
        cloid: str = None,
    ) -> dict:
        if order_type is None:
            order_type = {"limit": {"tif": "Gtc"}}
        # Resolve trigger price to float
        if "trigger" in order_type:
            trig = order_type["trigger"]
            if "triggerPx" in trig and isinstance(trig["triggerPx"], str):
                trig["triggerPx"] = float(trig["triggerPx"])
        c = Cloid(cloid) if cloid else None
        return self.exchange.order(
            name=coin,
            is_buy=is_buy,
            sz=size,
            limit_px=price,
            order_type=order_type,
            reduce_only=reduce_only,
            cloid=c,
        )

    def place_bracket_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        entry_price: float,
        tp_price: float,
        sl_price: float,
        reduce_only: bool = False,
        entry_order_type: dict = None,
    ) -> dict:
        if entry_order_type is None:
            entry_order_type = {"limit": {"tif": "Gtc"}}
        orders = [
            {
                "coin": coin,
                "is_buy": is_buy,
                "sz": size,
                "limit_px": entry_price,
                "order_type": entry_order_type,
                "reduce_only": reduce_only,
            },
            {
                "coin": coin,
                "is_buy": not is_buy,
                "sz": size,
                "limit_px": tp_price,
                "order_type": {"trigger": {"triggerPx": tp_price, "isMarket": False, "tpsl": "tp"}},
                "reduce_only": True,
            },
            {
                "coin": coin,
                "is_buy": not is_buy,
                "sz": size,
                "limit_px": sl_price,
                "order_type": {"trigger": {"triggerPx": sl_price, "isMarket": False, "tpsl": "sl"}},
                "reduce_only": True,
            },
        ]
        return self.exchange.bulk_orders(orders)

    def cancel_order(self, coin: str, oid: int) -> dict:
        return self.exchange.cancel(coin, oid)

    def cancel_all_orders(self, address: str = None) -> dict:
        open_orders = self.get_open_orders(address)
        if not open_orders:
            return {"message": "No open orders", "cancelledCount": 0}
        reqs = [{"coin": o["coin"], "oid": o["oid"]} for o in open_orders]
        result = self.exchange.bulk_cancel(reqs)
        return {"result": result, "cancelledCount": len(reqs)}

    def modify_order(
        self, oid: int, coin: str, is_buy: bool, size: float, price: float,
        reduce_only: bool = False, order_type: dict = None,
    ) -> dict:
        if order_type is None:
            order_type = {"limit": {"tif": "Gtc"}}
        return self.exchange.modify_order(
            oid=oid, name=coin, is_buy=is_buy, sz=size, limit_px=price,
            order_type=order_type, reduce_only=reduce_only,
        )

    def set_leverage(self, coin: str, leverage: int, is_cross: bool = True) -> dict:
        """Update leverage for a perp asset."""
        return self.exchange.update_leverage(leverage, coin, is_cross=is_cross)

    # ── Spot trading ──

    def spot_order(
        self,
        coin: str,
        is_buy: bool,
        size: float,
        price: float = 0.0,
        order_type: dict = None,
    ) -> dict:
        """Place a spot order. Coin should be the base token name (e.g. 'PURR')."""
        if order_type is None:
            order_type = {"limit": {"tif": "Gtc"}}
        return self.exchange.order(
            name=f"{coin}/USDC",
            is_buy=is_buy,
            sz=size,
            limit_px=price,
            order_type=order_type,
        )

    def spot_cancel(self, coin: str, oid: int) -> dict:
        return self.exchange.cancel(f"{coin}/USDC", oid)

    # ── Transfer ──

    def transfer_between_spot_and_perp(self, usdc_amount: float, to_perp: bool = True) -> dict:
        """Transfer USDC between spot and perp accounts."""
        return self.exchange.user_spot_transfer(usdc_amount, to_perp)

    # ── Helpers ──

    @staticmethod
    def parse_order_response(result: dict) -> OrderInfo:
        statuses = result.get("response", {}).get("data", {}).get("statuses", [{}])
        if not statuses:
            return OrderInfo(status="unknown", message="No status in response")
        status = statuses[0]
        if "resting" in status:
            return OrderInfo(status="resting", order_id=status["resting"]["oid"], message="Order resting on book")
        elif "filled" in status:
            f = status["filled"]
            return OrderInfo(status="filled", order_id=f["oid"], total_size=f["totalSz"], avg_price=f["avgPx"], message="Order filled")
        elif "error" in status:
            return OrderInfo(status="error", error=status["error"], message="Order failed")
        return OrderInfo(status="unknown", message=str(status))
