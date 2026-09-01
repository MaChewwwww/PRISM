# Agent decision monitoring contract

`StoryDetail.agentPerspectives` contains the seven canonical specialist perspectives. Each item identifies recorded, unavailable, or degraded evidence and, when recorded, contains a redacted headline, summary, evidence, limitations, UTC timestamp, provenance, and safe model metadata. `retrospective_reconstruction` rows carry source title/date/digest and a permanent reconstruction label; they are not live invocations.

# Data and API contracts

Revision: `2026-08-31 / deterministic-historical-options-v1`

Runtime models live in `backend/app/contracts` and `backend/app/presentation`. `backend/scripts/export_contracts.py` starts from `FastAPI.app.openapi()`, then merges exported domain schemas. Committed outputs are `backend/build/contracts.openapi.json` and `frontend/src/types/api.generated.ts`.

## Contract conventions

- Identifiers are stable UUID strings where domain identity requires them.
- Timestamps are timezone-aware UTC RFC3339 values.
- Financial, ratio, and percentage values cross trust boundaries as decimal strings.
- Enums are closed and typed; unknown members fail validation.
- Breaking shapes use a clean contract break; stale fixture aliases are not supported.
- Generated artifacts are regenerated, never edited by hand.
- Sensitive provider, account, credential, and raw error data is absent from presentation responses.

## Governance contracts

The BA registry is `backend/app/rules/authorized_baseline.v1.json`. Typed contracts cover ruleset identity, lifecycle, effective period, parameters, profile identity and compatibility, authorized profile ranges, rule priority, typed reason codes, rule traces, market regime, portfolio risk, and authorization bindings.

`ExitPolicy` requires a take-profit from 75% through 100%, a fixed 50% stop-loss, a DTE threshold from 2 through 14 days, and a holding limit from 3 through 45 days. The active Balanced defaults are 75% take-profit, 50% stop-loss, 7 DTE, and 14 days. The four-trading-day hackathon override is a separate active operating constraint.

The governance read model also exposes the registry-backed hackathon window as UTC timestamps: trading start, new-entry cutoff, official scoring point, force-flatten deadline, and outer boundary. `scoring_basis` is the closed value `total_account_equity`; the effective maximum hold is four trading days bounded by the scoring point.

Autonomous research persists immutable `option_iv_observations` with provider/source, UTC observation time, and decimal IV. The worker computes IV rank from that history (or a provider-supplied current rank), and records option-payoff EV fields including premium, NBBO slippage, fill probability, maximum loss, and reward/risk in the research bundle. Portfolio snapshots retain OCC-derived underlying, sector, correlated cluster, expiration, Delta, Vega, and quote-freshness metadata used by concentration rules; unknown or stale metadata fails closed.

## Decision semantics

| Scope | Values |
| --- | --- |
| Per-rule result | `PASS`, `MODIFY`, `FAIL` |
| Aggregate authorization | `APPROVE`, `REJECT`, `MODIFIED_PENDING_ACCEPTANCE` |

Only `APPROVE` may continue toward execution. `MODIFIED_PENDING_ACCEPTANCE` carries no authority. Accepting a modification creates a revised proposal and digest that must be authorized again.

## Endpoint catalog

