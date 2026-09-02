# Production provenance boundary

Production monitoring filters historical/backtest ShadowFund sessions. Recorded production counterfactuals remain non-trade-labelled; simulated historical sessions are available only to staging projections.

# ShadowFund / Shadow Portfolio

ShadowFund is PRISM's durable, non-executable counterfactual engine. It never creates, authorizes, amends, cancels, or submits an order. It writes only its own immutable evaluation records and reads timestamped market observations through market-data adapters.

## Lifecycle

Every terminal autonomous decision (`APPROVE`, `REJECT`, `MODIFIED_PENDING_ACCEPTANCE`, and durable `NO_TRADE`) creates one session bound to an immutable evaluation-root digest. A session records the proposal and authorization linkage when available, ruleset/profile versions, source feed/mode, valuation-policy version, input digest, horizon, and explicit refusal reason.

Each session has the canonical branch set:

| Branch | Semantics |
| --- | --- |
| Chosen path | Confirmed paper fill when one is available; otherwise cash. |
| Cash / no action | Always a complete zero-risk control. |
| Half-size | The primary eligible strategy at exactly `0.5x` virtual economics. Fractional virtual contracts are disclosed and never sent to Alpaca. |
| Contrarian | Opposite directional intent, with contracts selected by the existing deterministic eligibility gate. |
| AI specialist alternative | Agent 7 supplies strict direction/structure/rationale intent only. Deterministic code selects contracts; invalid or ineligible intent is an incomplete branch. |

Sessions with no viable proposal remain cash-only `INCOMPLETE` evidence rather than being omitted. Branch entry/marks use timestamped bid/ask observations, the authorized freshness and spread controls, approved option economics, and deterministic take-profit, stop-loss, DTE, and horizon exits. Missing, stale, incomplete, unauthorized, or entitlement-blocked observations become `INCOMPLETE` / `DATA_UNAVAILABLE`; no midpoint, fill, or favorable mark is invented.

The production observation cadence is entry, each 5-minute autonomous cycle, virtual exit, and horizon close. The official four-trading-day scoring horizon is the BA-owned scoring/force-flatten timestamp. Staging invokes the same configured Agent 1-7 research pipeline against point-in-time historical bars, news, and SEC filings; unavailable historical option contracts/quotes remain a visible `DATA_UNAVAILABLE` / cash-only result rather than an invented trade.

## Persistence and presentation

`shadow_sessions`, `shadow_branches`, `shadow_observations`, `shadow_valuations`, `shadow_post_analysis_batches`, and `shadow_profile_recommendations` are separate from paper execution, active portfolio, and backtest run records. The evaluation-root digest is unique. Each persisted observation has a SHA-256 input payload digest.

The existing authenticated `/presentation/alternatives` routes project these records. In production they use `data_mode=recorded`; in staging they select only the active completed backtest run and use `data_mode=simulated` with **Historical simulation** provenance. Staging branch projections retain the semantic `branch_key` and expose hypothetical touch fills, entry/exit times, slippage, and per-leg details without calling them Alpaca paper fills. No completed staging run produces a structurally valid explicit empty state, never a fixture fallback. Virtual values are never called Alpaca paper fills or Active Portfolio values.

The deterministic staging replay uses the August 24–27, 2026 four-session analogue, one strict decision per symbol at the 09:30 ET open, and five-minute management through the close. New entries stop at the Wednesday close and all open branches force-flatten at Thursday close. A provider preflight or required NBBO gap fails the run closed; it never creates a synthetic mark.

## Post-Analysis

Consolidated post-analysis runs automatically every Friday after the US equity market closes (`weekly_friday_post_analysis`), at the production hackathon official scoring/force-flatten milestone (`official_scoring`), and upon completion of a staging historical backtest (`completed_historical_backtest`). The evidence-qualified `PostAnalysisAgent` gathers weekly paper executions, risk metrics, and ShadowFund counterfactual branch marks to synthesize bounded profile recommendations only for `target_position_size_pct` and `opportunity_score_threshold`. Exit-policy calibration remains manual until complete, identical-quote policy comparisons exist. When trading/shadow evidence is empty or insufficient, the system safely records an explicit fail-closed `NO_RECOMMENDATION` batch without mutating profile state. Neither mode can amend an immutable ruleset or execute orders.

## Alpaca and data limits

Historical market-data access is read-only. Historical options data starts in February 2024; inactive contracts are historical-adapter-only. Historical option quote availability depends on the entitled feed: Basic options access is indicative and limited to recent data, so unavailable historical observations fail closed. Sources retrieved 2026-08-31: [Historical API](https://docs.alpaca.markets/us/docs/historical-api), [Historical Option Data](https://docs.alpaca.markets/us/docs/historical-option-data), and [Market Data API plans](https://docs.alpaca.markets/us/docs/about-market-data-api).

ShadowFund evaluates counterfactual capability and data/governance behavior, not strategy performance. It does not model market impact, queue position, latency, partial fills, price improvement, assignment, fees, or thin-options liquidity.
