# PRISM architecture

Revision: `2026-08-30 / autonomous-paper-parity-v4`

PRISM is a paper-only, auditable decision platform. It separates specialist AI analysis from deterministic authorization and broker execution. The repository includes authenticated specialist research routes, persisted research tables, strict provenance/freshness gates, SEC companyfacts sourcing, option-chain/contract adapters, deterministic P0-P5 authorization, authenticated durable autonomous controls, durable receipts/reconciliation, and a generated frontend transport contract. The same autonomous worker runs in staging and production; separate paper credentials select the account.

## Authority and dependency direction

```text
repository invariants
  -> BA process and versioned numerical register
  -> AI topology and responsibilities
  -> API contracts
  -> implementation and tests
  -> explanatory concept documents
```

Within the backend:

```text
API and schedulers -> application services -> domain rules and ports -> adapters
```

Domain contracts and deterministic policies do not import FastAPI, Alpaca, LLM clients, or frontend code.

## Canonical decision topology

The seven specialist stages are canonical and ordered:

1. News Agent
2. Quantitative Agent
3. Industry Agent
4. Fundamental Agent
5. Macroeconomic Agent
6. Market Reaction/Mispricing Agent
7. Trading Decision Agent

Their outputs then pass through:

8. AI-assisted Risk Management
9. Deterministic Rules Engine
10. Paper Execution, only after a valid `APPROVE`
11. ShadowFund counterfactual evaluation
12. Asynchronous Post-Analysis recommendations

The specialists may run independent evidence work where dependencies allow, but the Market Reaction/Mispricing and Trading Decision stages synthesize validated inputs. No AI stage owns execution authority.

```text
signal and market snapshot
  -> seven specialist perspectives
  -> TradeProposal or NO_TRADE
  -> AI-assisted risk critique
  -> deterministic rule trace
  -> APPROVE | REJECT | MODIFIED_PENDING_ACCEPTANCE
  -> paper execution only for APPROVE
  -> ShadowFund evaluation
  -> asynchronous Post-Analysis recommendation
```

Per-rule results are `PASS`, `MODIFY`, or `FAIL`. A modification never authorizes execution. Operator acceptance creates a revised proposal, new digest, and new authorization evaluation.

## System context

```text
Operator browser
  -> Next.js server and authenticated session forwarding
  -> FastAPI modular monolith
       -> PostgreSQL through an Alembic-managed schema
       -> optional Redis cache
       -> Alpaca data adapter through alpaca-py, future broader integration
       -> gated Alpaca paper execution adapter
       -> provider-neutral LLM adapter
```

The frontend receives neither Alpaca nor LLM credentials and never calls Alpaca directly.

## Backend boundaries

| Boundary | Responsibility | Current state |
| --- | --- | --- |
| `contracts` | Typed proposal, risk, governance, authorization, execution, profile, and audit records | Implemented skeleton |
| `rules` | Versioned BA registry and deterministic policy boundary | Registry, P0-P5 evaluator, Balanced threshold 84, and typed traces implemented |
| `research` | Provider-normalized evidence and structured research | Seven specialist workflows, SEC-sourced fundamentals, historical analog option-payoff EV, IV-rank history, and strict freshness/provenance gates |
| `presentation` | Backend-owned illustrative read models | Implemented with versioned fixture adapter |
| `proposal` | Trading Decision proposal synthesis | Canonical digest-bound proposals persisted by the autonomous worker; the public research endpoint remains `NO_TRADE` without complete binding |
| `risk` | AI-assisted adversarial critique | Structured RiskAssessment persisted before deterministic authorization |
| `market` | Alpaca market/news adapter | Account/portfolio, stock bars, active contracts, fresh chain quotes/Greeks, and news |
| `portfolio` | Durable snapshots and exposure calculations | OCC/chain-enriched account snapshots persisted per cycle with six-position, cash, ticker/sector/cluster, Greek, and expiry concentration gates |
| `execution` | Final paper checks, translation, idempotency, reconciliation | Durable PostgreSQL receipts, client-order idempotency, restart reconciliation, and paper-only CLI submission |
| `shadowfund` | Immutable counterfactual branches and evaluation | Non-executable evaluation roots and shadow candidates implemented; valuation/fill ingestion deferred |
| `audit` | Append-oriented decision and execution events | Alembic audit-root tables and cycle emissions implemented; full event projector deferred |

## Research slices

The current research boundary exposes authenticated, non-authoritative slices for News, Market Reaction/Mispricing, and the Quantitative Agent. Quantitative analysis is deterministic and consumes normalized historical bars to calculate RSI, MACD, SMA, Bollinger Bands, ATR, annualized volatility, volume surge, and a bounded momentum score. It returns a `QuantitativeAnalysisReport` and cannot authorize or submit an order. Provider reads remain server-side, bounded, retried only for transient failures, and surfaced through redacted errors.

## Presentation skeleton

