# Production monitoring status

Implemented: the authenticated decision-detail projection exposes durable, redacted seven-agent perspectives. Missing evidence is explicit. Day 1 NVDA records are static retrospective reconstructions sourced from the tracked excerpt and excluded from LLM usage metrics. Production monitoring excludes historical/backtest ShadowFund sessions.

# PRISM implementation plan

## Consolidated skeleton: implemented in this pass

- Versioned BA ruleset/profile registry and typed governance contracts.
- FastAPI-derived OpenAPI with real paths and generated TypeScript transport types.
- Authenticated backend-owned monitoring APIs for every story-first frontend surface.
- Canonical seven-specialist roster followed by Risk Management, deterministic Rules Engine, paper Execution boundary, ShadowFund, and asynchronous Post-Analysis.
- Sourced IV-rank history (provider, durable chain observations, or option-bar IV inversion) and option-payoff EV with observed premium, NBBO slippage, and fill probability.
- OCC/Alpaca-chain portfolio enrichment for sector, correlated cluster, expiration, Delta, Vega, and freshness-aware concentration controls.
- Server-side frontend monitoring adapter, recorded provenance, read-only governance, and manual profile-recommendation review.
- Removed browser password disclosure and strengthened non-development authentication validation.
- Alembic baseline, one-shot Compose migration, dependency-aware readiness, configurable CORS, and aligned ports/deployment documentation.
- Governance/document semantic checks and synchronized Markdown/DOCX concept deliverables.
- BA-authorized hackathon window is registry-backed: start Aug 31 09:30 ET, new-entry cutoff Sep 2 16:00 ET, total-equity scoring and force-flatten at Sep 3 close, and Sep 4 09:30 ET outer boundary.

All workspace data now uses authenticated monitoring projections over durable records; there is no illustrative fixture fallback. Production projects recorded ShadowFund sessions, while staging projects only the active completed historical-backtest run with `data_mode=simulated` and historical-simulation provenance. Neither variant represents an Alpaca paper fill or alters the Active Portfolio. Autonomous execution is production-only, uses a separate server-side paper account, and remains fail-closed until readiness, evidence, authorization, and CLI capability gates pass. Staging rejects autonomous trading and uses the separate non-executing historical backtest boundary.

## Stabilization pass: implemented safeguards

- Specialist reports are Alembic-persisted; decision caches are model/provider/freshness-bound and do not fabricate missing bars.
- Illustrative fundamentals are rejected by executable research paths; provider errors are redacted.
- Option contracts and option-chain quote/Greek adapters enforce fresh server-side inputs; strategy selection enforces DTE, NBBO, spread, and positive-debit rules.
- P0-P5 deterministic authorization, durable kill-switch controls, advisory-locked cycle audit rows, and strict autonomous readiness are implemented. Missing state, stale quotes, missing Greeks, non-paper mode, drawdown limits, and broker-closed timing fail closed.
- The production autonomous worker performs restart reconciliation, account/portfolio snapshot, SEC-sourced fundamentals, specialist research, five-year/30-event analog coverage, live option selection, AI risk assessment, deterministic authorization, mandatory exits, durable receipt submission, and audit. Staging rejects autonomous trading and validates through a separate historical backtest that must not invoke this worker or its execution adapter.
- Frontend fixture labels and invocation metadata are truthful.

Submission remains a release-gated capability. The worker records `NO_TRADE` when IV history, option-payoff evidence, concentration/Greeks inputs, or deployment/readiness evidence is unavailable. A PR and a fresh staging deployment are required before `EXECUTION_KILL_SWITCH` can be disabled. Existing option positions are OCC-parsed and refreshed from the live chain; sector/cluster/ticker and same-expiry exposure are calculated from their observed market values, while net Delta/Vega stress is included in the aggregate risk budget.

## Market Tracker skeleton: implemented, provider integration deferred

The `/market-tracker` route and Inspect navigation entry reserve a chart/watchlist workspace, shared UTC date-range URLs, a default `1Day` timeframe, and six independently filterable activity kinds (`fill`, `order`, `proposal`, `decision`, `no_trade`, `shadow`). The page makes no provider or backend request and renders no fake market/account values. Only confirmed `fill` activity will count as a verified trade when the planned endpoint is implemented. The endpoint contract, server-owned Alpaca flow, entitlement caveats, and deferred milestones are recorded in `MARKET_TRACKER.md` and `ALPACA_INTEGRATION.md`.

## Specialist orchestration

The seven specialist workflows are executed by the shared autonomous worker with strict provider evidence and structured outputs. Illustrative financials remain presentation-only; autonomous fundamentals come from timestamped SEC companyfacts records.

## Proposal, risk, and deterministic authorization

The worker persists canonical `TradeProposal`, `RiskAssessment`, portfolio snapshots, authorization decisions, rule traces, and immutable evaluation roots. Only an unexpired `APPROVE` bound to the research-bundle digest and current paper account can reach execution.

## Portfolio and paper execution

Portfolio snapshots, five-year historical analogs, PostgreSQL execution receipts, restart reconciliation, mandatory paper exits, and CLI capability probes are implemented. ShadowFund sessions/branches/observations/valuations and their no-execution presentation projection consume immutable evaluation roots without changing execution authority. Networked tests remain opt-in and must not place an order without explicit user authorization.

## Later: operations and evaluation

Add restore drills, SLOs after owner approval, full observability, and threat modeling. Backend profile activation persistence, manual activation, user-configured automatic calibration, weekly Friday post-close Post-Analysis triggers, and evidence-qualified `PostAnalysisAgent` recommendation generation are implemented; manual frontend profile-activation controls remain pending. Live trading remains outside scope.

## Deterministic historical-options simulator: staging-only

The staging replay uses the August 24–27, 2026 four-session analogue, daily strict decisions at the 09:30 ET open, and five-minute option management through Thursday close. It requires an entitled historical NBBO provider, persists run-scoped option payloads plus ShadowFund observations/valuations, and records a backtest-only P0–P5 rule trace. Missing contracts, quotes, or entitlement remain `DATA_UNAVAILABLE` and cannot activate presentation. Simulated touch fills are projected only through `/presentation/alternatives`; production autonomous execution, paper receipts, and the Active Portfolio remain unchanged.
