# ShadowFund

ShadowFund is PRISM's non-executable counterfactual evaluation boundary. It compares alternate choices against the same subsequent market path without submitting, amending, or cancelling broker orders.

The current skeleton exposes an `illustrative_fixture` presentation of ShadowFund branches. It does not implement valuation, persistence, provider ingestion, or a paper-account adapter, and it must not be described as a completed engine.

## Future lifecycle

1. A completed authorization or significant rejection creates an immutable evaluation root.
2. Each branch changes exactly one declared decision variable and references the same evidence/snapshot lineage.
3. Timestamped market observations are normalized with source, freshness, and valuation policy.
4. Every comparable branch is valued under the same deterministic policy.
5. Branches close at the configured horizon or a deterministic exit.
6. Results become asynchronous Post-Analysis evidence; they never create execution authority or activate a profile.

## Canonical branches

| Branch | Variation | Provenance label |
| --- | --- | --- |
| Cash / no action | No position | `ShadowFund` when produced by the engine; `Illustrative fixture` in the current dataset |
| Half size | Same structure at 0.5x allocation | Same rule |
| Unhedged or contrarian | Explicit alternate structure/direction | Same rule |
| Specialist alternative | A declared alternative extracted by Trading Decision | Same rule |

Additional branches require versioned definitions. Counterfactuals never weaken the deterministic gate.

## Metrics and assumptions

A completed branch records gross/net P&L, maximum adverse/favorable excursion, drawdown, exposure duration, capital at risk, fill/valuation confidence, data completeness, and comparison delta. Options retain intrinsic/extrinsic assumptions, spread width, expiration proximity, and mark method.

Inputs may arrive late or incomplete. Missing inputs produce an explicit incomplete outcome, never a favorable imputation. Money, quantities, percentages, and ratios are decimal strings at API boundaries; timestamps are UTC.

## Evaluation horizons

The reusable evaluation policy supports intraday and five-trading-day views. The hackathon operating configuration uses a primary four-trading-day horizon to match its tighter holding override while retaining the intraday view. Counterfactual branches are evaluated through the official scoring point of total account equity at EOD Thursday Sep 3, 2026; the agent starts Monday Aug 31 at 09:30 ET. This does not replace the separate 14-day baseline position holding limit.

## Limitations

Shadow results are simulations. They do not reproduce market impact, queue position, all latency, partial fills, price improvement, assignment, fees, or thin-options liquidity. Every result must disclose its coverage, valuation policy, and uncertainty.

## Safety boundary

ShadowFund cannot submit orders or authorize proposals. Post-Analysis can recommend changes only to the bounded AI Profile fields in `AI_PROFILES.md`; deterministic validation and manual review remain mandatory.
