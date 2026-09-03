# Durable decision evidence

After synthesis, PRISM persists a normalized monitoring snapshot for News, Quantitative, Industry, Fundamental, Macroeconomic, Market Reaction/Mispricing, and Trading Decision. The snapshot is redacted and append-only; it does not preserve prompts or hidden reasoning and has no authority over scoring, authorization, strike selection, exits, or paper execution.

# PRISM AI agents

Revision: `2026-08-30 / autonomous-paper-parity-v3`

AI produces evidence, proposals, critiques, and recommendations. Deterministic code owns authorization. The canonical topology contains seven specialist agents, followed by distinct risk, authorization, execution, evaluation, and learning stages.

## Canonical specialist sequence

| Order | Agent | Responsibility | Authoritative limit |
| --- | --- | --- | --- |
| 1 | News Agent | Normalize and classify catalysts; retain source, time, uncertainty, and evidence references. | Research only; cannot propose an order. |
| 2 | Quantitative Agent | Evaluate price, volume, volatility, options, liquidity, and historical analog behavior. | Research only; decimal-safe inputs required. |
| 3 | Industry Agent | Compare sector, peers, supply chain, and competitive context. | Research only. |
| 4 | Fundamental Agent | Assess earnings, valuation, balance-sheet, and issuer-specific evidence. | Research only. |
| 5 | Macroeconomic Agent | Assess rates, policy, indexes, volatility regime, and cross-asset context. | Research only. |
| 6 | Market Reaction/Mispricing Agent | Synthesize expected versus observed reaction and whether a defensible reaction gap exists. | May emit `NO_CLEAR_EDGE`; cannot authorize. |
| 7 | Trading Decision Agent | Produce a versioned `TradeProposal` or `NO_TRADE`, including structure, economics, exit policy, evidence, and limitations. | Proposal only. |

Specialist work may be concurrent where inputs are independent, but synthesis consumes validated, timestamped outputs. Missing, stale, invalid, contradictory, or unparseable evidence degrades confidence or ends in `NO_TRADE`.

## Downstream stages

| Stage | Type | Responsibility |
| --- | --- | --- |
| Risk Management | AI-assisted | Challenge portfolio concentration, drawdown, liquidity, volatility, tail risk, and contradictory evidence; recommend changes but do not authorize. |
| Rules Engine | Deterministic | Evaluate typed rules as `PASS`, `MODIFY`, or `FAIL`; produce aggregate `APPROVE`, `REJECT`, or `MODIFIED_PENDING_ACCEPTANCE`. |
| Execution | Deterministic integration | Recheck immutable bindings and changing state, then translate only a current `APPROVE` into an Alpaca paper order. MLeg position intents and paper-only CLI translation are implemented; submission remains gated. |
| ShadowFund | Deterministic evaluation | Persist a session for every terminal decision and value cash, 0.5x virtual sizing, contrarian, and Agent 7 alternative branches from timestamped bid/ask observations. It is non-executable and fails closed to incomplete data. |
| Post-Analysis | Asynchronous, bounded | Post-Analysis runs automatically after Friday market close, after production official scoring/force-flatten, or upon completed staging backtest. The `PostAnalysisAgent` synthesizes weekly execution and ShadowFund counterfactual evidence to propose bounded profile recommendations (`target_position_size_pct`, `opportunity_score_threshold`). Exit-policy calibration remains manual until complete ShadowFund evidence exists; neither path changes execution authority. |

Agent 7's optional ShadowFund intent is strict structured research evidence: direction, supported structure, and rationale only. It cannot contain a contract, strike, price, quantity, or order instruction; deterministic code selects an eligible virtual contract or records an incomplete branch.

## Structured records

Each AI output includes schema version, trace ID, source record IDs, observed/generated times, agent/model/prompt versions, evidence references, confidence, uncertainty, limitations, and terminal state. The system records concise rationale, not hidden chain-of-thought.

The Trading Decision Agent's `TradeProposal` binds the research record and market snapshot, selects only supported paper option structures, declares realistic expected value and reward/risk, and includes an `ExitPolicy`. Active Balanced exits follow calibrated ExitPolicyV2: +20% profit arm, 10 percentage point trailing giveback, +40% hard take-profit, fixed -50% stop-loss, 2-cycle thesis invalidation, 390-minute stagnation stop, 7 DTE, and a 14-day baseline holding limit; the hackathon operating override is four trading days.

During the BA-authorized hackathon window, Trading Decision must not propose a new entry after Wednesday Sep 2, 2026 16:00 ET. The effective hold ends at the EOD Thursday Sep 3 total-equity scoring point, when all positions are force-flattened; Friday Sep 4 09:30 ET is only the outer window boundary. Sep-3-expiring contracts cannot be carried into settlement.

## Research and opportunity score

The Market Reaction/Mispricing stage may emit an opportunity score from 0 through 100, but score alone is never permission. The absolute floor is 75; the active baseline profiles require Balanced 78, Conservative 85, and Aggressive 75. A proposal must independently pass realistic net EV of at least +0.15R, reward/risk of at least 1.5:1, portfolio-risk, freshness, liquidity, and execution-quality gates.

## Regime and structure guidance

In a VOLATILE regime with IV Rank above 50%, deterministic policy restricts proposals to defined-risk 1:1 debit spreads, caps target allocation at 1.5%, and caps planned stop risk at 0.75% of equity. In NORMAL conditions, supported single-leg long calls/puts and debit spreads remain subject to all hard controls. AI may describe a regime; deterministic code applies the rule.

## Provider boundary and failure behavior

Model providers remain behind a neutral adapter. Invalid structured output, missing required evidence, timeouts after classified retries, or unsafe provider responses stop the relevant workflow and expose a redacted error. The implemented `/api/v1/research/news/analyze`, `/api/v1/research/reaction/analyze`, and deterministic `/api/v1/research/quant/analyze` slices are non-authoritative and do not change this boundary. Quantitative analysis uses only normalized historical bars and emits a typed technical report; it never proposes or authorizes an order.

The active model/provider selection remains deployment configuration. Executable workflows use timestamped SEC companyfacts records and reject the illustrative registry. Automatic AI Profile activation is controlled by the authenticated operator's database preference, evaluating batches generated by the `PostAnalysisAgent` or manual uploads against BA-authorized bounds. Incomplete or missing evidence fails closed to a `NO_RECOMMENDATION` batch without mutating profile state.

The authenticated decision endpoint returns `NO_TRADE` unless it can bind a complete live research bundle and option selection. The autonomous worker is the only path that constructs and persists a canonical digest-bound `TradeProposal`; a specialist report or HTTP response alone never grants execution authority.

Autonomous execution additionally requires a sourced IV-rank observation. The Alpaca chain adapter preserves a provider-supplied rank when available; otherwise the worker computes a deterministic percentile from a configured historical provider, immutable chain observations, or Decimal Black-Scholes IV inversions over Alpaca option bars paired with underlying bars. Missing/insufficient history is an explicit `NO_TRADE`, never a guessed value.
