# Alpaca Integration

## Responsibility split

- `alpaca-py` is the selected typed read gateway. The current implemented provider slice is news analysis; broader account, asset, stock, and option reads remain adapter work.
- Alpaca CLI v0.0.13 is the selected future order-submission adapter. The current skeleton does not submit orders.
- Alpaca MCP may be used by developers for read-only investigation with toolsets limited to `account`, `assets`, `stock-data`, `options-data`, and `news`. Trading tools are excluded and credentials are never committed.

No frontend or AI agent calls a trading surface directly.

## Paper account and options scope

Configuration must target Alpaca's paper endpoint. Live mode is a startup error. Execution is separately disabled by default.

Initial strategies are long calls, long puts, and two-leg call/put debit spreads. Single long options require Level 2; spreads require Level 3. Spread legs must use the same underlying and expiration, simplified 1:1 ratios, `order_class=mleg`, limit pricing, and `day` time-in-force. The system rejects uncovered shorts, credit spreads, equity-option combinations, inactive/non-tradable contracts, extended-hours options, exercise requests, and other strategies.

The BA rules require defined-risk debit spreads when IV Rank exceeds 50%. The future market adapter must source and validate the inputs needed for that rule; the current skeleton does not claim that computation is implemented.

For the BA-authorized hackathon window, official scoring uses total account equity at EOD Thursday Sep 3, 2026. New entries stop at Wednesday Sep 2, 2026 16:00 ET and all positions force-flatten by Thursday's close. The outer Friday Sep 4 09:30 ET boundary is not a scoring extension. A Sep-3-expiring contract must not be held into settlement; the 0-DTE block, DTE exit, and force-flatten are cumulative controls.


## Request discipline

Read requests use bounded timeouts and typed response validation. Retries are limited to transient failures and honor provider guidance; mutating requests are never blindly retried. Before execution, the service refreshes account/options-level state and contract tradability. Rate-limit responses create an explicit degraded condition rather than stale success.

The CLI receives an argument array and JSON through standard input; no shell-built command is permitted. Credentials are supplied only in the child-process environment. stdout/stderr are parsed and redacted before persistence or logging.

## Ambiguous submissions

The system persists the client order identifier and intent before invoking the CLI. On timeout, disconnect, or unparseable response, reconciliation looks up the order by `client_order_id`. Only a confirmed absence can transition the attempt for an operator-approved retry.

## Historical data caching and persistence

The repository interfaces reserve a cache-aside boundary for future market-data adapters. Persisted historical bars, quote snapshots, Redis warming, and deterministic replay storage are not implemented in this skeleton and must not be represented as live or provider-backed data. When those adapters are added, they must preserve immutable query digests, bounded provider requests, and reproducible replay fixtures without changing the paper-only execution boundary.


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
