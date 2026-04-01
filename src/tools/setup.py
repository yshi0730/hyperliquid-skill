"""Setup and configuration tools."""

from __future__ import annotations

import json
import logging
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..hl_client import get_shared_client, reset_shared_client, HLConfig, HyperliquidClient

logger = logging.getLogger(__name__)


def register_setup_tools(server: Server):

    @server.list_tools()
    async def _list(prev=server._tool_list_handlers):
        # This pattern merges tools from multiple modules — handled in server.py
        pass

    def _tools() -> list[Tool]:
        return [
            Tool(
                name="hl_setup_guide",
                description="Show step-by-step guide for setting up Hyperliquid trading (wallet, deposit, API config)",
                inputSchema={"type": "object", "properties": {"step": {"type": "integer", "description": "Show a specific step (1-4), or omit for full guide"}}},
            ),
            Tool(
                name="hl_configure",
                description="Configure Hyperliquid connection. Reads from environment variables HYPERLIQUID_PRIVATE_KEY, HYPERLIQUID_TESTNET, etc.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "testnet": {"type": "boolean", "description": "Use testnet (default: false)", "default": False},
                    },
                },
            ),
            Tool(
                name="hl_get_connection_status",
                description="Check if Hyperliquid connection is working and show account status",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    async def handle(name: str, arguments: dict) -> list[TextContent]:
        if name == "hl_setup_guide":
            step = arguments.get("step")
            guide = _get_setup_guide(step)
            return [TextContent(type="text", text=guide)]

        elif name == "hl_configure":
            reset_shared_client()
            try:
                client = get_shared_client()
                mode = "TESTNET" if client.is_testnet else "MAINNET"
                user_state = client.get_user_state()
                acct_val = user_state["marginSummary"]["accountValue"]
                return [TextContent(type="text", text=json.dumps({
                    "status": "connected",
                    "mode": mode,
                    "address": client.address,
                    "accountValue": acct_val,
                }))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"status": "error", "error": str(e)}))]

        elif name == "hl_get_connection_status":
            try:
                client = get_shared_client()
                mode = "TESTNET" if client.is_testnet else "MAINNET"
                user_state = client.get_user_state()
                ms = user_state["marginSummary"]
                spot_state = client.get_spot_user_state()
                return [TextContent(type="text", text=json.dumps({
                    "status": "connected",
                    "mode": mode,
                    "address": client.address,
                    "perp": {
                        "accountValue": ms["accountValue"],
                        "totalMarginUsed": ms["totalMarginUsed"],
                        "withdrawable": user_state["withdrawable"],
                        "openPositions": len(user_state["assetPositions"]),
                    },
                    "spot": {
                        "balances": spot_state.get("balances", []),
                    },
                }))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({"status": "disconnected", "error": str(e)}))]

        raise ValueError(f"Unknown tool: {name}")

    return _tools, handle


def _get_setup_guide(step: int = None) -> str:
    steps = {
        1: """## Step 1: Create a Wallet
Create an Ethereum-compatible wallet (MetaMask, Rabby, etc.) and securely save your private key.
⚠️ NEVER share your private key with anyone.""",

        2: """## Step 2: Deposit Funds
**Mainnet**: Go to https://app.hyperliquid.xyz → Connect wallet → Deposit USDC from Arbitrum
**Testnet**: Go to https://app.hyperliquid-testnet.xyz → Use faucet to get test USDC""",

        3: """## Step 3: Configure Environment
Set these environment variables:
```
HYPERLIQUID_PRIVATE_KEY=0xYourPrivateKey
HYPERLIQUID_TESTNET=true   # Start with testnet!
```
Optional:
```
HYPERLIQUID_ACCOUNT_ADDRESS=0x...  # For agent/API wallet mode
HYPERLIQUID_VAULT_ADDRESS=0x...    # For vault trading
```""",

        4: """## Step 4: Verify Connection
Run `hl_configure` to test your connection. If successful, you'll see your account balance.
Start with testnet to practice, then switch to mainnet when ready.""",
    }

    if step and step in steps:
        return steps[step]

    return "# Hyperliquid Setup Guide\n\n" + "\n\n".join(
        f"### {v}" for v in steps.values()
    ) + "\n\n💡 Tip: Start with testnet (`HYPERLIQUID_TESTNET=true`) to practice risk-free!"
