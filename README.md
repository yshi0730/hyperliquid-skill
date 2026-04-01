# Hyperliquid Trading Skill

Professional crypto spot & perpetual futures trading skill for OpenClaw, powered by [Hyperliquid](https://hyperliquid.xyz).

## Features

- **Spot Trading** — Buy/sell tokens on Hyperliquid spot market
- **Perpetual Futures** — Long/short with up to 50x leverage
- **Bracket Orders** — Entry + take-profit + stop-loss in one atomic batch
- **Market Data** — Real-time prices, candles, order book, funding rates, recent trades
- **Strategy Templates** — Momentum, mean reversion, funding arbitrage, grid, DCA
- **Backtesting** — Test strategies against historical data with Sharpe, max drawdown, win rate
- **Monitoring** — Price alerts, liquidation proximity warnings
- **Trade Journal** — Track and review all trades with notes
- **Vault Management** — Query vault details and performance
- **Spot/Perp Transfer** — Move USDC between accounts

## Prerequisites

1. Ethereum wallet with private key
2. USDC on Arbitrum (mainnet) or testnet faucet funds
3. Python 3.10+

## Setup

```bash
pip install -e .
```

## Usage

```bash
# Start MCP server (stdio transport)
hyperliquid-skill

# Or run directly
python -m src.server
```

## Configuration

Set environment variables:

```bash
export HYPERLIQUID_PRIVATE_KEY=0xYourPrivateKey
export HYPERLIQUID_TESTNET=true   # Start with testnet!

# Optional
export HYPERLIQUID_ACCOUNT_ADDRESS=0x...  # Agent/API wallet mode
export HYPERLIQUID_VAULT_ADDRESS=0x...    # Vault trading
```
