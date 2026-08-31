# AI Profiles

Revision: `2026-08-29 / ecosystem-consolidation-v1`

An AI Profile is a versioned strategy-preference record inside deterministic hard limits. It is not portfolio/account state and cannot weaken a ruleset.

## Lifecycle

```text
draft recommendation -> deterministic validation -> manual review -> activation -> superseded
```

PRISM persists an append-oriented AI Profile lifecycle. The registry-backed Balanced profile is seeded on first use. A completed Post-Analysis batch may produce one bounded successor profile after every suggested authorized field is deterministically validated; unsuggested fields retain their active values. The previous active profile is superseded, never overwritten.

## Authorized fields and bounds

| Field | Minimum | Maximum | Notes |
| --- | ---: | ---: | --- |
| `target_position_size_pct` | 1.50% | 2.50% | A target only; hard portfolio and per-trade risk caps still apply. |
| `opportunity_score_threshold` | 75 | 95 | Minimum specialist synthesis score before proposal eligibility. |
| `take_profit_pct` | 75.00% | 100.00% | Must also satisfy realistic reward/risk of at least 1.5:1. |
| `stop_loss_pct` | 50.00% | 50.00% | Fixed hard exit; not tunable. |

## Standard profiles

| Field | Conservative | Balanced | Aggressive |
| --- | ---: | ---: | ---: |
| Target position size | 1.50% | 2.00% | 2.50% |
| Opportunity score | 85 | 78 | 75 |
| Take-profit | 75.00% | 75.00% | 100.00% |
| Stop-loss | 50.00% | 50.00% | 50.00% |

Balanced is the active default in ruleset `prism-authorized-baseline@1.0.0`. Final executable sizing is always the minimum of target allocation, per-trade stop-risk, ticker/sector/cluster/portfolio caps, regime, liquidity, and buying-power constraints.

## Compatibility and activation

Every profile identifies its version, lifecycle state, effective period, compatible ruleset, activation mode, and audit metadata. A deterministic validator rejects unknown fields, values outside the bounds, incompatible versions, missing evidence, or any attempt to change hard controls.

Post-Analysis may recommend only the four fields above. The authenticated operator selects `manual` or `automatic` calibration through the backend profile-governance API. New operator preferences default to `automatic`; an existing persisted preference is never silently changed. Manual activation requires an explicit authenticated `POST /api/v1/profiles/activate-post-analysis` request for a complete draft batch. Automatic activation is controlled solely by that persisted operator preference and remains bounded by deterministic validation. Neither mode can change an immutable ruleset or any hard control.

ShadowFund post-analysis runs automatically after market close every Friday (`weekly_friday_post_analysis`), after production official scoring/force-flatten, or upon a completed staging historical backtest. The `PostAnalysisAgent` evaluates weekly trading evidence and ShadowFund counterfactual branch marks to produce structured recommendations within the authorized parameter bounds; incomplete or empty evidence safely records a `NO_RECOMMENDATION` batch. Incomplete evidence cannot activate a profile. Profile, preference, and audit records contain no execution authority; the deterministic rule engine binds the selected profile ID/version into each authorization.

## Regime override

When the deterministic regime is VOLATILE, target position size is capped at 1.50%, planned risk is capped at 0.75% of current equity, and only supported 1:1 debit spreads are permitted. The override applies regardless of profile.
