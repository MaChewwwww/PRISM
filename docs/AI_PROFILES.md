# AI Profiles

## Definition

An AI Profile is a versioned set of strategy and risk preferences that operates inside platform hard limits and deterministic business-rule boundaries. It is not the Alpaca portfolio or account state.

## Lifecycle

```text
draft recommendation -> deterministic validation -> review/approval -> activation -> superseded
```

Each profile records `profile_id`, version, status, effective time, source recommendation, configurable parameters, ruleset compatibility, activation mode, creator/approver, and audit metadata. Only one profile may be active for a decision time.

## Governance levels

1. Platform hard limits are non-bypassable engineering controls.
2. Deterministic business rules define approved permissions, ceilings, floors, and configurable ranges.
3. The active AI Profile selects values only within those ranges.

The BA has authorized the configurable parameters, their bounds, and the standardized profiles below (see [Authorized profile schema and standardized profiles](#authorized-profile-schema-and-standardized-profiles)). Additional profile-configurable preferences include active intraday `trading_windows` (within the 09:30–16:00 ET market boundary), opportunity confidence floor, preferred event categories, sizing preference within a hard cap, expected-value threshold, entry-quality preference, trade-frequency preference, and regime sensitivity. Profiles may tune these only within active ruleset-defined bounds; hard limits, loss caps, instrument restrictions, and mandatory exits remain outside AI control.

## Recommendation and activation

Post-Analysis AI may propose changes with evidence, expected effect, uncertainty, and affected parameters. A deterministic validator rejects unknown fields, values outside approved ranges, incompatible rulesets, missing evidence, or attempts to weaken hard controls.

Manual Prescriptive mode is the initial supported activation model: an authorized operator applies, modifies, or rejects the recommendation. Automatic weekly activation is deferred and must not be inferred from scheduling infrastructure.

Every activation records the previous profile, new profile, recommendation, validation result, activation mode, actor, and timestamp. Historical decisions retain the profile version used at their decision time.

## Authorized profile schema and standardized profiles

### 1. Profile scope and hard boundaries

Post-Analysis AI may recommend changes to these parameters, but recommendations can never exceed the deterministic limits.

| Configurable parameter | Absolute minimum | Absolute maximum | Description |
| :--- | :---: | :---: | :--- |
| `target_position_size_pct` | $1.5\%$ | $2.5\%$ | Target capital allocation per trade; actual size remains subject to the $1.0\%$ normal / $0.75\%$ volatile risk caps and portfolio constraints. The authorized normal baseline (Balanced default) is $2.0\%$. |
| `opportunity_score_threshold` | $75$ | $95$ | Minimum Research Agent score required to enter the Proposal stage; higher profiles may require more. |
| `take_profit_pct` | $75.0\%$ | $100.0\%$ | Profit target measured against initial debit; the final target must satisfy the $1.5{:}1$ minimum realistic reward/risk. |
| `stop_loss_pct` | $50.0\%$ | $50.0\%$ | Hard maximum-loss threshold on initial debit, fixed at $50\%$; sizing is constrained so this stop does not exceed the per-trade risk cap. |

### 2. Standardized AI profiles

The system supports three versioned profiles. **Balanced** is the default for the hackathon MVP.

| Parameter | Conservative | Balanced (default) | Aggressive |
| :--- | :---: | :---: | :---: |
| `target_position_size_pct` | $1.5\%$ | $2.0\%$ | $2.5\%$ |
| `opportunity_score_threshold` | $90$ | $84$ | $80$ |
| `take_profit_pct` | $75.0\%$ | $75.0\%$ | $100.0\%$ |
| `stop_loss_pct` | $50.0\%$ | $50.0\%$ | $50.0\%$ |

> All profiles use a fixed $50\%$ hard stop-loss; sizing is constrained so this stop never exceeds the per-trade risk cap ($1.0\%$ normal / $0.75\%$ volatile). Profiles differ on allocation ($1.5\%$ / $2.0\%$ / $2.5\%$), selectivity (opportunity score $90$ / $84$ / $80$), and profit-taking (take-profit $75\%$ / $75\%$ / $100\%$). Final executable size for every profile remains the minimum of all applicable hard caps.

### 3. Dynamic regime overrides

Regardless of the active AI Profile, when the market regime is VOLATILE (underlying IV Rank $> 50\%$) the deterministic rules engine forces:

- `target_position_size_pct` is hard-capped at $1.5\%$ maximum.
- `option_structure` is restricted strictly to 1:1 debit spreads (no single-leg trades permitted).

Hard limits, loss caps, instrument restrictions, and mandatory exits remain outside AI control at all times.

## Deterministic profile validator gate

Before a recommended profile `v(N+1)` can be made active, it must pass an automated validation check. If any parameter breaches its hard boundary, the recommendation is flagged REJECTED and discarded immediately.

| Parameter | Allowed boundary range |
| :--- | :---: |
| Target position size | $[1.5\%, 2.5\%]$ |
| Opportunity score threshold | $[75, 95]$ |
| Take-profit target | $[75.0\%, 100.0\%]$ |
| Stop-loss limit | $[50.0\%, 50.0\%]$ |

## Activation modes

- **Manual Prescriptive mode (mandatory MVP default):** Post-Analysis AI generates an `AIProfileRecommendation` from ShadowFund and paper-trade performance. An administrator manually reviews the evidence on the command center and clicks Apply, Edit, or Reject before parameters update for the upcoming trading week.
- **Automatic Switching mode (opt-in):** If enabled by an admin, validated profile recommendations activate automatically ahead of Monday market open without human intervention. This mode remains deferred for the MVP and must not be inferred from scheduling infrastructure.

## Immutable activation audit

Every profile state change records an immutable row in PostgreSQL containing:

- `previous_profile_id`
- `new_profile_id`
- `recommendation_id`
- `activation_mode` (MANUAL vs AUTOMATIC)
- `approver_id`
- `timestamp`