All frontend story surfaces load through one server-side adapter typed from generated OpenAPI. Authenticated backend presentation endpoints expose fixed `illustrative_fixture` data with `generated_at`, `as_of`, requested UTC range, and fixture version. The fixture adapter is replaceable by later persisted and Alpaca-backed repository implementations, but those adapters are not implemented here.

Presentation data never claims a broker call, paper fill, account holding, or LLM invocation. Stable fixture decision IDs and UTC range URLs preserve cross-page trace navigation.

## Market Tracker boundary (deferred)

The `/market-tracker` route is a provider-free frontend skeleton. It reserves an interactive price/time chart, symbol watchlist, timeframe controls, and independently filterable activity overlays, but renders no symbols, prices, bars, positions, orders, fills, or provider claims until a server adapter is authorized. The six activity kinds are `fill`, `order`, `proposal`, `decision`, `no_trade`, and `shadow`; only confirmed `fill` activity qualifies as an actual trade.

The planned flow is `Browser -> authenticated Next.js server adapter -> FastAPI market-tracker endpoint -> server-only Alpaca adapter and persisted PRISM repositories`. The browser will never receive Alpaca credentials or connect to Alpaca. Historical REST loading is the first future milestone; server-owned market and account streams, persistence, reconciliation, and cache warming follow later. The route preserves the shared UTC `range`, `from`, and `to` URL parameters while the endpoint remains intentionally absent from the current OpenAPI artifact.

## Hackathon operating window

The BA-owned registry also carries the fixed-date hackathon window. It starts Monday Aug 31, 2026 at 09:30 ET, stops new entries at Wednesday Sep 2, 2026 16:00 ET, scores total account equity at EOD Thursday Sep 3, 2026, and force-flattens by that close. Friday Sep 4 at 09:30 ET is an outer boundary only. The presentation governance endpoint exposes the registry's UTC timestamps and the human-readable ET controls; future deterministic authorization must enforce them. No Sep-3-expiring contract may be held into settlement.

## Autonomous run control

Autonomous paper execution is an explicit server-side opt-in, controlled by `AUTONOMOUS_TRADING_ENABLED` and a UTC half-open interval from `AUTONOMOUS_TRADING_START_AT` through (but excluding) `AUTONOMOUS_TRADING_END_AT`. The flag defaults to false, requires `EXECUTION_ENABLED=true`, an active ruleset, and a complete Alpaca paper credential pair. Production intervals must be contained within the registry's hackathon trading start and force-flatten deadline. Staging uses a separate paper credential pair and may select a bounded rehearsal interval; this does not change the production BA window or any deterministic authorization requirement.

The shared autonomous worker runs in staging and production when explicitly enabled, uses a PostgreSQL session advisory lock, reconciles unfinished receipts before every cycle (including kill-switched cycles), records cycle outcomes and reconciliation transitions, and checks the durable kill switch. It processes exactly the seven-symbol allowlist, requires fresh sourced evidence, complete option quotes/Greeks, at least 30 comparable five-year events, live account/portfolio and market-clock data, AI risk acceptance, and a deterministic `APPROVE`. Missing or degraded inputs produce `NO_TRADE`; mandatory exits and force-flatten are attempted before new entries.

The worker is not considered release-ready merely because the API is healthy. The deployed revision, Alembic head, worker heartbeat, CLI probes, paper account/options level, market-data freshness, and empty reconciliation queue must be verified together. Until that deployment gate is green, the static kill switch remains active.

## Authorization binding

An authorization decision binds at least:

- proposal identifier, version, and digest;
- ruleset identifier and version;
- AI Profile identifier and version;
- market and portfolio snapshot digests;
- allowed payload digest;
- rule trace, decision time, and expiration.

Only `APPROVE` may reach the execution service. Before any future submission, execution must recheck paper mode, execution-enabled state, autonomous window (when enabled), kill switch, authorization currency, payload digest, account and market freshness, permissions, buying-power inputs, contract activity, and client order ID.

## Database and readiness

Alembic owns schema creation, including specialist reports, research bundles, proposals, risk assessments, portfolio snapshots, immutable option-IV observations, authorizations, execution receipts, reconciliation events, autonomous controls, and cycle audit anchors. Application startup never calls `create_all()` and never swallows database initialization failures. Compose runs a one-shot migration service before the backend. When autonomous mode is enabled, readiness additionally requires the pinned CLI, paper credentials, active ruleset, verified paper account, and Level 3 options capability.

## Failure posture

Missing rules, invalid profile compatibility, stale data, invalid AI output, unsupported permissions, unavailable required dependencies, ambiguous paper environment, or digest mismatch fail closed. Provider failures are classified and redacted. Monitoring and audit remain available when execution is disabled.

Automatic AI Profile switching is deferred. Post-Analysis recommendations are limited to authorized fields, require deterministic validation, and remain pending manual operator review. Shadow candidates are persisted as non-executable branches.
