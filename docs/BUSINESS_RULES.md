# Business Rules

## Purpose and status

Deterministic rules are the authoritative trade gate. The BA owns rule intent, thresholds, precedence, exceptions, and acceptance cases. Those values are currently in progress; engineering must implement a configurable engine and fail closed when required configuration is absent.

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

The competition account starting capital baseline is established at $100,000.00 USD. Position concentration, order notional, portfolio cash buffer, drawdown, concurrent positions, liquidity, minimum confidence, data freshness duration, exit policy, and ShadowFund horizon remain BA/product TBDs. An absent mandatory value returns `RULESET_NOT_CONFIGURED`.

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

- **Take-Profit Rule ($\text{TP}$):** Automatically triggers a closing order when position unrealized profit reaches or exceeds the configured `take_profit_pct` (default: **$50.0\%$** of theoretical maximum profit). This captures the bulk of the move without suffering late-stage time decay.
- **Stop-Loss Rule ($\text{SL}$):** Automatically triggers a closing order when position loss reaches or exceeds the configured `stop_loss_pct` (default: **$50.0\%$** of initial debit paid), capping maximum capital loss per trade.
- **Time/DTE Rule (Gamma Pin Risk):** Force-closes any open option position when days-to-expiration reaches $\le \text{dte\_threshold}$ (default: **$\le 7\text{ days}$**), avoiding assignment risks and illiquid expiration dynamics.
- **Max Holding Duration:** Force-closes positions after `max_hold_days` elapsed sessions (default: **$14\text{ days}$**) if the reaction thesis has not materialized.

### AI Profile tunability and safety bounds

Exit parameters are configurable per active **`AIProfile`** (by the user or recommended via **Post-Analysis AI**), but must strictly adhere to the following deterministic safety envelope:

| Parameter | Default | Safe Approved Range | Enforcement Action on Breach |
| :--- | :---: | :---: | :--- |
| `take_profit_pct` | $50.0\%$ | $[20.0\%, 90.0\%]$ | Rejects profile activation if $< 20.0\%$ or $> 90.0\%$ |
| `stop_loss_pct` | $50.0\%$ | $[20.0\%, 75.0\%]$ | Rejects profile activation if $< 20.0\%$ or $> 75.0\%$ |
| `dte_threshold` | $7\text{ days}$ | $[2\text{ days}, 14\text{ days}]$ | Rejects if $< 2\text{d}$ (pin risk) or $> 14\text{d}$ |
| `max_hold_days` | $14\text{ days}$ | $[3\text{ days}, 45\text{ days}]$ | Rejects if $< 3\text{d}$ or $> 45\text{d}$ |

When Post-Analysis AI audits historical ShadowFund counterfactual sessions, it may generate an `AIProfileRecommendation` to adjust these parameters to optimize risk-adjusted returns (Sharpe ratio / win rate). The recommendation can be applied manually by the operator or automatically switched if guardrailed auto-tuning is enabled.


## Versioning and audit


Rulesets are immutable after activation. A decision stores the ruleset version, individual evaluations, input snapshot references, effective profile version, outcome, allowed payload digest, and expiration. Retired rules remain queryable for historical audit.
