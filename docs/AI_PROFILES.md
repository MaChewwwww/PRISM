# AI Profiles

Revision: `2026-08-29 / ecosystem-consolidation-v1`

An AI Profile is a versioned strategy-preference record inside deterministic hard limits. It is not portfolio/account state and cannot weaken a ruleset.

## Lifecycle

```text
draft recommendation -> deterministic validation -> manual review -> activation -> superseded
```

The current skeleton exposes recommendations and validation states as read-only illustrative data. Profile persistence and activation APIs are deferred. Automatic switching is not authorized for the MVP.

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
| Opportunity score | 90 | 84 | 80 |
| Take-profit | 75.00% | 75.00% | 100.00% |
| Stop-loss | 50.00% | 50.00% | 50.00% |

Balanced is the active default in ruleset `prism-authorized-baseline@1.0.0`. Final executable sizing is always the minimum of target allocation, per-trade stop-risk, ticker/sector/cluster/portfolio caps, regime, liquidity, and buying-power constraints.

## Compatibility and activation

Every profile identifies its version, lifecycle state, effective period, compatible ruleset, activation mode, and audit metadata. A deterministic validator rejects unknown fields, values outside the bounds, incompatible versions, missing evidence, or any attempt to change hard controls.

Post-Analysis may recommend only the four fields above. Manual Prescriptive mode is the only authorized activation model. An operator may review, edit, or reject a recommendation, but any edit must be validated before activation. Scheduling infrastructure does not imply approval or activation.

## Regime override

When the deterministic regime is VOLATILE, target position size is capped at 1.50%, planned risk is capped at 0.75% of current equity, and only supported 1:1 debit spreads are permitted. The override applies regardless of profile.
