"""Market data tools — prices, candles, orderbook, funding, meta."""

from __future__ import annotations

import json
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client


def register_market_data_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_get_meta",
                description="Get exchange metadata: all perp assets with indices, names, max leverage. Essential for mapping coin names to asset indices.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_spot_meta",
                description="Get spot exchange metadata: all spot tokens and trading pairs",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_all_prices",
                description="Get current mid prices for all perp assets — quick market overview",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_orderbook",
                description="Get L2 order book (bids & asks depth) for a specific asset",
                inputSchema={
                    "type": "object",
                    "properties": {"coin": {"type": "string", "description": "Asset symbol, e.g. 'BTC', 'ETH', 'SOL'"}},
                    "required": ["coin"],
                },
            ),
            Tool(
                name="hl_get_recent_trades",
                description="Get recent trades for an asset",
                inputSchema={
                    "type": "object",
                    "properties": {"coin": {"type": "string", "description": "Asset symbol"}},
                    "required": ["coin"],
                },
            ),
            Tool(
                name="hl_get_candles",
                description="Get historical OHLCV candle data for chart analysis",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Asset symbol"},
                        "interval": {"type": "string", "enum": ["1m", "5m", "15m", "1h", "4h", "1d"], "description": "Candle interval"},
                        "startTime": {"type": "integer", "description": "Start time in milliseconds"},
                        "endTime": {"type": "integer", "description": "End time in ms (optional)"},
                    },
                    "required": ["coin", "interval", "startTime"],
                },
            ),
            Tool(
                name="hl_get_funding_history",
                description="Get historical funding rates for a perp asset",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Asset symbol"},
                        "startTime": {"type": "integer", "description": "Start time in milliseconds"},
                        "endTime": {"type": "integer", "description": "End time in ms (optional)"},
                    },
                    "required": ["coin", "startTime"],
                },
            ),
            Tool(
                name="hl_get_user_fills",
                description="Get user's historical trade fills",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "startTime": {"type": "integer", "description": "Start time in milliseconds"},
                        "endTime": {"type": "integer", "description": "End time in ms (optional)"},
                    },
                    "required": ["startTime"],
                },
            ),
            Tool(
                name="hl_get_user_funding",
                description="Get user's funding payment history",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "startTime": {"type": "integer", "description": "Start time in milliseconds"},
                        "endTime": {"type": "integer", "description": "End time in ms (optional)"},
                    },
                    "required": ["startTime"],
                },
            ),
            Tool(
                name="hl_market_overview",
                description="Get a quick market overview: top movers, BTC/ETH prices, total open interest snapshot",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        client = get_shared_client()

        if name == "hl_get_meta":
            meta = client.get_perp_meta()
            assets = [
                {"index": i, "name": a["name"], "maxLeverage": a["maxLeverage"], "onlyIsolated": a.get("onlyIsolated", False)}
                for i, a in enumerate(meta["universe"])
            ]
            return [TextContent(type="text", text=json.dumps({"assets": assets, "totalAssets": len(assets)}))]

        elif name == "hl_get_spot_meta":
            meta = client.get_spot_meta()
            return [TextContent(type="text", text=json.dumps(meta))]

        elif name == "hl_get_all_prices":
            mids = client.get_all_mids()
            return [TextContent(type="text", text=json.dumps({"prices": mids, "count": len(mids)}))]

        elif name == "hl_get_orderbook":
            book = client.get_l2_snapshot(arguments["coin"])
            return [TextContent(type="text", text=json.dumps({"coin": arguments["coin"], "orderbook": book}))]

        elif name == "hl_get_recent_trades":
            trades = client.get_recent_trades(arguments["coin"])
            return [TextContent(type="text", text=json.dumps({"coin": arguments["coin"], "trades": trades, "count": len(trades) if trades else 0}))]

        elif name == "hl_get_candles":
            candles = client.get_candles(
                arguments["coin"], arguments["interval"],
                int(arguments["startTime"]), arguments.get("endTime"),
            )
            return [TextContent(type="text", text=json.dumps({"coin": arguments["coin"], "interval": arguments["interval"], "candles": candles, "count": len(candles) if candles else 0}))]

        elif name == "hl_get_funding_history":
            data = client.get_funding_history(arguments["coin"], int(arguments["startTime"]), arguments.get("endTime"))
            return [TextContent(type="text", text=json.dumps({"coin": arguments["coin"], "funding": data, "count": len(data) if data else 0}))]

        elif name == "hl_get_user_fills":
            fills = client.get_user_fills(int(arguments["startTime"]), arguments.get("endTime"))
            return [TextContent(type="text", text=json.dumps({"fills": fills, "count": len(fills) if fills else 0}))]

        elif name == "hl_get_user_funding":
            data = client.get_user_funding(int(arguments["startTime"]), arguments.get("endTime"))
            return [TextContent(type="text", text=json.dumps({"funding": data, "count": len(data) if data else 0}))]

        elif name == "hl_market_overview":
            mids = client.get_all_mids()
            # Extract key assets
            key_assets = {}
            for coin in ["BTC", "ETH", "SOL", "DOGE", "ARB", "OP", "AVAX", "MATIC", "LINK", "UNI"]:
                if coin in mids:
                    key_assets[coin] = mids[coin]
            return [TextContent(type="text", text=json.dumps({
                "mode": "TESTNET" if client.is_testnet else "MAINNET",
                "keyAssets": key_assets,
                "totalPerps": len(mids),
            }))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle
