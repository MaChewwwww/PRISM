# Data and API contracts

Revision: `2026-08-29 / ecosystem-consolidation-v1`

Runtime models live in `backend/app/contracts` and `backend/app/presentation`. `backend/scripts/export_contracts.py` starts from `FastAPI.app.openapi()`, then merges exported domain schemas. Committed outputs are `backend/build/contracts.openapi.json` and `frontend/src/types/api.generated.ts`.

## Contract conventions

- Identifiers are stable UUID strings where domain identity requires them.
- Timestamps are timezone-aware UTC RFC3339 values.
- Financial, ratio, and percentage values cross trust boundaries as decimal strings.
- Enums are closed and typed; unknown members fail validation.
- Breaking shapes use a clean contract break; stale fixture aliases are not supported.
- Generated artifacts are regenerated, never edited by hand.
- Sensitive provider, account, credential, and raw error data is absent from presentation responses.

## Governance contracts

The BA registry is `backend/app/rules/authorized_baseline.v1.json`. Typed contracts cover ruleset identity, lifecycle, effective period, parameters, profile identity and compatibility, authorized profile ranges, rule priority, typed reason codes, rule traces, market regime, portfolio risk, and authorization bindings.

`ExitPolicy` requires a take-profit from 75% through 100%, a fixed 50% stop-loss, a DTE threshold from 2 through 14 days, and a holding limit from 3 through 45 days. The active Balanced defaults are 75% take-profit, 50% stop-loss, 7 DTE, and 14 days. The four-trading-day hackathon override is a separate active operating constraint.

The governance read model also exposes the registry-backed hackathon window as UTC timestamps: trading start, new-entry cutoff, official scoring point, force-flatten deadline, and outer boundary. `scoring_basis` is the closed value `total_account_equity`; the effective maximum hold is four trading days bounded by the scoring point.

## Decision semantics

| Scope | Values |
| --- | --- |
| Per-rule result | `PASS`, `MODIFY`, `FAIL` |
| Aggregate authorization | `APPROVE`, `REJECT`, `MODIFIED_PENDING_ACCEPTANCE` |

Only `APPROVE` may continue toward execution. `MODIFIED_PENDING_ACCEPTANCE` carries no authority. Accepting a modification creates a revised proposal and digest that must be authorized again.

## Endpoint catalog

| Method | Path | Purpose | Authentication |
| --- | --- | --- | --- |
| GET | `/api/v1/health/live` | Process liveness | No |
| GET | `/api/v1/health/ready` | Required configuration and database readiness | No |
| POST | `/api/v1/auth/login` | Seeded operator authentication; sets HTTP-only session cookie | No |
| GET | `/api/v1/auth/me` | Current operator session | Yes |
| POST | `/api/v1/auth/logout` | Clears session cookie | No |
| GET | `/api/v1/system/status` | Redacted operational state | Yes |
| POST | `/api/v1/research/news/analyze` | Non-authoritative structured news research | Yes |
| POST | `/api/v1/research/reaction/analyze` | Non-authoritative market-reaction and mispricing research | Yes |
| GET | `/api/v1/presentation/overview` | Illustrative overview | Yes |
| GET | `/api/v1/presentation/decisions` | Illustrative decision collection | Yes |
| GET | `/api/v1/presentation/decisions/{decision_id}` | Decision story and trace | Yes |
| GET | `/api/v1/presentation/portfolio` | Illustrative chosen path and comparisons | Yes |
| GET | `/api/v1/presentation/alternatives` | Shadow/simulated alternative collection | Yes |
| GET | `/api/v1/presentation/alternatives/{session_id}` | Alternative detail | Yes |
| GET | `/api/v1/presentation/news` | Illustrative news collection | Yes |
| GET | `/api/v1/presentation/agents` | Canonical agent and authority roster | Yes |
| GET | `/api/v1/presentation/agents/{agent_id}` | Agent detail | Yes |
| GET | `/api/v1/presentation/governance` | Active ruleset, profile, and semantics | Yes |
| GET | `/api/v1/presentation/weekly-summary` | Manual-review profile recommendations | Yes |
| GET | `/openapi.json` | OpenAPI paths and schemas | No |

Collection endpoints require `from` and `to` query parameters. Both must be timezone-aware UTC timestamps, and `from` must not be later than `to`.

## Presentation metadata and provenance

Every presentation response includes metadata with:

- `generated_at`;
- `as_of`;
- requested UTC `from` and `to` calendar-date range derived from the validated timestamps;
- `data_mode`;
- `fixture_version`.

The current adapter always returns `data_mode=illustrative_fixture` and `fixture_version=prism-demo-v1`. No response implies an Alpaca account request, paper order, fill, holding, P&L record, or provider/model invocation.

## News-analysis endpoint

The implemented news endpoint is non-authoritative research. It uses authenticated access, structured response validation, cached analysis records, classified transient retries in a worker thread, and redacted provider errors. Retries never block the event loop and never turn an AI result into execution authority.

## Market-reaction endpoint

`POST /api/v1/research/reaction/analyze` retrieves a bounded historical stock-bar window through the server-side Alpaca read adapter, computes deterministic reaction metrics, and asks the provider-neutral LLM gateway for a structured thesis and limitations. The response is a `ResearchReport` with decimal-safe actual/expected reaction, reaction gap, volume ratio, classification, and opportunity-score fields. It is non-authoritative and cannot authorize or submit an order. Research-report caching uses the Alembic-managed `research_reports` table and remains best-effort.

## Error and authorization boundaries

Errors expose stable, safe machine codes and redacted summaries. Provider response bodies, credentials, account details, and raw exception strings are not returned. Authorization binds proposal and payload digests, ruleset/profile versions, snapshot digests, rule trace, decision time, and allowed payload.

## Generation workflow

Run `pnpm contracts` after contract changes. CI runs `pnpm contracts:check`; any generated diff fails the check. Repository governance checks compare the presentation catalog with OpenAPI paths and verify registry/document consistency.
