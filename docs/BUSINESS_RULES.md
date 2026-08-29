# Business Rules

## Purpose and status

Deterministic rules are the authoritative trade gate. The BA owns rule intent, thresholds, precedence, exceptions, and acceptance cases. The BA has authorized an operating baseline (see [Authorized governance baseline](#authorized-governance-baseline) and the [Active baseline parameter register](#active-baseline-parameter-register) below); these values are the active ruleset for the hackathon MVP. Engineering must still implement a configurable engine, treat every value as versioned ruleset configuration, and fail closed when required configuration is absent. Future changes require a versioned ruleset or profile change and must preserve the hard safety boundaries defined here.

## Decision semantics

- `PASS`: the proposal satisfies the rule.
- `MODIFY`: the proposal is not executable as submitted; explicit bounded changes are returned.
- `FAIL`: the proposal is rejected.
- `APPROVE`: every required evaluation passes for the exact payload.
- `REJECT`: one or more required evaluations fail or required configuration is missing.

A MODIFY result does not authorize a mutated payload. The modification must become a new accepted proposal and be evaluated again.

## Rule definition template

| Field | Meaning |
| --- | --- |
| `rule_id` / version | Stable identity and immutable version |
| Name and description | Business-readable intent |
| Owner and status | BA/product owner; draft/approved/retired |
| Inputs | Exact contract fields and snapshot freshness |
| Condition | Deterministic expression |
| Configuration | Default, units, allowed range, source |
| Outcome | PASS, MODIFY, or FAIL and reason code |
| Priority | Evaluation/precedence order |
| Exceptions | Explicit approved exceptions, if any |
| Profile configurable | Whether a profile may choose inside a named range |
| Tests | Boundary, negative, and interaction cases |

## Initial platform rules

The following are engineering hard limits, not BA thresholds: paper environment only; execution disabled by default; active ruleset required; valid unexpired authorization required; exact proposal/payload digest; active/tradable option contracts; appropriate options level; `day` options orders; no extended hours (market boundary: 09:30–16:00 America/New_York); only long calls, long puts, and 1:1 two-leg debit spreads; client order ID required; kill switch honored; shadow candidates (`ShadowCandidate`) are strictly non-executable and barred from the broker execution adapter.


Active trading windows are configurable as one or more intraday intervals within the regular market session boundary (default: `[{"start": "09:30", "end": "16:00"}]` in `America/New_York` time). Proposals submitted outside configured active windows fail closed with reason code `OUTSIDE_TRADING_WINDOW`.

The competition account starting capital baseline is established at $100,000.00 USD. Position concentration, order notional, portfolio cash buffer, drawdown, concurrent positions, liquidity, minimum confidence, data freshness duration, exit policy, and ShadowFund horizon are authorized in the [Active baseline parameter register](#active-baseline-parameter-register). An absent mandatory value still returns `RULESET_NOT_CONFIGURED`.

## Implied volatility (IV) regime and strategy constraints

To protect capital against post-catalyst volatility collapse (IV crush) and vega deflation:

- **High IV Regime ($\text{IV Rank} > 50\%$ or $\text{IV}/\text{HV} > 1.20$):**
  - Single-leg long options (`long_call`, `long_put`) are **strictly prohibited** and fail evaluation with reason code `HIGH_IV_SINGLE_LEG_PROHIBITED`.
  - Only two-leg Defined-Risk Debit Spreads (`call_debit_spread`, `put_debit_spread`) are permitted, ensuring the short OTM leg offsets positive vega exposure and cushions post-event IV collapse.
- **Normal / Low IV Regime ($\text{IV Rank} \le 50\%$ and $\text{IV}/\text{HV} \le 1.20$):**
  - Both single-leg long options and two-leg debit spreads are permitted; single legs capitalize on potential volatility expansion.
- **Extreme IV Regime ($\text{IV Rank} > 90\%$):**
  - Single legs are hard-rejected; debit spread width is constrained to minimize vega drag, or the proposal is modified to `NO_TRADE`.

## Deterministic options exit policy and position lifecycle

To prevent holding open option spreads until expiration—which incurs unnecessary theta decay, assignment friction, and gamma pin risk—the system evaluates position-level exit rules:

- **Take-Profit Rule ($\text{TP}$):** Automatically triggers a closing order when position unrealized profit reaches or exceeds the configured `take_profit_pct` measured against the initial debit paid (Balanced default: **$75.0\%$**; Aggressive up to **$100.0\%$**). The final target must satisfy the $1.5{:}1$ minimum realistic reward/risk. This captures the move without suffering late-stage time decay.
- **Stop-Loss Rule ($\text{SL}$):** Automatically triggers a closing order when position loss reaches or exceeds the configured `stop_loss_pct` (fixed at **$50.0\%$** of initial debit paid), capping maximum capital loss per trade.
- **Time/DTE Rule (Gamma Pin Risk):** Force-closes any open option position when days-to-expiration reaches $\le \text{dte\_threshold}$ (default: **$\le 7\text{ days}$**), avoiding assignment risks and illiquid expiration dynamics.
- **Max Holding Duration:** Force-closes positions after `max_hold_days` elapsed sessions (default: **$14\text{ days}$**) if the reaction thesis has not materialized.

### AI Profile tunability and safety bounds

Exit parameters are configurable per active **`AIProfile`** (by the user or recommended via **Post-Analysis AI**), but must strictly adhere to the following deterministic safety envelope:

| Parameter | Default | Safe Approved Range | Enforcement Action on Breach |
| :--- | :---: | :---: | :--- |
| `take_profit_pct` | $75.0\%$ | $[75.0\%, 100.0\%]$ | Rejects profile activation if $< 75.0\%$ or $> 100.0\%$ |
| `stop_loss_pct` | $50.0\%$ | $[50.0\%, 50.0\%]$ | Rejects profile activation if $\ne 50.0\%$ |
| `dte_threshold` | $7\text{ days}$ | $[2\text{ days}, 14\text{ days}]$ | Rejects if $< 2\text{d}$ (pin risk) or $> 14\text{d}$ |
| `max_hold_days` | $14\text{ days}$ | $[3\text{ days}, 45\text{ days}]$ | Rejects if $< 3\text{d}$ or $> 45\text{d}$ |

> The `take_profit_pct` and `stop_loss_pct` ranges above reflect the authorized BA governance baseline. The stop-loss is a fixed $50\%$ hard exit applied to every position; profile tuning of `take_profit_pct` is bounded to $[75.0\%, 100.0\%]$ (Balanced default $75\%$), and the final take-profit target must satisfy the $1.5{:}1$ minimum realistic reward/risk.

When Post-Analysis AI audits historical ShadowFund counterfactual sessions, it may generate an `AIProfileRecommendation` to adjust these parameters to optimize risk-adjusted returns (Sharpe ratio / win rate). The recommendation can be applied manually by the operator or automatically switched if guardrailed auto-tuning is enabled.


## Versioning and audit


Rulesets are immutable after activation. A decision stores the ruleset version, individual evaluations, input snapshot references, effective profile version, outcome, allowed payload digest, and expiration. Retired rules remain queryable for historical audit.

## Rule evaluation precedence and thresholds

The rules engine evaluates proposals in a hierarchical precedence. Priority levels supersede one another: **P0** safety and data-integrity controls supersede **P1** instrument permissions, **P2** account/portfolio risk, **P3** execution quality, **P4** strategy quality, and **P5** optimization preferences. Optimization logic may select among eligible trades but may never weaken a higher-priority rule. If any required rule fails, evaluation terminates immediately and returns `REJECT`.

### P0 — Safety and data integrity

- **Rule 1 — Market data freshness:** Pricing data and research timestamps must be $\le 30$ seconds old. `REJECT` if stale.
- **Rule 2 — Daily loss circuit breaker:** Current-day realized + unrealized drawdown must remain below $1.5\%$ (CAUTION), $2.25\%$ (DEFENSIVE), and $3.0\%$ (HALT) of start-of-day equity. The $3.0\%$ level is the non-bypassable new-risk halt. At CAUTION, reduce new-risk budget; at DEFENSIVE, permit only highest-quality opportunities with reduced sizing; at HALT, reject all new proposals. Active positions remain governed by their individual exit parameters and mandatory exits.
- **Rule 3 — Available cash buffer:** The account must retain a minimum of $5.0\%$ ($\$5{,}000$ at the $\$100{,}000$ baseline) of current equity in unallocated cash / buying-power reserve. `REJECT` if the proposed trade reduces available buying power below this threshold.

### P1 — Instrument and regime permissions

- **Rule 4 — Position concentration cap:** Total allocated capital to a single ticker (existing + proposed) must be $\le 5.0\%$ of total equity, measured before and after the proposed trade. `MODIFY` (reduce sizing to fit the cap) or `REJECT` if the minimum contract size exceeds the cap.
- **Rule 5 — Instrument and regime validation:** The trade must be an approved Level 2 / Level 3 option. If IV Rank $> 50\%$ (Volatile regime), single-leg options are blocked and only 1:1 debit spreads are permitted. `REJECT` if invalid.

### P2 — Account and portfolio risk

- **Rule 8 — Per-trade risk:** Maximum loss at the hard stop must not exceed the risk-per-trade limit ($1.0\%$ of current equity normal, $0.75\%$ volatile).
- **Rule 9 — Portfolio exposure and correlation:** Evaluate incremental Delta, Vega, ticker/sector exposure, correlated positions, event concentration, and expiration concentration. `MODIFY` or `REJECT` when limits are exceeded.
- **Rule 11 — Risk state:** Risk state must be NORMAL, CAUTION, DEFENSIVE, or HALT (thresholds at $1.5\%$ / $2.25\%$ / $3.0\%$ start-of-day drawdown). Effective risk must decrease as drawdown increases. No martingale or loss-recovery sizing.

### P3 — Execution quality

- **Rule 10 — Liquidity and execution economics:** `REJECT` or `MODIFY` when bid/ask width, open-interest/volume conditions, or estimated slippage exceed limits. The bid/ask spread of a proposed contract must not exceed $10\%$ of its premium; wider spreads are flagged as high execution risk and fail this rule. A valid thesis with poor execution economics is not an executable trade.
- **Rule 13 — Execution re-validation:** Immediately before broker submission, re-fetch execution-critical data and re-run applicable rules. A material change requires re-authorization.
- **Rule 14 — Exit integrity:** Every position must have a hard maximum-loss boundary, take-profit/management plan, time stop, DTE rule, and thesis-invalidation policy. AI cannot weaken hard exits.

### P4 — Strategy quality (trade economics)

- **Rule 6 — Expected value:** Calculate net expected value using realistic probabilities, expected profit/loss, fees, bid/ask cost, and estimated slippage. `REJECT` when net EV is below $+0.15\text{R}$, where R is the deterministic hard-stop risk for the trade. Do not use maximum theoretical option payoff as expected profit.
- **Rule 7 — Reward/risk:** Require a realistic reward/risk of at least $1.5{:}1$ using executable, probability-weighted outcomes.
- **Rule 15 — Strategy health / kill switch:** If strategy expectancy, execution quality, drawdown, data integrity, or reconciliation deteriorates beyond approved thresholds, reduce risk or halt new trades until recovery criteria are met.

### P5 — Optimization preferences

- **Rule 12 — Opportunity competition:** When multiple eligible trades compete for a finite risk budget, authorize only the highest-ranked candidates by net expected value, risk-adjusted return, reward/risk, evidence quality, portfolio fit, and execution quality. Do not execute every qualifying signal. Optimization may select among eligible trades but may never weaken a higher-priority rule.

## Quantitative trade economics and position sizing

- The maximum planned loss at the deterministic hard stop shall not exceed $1.0\%$ of current equity per new position. During VOLATILE conditions the maximum planned loss is reduced to $0.75\%$.
- Final executable allocation is the minimum of all applicable caps:

  $$\text{Final Allocation \%} = \min\left(\text{Target Alloc \%},\ \frac{\text{Max Risk per Trade \%}}{\text{Stop-Loss \%}},\ \text{Ticker Cap \%},\ \text{Sector/Cluster Cap \%},\ \text{Portfolio-Risk Cap \%},\ \text{Regime Cap \%},\ \text{Liquidity Cap \%},\ \text{Buying-Power Cap \%}\right)$$

  With a $50\%$ hard stop, a $1.0\%$ normal risk cap implies a $2.0\%$ normal allocation ceiling; with the $0.75\%$ volatile risk cap, a $1.5\%$ volatile allocation ceiling applies. The deterministic engine rounds down to the nearest executable contract size.
- A proposal must have net expected value $\ge +0.15\text{R}$ after estimated spread cost, slippage, fees, and other material execution costs.
- A proposal must have realistic reward/risk $\ge 1.5{:}1$ using executable, probability-weighted outcomes. Maximum theoretical option payoff shall not be used as expected profit.
- Aggregate modeled hard-stop risk across active and proposed positions shall not exceed $3.0\%$ of current equity. New trades must also satisfy ticker, sector, correlation, event, Delta, and Vega limits.
- AI Profile target allocation is a target, not permission to exceed hard risk caps. Final executable size is the minimum applicable constraint, including the $1.0\%$ normal / $0.75\%$ volatile risk-per-trade limits.

## Dynamic regime behavior

Market regimes act as a master override. They dynamically alter both deterministic rule ceilings and allowed option structures, temporarily superseding the active AI Profile to protect the portfolio.

| Regime state | Quantitative detection trigger | Deterministic rule and proposal overrides |
| :--- | :--- | :--- |
| **NORMAL** | Underlying IV Rank between $20\%$ and $50\%$. | System operates normally. Single-leg long calls/puts and debit spreads are permitted subject to the AI Profile's sizing constraints. |
| **VOLATILE** | Underlying IV Rank $> 50\%$ OR volume $> 2.0\times$ 20-day average. | Vega protection: single-leg options are strictly blocked to avoid IV crush; only defined-risk 1:1 debit spreads are permitted. Maximum position size is hard-capped at $1.5\%$ (target allocation), overriding the AI Profile, and the $0.75\%$ volatile risk-per-trade cap applies. |
| **EVENT** | Underlying has a scheduled earnings release or FDA binary event within the next 7 days. | Binary-risk block: new trade proposals for that ticker are automatically rejected to avoid holding through binary, unpredictable gaps. |
| **CRISIS** | Macro circuit breaker: SPY drops $> 3.0\%$ intraday OR VIX spikes $> 35$. | System halt: all new `TradeProposal` generation is suspended. Active positions default to their hard $50\%$ stop-loss or $\le 7$ DTE exits. |

Regardless of the active AI Profile, when the regime is VOLATILE the deterministic engine forces `target_position_size_pct` to a hard cap and restricts `option_structure` strictly to 1:1 debit spreads (no single-leg trades).

## Supported instruments

- **Options only:** The system trades options on highly liquid, large-cap US equities. Direct purchase or shorting of underlying equity shares is completely blocked to enforce the hackathon options-trading mandate.
- **Permitted structures:** Strategy selection must optimize the supported structure for the catalyst, IV state, DTE, Greeks profile, liquidity, maximum loss, realistic payoff, and expected value. "Cheapest premium" is not, by itself, an acceptable selection criterion.

| Options level | Permitted structure | Regime condition / notes |
| :--- | :--- | :--- |
| Level 2 | Long calls and long puts | Permitted only during NORMAL regimes where IV Rank $\le 50\%$. |
| Level 3 | 1:1 call and put debit spreads | Mandatory during VOLATILE regimes (IV Rank $> 50\%$) to mitigate vega crush. |

- **Explicitly blocked:** credit spreads (assignment/margin complexity in the Alpaca paper environment); naked short calls/puts; complex multi-leg structures exceeding 2 legs (iron condors, butterflies); 0-DTE contracts (minimum allowed expiration is 2 days out to prevent extreme intraday pin risk).

## Risk state model

- **NORMAL:** full active profile subject to hard limits.
- **CAUTION:** reduce effective new-risk budget and/or increase edge thresholds after material drawdown or early strategy deterioration.
- **DEFENSIVE:** permit only the highest-quality opportunities, use reduced sizing, and restrict marginal regimes/structures.
- **HALT:** block new risk while continuing position monitoring, reconciliation, audit, and mandatory exits.

## Authorized governance baseline

The BA has authorized the current operating controls. They cover risk-per-trade, liquidity, concentration, drawdown, exits, event restrictions, and AI Profile bounds. These controls are effective for the current ruleset version and are fully authorized for the current operating baseline. Hard controls are non-bypassable; AI Profiles may tune only within the configurable ranges defined by the active ruleset. A profile target may never override the $1.0\%$ normal / $0.75\%$ volatile risk-per-trade caps, the portfolio risk cap, concentration limits, liquidity restrictions, or drawdown states. Future changes require a versioned ruleset or profile change and must preserve the hard safety boundaries defined here.

### Active baseline parameter register

| Parameter | Active baseline | Purpose / note |
| :--- | :--- | :--- |
| Maximum risk per trade | $1.0\%$ of current equity | Hard risk budget per new position at the initial deterministic stop. |
| Normal target allocation | $2.0\%$ of equity | Balanced baseline target; final executable allocation remains risk-capped. |
| Volatile target allocation | $\le 1.5\%$ of equity | Defined-risk regime; subject to the separate $0.75\%$ per-trade risk cap. |
| Volatile risk per trade | $0.75\%$ of current equity | Additional protection when IV Rank $> 50\%$ or abnormal-volume regime is active. |
| Daily drawdown states | $1.5\%$ / $2.25\%$ / $3.0\%$ | CAUTION / DEFENSIVE / HALT from start-of-day equity; HALT blocks new risk. |
| Cash / buying-power buffer | $\ge 5.0\%$ | Non-bypassable liquidity reserve ($\$5{,}000$ at the $\$100{,}000$ baseline). |
| Ticker concentration | $\le 5.0\%$ | Existing + proposed allocated capital for one ticker. |
| Sector concentration | $\le 10.0\%$ | Aggregate allocated capital by sector. |
| Correlated cluster concentration | $\le 7.5\%$ | Aggregate exposure to highly correlated positions/factors. |
| Aggregate modeled hard-stop risk | $\le 3.0\%$ | Portfolio loss if all active hard stops were reached, before approving new risk. |
| Maximum open positions | 6 | Limits operational fragmentation and concentration of attention/capital. |
| Maximum bid/ask spread | $\le 10\%$ of premium | Execution-quality hard ceiling on the proposed contract(s); wider spreads fail Rule 10. |
| Data freshness | $\le 30$ seconds | Pricing/research timestamps must be within this window (Rule 1). |
| Opportunity / EV / reward gates | Score $\ge 75$; Balanced $\ge 84$; net EV $\ge +0.15\text{R}$; R:R $\ge 1.5{:}1$ | All gates must pass; score alone is never sufficient. |

## P&L and capital allocation objective

The system optimizes sustainable risk-adjusted net P&L rather than trade frequency or win rate alone. Trade selection favors positive expected value, attractive realistic reward/risk, efficient use of risk budget, and controlled drawdown. A `NO_TRADE` outcome is preferred whenever the estimated edge is insufficient after execution costs and portfolio effects. Winning trades must be allowed sufficient room to realize their modeled edge; losing trades must remain capped by deterministic risk controls.

## Decision quality acceptance criteria

- **AC-01:** A negative-EV candidate is rejected after net execution costs.
- **AC-02:** A candidate below the reward/risk floor is rejected or modified.
- **AC-03:** A candidate breaching ticker/sector/correlation exposure is modified or rejected.
- **AC-04:** Stale or inconsistent market/option data prevents execution.
- **AC-05:** A material pre-submit market change forces re-authorization.
- **AC-06:** Losses never trigger increased sizing for recovery.
- **AC-07:** Every completed trade records gross/net P&L, realized/unrealized effects, entry/exit, holding period, exit reason, and audit trace.
- **AC-08:** Post-analysis recommendations cannot change hard limits or activate outside authorized ranges.
- **AC-09:** Rejected opportunities are eligible for ShadowFund evaluation without creating an execution path.
- **AC-10:** The same versioned inputs and ruleset reproduce the same deterministic authorization result.

## Hackathon operating configuration

This is a distinct, hackathon-specific operating configuration that coexists with the authorized governance baseline. It is applied only when the hackathon config is the active ruleset; it does not replace the [Active baseline parameter register](#active-baseline-parameter-register). Where a value below differs from the authorized baseline, the difference is intentional and scoped to the hackathon and is called out in the notes.

| Rule | Hackathon setting | Note vs authorized baseline |
| :--- | ---: | :--- |
| Maximum hold | **4 trading days** | Tighter than the baseline `max_hold_days` default of 14 calendar days; within the approved safety range $[3, 45]$ days. |
| Primary P&L evaluation | **4 trading days** | Hackathon-specific primary evaluation window. |
| ShadowFund primary horizon | **4 trading days** | Differs from the baseline ShadowFund horizons (intraday and 1-week / 5 trading days); see `SHADOWFUND.md` [Evaluation windows](SHADOWFUND.md#evaluation-windows). |
| DTE exit | **$\le 7$ DTE** | Same as baseline. |
| 0-DTE | **Blocked** | Same as baseline (minimum expiration is 2 days out). |
| Early thesis invalidation | **Immediate exit** | Same as baseline (deterministic Early Thesis Exit on contradictory news). |
| Hard stop | **50% of initial debit** | Same as baseline (fixed $50\%$ stop-loss). |
| Take profit | **75% Balanced / up to 100% Aggressive** | Same as baseline (`take_profit_pct` range $[75\%, 100\%]$). |

The hard safety controls (risk-per-trade caps, concentration limits, drawdown states, liquidity reserve, instrument restrictions, and mandatory exits) remain unchanged under this configuration. Only the hold duration and evaluation/ShadowFund horizons are shortened for the hackathon.
