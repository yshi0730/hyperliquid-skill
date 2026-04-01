"""Perpetual futures trading tools."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client
from ..storage.db import get_db


def register_trading_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_place_order",
                description="Place a perpetual futures order (limit/market/trigger). Min order value $10. Use hl_get_meta to look up coin names.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Coin name, e.g. 'BTC', 'ETH', 'SOL'"},
                        "isBuy": {"type": "boolean", "description": "True=long/buy, False=short/sell"},
                        "size": {"type": "string", "description": "Order size as string, e.g. '0.1'"},
                        "price": {"type": "string", "description": "Limit price as string. '0' for market orders.", "default": "0"},
                        "reduceOnly": {"type": "boolean", "description": "Reduce-only order", "default": False},
                        "orderType": {"type": "object", "description": "Order type config. Default: {limit: {tif: 'Gtc'}}. For trigger: {trigger: {triggerPx: '100', isMarket: false, tpsl: 'tp'|'sl'}}"},
                    },
                    "required": ["coin", "isBuy", "size"],
                },
            ),
            Tool(
                name="hl_place_bracket_order",
                description="Place a bracket order: entry + take-profit + stop-loss in one atomic batch. Min $10.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Coin name"},
                        "isBuy": {"type": "boolean", "description": "True=long, False=short"},
                        "size": {"type": "string", "description": "Position size"},
                        "entryPrice": {"type": "string", "description": "Entry limit price ('0' for market)"},
                        "takeProfitPrice": {"type": "string", "description": "TP trigger price"},
                        "stopLossPrice": {"type": "string", "description": "SL trigger price"},
                    },
                    "required": ["coin", "isBuy", "size", "takeProfitPrice", "stopLossPrice"],
                },
            ),
            Tool(
                name="hl_cancel_order",
                description="Cancel a specific order by coin and order ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Coin name"},
                        "oid": {"type": "integer", "description": "Order ID"},
                    },
                    "required": ["coin", "oid"],
                },
            ),
            Tool(
                name="hl_cancel_all_orders",
                description="Cancel ALL open orders. Use with caution.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_modify_order",
                description="Modify an existing order's price and/or size",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "oid": {"type": "integer", "description": "Order ID to modify"},
                        "coin": {"type": "string"},
                        "isBuy": {"type": "boolean"},
                        "size": {"type": "string", "description": "New size"},
                        "price": {"type": "string", "description": "New price"},
                    },
                    "required": ["oid", "coin", "isBuy", "size", "price"],
                },
            ),
            Tool(
                name="hl_get_open_orders",
                description="List all currently open orders",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_order_status",
                description="Check status of a specific order",
                inputSchema={
                    "type": "object",
                    "properties": {"oid": {"type": "integer", "description": "Order ID"}},
                    "required": ["oid"],
                },
            ),
            Tool(
                name="hl_set_leverage",
                description="Set leverage for a perp asset",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Coin name"},
                        "leverage": {"type": "integer", "description": "Leverage value (1-50)"},
                        "isCross": {"type": "boolean", "description": "Cross margin (true) or isolated (false)", "default": True},
                    },
                    "required": ["coin", "leverage"],
                },
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        client = get_shared_client()
        mode = "TESTNET" if client.is_testnet else "MAINNET"

        if name == "hl_place_order":
            coin = arguments["coin"]
            is_buy = arguments["isBuy"]
            size = float(arguments["size"])
            price = float(arguments.get("price", "0"))
            reduce_only = arguments.get("reduceOnly", False)
            order_type = arguments.get("orderType", {"limit": {"tif": "Gtc"}})

            result = client.place_order(coin, is_buy, size, price, reduce_only, order_type)
            info = client.parse_order_response(result)

            # Log trade
            _log_trade(coin, "buy" if is_buy else "sell", size, price, info, "perp")

            return [TextContent(type="text", text=json.dumps({
                "mode": mode, "coin": coin, "side": "BUY" if is_buy else "SELL",
                "size": str(size), "price": str(price),
                "order": {"status": info.status, "orderId": info.order_id, "message": info.message,
                          "avgPrice": info.avg_price, "error": info.error},
            }))]

        elif name == "hl_place_bracket_order":
            coin = arguments["coin"]
            is_buy = arguments["isBuy"]
            size = float(arguments["size"])
            entry_price = float(arguments.get("entryPrice", "0"))
            tp = float(arguments["takeProfitPrice"])
            sl = float(arguments["stopLossPrice"])

            result = client.place_bracket_order(coin, is_buy, size, entry_price, tp, sl)
            statuses = result.get("response", {}).get("data", {}).get("statuses", [])
            orders = []
            labels = ["entry", "take-profit", "stop-loss"]
            for i, s in enumerate(statuses):
                info = client.parse_order_response({"response": {"data": {"statuses": [s]}}})
                orders.append({"type": labels[i] if i < 3 else "unknown", "status": info.status, "orderId": info.order_id, "error": info.error})

            _log_trade(coin, "buy" if is_buy else "sell", size, entry_price, orders[0] if orders else None, "perp")

            return [TextContent(type="text", text=json.dumps({
                "mode": mode, "coin": coin, "side": "LONG" if is_buy else "SHORT",
                "size": str(size), "entryPrice": str(entry_price),
                "takeProfit": str(tp), "stopLoss": str(sl), "orders": orders,
            }))]

        elif name == "hl_cancel_order":
            result = client.cancel_order(arguments["coin"], int(arguments["oid"]))
            return [TextContent(type="text", text=json.dumps({"mode": mode, "cancelled": {"coin": arguments["coin"], "oid": arguments["oid"]}, "result": result}))]

        elif name == "hl_cancel_all_orders":
            result = client.cancel_all_orders()
            return [TextContent(type="text", text=json.dumps({"mode": mode, **result}))]

        elif name == "hl_modify_order":
            result = client.modify_order(
                int(arguments["oid"]), arguments["coin"], arguments["isBuy"],
                float(arguments["size"]), float(arguments["price"]),
            )
            return [TextContent(type="text", text=json.dumps({"mode": mode, "modified": arguments, "result": result}))]

        elif name == "hl_get_open_orders":
            orders = client.get_open_orders()
            return [TextContent(type="text", text=json.dumps({"mode": mode, "orders": orders, "count": len(orders) if orders else 0}))]

        elif name == "hl_get_order_status":
            result = client.query_order(int(arguments["oid"]))
            return [TextContent(type="text", text=json.dumps({"mode": mode, "oid": arguments["oid"], "order": result}))]

        elif name == "hl_set_leverage":
            result = client.set_leverage(arguments["coin"], int(arguments["leverage"]), arguments.get("isCross", True))
            return [TextContent(type="text", text=json.dumps({"mode": mode, "coin": arguments["coin"], "leverage": arguments["leverage"], "result": result}))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle


def _log_trade(coin, side, size, price, info, market_type):
    try:
        db = get_db()
        oid = info.order_id if hasattr(info, "order_id") else (info.get("orderId") if isinstance(info, dict) else None)
        status = info.status if hasattr(info, "status") else (info.get("status") if isinstance(info, dict) else "unknown")
        db.execute(
            "INSERT INTO trades (id, order_id, coin, side, size, price, market_type, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            (str(uuid.uuid4()), str(oid), coin, side, size, price, market_type, status),
        )
        db.commit()
    except Exception:
        pass  # Don't fail trading on logging errors