| Method | Path | Purpose | Authentication |
| --- | --- | --- | --- |
| GET | `/api/v1/health/live` | Process liveness | No |
| GET | `/api/v1/health/ready` | Required configuration and database readiness | No |
| POST | `/api/v1/auth/login` | Seeded operator authentication; sets HTTP-only session cookie | No |
| GET | `/api/v1/auth/me` | Current operator session | Yes |
| POST | `/api/v1/auth/logout` | Clears session cookie | No |
| GET | `/api/v1/system/status` | Redacted operational state | Yes |
| GET | `/api/v1/autonomous/status` | Durable autonomous state and kill-switch audit metadata | Yes |
| POST | `/api/v1/autonomous/kill-switch` | Authenticated, audited kill-switch update | Yes |
| GET | `/api/v1/autonomous/cycles` | Bounded UTC-range autonomous worker outcomes | Yes |
| GET | `/api/v1/autonomous/decisions` | Bounded UTC-range proposal/risk/authorization summaries | Yes |
| GET | `/api/v1/autonomous/executions` | Bounded UTC-range sanitized paper execution receipts | Yes |
| GET | `/api/v1/autonomous/portfolio/latest` | Latest persisted normalized portfolio snapshot | Yes |
| POST | `/api/v1/research/news/analyze` | Non-authoritative structured news research | Yes |
| POST | `/api/v1/research/reaction/analyze` | Non-authoritative market-reaction and mispricing research | Yes |
| POST | `/api/v1/research/quant/analyze` | Deterministic quantitative technical analysis | Yes |
| POST | `/api/v1/research/fundamental/analyze` | Sourced fundamental analysis; illustrative fixtures are rejected | Yes |
| POST | `/api/v1/research/industry/analyze` | Structured industry/peer research | Yes |
| POST | `/api/v1/research/macro/analyze` | Structured macroeconomic research | Yes |
| POST | `/api/v1/research/decision/synthesize` | Seven-agent synthesis; autonomous use requires a canonical proposal pipeline | Yes |
| GET | `/api/v1/monitoring/overview` | Recorded overview projection | Yes |
| GET | `/api/v1/monitoring/decisions` | Recorded decision collection | Yes |
| GET | `/api/v1/monitoring/decisions/{proposal_id}` | Decision trace and operational evidence | Yes |
| GET | `/api/v1/monitoring/portfolio` | Recorded portfolio and exit-check freshness | Yes |
| GET | `/api/v1/monitoring/alternatives` | ShadowFund alternative collection | Yes |
| GET | `/api/v1/monitoring/alternatives/{session_id}` | ShadowFund alternative detail | Yes |
| GET | `/api/v1/presentation/alternatives` | Documented compatibility projection of recorded ShadowFund alternatives | Yes |
| GET | `/api/v1/monitoring/news` | Recorded news-analysis collection | Yes |
| GET | `/api/v1/monitoring/agents` | Recorded model-usage projection | Yes |
| GET | `/api/v1/monitoring/agents/{agent_id}` | Recorded model-operation detail | Yes |
| GET | `/api/v1/monitoring/governance` | Read-only active ruleset and profile | Yes |
| GET | `/api/v1/monitoring/weekly-summary` | Read-only post-analysis projection | Yes |
| GET | `/api/v1/profiles/governance` | Active persisted profile and authenticated operator calibration preference | Yes |
| PUT | `/api/v1/profiles/calibration-preference` | Select manual or automatic calibration preference | Yes |
| POST | `/api/v1/profiles/activate-post-analysis` | Manually activate a complete, validated Post-Analysis batch | Yes |
| GET | `/api/v1/llm-usage/summary` | UTC-range-bounded aggregated provider-reported LLM tokens and optional estimated cost | Yes |
| GET | `/api/v1/market-tracker` | **Planned, deferred** normalized bars, watchlist, and activity markers | Yes |
| GET | `/openapi.json` | OpenAPI paths and schemas | No |

Collection endpoints require `from` and `to` query parameters. Both must be timezone-aware UTC timestamps, and `from` must not be later than `to`.

## Autonomous operational read models

The authenticated autonomous read endpoints are polling-oriented projections of
existing durable records. They never instantiate the worker, refresh Alpaca
data, or invoke an execution adapter. `cycles`, `decisions`, and `executions`
require a bounded UTC range and accept a maximum `limit` of 200; decisions may
filter by symbol and authorization outcome, and executions by receipt status.

`portfolio/latest` projects the newest persisted worker snapshot or returns an
explicit empty state before the first successful account snapshot. Its values
are normalized decimal strings. The endpoints omit broker and client order IDs,
account identifiers, raw provider payloads, raw broker messages, credentials,
and hidden reasoning. Execution receipts have an `operation` of `entry` or
`exit`; position-level exits have a normalized `symbol`, an explicit `exit_reason`
(`pnl_threshold`, `max_hold_days`, `dte_threshold`, or
`hackathon_force_flatten`), and may have no `proposal_id`. A close request is
reported as `submitted` until broker response or position reconciliation proves
the close, so the API never infers a fill from a delete request alone. Cycle
reads expose sanitized `exit_checks` so the triggering predicate remains visible
without exposing provider payloads. Recorded ShadowFund alternatives remain
available through the documented `/presentation/alternatives` compatibility
projection and the `/monitoring/alternatives` read model. Both retain their
existing provenance labels and non-executable semantics.

Deterministic P2 and P4 rule traces emit reason codes from the predicates that
actually failed. For example, a positive EV below the authorized floor is
`EXPECTED_VALUE_BELOW_FLOOR`, while a negative EV is
`NEGATIVE_EXPECTED_VALUE`; the trace does not include unrelated possible causes.

## Presentation metadata and provenance

Every presentation response includes metadata with:

- `generated_at`;
- `as_of`;
- requested UTC `from` and `to` calendar-date range derived from the validated timestamps;
- `data_mode`;
- `fixture_version`.

Monitoring returns `data_mode=recorded` for durable production roots and `data_mode=simulated` for ShadowFund historical simulation. There is no illustrative fixture fallback. No response implies an Alpaca account request, paper order, fill, holding, P&L record, or provider/model invocation beyond its explicit recorded provenance.

## Planned Market Tracker contract (not implemented)

