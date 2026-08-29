# ShadowFund

ShadowFund is a multi-timeline counterfactual evaluation system. It records what an approved strategy would have done under alternate profile, rule, timing, or sizing choices without placing additional broker orders.

## 3-Layer Hybrid Architecture

ShadowFund organizes counterfactual analysis into three complementary tiers:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Trade-Level Scientific Counterfactuals (Deterministic Math)           │
│ • Actual Execution: Chosen paper order sent to Alpaca (e.g. Call Debit Spread)  │
│ • No-Action Baseline: 100% Cash allocation ($0 cost)                           │
│ • Sizing Variation: 0.5x Conservative Sizing allocation                         │
│ • Unhedged Structure: Single Long Option (Isolates IV crush & spread hedge)    │
├─────────────────────────────────────────────────────────────────────────────────┤
│ LAYER 2: Agent-Level Divergent Perspectives (Single-Prompt LLM Extraction)     │
│ • Extracted in the same Proposal Agent LLM pass with zero extra token roundtrip│
│ • Contrarian Fade: Directional reversal thesis (e.g. Put Debit Spread)         │
│ • Alternative Delta/DTE: Alternate expiry / strike candidate                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ LAYER 3: Portfolio-Level AI Profile Tournament (Post-Analysis AI Engine)       │
│ • Multi-Profile Cumulative Tracking: Conservative vs Balanced vs Aggressive    │
│ • Empirical Backtest Diffs: Computes Sharpe ratio, drawdown, and win rate      │
│ • Recommendation Engine: Generates AIProfileRecommendation for operator review │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Lifecycle

1. A production proposal and its immutable inputs create a root shadow session.
2. The proposal embeds deterministic and LLM-extracted `shadow_candidates` in a single pass.
3. Each branch declares exactly one controlled variation and references its parent session.
4. Market observations from Alpaca are captured with source, event time, receipt time, and freshness.
5. The evaluator applies the same deterministic valuation policy to every comparable branch simultaneously.
6. Branches close at their declared horizon or on an explicit exit condition (TP, SL, DTE stop).
7. Results become evidence for an `AIProfileRecommendation`; they never activate configuration automatically.


## Data assumptions

- Quotes, trades, bars, news, and option-chain snapshots can arrive late or be incomplete.
- Options marks must record the selected valuation method, bid/ask width, and whether the market was crossed or stale.
- Corporate actions, symbol changes, contract adjustments, and market-calendar boundaries must be normalized before comparison.
- All event times are UTC RFC3339 timestamps. Money, price, quantity, and percentage decimals are serialized as strings.
- Missing inputs produce an explicit incomplete result; they are never silently imputed as a favorable fill.

## Counterfactual metrics

At minimum, a completed branch records gross and net P&L, maximum adverse/favorable excursion, drawdown, exposure duration, fill confidence, data completeness, and comparison delta against its parent. Options branches additionally retain intrinsic/extrinsic value assumptions, spread width, and expiration proximity.

## Evaluation windows

The proposal selects a versioned evaluation policy such as end-of-session, fixed elapsed time, event-resolution window, or option expiration. The policy must define calendar treatment, observation cadence, terminal price selection, and behavior when the terminal observation is unavailable. Exact BA-owned horizons remain **TBD**.

## Limitations and disclosures

Shadow results are simulations, not executable returns. Alpaca paper trading and ShadowFund do not model all market impact, queue position, latency, price improvement, regulatory fees, assignment risk, or liquidity constraints. Thin option markets can make midpoint-based results materially optimistic. Results must always show their data coverage and simulation limitations.

## Safety boundary

ShadowFund cannot submit, amend, cancel, or recommend an order directly. It can emit evidence and a recommendation candidate only; human activation and deterministic authorization remain separate steps.
