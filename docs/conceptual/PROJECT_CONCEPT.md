# PRISM project concept

Revision: `2026-08-29 / ecosystem-consolidation-v1`

**One signal. Multiple perspectives. Better decisions.**

## Executive overview

PRISM helps an authenticated operator turn a fast-moving market event into a decision that can be understood, challenged, and audited. It combines several AI perspectives with a deterministic safety gate, then records why the outcome was to act, change the proposal, reject it, or do nothing.

**The core idea:** AI broadens the analysis; deterministic code controls authorization. Any order is Alpaca paper-only. Live trading is prohibited.

PRISM brings the full decision lifecycle into one governed product: evidence gathering, multi-perspective analysis, trade proposal or `NO_TRADE`, adversarial risk review, deterministic authorization, paper execution, counterfactual comparison, and controlled learning.

This document describes the complete product concept. Delivery progress is tracked separately in the [Implementation Plan](../IMPLEMENTATION_PLAN.md). During development and demonstrations, any `illustrative_fixture` data must be clearly labeled and must never be represented as an Alpaca account, paper order, fill, holding, profit-and-loss record, or model invocation.

## The problem PRISM addresses

Market events are easy to oversimplify. A positive headline does not automatically mean buy, and a negative headline does not automatically mean sell. A useful decision also depends on questions such as:

- Is the event important enough to matter?
- Has the market already priced it in?
- Does price, volume, volatility, or peer behavior confirm the story?
- Is the trade economically attractive after spread and execution costs?
- Does the position fit the portfolio's risk, concentration, liquidity, and time limits?

Most tools answer only part of this chain. PRISM is designed to connect the evidence, the recommendation, the challenge, the governing rules, and the eventual outcome into one decision story.

## Product vision

PRISM is a governed decision journal for paper trading. Its purpose is to:

- reduce single-perspective and headline-driven decisions;
- make both action and restraint explainable;
- enforce risk controls consistently, even when AI is unavailable or wrong;
- preserve a reviewable record of the evidence, rule checks, and outcome;
- compare the chosen path with credible alternatives without risking capital; and
- turn completed decisions into bounded, reviewable improvement proposals.

PRISM is not a live-trading product, a promise of profit, or a black-box system that lets an AI place orders. It is also not designed to maximize trade frequency. `NO_TRADE`, `REJECT`, and incomplete evidence are valid outcomes.

## Who the product serves

| Audience | What they need | What PRISM provides |
| --- | --- | --- |
| Operator | A clear view of what happened, what the system recommends, and what is allowed | An authenticated, story-first workspace with evidence, decisions, rules, and outcomes |
| Reviewer or judge | Confidence that the demonstration is truthful and governed | Explicit data provenance, fixed rules, paper-only boundaries, and auditable decision traces |
| Product, risk, and engineering team | A shared view of scope, controls, and progress | Versioned requirements, contracts, tests, and one consistent product baseline |

## How a decision moves through PRISM

```text
market signal and current context
  -> seven specialist perspectives
  -> TradeProposal or NO_TRADE
  -> AI-assisted risk challenge
  -> deterministic rule checks
  -> APPROVE | REJECT | MODIFIED_PENDING_ACCEPTANCE
  -> Alpaca paper execution only for APPROVE
  -> ShadowFund comparison
  -> Post-Analysis batch and bounded profile-review path
```

In plain language:

1. PRISM captures a catalyst and the relevant market context.
2. Seven specialists examine the same opportunity from different angles.
3. The Trading Decision Agent proposes a supported paper option structure or ends with `NO_TRADE`.
4. AI-assisted Risk Management challenges the proposal and highlights portfolio or market concerns.
5. Deterministic rules decide whether the exact proposal is permitted.
6. Only `APPROVE` may proceed to paper execution.
7. ShadowFund compares alternative choices on the same subsequent market path.
8. Post-Analysis persists one immutable batch; the current implementation records `NO_RECOMMENDATION` until evidence-qualified recommendations are available.

Every stage uses structured, versioned records. Missing, stale, contradictory, or invalid evidence reduces confidence or stops the workflow; it never creates permission to trade.

## The seven specialist perspectives

The order and responsibilities below are canonical.

| Specialist | Question it answers | Limit |
| --- | --- | --- |
| News Agent | What happened, when, from which source, and with what uncertainty? | Research only |
| Quantitative Agent | What do price, volume, volatility, liquidity, options data, and historical behavior show? | Research only |
| Industry Agent | How does the event compare with peers, the sector, supply chain, and competitors? | Research only |
| Fundamental Agent | What does it mean for earnings, valuation, balance-sheet quality, and company outlook? | Research only |
| Macroeconomic Agent | How do rates, policy, indexes, volatility, and the wider regime affect the opportunity? | Research only |
| Market Reaction/Mispricing Agent | Is the observed market reaction justified, excessive, insufficient, or unclear? | May identify an edge or `NO_CLEAR_EDGE`; cannot authorize |
| Trading Decision Agent | Is there a supported, economically credible proposal, or should the system choose `NO_TRADE`? | Proposal only |

These specialists are followed by distinct responsibilities:

