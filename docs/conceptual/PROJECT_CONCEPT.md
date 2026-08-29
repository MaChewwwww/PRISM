# PRISM project concept

Revision: `2026-08-29 / ecosystem-consolidation-v1`

**One signal. Multiple perspectives. Better decisions.**

## Executive summary

PRISM is a paper-only market intelligence and governed decision platform. It decomposes one market signal into seven specialist AI perspectives, challenges the resulting proposal with AI-assisted Risk Management, and delegates all execution authority to deterministic code. ShadowFund compares alternatives on the same subsequent market path, and asynchronous Post-Analysis may recommend bounded AI Profile changes for manual review.

The current product is a contract-aligned skeleton. It implements versioned governance data, typed contracts, authenticated news, deterministic quantitative, and market-reaction research slices, backend-owned illustrative presentation APIs, a story-first frontend, and deployment/migration foundations. It does not yet implement full specialist orchestration, durable portfolio/authorization/ShadowFund engines, or broker order submission.

Every current demonstration response is labeled **Illustrative fixture**. It does not represent an Alpaca account, paper order, fill, holding, P&L record, or model/provider call.

## Authority chain

PRISM resolves conflicts in this order:

1. Repository invariants.
2. BA-owned business process and versioned numerical register.
3. AI Engineer-owned topology and responsibility boundaries.
4. API contracts and generated transport types.
5. Implementation and tests.
6. This explanatory concept and its synchronized DOCX form.

BA-authorized values override older examples, and the seven-specialist architecture is canonical. SLOs, backup retention, RPO, RTO, and other values absent from the register remain unresolved.

## Problem and product thesis

Simple sentiment systems reduce market events to positive news -> buy and negative news -> sell. They miss whether the event is material, whether the market already priced it, whether the reaction differs from comparable events, and whether a theoretically attractive position is executable within portfolio constraints.

PRISM treats each candidate as a decision story:

```text
catalyst and market snapshot
  -> specialist evidence
  -> reaction-gap synthesis
  -> proposal or NO_TRADE
  -> adversarial risk critique
  -> deterministic authorization
  -> paper-only execution when genuinely enabled
  -> counterfactual evaluation
  -> bounded learning recommendation
```

The objective is not maximum trade frequency. It is a traceable record of why action or restraint was appropriate under a specific version of evidence, rules, and profile.

## Canonical agent topology

The specialist order is canonical:

1. **News Agent** classifies catalysts, sources, event time, uncertainty, and evidence provenance.
2. **Quantitative Agent** evaluates price, volume, volatility, options, liquidity, and historical analogs.
3. **Industry Agent** evaluates sector, peer, supply-chain, and competitive context.
4. **Fundamental Agent** evaluates issuer economics, guidance, valuation, balance-sheet, and quality.
5. **Macroeconomic Agent** evaluates rates, policy, indexes, volatility regime, and cross-asset context.
6. **Market Reaction/Mispricing Agent** compares expected and observed reaction and determines whether a defensible reaction gap exists.
7. **Trading Decision Agent** produces a versioned `TradeProposal` or `NO_TRADE`, including structure, economics, evidence, exit policy, and limitations.

The specialist chain is followed by:

- **Risk Management**, an AI-assisted adversarial critique of portfolio, regime, liquidity, drawdown, and tail risk.
- **Deterministic Rules Engine**, the sole authorization authority.
- **Paper Execution**, a deterministic adapter that may translate only a current `APPROVE`; it is disabled and not implemented in this skeleton.
- **ShadowFund**, deterministic counterfactual evaluation; only illustrative views exist in this skeleton.
- **Post-Analysis**, asynchronous recommendations limited to authorized AI Profile fields and pending deterministic validation/manual review.

No AI agent, browser route, prompt, MCP tool, or maintenance script can authorize or place an order.

## Decision vocabulary

Individual rules return one of:

- `PASS`: the evaluated input satisfies the rule.
- `MODIFY`: a safe deterministic revision is possible, such as reducing size.
- `FAIL`: the proposal cannot proceed under the active rule.

Aggregation returns one of:

- `APPROVE`: every required rule permits the exact bound proposal.
- `REJECT`: the proposal is terminally blocked.
- `MODIFIED_PENDING_ACCEPTANCE`: proposed changes carry no execution authority.

Only `APPROVE` may continue toward execution. Accepting a modification creates a new proposal version and digest; it must be authorized again.

## Governance baseline