The future authenticated `GET /api/v1/market-tracker` accepts `symbol`, validated UTC `from` and `to`, `timeframe` (`1Min`, `5Min`, `15Min`, `1Hour`, or `1Day`), selected activity kinds, and `traded_only`. Its response will define `MarketTrackerResponse`, `MarketBar`, `MarketWatchlistItem`, and `MarketActivityMarker` types plus capability/freshness metadata. Bars contain UTC timestamps, OHLCV, trade count, and optional VWAP. Watchlist items contain normalized snapshot values, change, and verified-trade state. Activity markers retain event kind, instrument, status, identifiers, optional decimal price/quantity, and provenance; option markers chart the underlying while retaining contract, expiration, strike, side, and leg details.

All future prices, quantities, percentages, and Greeks remain decimal strings. The standard metadata envelope will include `generated_at`, `as_of`, the requested UTC range, `data_mode`, provider/fixture source, and freshness. The endpoint is deliberately not in generated OpenAPI or frontend transport types in this skeleton. Empty and degraded responses must be explicit and must never fabricate market or account data.

## News-analysis endpoint

The implemented news endpoint is non-authoritative research. It uses authenticated access, structured response validation, cached analysis records, classified transient retries in a worker thread, and redacted provider errors. Retries never block the event loop and never turn an AI result into execution authority.

## Market-reaction endpoint

`POST /api/v1/research/reaction/analyze` retrieves a bounded historical stock-bar window through the server-side Alpaca read adapter, computes deterministic reaction metrics, and asks the provider-neutral LLM gateway for a structured thesis and limitations. The response is a `ResearchReport` with decimal-safe actual/expected reaction, reaction gap, volume ratio, classification, and opportunity-score fields. It is non-authoritative and cannot authorize or submit an order. Research-report caching uses the Alembic-managed `research_reports` table and remains best-effort.

## Quantitative endpoint

`POST /api/v1/research/quant/analyze` accepts an authenticated `symbol` and bounded `bar_limit` from 20 through 500 (default 250). It retrieves normalized historical bars through the server-side Alpaca gateway and returns a deterministic `QuantitativeAnalysisReport` containing RSI (14), MACD (12, 26, 9), SMA (20, 50, 200), Bollinger Bands (20, 2), ATR (14), annualized volatility, volume surge ratio, and a 0-100 momentum score with trend classification. Decimal values serialize as strings. This report is research evidence only: it is not a `TradeProposal`, authorization, execution instruction, or provider/account assertion. Provider failures use a stable redacted error response.

## Error and authorization boundaries

Errors expose stable, safe machine codes and redacted summaries. Provider response bodies, credentials, account details, and raw exception strings are not returned. Authorization binds proposal and payload digests, ruleset/profile versions, snapshot digests, rule trace, decision time, and allowed payload.

## Generation workflow

Contract generation derives the FastAPI control-plane paths and the domain schemas before emitting committed OpenAPI and TypeScript artifacts.

## Profile calibration control plane

`/profiles/governance` returns the active profile ID/version and bounded decimal parameters alongside the authenticated operator preference. `PUT /profiles/calibration-preference` persists `manual` or `automatic`; it does not itself activate a profile. `POST /profiles/activate-post-analysis` accepts only a draft batch UUID with one or more uniquely named authorized recommendations already within the registry bounds; unspecified fields retain their active values. The server rejects duplicated or out-of-bounds batches. Automatic activation follows the persisted operator preference. Every activation creates a successor profile and immutable audit event, while existing authorization records remain bound to the profile version they used.

For `/presentation/alternatives`, production now projects persisted ShadowFund sessions with `data_mode=recorded`. Staging projects only the active completed backtest run with `data_mode=simulated` and `Historical simulation` provenance. The collection and detail expose evaluation-root digest, ruleset/profile and valuation-policy versions, terminal outcome, branch gross/net P&L, delta, MAE/MFE, drawdown, duration, capital at risk, allocation multiplier, confidence, coverage, and refusal reasons. No completed staging run returns a valid explicit empty collection, never an illustrative fixture.

Historical-options sessions add `branch_key` (the stable semantic key alongside the UUID) and optional simulated-fill metadata: fill status, quantity, UTC entry/exit timestamps, net touch prices, spread-derived slippage, exit reason, cost model, and per-leg prices. Staging sessions also expose the analogue window and five-minute cadence. These fields are additive; the `/presentation/portfolio` contract remains the separate Active Portfolio/illustrative surface.

The staging backtest uses a provider-neutral historical-options port requiring timestamped bid/ask observations. Missing contracts, quotes, or feed entitlement produce `DATA_UNAVAILABLE` / inactive runs; OHLC or midpoint substitutes are not valid evidence. All monetary values remain decimal strings at this boundary.

Run `pnpm contracts` after contract changes. CI runs `pnpm contracts:check`; any generated diff fails the check. Repository governance checks compare the presentation catalog with OpenAPI paths and verify registry/document consistency.