- **Risk Management** challenges the proposal but cannot approve it.
- **Rules Engine** is deterministic and owns authorization.
- **Execution** may translate only an approved, unchanged payload into a paper order.
- **ShadowFund** evaluates alternatives and has no trading authority.
- **Post-Analysis** persists a bounded batch after scoring or a completed backtest. The current implementation records `NO_RECOMMENDATION` until an evidence-qualified recommendation producer is available.

No AI agent, browser route, prompt, developer tool, or maintenance script may bypass the Rules Engine.

## Decision outcomes in plain language

Each rule returns one result:

- `PASS`: the proposal satisfies that rule.
- `MODIFY`: a specific safe change is possible, such as reducing position size.
- `FAIL`: the proposal cannot proceed under the active rules.

The combined decision is:

- `APPROVE`: the exact proposal is authorized.
- `REJECT`: the proposal is blocked.
- `MODIFIED_PENDING_ACCEPTANCE`: a safer revision has been suggested, but it has no authority yet.

A modification is never treated as approval. If the operator accepts it, PRISM creates a new proposal and evaluates it again.

## Safety model

Safety is a product feature, not a background technical detail.

- **Paper-only:** every genuine execution target must be an Alpaca paper account. Live mode is rejected.
- **Disabled by default:** execution and autonomous scheduling are off unless explicitly configured.
- **AI cannot authorize:** AI produces research, proposals, critiques, or recommendations. Deterministic code makes the final decision.
- **Fail closed:** stale data, missing configuration, invalid output, mismatched records, unsupported permissions, or uncertain provider state results in no order.
- **Exact binding:** an authorization is tied to the proposal, ruleset, AI Profile, market and portfolio snapshots, allowed order payload, decision time, and expiry.
- **Last-moment checks:** execution must recheck paper mode, kill switch, freshness, permissions, buying power, contract activity, and the exact payload.
- **No credentials in the browser:** Alpaca and LLM secrets remain server-side.
- **Auditable and repeatable:** versioned inputs and rules produce a traceable result; ambiguous submissions are reconciled by client order ID instead of blindly retried.

## What the operator experiences

PRISM presents decisions as stories rather than as backend modules.

| Surface | Purpose |
| --- | --- |
| Overview | Summarize decision activity, portfolio context, outcomes, and recommendations |
| Decision Stories | Explain catalyst -> perspectives -> proposal -> risk -> rule outcome -> lesson |
| Portfolio | Compare the chosen path with other tracked paths and exposures |
| Alternatives | Review ShadowFund counterfactual branches, results, and limitations |
| News and catalysts | Inspect event evidence, significance, and related decisions |
| Market Tracker | Pair price charts with fills, orders, proposals, decisions, `NO_TRADE`, and shadow events |
| Agents and tools | Show specialist roles, concise rationale, versions, latency, and recorded tool use |
| Rules | Explain the active ruleset, decision meanings, profiles, and hackathon window |
| Weekly Summary | Present Post-Analysis findings and profile suggestions for manual review |

The workspace is authenticated, uses a consistent UTC date range, supports responsive layouts, and treats provenance as part of the content. Labels such as **Alpaca paper**, **ShadowFund**, **Benchmark**, and **Simulated** are reserved for data that genuinely came from those sources.

## Authorized operating guardrails

The active ruleset is `prism-authorized-baseline@2.0.0`, with Balanced as the default AI Profile. The machine-readable source is `backend/app/rules/authorized_baseline.v1.json`.

| Area | Authorized guardrail |
| --- | --- |
| Capital baseline | 100,000.00 USD reference baseline; not a claim about an account balance |
| Position target | 2.00% of equity in NORMAL conditions; 1.50% maximum in VOLATILE conditions |
| Risk per trade | 1.00% of current equity in NORMAL; 0.75% in VOLATILE |
| Portfolio protection | At least 5.00% cash reserve; no more than 6 open positions; modeled hard-stop risk no more than 3.00% |
| Concentration | Ticker 5.00%; sector 10.00%; correlated cluster 7.50% maximum |
| Drawdown response | CAUTION at 1.50%; DEFENSIVE at 2.25%; HALT at 3.00% start-of-day drawdown |
| Evidence quality | Market and evidence freshness no more than 30 seconds |
| Execution quality | Bid/ask spread no more than 10.00% of premium |
| Opportunity quality | Absolute score floor 75; Balanced threshold 78 |
| Economics | Net expected value at least +0.15R and realistic reward/risk at least 1.50:1 |
| Standard exit | Balanced take-profit 75.00%; fixed stop-loss 50.00%; DTE exit default 7 days |
| Holding period | Reusable baseline 14 days; separate hackathon override 4 trading days |

The initial instrument scope is deliberately narrow: long calls, long puts, and two-leg 1:1 long call or put debit spreads. Options use whole contracts, `day` time in force, active contracts, and no extended-hours trading. Naked shorts, credit spreads, equity legs, rolls, unsupported permissions, and unverified account capabilities are rejected.

When IV Rank is above 50%, deterministic policy requires a defined-risk 1:1 debit spread and applies the tighter volatile allocation and risk caps.

