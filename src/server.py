#!/usr/bin/env python3
"""Hyperliquid Trading MCP Server — stdio transport."""

from __future__ import annotations

import asyncio
import json
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools.setup import register_setup_tools
from .tools.account import register_account_tools
from .tools.market_data import register_market_data_tools
from .tools.trading import register_trading_tools
from .tools.spot import register_spot_tools
from .tools.strategy import register_strategy_tools
from .tools.monitor import register_monitor_tools
from .tools.backtest import register_backtest_tools
from .tools.analytics import register_analytics_tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def create_server() -> Server:
    server = Server("hyperliquid-skill")

    # Collect tools and handlers from all modules
    modules = [
        register_setup_tools(server),
        register_account_tools(server),
        register_market_data_tools(server),
        register_trading_tools(server),
        register_spot_tools(server),
        register_strategy_tools(server),
        register_monitor_tools(server),
        register_backtest_tools(server),
        register_analytics_tools(server),
    ]

    all_tool_fns = [m[0] for m in modules]
    all_handlers = {m: m[1] for m in modules}  # not used directly, we build a dispatch

    # Build dispatch table: tool_name -> handler
    dispatch: dict[str, callable] = {}
    all_tools: list[Tool] = []
    for tools_fn, handler_fn in modules:
        tools = tools_fn()
        all_tools.extend(tools)
        for t in tools:
            dispatch[t.name] = handler_fn

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return all_tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        handler = dispatch.get(name)
        if not handler:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
        try:
            return await handler(name, arguments)
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return [TextContent(type="text", text=json.dumps({"error": str(e), "tool": name}))]

    return server


async def amain() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Hyperliquid MCP Server started")
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