Ruleset `prism-authorized-baseline@1.0.0` is active from `2026-08-29T00:00:00Z`, remains open-ended until superseded, and uses Balanced as its default profile. The machine-readable authority is `backend/app/rules/authorized_baseline.v1.json`.

| Parameter | Authorized value |
| --- | ---: |
| Starting-capital baseline | 100,000.00 USD |
| Maximum risk per trade, NORMAL | 1.00% of current equity |
| Maximum risk per trade, VOLATILE | 0.75% of current equity |
| Normal / volatile target allocation | 2.00% / 1.50% maximum |
| Drawdown CAUTION / DEFENSIVE / HALT | 1.50% / 2.25% / 3.00% |
| Minimum cash reserve | 5.00% |
| Ticker / sector / correlated-cluster concentration | 5.00% / 10.00% / 7.50% maximum |
| Aggregate modeled hard-stop risk | 3.00% maximum |
| Maximum open positions | 6 |
| Maximum bid/ask spread | 10.00% of premium |
| Evidence and market-data freshness | 30 seconds maximum |
| Opportunity score | 75 absolute floor; Balanced 84 |
| Net expected value / realistic reward-risk | +0.15R minimum / 1.50:1 minimum |
| Balanced take-profit / fixed stop-loss | 75.00% / 50.00% of initial debit |
| Authorized take-profit range | 75.00% through 100.00% |
| DTE exit | 7 days default; range 2 through 14 days |
| Baseline maximum hold | 14 days; range 3 through 45 days |
| Hackathon maximum-hold override | 4 trading days |

The 14-day value is the reusable baseline holding limit. The four-trading-day value is a tighter hackathon operating override and must not overwrite or masquerade as the baseline.

### Hackathon evaluation window

The BA-authorized hackathon window starts Monday Aug 31, 2026 at 09:30 ET. Official P&L is measured on total account equity at EOD Thursday Sep 3, 2026. Friday Sep 4 at 09:30 ET is only the outer window boundary. The new-entry cutoff is Wednesday Sep 2, 2026 16:00 ET, and every position is force-flattened by Thursday's close. The effective hold is the minimum of four trading days and the Thursday scoring point; 0-DTE and Sep-3 settlement exposure are blocked. These dates are represented as UTC in the versioned ruleset registry.

## AI Profiles

| Profile | Target allocation | Opportunity threshold | Take-profit | Stop-loss |
| --- | ---: | ---: | ---: | ---: |
| Conservative | 1.50% | 90 | 75.00% | 50.00% fixed |
| Balanced | 2.00% | 84 | 75.00% | 50.00% fixed |
| Aggressive | 2.50% | 80 | 100.00% | 50.00% fixed |

Post-Analysis may recommend changes only to target position size (1.50% through 2.50%), opportunity threshold (75 through 95), take-profit (75.00% through 100.00%), and the fixed 50.00% stop-loss field. The validator rejects unknown fields, incompatible versions, and out-of-bounds changes.

Manual Prescriptive mode is the only authorized activation model. The current skeleton is read-only and does not persist or activate recommendations. Automatic switching is deferred.

## Market regime and option envelope

The initial instrument envelope contains long calls, long puts, and two-leg 1:1 long call/put debit spreads. Options use whole contracts, `day` time in force, active OCC contracts, and no extended-hours trading. Naked shorts, credit spreads, equity legs, rolls, more than two legs, unsupported permissions, and unverified account capabilities fail closed.

When IV Rank is above 50%, the deterministic VOLATILE rule restricts proposals to 1:1 debit spreads, caps target allocation at 1.50%, and caps planned stop risk at 0.75% of equity. AI may identify context, but code applies the rule.

Every proposal requires a take-profit, fixed stop-loss, DTE exit, time exit, and thesis-invalidation path. Balanced take-profit is 75%; stop-loss is fixed at 50%.

## Authorization and execution boundary

Authorization binds proposal identifier/version/digest, ruleset and profile versions, market and portfolio snapshot digests, allowed payload digest, rule trace, decision time, and expiration. Before any future submission, execution must recheck paper mode, execution-enabled state, kill switch, authorization currency, matching payload, freshness, account permissions, buying-power inputs, contract activity, and client order ID.

Live trading is prohibited. Execution defaults off and fails closed. The current skeleton contains validation boundaries but no broker submission implementation.

## ShadowFund and learning

ShadowFund will evaluate cash/no-action, half-size, unhedged or contrarian, and declared specialist alternatives on the same market path. It records comparable net outcome, drawdown, adverse/favorable excursion, exposure duration, valuation confidence, and data completeness. Simulations must disclose limitations and never imply executable returns.

