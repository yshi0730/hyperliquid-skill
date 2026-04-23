# USER.md - How to Use This Agent

## What I Can Do

I'm your autonomous crypto trading AI on Hyperliquid — the fastest on-chain perpetual futures and spot exchange. I don't just advise; I research, build, execute, and monitor. Tell me what you want, and I make it happen.

### Core Capabilities

- **Autonomous Trading** — I execute trades, manage positions, and run strategies on your behalf within your configured guardrails (position limits, daily loss circuit breaker, asset whitelist). Manual trades get confirmation; authorized strategies run autonomously.
- **Spot Trading** — Buy and sell tokens directly on Hyperliquid spot market
- **Perpetual Futures** — Long/short with up to 50x leverage, bracket orders (entry + TP + SL), TWAP execution
- **Visual Dashboard** — Live portfolio dashboard with positions, PnL curves, funding rate heatmaps, and strategy performance charts
- **Market Research** — Real-time prices, candle charts, order book depth, funding rates, recent trades, open interest
- **Strategy Building** — Create custom strategies using templates (momentum, mean reversion, funding arbitrage, grid trading, DCA) and deploy them to run autonomously
- **Overnight Research** — While you sleep, I can scan for funding arbitrage opportunities, unusual volume, new token listings, and prepare a morning briefing
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

- "帮我建一个 funding 套利策略"
- "帮我建 dashboard"
- "每天早上给我出一份研究报告"
- "BTC 现在什么价？"
- "Show me ETH funding rate history"
- "做多 0.1 BTC，限价 $95,000，止盈 $100,000，止损 $92,000"
- "查看我的持仓和未实现盈亏"
- "现货买入 100 USDC 的 PURR"
- "Create a funding rate arbitrage strategy and run it"
- "Backtest my momentum strategy on SOL, last 6 months"
- "Set alert: notify me if ETH drops below $3,000"
- "这个月的交易表现怎么样？"
- "Review my trades this week"
- "扫描一下有没有好的套利机会"

## Requirements

- Python 3.10+
- An Ethereum wallet private key
- USDC on Arbitrum (for mainnet) or testnet faucet funds
- `hyperliquid-python-sdk` package (installed automatically)
