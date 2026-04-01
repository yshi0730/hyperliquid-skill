"""Strategy management tools with crypto-specific templates."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..storage.db import get_db

TEMPLATES = {
    "momentum": {
        "name": "Momentum Breakout",
        "description": "Buy when price breaks above N-period high, sell when it breaks below N-period low. Classic trend-following for crypto.",
        "rules": {
            "universe": ["BTC"],
            "entry": {"indicator": "price_vs_high", "period": 20, "op": "gt"},
            "exit": {"indicator": "price_vs_low", "period": 10, "op": "lt"},
            "risk": {"stop_loss_pct": 5, "take_profit_pct": 15, "max_position_pct": 20},
        },
    },
    "mean_reversion": {
        "name": "Bollinger Mean Reversion",
        "description": "Short when price touches upper Bollinger Band, long when it touches lower band. Works in ranging markets.",
        "rules": {
            "universe": ["ETH"],
            "entry_long": {"indicator": "bb_lower_touch", "period": 20, "std": 2},
            "entry_short": {"indicator": "bb_upper_touch", "period": 20, "std": 2},
            "exit": {"indicator": "sma_cross", "period": 20},
            "risk": {"stop_loss_pct": 3, "max_position_pct": 15},
        },
    },
    "funding_arb": {
        "name": "Funding Rate Arbitrage",
        "description": "When funding is extremely positive (longs pay shorts), go short perp + long spot to earn funding. Vice versa for negative funding.",
        "rules": {
            "universe": ["BTC", "ETH", "SOL"],
            "entry": {"indicator": "funding_rate", "threshold": 0.01, "direction": "opposite"},
            "exit": {"indicator": "funding_rate", "threshold": 0.005, "direction": "normalize"},
            "risk": {"max_position_pct": 30, "max_leverage": 3},
        },
    },
    "grid": {
        "name": "Grid Trading",
        "description": "Place buy and sell orders at regular price intervals. Profits from oscillation in a defined range.",
        "rules": {
            "universe": ["ETH"],
            "grid": {"lower": 2500, "upper": 4000, "grids": 20, "size_per_grid_pct": 2},
            "risk": {"stop_loss_below": 2200, "max_position_pct": 50},
        },
    },
    "dca": {
        "name": "Dollar Cost Averaging",
        "description": "Invest fixed USDC amount at regular intervals regardless of price. Reduces timing risk.",
        "rules": {
            "universe": ["BTC", "ETH"],
            "schedule": "weekly",
            "amount_usdc": 100,
            "market_type": "spot",
            "risk": {"stop_loss_pct": 25},
        },
    },
}


def register_strategy_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_list_strategy_templates",
                description="List available strategy templates (momentum, mean reversion, funding arb, grid, DCA)",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_create_strategy",
                description="Create and save a custom strategy",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "rules": {"type": "object", "description": "Strategy rules (JSON)"},
                    },
                    "required": ["name", "rules"],
                },
            ),
            Tool(
                name="hl_list_strategies",
                description="List all saved strategies",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_strategy",
                description="Get details of a saved strategy",
                inputSchema={"type": "object", "properties": {"strategy_id": {"type": "string"}}, "required": ["strategy_id"]},
            ),
            Tool(
                name="hl_delete_strategy",
                description="Delete a saved strategy",
                inputSchema={"type": "object", "properties": {"strategy_id": {"type": "string"}}, "required": ["strategy_id"]},
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        db = get_db()

        if name == "hl_list_strategy_templates":
            out = []
            for key, tpl in TEMPLATES.items():
                out.append({"id": key, "name": tpl["name"], "description": tpl["description"], "rules": tpl["rules"]})
            return [TextContent(type="text", text=json.dumps({"templates": out}))]

        elif name == "hl_create_strategy":
            sid = str(uuid.uuid4())[:8]
            db.execute(
                "INSERT INTO strategies (id, name, description, rules, created_at, updated_at) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
                (sid, arguments["name"], arguments.get("description", ""), json.dumps(arguments["rules"])),
            )
            db.commit()
            return [TextContent(type="text", text=json.dumps({"id": sid, "name": arguments["name"], "status": "created"}))]

        elif name == "hl_list_strategies":
            rows = db.execute("SELECT id, name, description, is_active, created_at FROM strategies ORDER BY created_at DESC").fetchall()
            strategies = [dict(r) for r in rows]
            return [TextContent(type="text", text=json.dumps({"strategies": strategies, "count": len(strategies)}))]

        elif name == "hl_get_strategy":
            row = db.execute("SELECT * FROM strategies WHERE id = ?", (arguments["strategy_id"],)).fetchone()
            if not row:
                return [TextContent(type="text", text=json.dumps({"error": "Strategy not found"}))]
            s = dict(row)
            s["rules"] = json.loads(s["rules"])
            return [TextContent(type="text", text=json.dumps(s))]

        elif name == "hl_delete_strategy":
            db.execute("DELETE FROM strategies WHERE id = ?", (arguments["strategy_id"],))
            db.commit()
            return [TextContent(type="text", text=json.dumps({"deleted": arguments["strategy_id"]}))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle
