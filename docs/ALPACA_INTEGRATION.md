# Alpaca Integration

## Responsibility split

- `alpaca-py` is the typed read gateway for account verification, assets, stock/option market data, and news.
- Alpaca CLI v0.0.13 is the only order-submission adapter. It is invoked only after deterministic authorization.
- Alpaca MCP may be used by developers for read-only investigation with toolsets limited to `account`, `assets`, `stock-data`, `options-data`, and `news`. Trading tools are excluded and credentials are never committed.

No frontend or AI agent calls a trading surface directly.

## Paper account and options scope

Configuration must target Alpaca's paper endpoint. Live mode is a startup error. Execution is separately disabled by default.

Initial strategies are long calls, long puts, and two-leg call/put debit spreads. Single long options require Level 2; spreads require Level 3. Spread legs must use the same underlying and expiration, simplified 1:1 ratios, `order_class=mleg`, limit pricing, and `day` time-in-force. The system rejects uncovered shorts, credit spreads, equity-option combinations, inactive/non-tradable contracts, extended-hours options, exercise requests, and other strategies.

To prevent implied volatility crush on post-catalyst entries, the system computes **IV Rank** and **IV-to-HV ratios** from Alpaca option chain snapshots (`OptionHistoricalDataClient`). When IV Rank exceeds $50\%$, single-leg long options are blocked and the system enforces Level 3 Defined-Risk Debit Spreads.


## Request discipline

Read requests use bounded timeouts and typed response validation. Retries are limited to transient failures and honor provider guidance; mutating requests are never blindly retried. Before execution, the service refreshes account/options-level state and contract tradability. Rate-limit responses create an explicit degraded condition rather than stale success.

The CLI receives an argument array and JSON through standard input; no shell-built command is permitted. Credentials are supplied only in the child-process environment. stdout/stderr are parsed and redacted before persistence or logging.

## Ambiguous submissions

The system persists the client order identifier and intent before invoking the CLI. On timeout, disconnect, or unparseable response, reconciliation looks up the order by `client_order_id`. Only a confirmed absence can transition the attempt for an operator-approved retry.

## Historical data caching and persistence

To minimize latency, eliminate redundant Alpaca API calls, and protect against rate limits during backtesting and research analog discovery:

- **Historical Bars & Quotes Persistence:** Past market data (completed session bars and quote snapshots) is immutable. Responses fetched via `alpaca-py` are stored in PostgreSQL (`HistoricalMarketDataRecord`) indexed by a SHA-256 `query_digest`. Subsequent requests for identical time intervals hit the local database immediately.
- **Two-Tier Cache-Aside Architecture:** Fast in-memory / Redis cache (Tier 1) handles active intraday queries and warm lookups; PostgreSQL (Tier 2) serves as the persistent historical repository.
- **Deterministic Replays:** Saved historical records guarantee reproducible research calibration and predictable judging replay fixtures without network dependencies.


## Official-source workflow

Before implementing or changing Alpaca behavior, follow `.agents/rules/20-alpaca-documentation.md`: inspect `https://docs.alpaca.markets/llms.txt`, prefer the official Markdown pages and OpenAPI schemas, check the installed CLI's `--help`/`--schema`, review SDK release notes, and compare against locked versions. Useful starting points include:

- https://docs.alpaca.markets/us/docs/getting-started
- https://docs.alpaca.markets/us/docs/getting-started-with-trading-api
- https://docs.alpaca.markets/us/docs/getting-started-with-alpaca-market-data
- https://docs.alpaca.markets/us/docs/options-level-3-trading
- https://docs.alpaca.markets/us/docs/alpaca-mcp-server
- https://docs.alpaca.markets/us/docs/alpacas-cli
- https://docs.alpaca.markets/us/docs/paper-trading

## Version and provenance policy

Runtime SDKs, the CLI, and vendored Alpaca skills are pinned. The vendored skills are reference material; repository trading-safety rules remain authoritative. Upgrade changes require documentation review, contract/test updates, and paper-only verification.
