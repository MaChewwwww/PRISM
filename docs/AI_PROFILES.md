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

Examples of potentially profile-configurable values include active intraday `trading_windows` (within the 09:30–16:00 ET market boundary), opportunity confidence floor, preferred event categories, sizing preference within a hard cap, and stricter effective exposure targets. These remain illustrative until the BA identifies each field and its valid range.

## Recommendation and activation

Post-Analysis AI may propose changes with evidence, expected effect, uncertainty, and affected parameters. A deterministic validator rejects unknown fields, values outside approved ranges, incompatible rulesets, missing evidence, or attempts to weaken hard controls.

Manual Prescriptive mode is the initial supported activation model: an authorized operator applies, modifies, or rejects the recommendation. Automatic weekly activation is deferred and must not be inferred from scheduling infrastructure.

Every activation records the previous profile, new profile, recommendation, validation result, activation mode, actor, and timestamp. Historical decisions retain the profile version used at their decision time.
