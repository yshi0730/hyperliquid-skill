# USER.md - How to Use This Agent

## What I Can Do

I'm your personal crypto trading advisor on Hyperliquid — the fastest on-chain perpetual futures and spot exchange. I handle everything from market research to live order execution.

### Core Capabilities

- **Spot Trading** — Buy and sell tokens directly on Hyperliquid spot market
- **Perpetual Futures** — Long/short with up to 50x leverage, bracket orders (entry + TP + SL), TWAP execution
- **Market Research** — Real-time prices, candle charts, order book depth, funding rates, recent trades, open interest
- **Strategy Building** — Create custom strategies using templates (momentum, mean reversion, funding arbitrage, grid trading, DCA)
- **Backtesting** — Test strategies against historical data with performance metrics (Sharpe, max drawdown, win rate)
- **Monitoring** — Price alerts, liquidation proximity warnings, funding rate alerts
- **Portfolio Review** — Performance reports, trade journal, review sessions with actionable insights
- **Vault Management** — Query vault details and performance

## Getting Started

1. **Get a wallet** — You need an Ethereum-compatible wallet with a private key
2. **Register on Hyperliquid** — Go to https://app.hyperliquid.xyz, connect wallet, deposit USDC from Arbitrum
3. **First time?** Just say hi — I'll walk you through configuration
4. **Start with testnet** — I strongly recommend practicing on testnet first (https://app.hyperliquid-testnet.xyz)

## Example Interactions

- "BTC 现在什么价？"
- "Show me ETH funding rate history"
- "做多 0.1 BTC，限价 $95,000，止盈 $100,000，止损 $92,000"
- "查看我的持仓和未实现盈亏"
- "现货买入 100 USDC 的 PURR"
- "Create a funding rate arbitrage strategy"
- "Backtest my momentum strategy on SOL, last 6 months"
- "Set alert: notify me if ETH drops below $3,000"
- "这个月的交易表现怎么样？"
- "Review my trades this week"

## Requirements

- Python 3.10+
- An Ethereum wallet private key
- USDC on Arbitrum (for mainnet) or testnet faucet funds
- `hyperliquid-python-sdk` package (installed automatically)
