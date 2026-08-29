# PRISM architecture

Revision: `2026-08-29 / ecosystem-consolidation-v1`

PRISM is a paper-only, auditable decision platform. It separates specialist AI analysis from deterministic authorization and broker execution. The current repository is a contract-aligned skeleton: it implements a news-analysis slice, typed domain boundaries, authenticated illustrative presentation APIs, a generated frontend transport contract, and deployment foundations. Full orchestration, persisted portfolio services, ShadowFund evaluation, and paper order execution remain future work.

## Authority and dependency direction

```text
repository invariants
  -> BA process and versioned numerical register
  -> AI topology and responsibilities
  -> API contracts
  -> implementation and tests
  -> explanatory concept documents
```

Within the backend:

```text
API and schedulers -> application services -> domain rules and ports -> adapters
```

Domain contracts and deterministic policies do not import FastAPI, Alpaca, LLM clients, or frontend code.

## Canonical decision topology

The seven specialist stages are canonical and ordered:

1. News Agent
2. Quantitative Agent
3. Industry Agent
4. Fundamental Agent
5. Macroeconomic Agent
6. Market Reaction/Mispricing Agent
7. Trading Decision Agent

Their outputs then pass through:

8. AI-assisted Risk Management
9. Deterministic Rules Engine
10. Paper Execution, only after a valid `APPROVE`
11. ShadowFund counterfactual evaluation
12. Asynchronous Post-Analysis recommendations

The specialists may run independent evidence work where dependencies allow, but the Market Reaction/Mispricing and Trading Decision stages synthesize validated inputs. No AI stage owns execution authority.

```text
signal and market snapshot
  -> seven specialist perspectives
  -> TradeProposal or NO_TRADE
  -> AI-assisted risk critique
  -> deterministic rule trace
  -> APPROVE | REJECT | MODIFIED_PENDING_ACCEPTANCE
  -> paper execution only for APPROVE
  -> ShadowFund evaluation
  -> asynchronous Post-Analysis recommendation
```

Per-rule results are `PASS`, `MODIFY`, or `FAIL`. A modification never authorizes execution. Operator acceptance creates a revised proposal, new digest, and new authorization evaluation.

## System context

```text
Operator browser
  -> Next.js server and authenticated session forwarding
  -> FastAPI modular monolith
       -> PostgreSQL through an Alembic-managed schema
       -> optional Redis cache
       -> Alpaca data adapter through alpaca-py, future broader integration
       -> gated Alpaca paper execution adapter, future activation
       -> provider-neutral LLM adapter
```

The frontend receives neither Alpaca nor LLM credentials and never calls Alpaca directly.

## Backend boundaries

| Boundary | Responsibility | Current state |
| --- | --- | --- |
| `contracts` | Typed proposal, risk, governance, authorization, execution, profile, and audit records | Implemented skeleton |
| `rules` | Versioned BA registry and deterministic policy boundary | Registry and typed boundary implemented; full evaluator deferred |
| `research` | Provider-normalized evidence and structured research | News-analysis endpoint implemented; full specialist orchestration deferred |
| `presentation` | Backend-owned illustrative read models | Implemented with versioned fixture adapter |
| `proposal` | Trading Decision proposal synthesis | Contract only / deferred |
| `risk` | AI-assisted adversarial critique | Contract/presentation only / deferred |
| `market` | Alpaca market/news adapter | Partial news slice |
| `portfolio` | Durable snapshots and exposure calculations | Deferred |
| `execution` | Final paper checks, translation, idempotency, reconciliation | Validation skeleton; submission deferred and disabled |
| `shadowfund` | Immutable counterfactual branches and evaluation | Presentation fixture only / deferred engine |
| `audit` | Append-oriented decision and execution events | Contract only / deferred persistence |

## Presentation skeleton

All frontend story surfaces load through one server-side adapter typed from generated OpenAPI. Authenticated backend presentation endpoints expose fixed `illustrative_fixture` data with `generated_at`, `as_of`, requested UTC range, and fixture version. The fixture adapter is replaceable by later persisted and Alpaca-backed repository implementations, but those adapters are not implemented here.

Presentation data never claims a broker call, paper fill, account holding, or LLM invocation. Stable fixture decision IDs and UTC range URLs preserve cross-page trace navigation.

## Hackathon operating window

The BA-owned registry also carries the fixed-date hackathon window. It starts Monday Aug 31, 2026 at 09:30 ET, stops new entries at Wednesday Sep 2, 2026 16:00 ET, scores total account equity at EOD Thursday Sep 3, 2026, and force-flattens by that close. Friday Sep 4 at 09:30 ET is an outer boundary only. The presentation governance endpoint exposes the registry's UTC timestamps and the human-readable ET controls; future deterministic authorization must enforce them. No Sep-3-expiring contract may be held into settlement.

## Authorization binding

An authorization decision binds at least:

- proposal identifier, version, and digest;
- ruleset identifier and version;
- AI Profile identifier and version;
- market and portfolio snapshot digests;
- allowed payload digest;
- rule trace, decision time, and expiration.

Only `APPROVE` may reach the execution service. Before any future submission, execution must recheck paper mode, execution-enabled state, kill switch, authorization currency, payload digest, account and market freshness, permissions, buying-power inputs, contract activity, and client order ID.

## Database and readiness

Alembic owns schema creation. Application startup never calls `create_all()` and never swallows database initialization failures. Compose runs a one-shot migration service before the backend. Readiness checks required configuration and database connectivity; liveness reports process availability only.

## Failure posture

Missing rules, invalid profile compatibility, stale data, invalid AI output, unsupported permissions, unavailable required dependencies, ambiguous paper environment, or digest mismatch fail closed. Provider failures are classified and redacted. Monitoring and audit remain available when execution is disabled.

Automatic AI Profile switching is deferred. Post-Analysis recommendations are limited to authorized fields, require deterministic validation, and remain pending manual operator review.
