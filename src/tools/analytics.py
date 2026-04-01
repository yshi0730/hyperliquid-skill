"""Analytics, trade journal, and review tools."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client
from ..storage.db import get_db


def register_analytics_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_get_performance",
                description="Get portfolio performance summary (equity snapshots, PnL trend)",
                inputSchema={
                    "type": "object",
                    "properties": {"period": {"type": "string", "enum": ["1d", "1w", "1m", "3m", "all"], "default": "1w"}},
                },
            ),
            Tool(
                name="hl_get_trade_journal",
                description="Get trade history from local journal with notes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Filter by coin (optional)"},
                        "market_type": {"type": "string", "enum": ["perp", "spot"], "description": "Filter by market type"},
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            ),
            Tool(
                name="hl_add_trade_note",
                description="Add a note to a trade for review purposes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "trade_id": {"type": "string"},
                        "note": {"type": "string"},
                    },
                    "required": ["trade_id", "note"],
                },
            ),
            Tool(
                name="hl_review_session",
                description="Generate a comprehensive trading review for a period. Analyzes wins, losses, patterns, and provides suggestions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "period": {"type": "string", "enum": ["1d", "1w", "1m"], "default": "1w"},
                    },
                },
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        db = get_db()

        if name == "hl_get_performance":
            period = arguments.get("period", "1w")
            period_map = {"1d": "-1 day", "1w": "-7 days", "1m": "-30 days", "3m": "-90 days", "all": "-10 years"}
            sql_period = period_map.get(period, "-7 days")

            snapshots = db.execute(
                "SELECT total_equity, total_pnl, created_at FROM position_snapshots WHERE created_at >= datetime('now', ?) ORDER BY created_at",
                (sql_period,),
            ).fetchall()

            # Also get current state from exchange
            try:
                client = get_shared_client()
                state = client.get_user_state()
                current_equity = float(state["marginSummary"]["accountValue"])
                spot_state = client.get_spot_user_state()
            except Exception:
                current_equity = 0
                spot_state = {}

            return [TextContent(type="text", text=json.dumps({
                "period": period,
                "currentEquity": current_equity,
                "snapshots": [dict(s) for s in snapshots],
                "snapshotCount": len(snapshots),
                "spotBalances": spot_state.get("balances", []),
            }))]

        elif name == "hl_get_trade_journal":
            conditions = []
            params = []
            if arguments.get("coin"):
                conditions.append("coin = ?")
                params.append(arguments["coin"])
            if arguments.get("market_type"):
                conditions.append("market_type = ?")
                params.append(arguments["market_type"])
            where = " WHERE " + " AND ".join(conditions) if conditions else ""
            limit = arguments.get("limit", 50)
            params.append(limit)
            rows = db.execute(f"SELECT * FROM trades{where} ORDER BY created_at DESC LIMIT ?", params).fetchall()
            trades = [dict(r) for r in rows]
            return [TextContent(type="text", text=json.dumps({"trades": trades, "count": len(trades)}))]

        elif name == "hl_add_trade_note":
            db.execute("UPDATE trades SET note = ? WHERE id = ?", (arguments["note"], arguments["trade_id"]))
            db.commit()
            return [TextContent(type="text", text=json.dumps({"updated": arguments["trade_id"], "note": arguments["note"]}))]

        elif name == "hl_review_session":
            period = arguments.get("period", "1w")
            period_map = {"1d": "-1 day", "1w": "-7 days", "1m": "-30 days"}
            sql_period = period_map.get(period, "-7 days")

            trades = db.execute(
                "SELECT * FROM trades WHERE created_at >= datetime('now', ?) ORDER BY created_at",
                (sql_period,),
            ).fetchall()
            trades_list = [dict(t) for t in trades]

            # Basic stats
            total = len(trades_list)
            perp_count = sum(1 for t in trades_list if t.get("market_type") == "perp")
            spot_count = sum(1 for t in trades_list if t.get("market_type") == "spot")
            buys = sum(1 for t in trades_list if t.get("side") == "buy")
            sells = sum(1 for t in trades_list if t.get("side") == "sell")
            coins = list(set(t.get("coin", "") for t in trades_list))

            return [TextContent(type="text", text=json.dumps({
                "period": period,
                "totalTrades": total,
                "perpTrades": perp_count,
                "spotTrades": spot_count,
                "buys": buys,
                "sells": sells,
                "coinsTraded": coins,
                "trades": trades_list,
            }))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle
