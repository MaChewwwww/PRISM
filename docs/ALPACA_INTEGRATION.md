# Alpaca Integration

## Responsibility split

- `alpaca-py` is the selected typed read gateway. Implemented reads include authenticated news, historical stock bars (the gateway explicitly requests the IEX feed so a paper-only/Basic account is supported), active option contracts, option-chain quotes, and Greeks; autonomous authorization still requires fresh snapshots and entitlement checks.
- Alpaca CLI v0.0.13 is the selected order-submission adapter. Translation, durable receipts, and reconciliation are implemented; readiness keeps the worker at `NO_TRADE` until CLI `version`, `--help`, `--schema`, and `--dry-run` checks pass in the built container.
- Alpaca MCP may be used by developers for read-only investigation with toolsets limited to `account`, `assets`, `stock-data`, `options-data`, and `news`. Trading tools are excluded and credentials are never committed.

No frontend or AI agent calls a trading surface directly.

## Paper account and options scope

Configuration must target Alpaca's paper endpoint. Live mode is a startup error. Execution is separately disabled by default.

Initial strategies are long calls, long puts, and two-leg call/put debit spreads. Single long options require Level 2; spreads require Level 3. Spread legs must use the same underlying and expiration, simplified 1:1 ratios, `order_class=mleg`, limit pricing, and `day` time-in-force. The system rejects uncovered shorts, credit spreads, equity-option combinations, inactive/non-tradable contracts, extended-hours options, exercise requests, and other strategies.

The BA rules require defined-risk debit spreads when IV Rank exceeds 50%. Alpaca's chain supplies current IV/Greeks but not an IV-rank time series. PRISM therefore accepts a declared server-side historical IV provider (`IV_RANK_HISTORY_URL`) or derives historical IV observations from Alpaca option/underlying bars with an explicit Decimal Black-Scholes inversion; all observations are immutable and timestamped. The deterministic percentile calculation rejects insufficient or unsourced history and never substitutes a realized-volatility proxy.

The Quantitative Agent retrieves normalized historical stock bars through `AlpacaPyGateway`, then computes deterministic RSI, MACD, moving averages, Bollinger Bands, ATR, annualized volatility, volume surge, and momentum. `POST /api/v1/research/quant/analyze` is authenticated and research-only; it cannot authorize or submit an order. Provider errors are logged by exception class and returned as a redacted temporary-unavailability response.

For the BA-authorized hackathon window, official scoring uses total account equity at EOD Thursday Sep 3, 2026. New entries stop at Wednesday Sep 2, 2026 16:00 ET and all positions force-flatten by Thursday's close. The outer Friday Sep 4 09:30 ET boundary is not a scoring extension. A Sep-3-expiring contract must not be held into settlement; the 0-DTE block, DTE exit, and force-flatten are cumulative controls.


## Request discipline

Read requests use bounded timeouts and typed response validation. Retries are limited to transient failures and honor provider guidance; mutating requests are never blindly retried. Before execution, the service refreshes account/options-level state and contract tradability. Rate-limit responses create an explicit degraded condition rather than stale success.

For live autonomous research, the gateway retrieves an IEX latest stock trade separately from historical daily bars. The latest trade's price and UTC timestamp are the bounded live-market observation used for the BA-authorized freshness check at the start of a cycle; daily bars remain historical evidence for technical/reaction/analogue calculations and cannot satisfy that gate. The worker still refreshes execution-critical option quotes before deterministic authorization. An unavailable or stale latest trade produces a no-trade result before specialist LLM calls. This behavior was verified against Alpaca's [latest stock trade](https://docs.alpaca.markets/us/reference/stocklatesttrades-1) and [latest stock bar](https://docs.alpaca.markets/us/reference/stocklatestbars-1) references on 2026-08-31.

The CLI receives an argument array and JSON through standard input; no shell-built command is permitted. Credentials are supplied only in the child-process environment. stdout/stderr are parsed and redacted before persistence or logging.

## Local paper-account monitor

`scripts/monitor_paper_account.py` is an operator-only, read-only diagnostic. It loads the ignored local `.env.production` explicitly, then reuses the application `Settings` validation and typed `AlpacaPyGateway` to call only `get_account()` and `get_all_positions()`. It does not import an execution adapter, run an autonomous cycle, mutate PRISM state, or submit/cancel an order. Account numbers and IDs remain redacted in output.

Run it from the repository root with the locked backend environment:

```powershell
uv run --project backend python scripts/monitor_paper_account.py
```

The underlying paper endpoints are Alpaca's [`GET /v2/account`](https://docs.alpaca.markets/us/reference/getaccount-1) and [`GET /v2/positions`](https://docs.alpaca.markets/us/reference/getallopenpositions). Their schemas and the pinned `alpaca-py` 0.44.0 release were reviewed on 2026-08-31.

## Ambiguous submissions

The system persists the client order identifier and intent before invoking the CLI. On timeout, disconnect, or unparseable response, reconciliation looks up the order by `client_order_id`. Only a confirmed absence can transition the attempt for an operator-approved retry.

## Historical data caching and persistence

The repository interfaces reserve a cache-aside boundary for future market-data adapters. Decision/proposal, risk, portfolio, authorization, execution-receipt, reconciliation, autonomous-cycle, and option-IV-observation roots are Alembic-managed. The staging backtest uses a separate provider-neutral historical-options adapter for contract metadata and timestamped NBBO. Persisted option payloads are run artifacts and ShadowFund observations, not account or execution records. The market-reaction report cache remains research output. The adapter preserves immutable query digests, bounded provider requests, and reproducible replay fixtures without changing the paper-only execution boundary. Alpaca historical bars/trades and latest snapshots do not satisfy the historical NBBO requirement by themselves; an entitled provider feed is required and missing coverage fails closed.

Autonomous paper execution is controlled by server-only `AUTONOMOUS_TRADING_ENABLED`, `AUTONOMOUS_TRADING_START_AT`, and `AUTONOMOUS_TRADING_END_AT` settings. The shared worker runs in production only when explicitly enabled, uses an advisory lock and durable kill switch, and records `NO_TRADE` until all deterministic authorization prerequisites pass. Production intervals are bounded by the BA registry's hackathon start and force-flatten timestamps. Staging uses the separate `app.backtest.run` command: its point-in-time gateway supplies historical bars/news and SEC filings available at each checkpoint to the same Agents 1-7 and configured LLM. It is non-executing, never imports the worker or paper-order adapter, and fails closed on unavailable historical data or entitlement.

ShadowFund uses only read-only market observations. Its historical adapter may discover inactive contracts only for past expiries and must bind the entitled feed, provider timestamps, and payload digests to each observation. Alpaca documents historical options from February 2024; Basic-plan option access is indicative and restricted to recent data, so historical quote/contract/IV gaps are recorded as `DATA_UNAVAILABLE` / `NO_TRADE`, never virtual fills. Sources retrieved 2026-08-31: [Historical API](https://docs.alpaca.markets/us/docs/historical-api), [Historical Option Data](https://docs.alpaca.markets/us/docs/historical-option-data), and [Market Data API plans](https://docs.alpaca.markets/us/docs/about-market-data-api).

The autonomous research path reads timestamped SEC companyfacts records for fundamentals, Alpaca stock bars/news for the six specialist inputs, and active option contracts plus complete, fresh option-chain quotes/Greeks for selection. A missing SEC record, stale or incomplete quote, unavailable provider, closed broker clock, unavailable portfolio/regime state, insufficient IV history, or fewer than thirty comparable five-year events is a deterministic `NO_TRADE`; no illustrative registry value is eligible for paper authorization. Historical analog returns are revalued through the selected option legs at intrinsic exit value, with observed premium, NBBO slippage, and spread-derived fill probability included in net EV and reward/risk.


## Official-source workflow

Before implementing or changing Alpaca behavior, follow `.agents/rules/20-alpaca-documentation.md`: inspect `https://docs.alpaca.markets/us/llms.txt`, prefer official US Markdown pages and OpenAPI schemas, check the installed CLI's `--help` and `--schema`, review SDK release notes, and compare against locked versions. Record retrieval dates when the verified behavior affects safety, contracts, or compatibility. Useful starting points include:

- https://docs.alpaca.markets/us/docs/getting-started
- https://docs.alpaca.markets/us/docs/getting-started-with-trading-api
- https://docs.alpaca.markets/us/docs/getting-started-with-alpaca-market-data
- https://docs.alpaca.markets/us/docs/options-level-3-trading
- https://docs.alpaca.markets/us/docs/alpaca-mcp-server
- https://docs.alpaca.markets/us/docs/alpacas-cli
- https://docs.alpaca.markets/us/docs/paper-trading

## Version and provenance policy

Runtime SDKs, the CLI, and vendored Alpaca skills are pinned. The vendored skills are reference material; repository trading-safety rules remain authoritative. Upgrade changes require documentation review, contract/test updates, and paper-only verification.

## Market Tracker integration design (deferred)

Verified against official Alpaca US documentation on `2026-08-29`. The future server-only adapter will use:

- historical `/v2/stocks/bars` for bounded, paginated chart windows and validated timeframes: [historical stock bars](https://docs.alpaca.markets/us/reference/stockbars);
- `/v2/stocks/snapshots` for selected watchlist symbols: [multi-symbol snapshots](https://docs.alpaca.markets/us/reference/stocksnapshots-1);
- `StockDataStream` trades, quotes, and bars for later server-owned live updates: [real-time stock pricing data](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data.md);
- `/v2/positions` for genuine open paper positions: [open positions](https://docs.alpaca.markets/us/reference/getallopenpositions);
- `/v2/orders` for paper order lifecycle records: [orders](https://docs.alpaca.markets/us/reference/getallorders-1);
- `/v2/account/activities` filtered to `FILL` and partial-fill trade activity for confirmed fills: [account activities](https://docs.alpaca.markets/us/reference/getaccountactivities-2);
- optional `trade_updates` for later account/order streaming: [working with orders](https://docs.alpaca.markets/us/docs/working-with-orders).

The market-data API supports HTTP and WebSocket delivery: [market data overview](https://docs.alpaca.markets/us/docs/about-market-data-api.md). Feed entitlement, symbol limits, historical lookback, and freshness vary by subscription; the server selects an authorized feed and exposes capability/freshness metadata. The browser receives normalized server events only and never receives Alpaca credentials. Historical REST loading is the first milestone; streams, persistence, reconciliation, and cache warming are deferred. No Alpaca call is made by the current Market Tracker skeleton.

Paper-only credentials are a separate key pair from any live account and must be used with the paper trading endpoint. Alpaca's Basic paper entitlement provides IEX equity data and the indicative options feed; a request for recent SIP equity data returns `403 subscription does not permit querying recent SIP data`, while `401` means the authentication headers are missing or invalid. These are credential/entitlement responses, not market-hours responses. The current worker remains paper-only and fails closed when the available feed cannot satisfy its freshness and options requirements.
