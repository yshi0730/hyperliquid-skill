"""Account and position tools."""

from __future__ import annotations

import json
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client


def register_account_tools(server: Server):

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_get_account",
                description="Get perpetual account summary (equity, margin, withdrawable, positions count)",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_positions",
                description="Get all open perpetual positions with PnL, leverage, and liquidation info",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hl_get_spot_balances",
                description="Get spot account token balances",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        client = get_shared_client()

        if name == "hl_get_account":
            state = client.get_user_state()
            ms = state["marginSummary"]
            mode = "TESTNET" if client.is_testnet else "MAINNET"
            return [TextContent(type="text", text=json.dumps({
                "mode": mode,
                "accountValue": ms["accountValue"],
                "totalMarginUsed": ms["totalMarginUsed"],
                "totalNtlPos": ms["totalNtlPos"],
                "totalRawUsd": ms["totalRawUsd"],
                "withdrawable": state["withdrawable"],
                "openPositions": len(state["assetPositions"]),
            }))]

        elif name == "hl_get_positions":
            state = client.get_user_state()
            positions = []
            for p in state["assetPositions"]:
                pos = p["position"]
                positions.append({
                    "coin": pos["coin"],
                    "size": pos["szi"],
                    "entryPrice": pos["entryPx"],
                    "unrealizedPnl": pos["unrealizedPnl"],
                    "returnOnEquity": pos.get("returnOnEquity", "0"),
                    "leverage": pos.get("leverage", {}).get("value", "N/A"),
                    "leverageType": pos.get("leverage", {}).get("type", "N/A"),
                    "liquidationPx": pos.get("liquidationPx"),
                    "marginUsed": pos.get("marginUsed", "0"),
                })
            return [TextContent(type="text", text=json.dumps({
                "mode": "TESTNET" if client.is_testnet else "MAINNET",
                "positions": positions,
                "marginSummary": state["marginSummary"],
            }))]

        elif name == "hl_get_spot_balances":
            spot_state = client.get_spot_user_state()
            return [TextContent(type="text", text=json.dumps({
                "mode": "TESTNET" if client.is_testnet else "MAINNET",
                "balances": spot_state.get("balances", []),
            }))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle
