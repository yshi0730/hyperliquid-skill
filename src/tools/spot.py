"""Spot trading tools."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client
from ..storage.db import get_db


def register_spot_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_spot_order",
                description="Place a spot order (buy or sell tokens). Coin is the base token name (e.g. 'PURR', 'HYPE'). Quoted in USDC.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Base token name, e.g. 'PURR', 'HYPE'"},
                        "isBuy": {"type": "boolean", "description": "True=buy, False=sell"},
                        "size": {"type": "string", "description": "Order size (token amount)"},
                        "price": {"type": "string", "description": "Limit price in USDC. '0' for market.", "default": "0"},
                        "orderType": {"type": "object", "description": "Order type config. Default: {limit: {tif: 'Gtc'}}"},
                    },
                    "required": ["coin", "isBuy", "size"],
                },
            ),
            Tool(
                name="hl_spot_cancel",
                description="Cancel a spot order",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Base token name"},
                        "oid": {"type": "integer", "description": "Order ID"},
                    },
                    "required": ["coin", "oid"],
                },
            ),
            Tool(
                name="hl_transfer",
                description="Transfer USDC between spot and perp accounts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number", "description": "USDC amount to transfer"},
                        "toPerp": {"type": "boolean", "description": "True=spot→perp, False=perp→spot"},
                    },
                    "required": ["amount", "toPerp"],
                },
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        client = get_shared_client()
        mode = "TESTNET" if client.is_testnet else "MAINNET"

        if name == "hl_spot_order":
            coin = arguments["coin"]
            is_buy = arguments["isBuy"]
            size = float(arguments["size"])
            price = float(arguments.get("price", "0"))
            order_type = arguments.get("orderType", {"limit": {"tif": "Gtc"}})

            result = client.spot_order(coin, is_buy, size, price, order_type)
            info = client.parse_order_response(result)

            # Log
            try:
                db = get_db()
                db.execute(
                    "INSERT INTO trades (id, order_id, coin, side, size, price, market_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'spot', ?, datetime('now'))",
                    (str(uuid.uuid4()), str(info.order_id), coin, "buy" if is_buy else "sell", size, price, info.status),
                )
                db.commit()
            except Exception:
                pass

            return [TextContent(type="text", text=json.dumps({
                "mode": mode, "market": "SPOT", "coin": coin,
                "side": "BUY" if is_buy else "SELL", "size": str(size), "price": str(price),
                "order": {"status": info.status, "orderId": info.order_id, "message": info.message, "error": info.error},
            }))]

        elif name == "hl_spot_cancel":
            result = client.spot_cancel(arguments["coin"], int(arguments["oid"]))
            return [TextContent(type="text", text=json.dumps({"mode": mode, "cancelled": arguments, "result": result}))]

        elif name == "hl_transfer":
            amount = float(arguments["amount"])
            to_perp = arguments["toPerp"]
            result = client.transfer_between_spot_and_perp(amount, to_perp)
            direction = "Spot → Perp" if to_perp else "Perp → Spot"
            return [TextContent(type="text", text=json.dumps({"mode": mode, "transfer": direction, "amount": amount, "result": result}))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle
