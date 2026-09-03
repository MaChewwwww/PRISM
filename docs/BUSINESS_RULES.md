# PRISM business rules

Revision: `2026-09-02 / performance-calibration-v2`

This document is the human-readable mirror of `backend/app/rules/authorized_baseline.v1.json`. The JSON registry is the only machine-readable numerical source. Changes require a new ruleset/profile version and synchronized contracts, tests, and documentation.

## Decision process

1. Seven specialist agents produce validated evidence.
2. Trading Decision emits `TradeProposal` or `NO_TRADE`.
3. AI-assisted Risk Management critiques the proposal and portfolio context.
4. Deterministic rules evaluate each rule as `PASS`, `MODIFY`, or `FAIL`.
5. Aggregation returns `APPROVE`, `REJECT`, or `MODIFIED_PENDING_ACCEPTANCE`.
6. Only `APPROVE` may proceed toward execution. An accepted modification creates a revised proposal and must be authorized again.
7. Any genuine execution target is Alpaca paper only. Execution is disabled by default; the production-shaped autonomous worker fails closed and records `NO_TRADE` until all live evidence, account, portfolio, option-chain, risk, and authorization gates pass.

## Active baseline parameter register

Ruleset: `prism-authorized-baseline@2.0.0`; lifecycle: `active`; effective from `2026-08-29T00:00:00Z`; open-ended until superseded; default profile: `balanced`.

| Parameter | Authorized value |
| --- | ---: |
| Starting-capital baseline | 100,000.00 USD |
| Maximum risk per trade, NORMAL | 1.00% of current equity |
| Maximum risk per trade, VOLATILE | 0.75% of current equity |
| Normal target allocation | 2.00% of equity |
| Volatile target allocation | 1.50% maximum |
| Drawdown CAUTION / DEFENSIVE / HALT | 1.50% / 2.25% / 3.00% from start-of-day equity |
| Cash / buying-power reserve | 5.00% minimum |
| Ticker concentration | 5.00% maximum |
| Sector concentration | 10.00% maximum |
| Correlated-cluster concentration | 7.50% maximum |
| Aggregate modeled hard-stop risk | 3.00% maximum |
| Maximum open positions | 6 |
| Maximum bid/ask spread | 10.00% of premium |
| Evidence/market-data freshness | 30 seconds maximum |
| Opportunity score | 75 absolute floor; Balanced 78 |
| Net expected value | +0.15R minimum after material execution costs |
| Realistic reward/risk | 1.50:1 minimum |
| Profit arm / trailing giveback / hard profit | +20.00% / 10 percentage points / +40.00% of initial strategy debit |
| Hard stop-loss | fixed -50.00% of initial strategy debit |
| Thesis invalidation | 2 completed failing deterministic-score cycles; or confirmed opposite signal |
| Stagnation time stop | 390 regular-session minutes if MFE is below +10.00% |
| DTE exit | 7 days default; authorized range 2 through 14 days |
| Baseline maximum hold | 14 days; authorized range 3 through 45 days |
| Hackathon maximum hold override | 4 trading days |

The 14-day value is the reusable baseline profile value. The four-trading-day value is the tighter hackathon operating override. They are not aliases and must be presented separately.

## Hackathon operating configuration

This is a distinct, hackathon-specific operating configuration. It keeps the BA baseline risk, concentration, liquidity, instrument, and exit controls unchanged while applying the four-trading-day hold override and the fixed evaluation window below. It does not replace the reusable 14-day baseline value.

### Hackathon evaluation window

The BA-authorized hackathon configuration follows the official evaluation window described in [PR #16](https://github.com/MaChew/PRISM/pull/16) (2026-08-29). Official P&L is measured on **total account equity**, not cash balance, at **EOD Thursday September 3, 2026**. The agent starts on **Monday August 31 at 09:30 ET**. **Friday September 4 at 09:30 ET** is only the outer window boundary and is not the scoring timestamp.

The four-session operating window is bounded as follows:

| Rule | Authorized setting | Operational meaning |
| --- | --- | --- |
| Trading start | Monday Aug 31, 2026 09:30 ET | First eligible entry time. |
| Official scoring point | EOD Thursday Sep 3, 2026; total account equity | The value used for the official P&L comparison. |
| Window outer boundary | Friday Sep 4, 2026 09:30 ET | Window edge only; it does not extend scoring or holding. |
| Effective maximum hold | Minimum of 4 trading days and the EOD Sep 3 scoring point | A late entry cannot run beyond the scoring point. |
| New-entry cutoff | Wednesday Sep 2, 2026 16:00 ET | No new positions after the Wednesday close; existing positions may only be managed or exited. |
| End-of-window force-flatten | By Thursday Sep 3, 2026 close | Close every position before settlement and score the resulting total equity. |

Every entry therefore has at least one full Thursday session of runway. The EV and realistic reward/risk gates still reject a proposal that cannot realize its modeled edge in the remaining window. The force-flatten supersedes the standard `max_hold_default_days` only for this hackathon configuration; hard stop, take-profit, DTE, thesis invalidation, and the 0-DTE block continue to apply earlier. A Sep-3-expiring contract must not be held into settlement because the force-flatten and DTE controls are mandatory.

### Autonomous run configuration

Autonomous paper execution is a production-only operational opt-in, not a replacement for this ruleset. `AUTONOMOUS_TRADING_ENABLED` defaults to `false`; in production, enabling it requires `EXECUTION_ENABLED=true`, an active ruleset, complete Alpaca paper credentials, and a UTC `AUTONOMOUS_TRADING_START_AT`/`AUTONOMOUS_TRADING_END_AT` pair. Production intervals must remain within the authorized hackathon trading start and force-flatten deadline. Staging rejects autonomous trading configuration and validates the system only through an explicitly enabled, non-executing historical backtest. Neither path may bypass paper mode, the kill switch, or mandatory rules.

ShadowFund does not alter BA numerical thresholds. It compares the legacy +75%/-50%, simple +30%/-50%, and adaptive 20/10/40 policies only where complete entry, path, and exit quotes exist. A missing historical/live observation is `DATA_UNAVAILABLE` / `INCOMPLETE`, never a simulated fill.

The production worker uses a 5-minute (300-second) cadence, seven-symbol allowlist, six-position cap, session advisory lock, mandatory exit checks, and durable kill switch. It does not manufacture evidence or orders; unavailable analog coverage, sourced fundamentals, stale data, incomplete quotes/Greeks, unavailable portfolio/regime controls, or an unverified deployment produce `NO_TRADE`. IV rank resolves from a current provider rank when present, otherwise durable observations, configured-provider observations, historical option-bar inversion when available, and the current option-chain observation. The effective minimum is reduced to the observations actually available; the older insufficient-history-only rejection is not reinstated. Existing OCC option positions are enriched from the live chain before sector/cluster/Greek/expiry checks. Historical analog returns are converted to option intrinsic payoffs and charged observed NBBO slippage and a deterministic spread-derived fill probability before the EV gate.

## Standard AI Profiles

| Profile | Target allocation | Opportunity threshold |
| --- | ---: | ---: | ---: | ---: |
| Conservative | 1.50% | 85 |
| Balanced | 2.00% | 78 |
| Aggressive | 2.50% | 75 |

Profile bounds are: allocation 1.50% through 2.50%; opportunity threshold 75 through 95. ExitPolicyV2 is ruleset-owned and is never profile-tunable.

## Deterministic priorities

| Priority | Gate | Required behavior |
| --- | --- | --- |
| P0 | Platform and authorization integrity | Reject live mode, disabled execution, kill switch, missing/invalid ruleset, incompatible profile, expired authorization, or digest mismatch. |
| P1 | Portfolio survival | Apply drawdown state, aggregate/ticker/sector/cluster concentration, cash reserve, max positions, and planned stop-risk controls. |
| P2 | Risk, instrument, and regime | Require a fresh acceptable AI risk assessment, permit only supported option structures and verified permissions, restrict VOLATILE to 1:1 debit spreads, and block CRISIS new risk. |
| P3 | Freshness and execution quality | Reject evidence older than 30 seconds and spreads wider than 10% of premium; validate active contracts and required snapshots. |
| P4 | Opportunity and economics | Require score, net EV, and realistic reward/risk gates independently. |
| P5 | Exit and payload completeness | Require ExitPolicyV2, strategy-level executable marking, DTE/holding controls, active ruleset identity, and an exact executable payload. |

`MODIFY` is valid only where a safe, deterministic revision can be described, such as reducing size to a concentration cap. A proposal that cannot be safely revised is `FAIL`. Aggregate modification state is `MODIFIED_PENDING_ACCEPTANCE`, never approval.

## Sizing and risk states

Final allocation is the smallest applicable limit among profile target, per-trade stop-risk, ticker cap, sector/cluster cap, aggregate portfolio-risk cap, regime cap, liquidity cap, and buying-power cap. With the fixed 50% stop, the 1.00% normal risk cap implies a 2.00% allocation ceiling, and the 0.75% volatile cap implies a 1.50% ceiling. Quantity rounds down to an executable whole-contract size.

## AI Profile activation governance

Post-Analysis can only propose the four profile fields in the active baseline register. A successor profile is valid only when its batch contains one or more unique authorized fields and every suggested value is within the registered bounds; any unspecified field retains the active value. Manual activation is an authenticated, audited backend action. Automatic calibration follows the authenticated operator's persisted database preference. Profiles cannot change the ruleset, hard limits, the paper-only boundary, or a previously issued authorization.

| State | Trigger | New-risk behavior |
| --- | --- | --- |
| NORMAL | Below 1.50% start-of-day drawdown | Normal authorized rules apply. |
| CAUTION | At least 1.50% | Reduce new-risk budget. |
| DEFENSIVE | At least 2.25% | Only highest-quality opportunities with reduced sizing. |
| HALT | At least 3.00% | Reject all new proposals. Mandatory exits still govern active positions. |

Market-regime detection details beyond authorized thresholds must remain versioned and testable. No martingale or loss-recovery sizing is permitted.

## Supported initial option envelope

Only long calls, long puts, and two-leg 1:1 long call/put debit spreads are in the initial envelope. Options use whole-contract quantities, `day` time in force, no extended hours, and active OCC contracts. Reject naked shorts, credit spreads, equity legs, rolls, more than two legs, unsupported approval levels, and unverified account capabilities.

## Exit behavior

Every position requires deterministic profit, loss, DTE, time, and thesis-invalidation exits under ExitPolicyV2. The calibrated adaptive profit policy arms at +20.00% return, trails by 10.00 percentage points of giveback from strategy MFE, and takes hard profit at +40.00%; the fixed stop-loss is -50.00% of initial strategy debit. Exits also trigger upon 2 completed thesis-invalidation cycles, stagnation time-stop (390 regular-session minutes if MFE < +10.00%), DTE threshold (7 days default), or hackathon max hold (4 trading days). The rules engine validates the policy before authorization, and autonomous monitoring applies mandatory exits independently of AI availability.

## Deliberately unresolved

Availability/latency SLOs, backup retention, RPO, RTO, and any numerical value absent from the versioned registry remain unresolved. Infrastructure examples do not authorize them.
