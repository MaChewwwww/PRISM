# Governance traceability

Revision: `2026-08-30 / autonomous-paper-parity-v4`

This matrix connects BA requirements, registry keys, AI responsibilities, contracts, presentation surfaces, and verification. The machine-readable values live in `backend/app/rules/authorized_baseline.v1.json`; prose mirrors that register and never overrides it.

| Business authority | Registry keys | AI responsibility | Contract / API | Frontend surface | Verification |
| --- | --- | --- | --- | --- | --- |
| Paper-only, fail-closed operation | Platform invariant; no tunable key | Trading Decision proposes; AI never authorizes | `AuthorizationDecision`, execution validation, `/health/ready` | Global shell, governance | execution and configuration tests |
| Seven specialist perspectives | Canonical topology; no tunable key | News, Quantitative, Industry, Fundamental, Macroeconomic, Market Reaction/Mispricing, Trading Decision | presentation agent schemas; `/presentation/agents` | Agents, decision story | topology governance check; presentation tests |
| AI-assisted risk followed by deterministic authority | No tunable key | Risk Management critiques; Rules Engine decides | typed rule trace and authorization binding | decision story, rules | authorization semantic tests |
| Starting-capital baseline | `starting_capital_usd` | Context only | decimal string in governance/portfolio responses | portfolio, governance | registry and provenance tests |
| Per-trade risk and target allocation | `max_risk_per_trade_pct`, `volatile_risk_per_trade_pct`, `normal_target_allocation_pct`, `volatile_target_allocation_pct` | Profiles propose targets within hard caps | typed profile parameters and portfolio-risk inputs | governance, weekly summary | registry/profile contract tests |
| Drawdown state controls | `drawdown_caution_pct`, `drawdown_defensive_pct`, `drawdown_halt_pct` | Risk supplies state evidence | `MarketRegime`, `PortfolioRiskState`, rule trace | decision story, governance | registry and rule-trace tests |
| Cash and concentration controls | `cash_buffer_pct`, `ticker_concentration_pct`, `sector_concentration_pct`, `correlated_cluster_concentration_pct`, `aggregate_hard_stop_risk_pct`, `max_open_positions` | Risk identifies conflicts | rule priority/reason codes; authorization inputs | governance, decision story | typed reason-code and fixture tests |
| Portfolio instrument metadata | No new threshold; Alpaca positions + OCC parser + option chain | No AI classification authority | portfolio snapshot payload: underlying, asset class, sector, cluster, expiration, Delta, Vega, quote age | portfolio, decision story | OCC parsing, fresh chain enrichment, and fail-closed metadata tests |
| Freshness and execution quality | `data_freshness_seconds`, `max_bid_ask_spread_pct` | Specialists timestamp evidence | UTC range metadata, rule trace | news, stories, governance | UTC validation and semantic checks |
| IV-rank and defined-risk structure | `IV_RANK_*`; IV > 50% structure rule | Quant/market adapters source current IV and historical observations; deterministic code computes rank | `option_iv_observations`, option strategy, rule trace | decision story, rules | IV-rank, option-bar inversion, and high-IV structure tests |
| Opportunity and economics gates | `opportunity_score_floor`, `balanced_opportunity_score`, `minimum_net_ev_r`, `minimum_reward_risk_ratio` | Research scores; Trading Decision proposes; rules decide | research/proposal/rule schemas | stories, governance | contract and registry consistency tests |
| Option-payoff EV | `minimum_net_ev_r`, `minimum_reward_risk_ratio`, `max_bid_ask_spread_pct` | Historical analogs provide comparable outcomes; deterministic model applies option payoff, premium, slippage, and fill probability | research bundle economics and authorization inputs | decision story, rules | option-payoff EV tests |
| Exit policy | `take_profit_default_pct`, `take_profit_min_pct`, `take_profit_max_pct`, `stop_loss_pct`, DTE keys, holding keys | Trading Decision includes policy; rules validate | bounded `ExitPolicy` | story, rules, weekly summary | contract boundary tests |
| Baseline versus hackathon holding limit | `max_hold_default_days`, `hackathon_max_hold_trading_days` | No AI override | versioned ruleset identity | governance | semantic documentation check |
| Hackathon evaluation window | `hackathon_window.trading_start_at`, `new_entry_cutoff_at`, `official_scoring_at`, `force_flatten_by`, `window_outer_boundary_at`, `scoring_basis` | Deterministic window controls; no AI override | typed registry and governance read model | governance, portfolio, alternatives | registry, API, and documentation consistency tests |
| Autonomous paper-trading schedule | `AUTONOMOUS_TRADING_ENABLED`, `AUTONOMOUS_TRADING_START_AT`, `AUTONOMOUS_TRADING_END_AT`, 900-second cadence, seven-symbol allowlist, six-position cap | No AI or operator shortcut; shared worker records fail-closed cycle outcomes | `AutonomousWorker`, `autonomous_controls`, `autonomous_cycles`, authenticated control endpoints | execution configuration and status | settings, advisory-lock, readiness, kill-switch, and no-invocation tests |
| ShadowFund lineage | No tunable key | Counterfactual candidates remain non-executable | `EvaluationRoot`, `autonomous_audit_events` | ShadowFund story surfaces | immutable-root and provenance tests |
| Profile governance | `profiles`, `profile_bounds` | Post-Analysis recommends authorized fields only | typed profile/recommendation models; `/presentation/weekly-summary` | weekly summary, rules | bounds and manual-review tests |
| Illustrative presentation data | Fixture version, not a ruleset key | Recorded examples only | all `/presentation/*` responses use `data_mode=illustrative_fixture` | all story-first routes | endpoint/auth/provenance tests |
| Market Tracker provenance and paper boundary | No tunable key; future contract only | Specialists and Trading Decision emit context; deterministic code remains authoritative | Planned `GET /api/v1/market-tracker`; UTC range, decimal values, capability/freshness metadata | `/market-tracker`, Inspect navigation | no-network skeleton, filter/taxonomy, accessibility, docs, and OpenAPI-deferred checks |
| Quantitative technical evidence | No tunable key; indicator windows are contract/documented computation inputs | Quantitative Agent computes deterministic evidence; no proposal or authorization authority | `QuantitativeAnalysisReport`; authenticated `POST /api/v1/research/quant/analyze` | Agents and future decision traces | indicator unit tests, decimal serialization, auth, bounded input, and redacted-provider tests |

## Decision vocabulary

| Scope | Values | Meaning |
| --- | --- | --- |
| Individual rule | `PASS`, `MODIFY`, `FAIL` | A rule accepts, requests a revision, or blocks the evaluated proposal. |
| Aggregate authorization | `APPROVE`, `REJECT`, `MODIFIED_PENDING_ACCEPTANCE` | Only `APPROVE` has authority to continue. A modification has no execution authority. |

## Deliberately unresolved values

Availability SLOs, latency SLOs, backup retention, RPO, and RTO remain unresolved. They are not present in the ruleset registry and must not be inferred from examples, infrastructure defaults, or fixture timestamps.