## Hackathon operating window

The fixed hackathon window is separate from the reusable baseline rules.

| Control | Authorized time and meaning |
| --- | --- |
| Trading start | Monday Aug 31, 2026 at 09:30 ET |
| New-entry cutoff | Wednesday Sep 2, 2026 at 16:00 ET; no new positions after the close |
| Official scoring and force-flatten | EOD Thursday Sep 3, 2026; close all positions and score total account equity |
| Outer boundary | Friday Sep 4, 2026 at 09:30 ET; a window edge only, not extra holding or scoring time |

The new-entry cutoff preserves enough time for positions to be managed before scoring. The effective hold is the earlier of 4 trading days or the Sep 3 scoring point. Take-profit, fixed stop-loss, DTE, thesis invalidation, and the block on settlement exposure may close a position sooner.

## AI Profiles and controlled learning

AI Profiles express strategy preference inside non-negotiable rules. They cannot weaken a hard safety limit.

| Profile | Target allocation | Opportunity threshold | Take-profit | Stop-loss |
| --- | ---: | ---: | ---: | ---: |
| Conservative | 1.50% | 85 | 75.00% | 50.00% fixed |
| Balanced | 2.00% | 78 | 75.00% | 50.00% fixed |
| Aggressive | 2.50% | 75 | 100.00% | 50.00% fixed |

Post-Analysis may recommend changes only to target size, opportunity threshold, take-profit, and the fixed stop-loss field. Recommendations must stay within authorized bounds and pass deterministic validation. A supplied, complete draft batch may be activated manually or automatically only when the authenticated operator's persisted preference is automatic; the current implementation records `NO_RECOMMENDATION` until an evidence-qualified recommendation producer is available.

## Technology and trust boundaries

The product uses a Next.js web application, a FastAPI backend, PostgreSQL with Alembic migrations, and optional Redis caching. Alpaca and LLM providers sit behind server-side adapters.

```text
operator browser
  -> authenticated Next.js server
  -> FastAPI application
  -> database, provider-neutral AI adapters, and server-only Alpaca adapters
```

The browser never receives Alpaca or LLM credentials and never calls Alpaca directly. Financial values cross API boundaries as decimal strings, timestamps are UTC, and generated contracts keep the frontend and backend aligned.

## Delivery workstreams

1. **Governed foundation:** business-rule registry, contracts, authentication, migrations, CI/CD, deployment, and audit-ready records.
2. **Decision intelligence:** all seven specialists, structured evidence, proposals, risk assessments, and the full deterministic evaluator.
3. **Portfolio and alternatives:** portfolio snapshots, exposure calculations, and ShadowFund valuation on a shared market path.
4. **Paper execution:** Alpaca paper submission, reconciliation, kill-switch behavior, authorization rechecks, monitoring, and opt-in integration tests.
5. **Controlled learning:** Post-Analysis batch evidence, bounded profile recommendations when available, deterministic validation, and manual or operator-configured automatic activation.

Each milestone must preserve paper-only operation, truthful provenance, deterministic authority, and testable failure behavior.

## Success criteria

PRISM succeeds when:

- an operator can understand why the system acted, changed course, rejected a proposal, or chose `NO_TRADE`;
- every decision is traceable to timestamped evidence, a ruleset version, and an AI Profile version;
- the same valid inputs and rules produce the same authorization result;
- no AI or browser path can bypass deterministic controls;
- every real provider, paper, shadow, benchmark, and simulated result is labeled truthfully;
- rejected and modified opportunities remain available for learning without forcing execution;
- Markdown, DOCX, requirements, contracts, generated types, implementation, and tests stay synchronized; and
- the product remains usable and accessible on mobile, tablet, and desktop.

Availability and latency SLOs, backup retention, RPO, and RTO are still unresolved. They must not be guessed or presented as commitments until their owners approve them.

## Key risks and dependencies

- **Data access and freshness:** Alpaca entitlements, provider availability, and thin options markets can limit evidence quality.
- **Provenance confusion:** illustrative data could be mistaken for real performance unless labels remain prominent.
- **AI variability:** structured validation, evidence requirements, and fail-closed behavior are essential because model output can be incomplete or wrong.
- **Execution risk:** paper submission must remain disabled until authorization, reconciliation, monitoring, and negative-path tests are complete.
- **Operational decisions:** service targets and recovery objectives remain owner decisions.

## Source of truth

This concept is an explanatory document. If it conflicts with a higher-authority source, the higher-authority source wins and both concept formats must be updated.

The authority order is repository invariants -> BA requirements and versioned numerical register -> AI architecture -> API contracts -> implementation and tests -> this concept.

Start with the [documentation index](../README.md), then use [Governance Traceability](../GOVERNANCE_TRACEABILITY.md), [Functional and Non-Functional Requirements](../FRS_NFRS.md), [Business Rules](../BUSINESS_RULES.md), [AI Agents](../AI_AGENTS.md), [AI Profiles](../AI_PROFILES.md), [Architecture](../ARCHITECTURE.md), and [Data and API Contracts](../DATA_API_CONTRACTS.md) for authoritative detail.