The reusable evaluation policy includes intraday and five-trading-day horizons. The hackathon configuration uses a primary four-trading-day horizon through the EOD Sep 3 scoring point while retaining the intraday view. ShadowFund never extends the scoring window or creates an execution path.

Completed evaluations may feed asynchronous Post-Analysis. Recommendations are evidence, not configuration authority.

## Data, API, and provenance

Financial and percentage values cross API boundaries as decimal strings. Timestamps are timezone-aware UTC. Contracts use closed enums, schema versions, stable identifiers, typed reason codes, and immutable authorization bindings.

The frontend uses generated OpenAPI types through one server-side adapter and forwards only the authenticated session. It preserves UTC `from`/`to` URLs and stable decision IDs across overview, decisions, portfolio, alternatives, news, agents, governance, and weekly-summary routes.

Every presentation response includes `generated_at`, `as_of`, requested range, `data_mode`, and fixture version. Current `data_mode` is always `illustrative_fixture`. Labels **Alpaca paper**, **ShadowFund**, **Benchmark**, and **Simulated** are reserved for data that genuinely matches those sources.

## Security and operations

The backend sets an HTTP-only `prism_session` cookie; login does not return a token. Example passwords and session secrets are rejected outside development. The browser has no endpoint that reveals a configured login password.

Alembic owns schema creation. Compose runs a one-shot migration before FastAPI. Readiness validates required configuration and database access; liveness only reports process response. Local direct ports are 3000/8000, while base Compose defaults are 3005/8005. Production publishes Nginx only and deploys automatically after successful protected `main` CI; staging is separately gated.

Provider errors are classified and redacted. The implemented news, deterministic quantitative, and market-reaction endpoints run non-authoritative research with structured validation, bounded provider reads, and non-blocking classified retries. Quantitative output is a typed technical report and never an authorization signal.

## Frontend concept

PRISM presents an authenticated, story-first journal rather than raw infrastructure entities. Core surfaces are Overview, Decision Stories, Portfolio, Alternatives, News, Agents, Governance, and Weekly Summary. Each surface handles loading, error, empty, and success states and preserves keyboard access, focus visibility, responsive navigation, and WCAG 2.2 AA contrast.

The visual skeleton uses Plus Jakarta Sans, monospace tabular financial values, obsidian/specular-glass surfaces, mineral teal, and stable spectral identities for the seven specialists. Decorative polish remains frontend-developer work; data boundaries and authority semantics do not.

Governance is read-only. Weekly Summary shows bounded Post-Analysis recommendations awaiting manual review and provides no threshold mutation or automatic activation path.

### Market Tracker

Market Tracker is an authenticated Inspect surface for a future interactive price/time chart, symbol watchlist, timeframe controls, and activity overlays. Its skeleton is intentionally provider-free: it preserves the shared UTC range and default `1Day` timeframe, but shows an explicit integration-deferred state with no fabricated symbols, prices, positions, orders, fills, or provider claims. Future overlays distinguish confirmed `fill`, `order`, `proposal`, `decision`, `no_trade`, and `shadow` events; only confirmed fills qualify as actual trades. The planned flow remains Browser -> authenticated Next.js server adapter -> FastAPI -> server-only Alpaca and persisted PRISM repositories. Historical bars and snapshots are the first future milestone, followed by server-owned streams and reconciliation; the browser never receives provider credentials.

## Delivery scope

### Implemented skeleton

- versioned BA registry and typed profile/ruleset contracts;
- FastAPI-generated OpenAPI paths and generated TypeScript;
- authenticated illustrative presentation APIs and stable decision IDs;
- story-first frontend connected only to backend APIs;
- canonical agent/governance/provenance presentation;
- implemented news, deterministic quantitative, and market-reaction research slices with redacted failures;
- authentication hardening, Alembic baseline, migration service, readiness, CORS, and port alignment.

### Deferred engines

- full seven-agent orchestration;
- durable proposal/risk/rules/profile/audit persistence;
- portfolio and Alpaca-backed repositories;
- broker paper execution and reconciliation;
- ShadowFund valuation engine;
- profile activation and automatic switching.

## Success criteria

The skeleton succeeds when contracts, rules, docs, Markdown/DOCX concept formats, generated artifacts, frontend data flows, migrations, and tests agree; every fixture surface identifies illustrative provenance; and no AI/browser path can bypass deterministic paper-only controls.
