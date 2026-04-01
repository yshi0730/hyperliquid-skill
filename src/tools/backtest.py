"""Backtest tools."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client
from ..storage.db import get_db
from ..backtest.engine import run_backtest


def register_backtest_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_backtest",
                description="Backtest a strategy against historical candle data. Fetches data from Hyperliquid and runs simulation.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "strategy_id": {"type": "string", "description": "Saved strategy ID, or omit to pass rules directly"},
                        "rules": {"type": "object", "description": "Strategy rules (if not using saved strategy)"},
                        "coin": {"type": "string", "description": "Coin to backtest on", "default": "BTC"},
                        "interval": {"type": "string", "enum": ["1h", "4h", "1d"], "default": "1d"},
                        "startTime": {"type": "integer", "description": "Start time in milliseconds"},
                        "endTime": {"type": "integer", "description": "End time in ms (optional)"},
                        "initialCapital": {"type": "number", "default": 10000},
                    },
                    "required": ["startTime"],
                },
            ),
            Tool(
                name="hl_get_backtest_results",
                description="Get results of a previously run backtest",
                inputSchema={
                    "type": "object",
                    "properties": {"backtest_id": {"type": "string"}},
                    "required": ["backtest_id"],
                },
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        db = get_db()

        if name == "hl_backtest":
            # Get strategy rules
            rules = arguments.get("rules")
            strategy_id = arguments.get("strategy_id")
            if not rules and strategy_id:
                row = db.execute("SELECT rules FROM strategies WHERE id = ?", (strategy_id,)).fetchone()
                if not row:
                    return [TextContent(type="text", text=json.dumps({"error": f"Strategy {strategy_id} not found"}))]
                rules = json.loads(row["rules"])
            if not rules:
                return [TextContent(type="text", text=json.dumps({"error": "Provide strategy_id or rules"}))]

            # Fetch candles
            client = get_shared_client()
            coin = arguments.get("coin", "BTC")
            interval = arguments.get("interval", "1d")
            start_time = int(arguments["startTime"])
            end_time = arguments.get("endTime")
            candles = client.get_candles(coin, interval, start_time, end_time)

            if not candles:
                return [TextContent(type="text", text=json.dumps({"error": "No candle data returned"}))]

            initial_capital = arguments.get("initialCapital", 10000)
            result = run_backtest(rules, candles, initial_capital)

            # Save
            bid = str(uuid.uuid4())[:8]
            config = {"coin": coin, "interval": interval, "startTime": start_time, "endTime": end_time, "initialCapital": initial_capital}
            db.execute(
                "INSERT INTO backtests (id, strategy_id, config, result, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                (bid, strategy_id or "adhoc", json.dumps(config), json.dumps(result)),
            )
            db.commit()

            return [TextContent(type="text", text=json.dumps({"backtestId": bid, "coin": coin, "interval": interval, "candles": len(candles), **result}))]

        elif name == "hl_get_backtest_results":
            row = db.execute("SELECT * FROM backtests WHERE id = ?", (arguments["backtest_id"],)).fetchone()
            if not row:
                return [TextContent(type="text", text=json.dumps({"error": "Backtest not found"}))]
            r = dict(row)
            r["config"] = json.loads(r["config"])
            r["result"] = json.loads(r["result"])
            return [TextContent(type="text", text=json.dumps(r))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle
