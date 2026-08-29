# PRISM Market Tracker

Revision: `2026-08-29 / market-tracker-skeleton-v1`

## Purpose and current scope

Market Tracker is a discoverable `Inspect -> Market Tracker` workspace for reading a future price/time market chart alongside PRISM activity. The interaction model is inspired by a TradingView-style workspace: a chart viewport, symbol watchlist, timeframe controls, and independently filterable activity overlays. “Interactive map” means an interactive price/time chart, not a geographic map.

The current route is a frontend skeleton at `/market-tracker`. It uses the shared authenticated workspace shell and UTC `range`, `from`, and `to` URL parameters. It makes no backend or provider request, renders no fake symbols or market values, and makes no account, position, order, fill, Alpaca, paper-trading, or provider claim. The empty/deferred state is intentional and remains visible until the future server contract is authorized.

## Interaction model

- The future chart defaults to `1Day`; `1Min`, `5Min`, `15Min`, and `1Hour` are also reserved.
- All activity categories start selected. Each filter and the Select all/Clear all actions are keyboard-accessible and only change local presentation state in this skeleton.
- The future watchlist is populated from server-normalized snapshots. No placeholder symbol, quote, price, position, or fill is rendered now.
- “Symbols with verified trades only” is a future filter. A symbol qualifies only when confirmed `fill` activity exists; proposals, NO_TRADE decisions, and ShadowFund events never qualify.
- The chart will render its own candlestick and volume layers. Alpaca provides data APIs, not a TradingView-style frontend widget.

## Activity taxonomy and provenance

| Kind | Meaning | Actual trade? |
| --- | --- | --- |
| `fill` | Confirmed Alpaca paper fill/activity | Yes |
| `order` | Paper order lifecycle | No |
| `proposal` | PRISM Trading Decision proposal | No |
| `decision` | Authorized or rejected PRISM decision event | No |
| `no_trade` | Terminal PRISM no-action decision | No |
| `shadow` | ShadowFund simulated branch event | No |

Options chart on the underlying symbol while preserving contract symbol, expiration, strike, side, and strategy/leg details in event detail. Provenance labels must remain truthful: Alpaca paper, ShadowFund, Benchmark, and Simulated are reserved for matching sources.

## Planned API boundary (deferred)

The future authenticated endpoint is `GET /api/v1/market-tracker` with `symbol`, validated UTC `from`/`to`, `timeframe`, selected activity filters, and `traded_only`. It is not implemented and is intentionally absent from the current generated OpenAPI and frontend transport types.

Planned normalized types are `MarketTrackerResponse`, `MarketBar` (UTC timestamp, OHLCV, volume, trade count, optional VWAP), `MarketWatchlistItem` (symbol, latest snapshot values, change, verified-trade state), and `MarketActivityMarker` (kind, timestamp, symbol/instrument, status, optional decimal price/quantity, trace/order/proposal/decision identifiers, provenance). Capability/freshness metadata will describe historical, snapshot, streaming, and account-activity availability. Prices, quantities, percentages, and Greeks remain decimal strings. The standard PRISM metadata envelope includes `generated_at`, `as_of`, requested range, data mode, provider/fixture source, and freshness.

## Future data flow and Alpaca semantics

```text
Browser
  -> authenticated Next.js server adapter
  -> FastAPI market-tracker endpoint
  -> server-only Alpaca adapter + persisted PRISM repositories
```

Historical REST bars are the first integration milestone, using bounded `/v2/stocks/bars` requests, validated timeframes, pagination, normalized query digests, and entitlement-aware feed selection. Watchlist snapshots use `/v2/stocks/snapshots`. Later, a server-owned `StockDataStream` can normalize trades, quotes, and bars; paper order activity may use `/v2/orders`, open positions `/v2/positions`, confirmed fills `/v2/account/activities`, and optional `trade_updates`. Feed availability and freshness depend on subscription entitlement, so the server exposes capability/degraded state instead of guessing.

The pinned SDK remains `alpaca-py==0.44.0`. No JavaScript Alpaca SDK, browser stream, or direct frontend provider integration is planned. No Alpaca call, order, stream subscription, or provider integration occurs in this skeleton.

## Privacy, safety, and deferred stages

The browser forwards only the authenticated session to the server adapter. Alpaca and LLM credentials remain server-only. Confirmed fills are the only execution evidence; research, proposals, decisions, NO_TRADE, and ShadowFund events remain visually distinct. Execution remains paper-only, disabled by default, and deterministic authorization still governs any future path.

Deferred stages are: historical REST adapter and normalized contract; snapshot/watchlist adapter; server-owned streaming; persisted activity reconciliation; capability/freshness caching; and chart-level event detail. Each stage must add authenticated contract tests, UTC validation, provenance checks, redacted failures, and explicit empty/degraded states before activation.

## Official sources

Official Alpaca US documentation was reviewed on `2026-08-29`: [market data overview](https://docs.alpaca.markets/us/docs/about-market-data-api.md), [historical stock bars](https://docs.alpaca.markets/us/reference/stockbars), [multi-symbol snapshots](https://docs.alpaca.markets/us/reference/stocksnapshots-1), [real-time stock pricing](https://docs.alpaca.markets/us/docs/real-time-stock-pricing-data.md), [open positions](https://docs.alpaca.markets/us/reference/getallopenpositions), [orders](https://docs.alpaca.markets/us/reference/getallorders-1), [account activities](https://docs.alpaca.markets/us/reference/getaccountactivities-2), and [working with orders](https://docs.alpaca.markets/us/docs/working-with-orders).
