"""Monitoring and alert tools."""

from __future__ import annotations

import json
import uuid
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client
from ..storage.db import get_db


def register_monitor_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_add_alert",
                description="Add a price/funding/liquidation alert rule",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "coin": {"type": "string", "description": "Asset symbol"},
                        "condition": {"type": "string", "enum": ["price_above", "price_below", "funding_above", "funding_below", "liquidation_proximity"], "description": "Alert condition type"},
                        "threshold": {"type": "number", "description": "Threshold value"},
                        "message": {"type": "string", "description": "Custom alert message (optional)"},
                    },
                    "required": ["coin", "condition", "threshold"],
                },
            ),
            Tool(
                name="hl_get_alerts",
                description="List all alert rules",
                inputSchema={"type": "object", "properties": {"active_only": {"type": "boolean", "default": True}}},
            ),
            Tool(
                name="hl_remove_alert",
                description="Remove an alert rule",
                inputSchema={"type": "object", "properties": {"alert_id": {"type": "string"}}, "required": ["alert_id"]},
            ),
            Tool(
                name="hl_get_alert_history",
                description="Get triggered alert history",
                inputSchema={"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
            ),
            Tool(
                name="hl_start_monitor",
                description="Start the background monitoring daemon (checks alerts periodically)",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_monitor_status",
                description="Get monitor status and any unacknowledged alerts",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        db = get_db()

        if name == "hl_add_alert":
            aid = str(uuid.uuid4())[:8]
            cond = json.dumps({"type": arguments["condition"], "threshold": arguments["threshold"]})
            action = json.dumps({"type": "notify", "message": arguments.get("message", f"{arguments['coin']} {arguments['condition']} {arguments['threshold']}")})
            db.execute(
                "INSERT INTO alert_rules (id, coin, condition, action, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
                (aid, arguments["coin"], cond, action),
            )
            db.commit()
            return [TextContent(type="text", text=json.dumps({"id": aid, "coin": arguments["coin"], "condition": arguments["condition"], "threshold": arguments["threshold"], "status": "active"}))]

        elif name == "hl_get_alerts":
            active_only = arguments.get("active_only", True)
            q = "SELECT * FROM alert_rules" + (" WHERE is_active = 1" if active_only else "") + " ORDER BY created_at DESC"
            rows = db.execute(q).fetchall()
            alerts = []
            for r in rows:
                a = dict(r)
                a["condition"] = json.loads(a["condition"])
                a["action"] = json.loads(a["action"])
                alerts.append(a)
            return [TextContent(type="text", text=json.dumps({"alerts": alerts, "count": len(alerts)}))]

        elif name == "hl_remove_alert":
            db.execute("DELETE FROM alert_rules WHERE id = ?", (arguments["alert_id"],))
            db.commit()
            return [TextContent(type="text", text=json.dumps({"deleted": arguments["alert_id"]}))]

        elif name == "hl_get_alert_history":
            limit = arguments.get("limit", 20)
            rows = db.execute("SELECT * FROM alert_history ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            history = [dict(r) for r in rows]
            return [TextContent(type="text", text=json.dumps({"history": history, "count": len(history)}))]

        elif name == "hl_start_monitor":
            # Phase 2: daemon-based monitor. For now, manual polling via hl_get_monitor_status.
            return [TextContent(type="text", text=json.dumps({
                "status": "manual_mode",
                "message": "Monitor is in manual polling mode. Use hl_get_monitor_status to check alerts against current prices. Daemon mode coming in a future update.",
            }))]

        elif name == "hl_get_monitor_status":
            # Check alerts against current prices
            try:
                client = get_shared_client()
                mids = client.get_all_mids()
            except Exception:
                mids = {}

            active_rules = db.execute("SELECT * FROM alert_rules WHERE is_active = 1").fetchall()
            triggered = []
            for r in active_rules:
                cond = json.loads(r["condition"])
                coin = r["coin"]
                if coin not in mids:
                    continue
                price = float(mids[coin])
                threshold = cond["threshold"]
                fire = False
                if cond["type"] == "price_above" and price >= threshold:
                    fire = True
                elif cond["type"] == "price_below" and price <= threshold:
                    fire = True

                if fire:
                    action = json.loads(r["action"])
                    alert_id = str(uuid.uuid4())[:8]
                    db.execute(
                        "INSERT INTO alert_history (id, rule_id, coin, message, data, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                        (alert_id, r["id"], coin, action.get("message", ""), json.dumps({"price": price, "threshold": threshold})),
                    )
                    triggered.append({"alertId": alert_id, "coin": coin, "condition": cond["type"], "threshold": threshold, "currentPrice": price, "message": action.get("message", "")})

            # Unacknowledged alerts
            unack = db.execute("SELECT * FROM alert_history WHERE acknowledged = 0 ORDER BY created_at DESC LIMIT 10").fetchall()
            unack_list = [dict(r) for r in unack]

            if triggered:
                db.commit()

            return [TextContent(type="text", text=json.dumps({
                "activeRules": len(active_rules),
                "justTriggered": triggered,
                "unacknowledged": unack_list,
            }))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle
