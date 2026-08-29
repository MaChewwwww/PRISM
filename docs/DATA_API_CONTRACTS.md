# Data and API Contracts

The canonical runtime models live in `backend/app/contracts`. Generated artifacts are committed at `backend/build/contracts.openapi.json` and `frontend/src/types/api.generated.ts`.

## Conventions

- Every domain record has `schema_version`, a UUID identifier, and `trace_id`.
- Timestamps are timezone-aware UTC RFC3339 values.
- Decimal values cross JSON boundaries as strings; binary floating point is not authoritative.
- Enums are closed and explicit. Unknown enum members fail validation until the contract is deliberately evolved.
- Additive compatible changes keep the schema version. Breaking semantic or structural changes increment it and require migration notes.
- Sensitive broker/account data is internal and absent from public status contracts.

## Domain schemas

The domain and API contracts define `HealthResponse`, `SystemStatus`, `LoginRequest`, `LoginResponse`, `AuthMeResponse`, `LogoutResponse`, `ResearchReport`, `TradeProposal`, `OptionLeg`, `OptionStrategy`, `RiskAssessment`, `RuleEvaluation`, `AuthorizationDecision`, `ExecutionReceipt`, `ShadowSession`, `AuditEvent`, `AIProfile`, `AIProfileRecommendation`, `HistoricalBar`, `HistoricalMarketDataRecord`, and `LLMEventAnalysis`. Their relationships follow the authority chain documented in [ARCHITECTURE.md](ARCHITECTURE.md).

## Historical market data and AI query caching

To optimize API throughput, avoid redundant token spend, and guarantee deterministic historical replays, historical market data queries and LLM event analysis results are persisted:

- **Historical Query Digest:** `HistoricalMarketDataRecord` uses a deterministic SHA-256 digest computed across `(symbol, data_type, timeframe, start_time, end_time)`.
- **Immutability & TTL Policy:**
  - *Completed historical intervals* (`end_time` prior to current session close) are marked `is_immutable = True` and cached indefinitely in PostgreSQL.
  - *Intraday / active quotes* respect `freshness_seconds` (ephemeral TTL in Redis / in-memory cache).
- **LLM Event Analysis Cache:** `LLMEventAnalysis` persists structured event classifications, sentiment, and significance scores keyed by `article_id` and raw text digest, preventing duplicate LLM evaluations of identical historical news items.


## Endpoint catalog

| Method | Path | Purpose | Auth Required |
| --- | --- | --- | --- |
| GET | `/api/v1/health/live` | Process liveness only | No |
| GET | `/api/v1/health/ready` | Dependency/configuration readiness | No |
| POST | `/api/v1/auth/login` | Seeded credentials authentication | No |
| GET | `/api/v1/auth/me` | Current authenticated operator session | Yes |
| POST | `/api/v1/auth/logout` | Terminate session and clear cookie | No |
| GET | `/api/v1/system/status` | Redacted operator status | Yes |
| GET | `/openapi.json` | Public OpenAPI document | No |

The status endpoint may expose readiness, paper mode, execution-enabled state, CLI availability/version, credential-presence booleans, account-verification state, and supported options level. It must never expose keys, account numbers, buying power, positions, orders, or raw provider errors.

## Error envelope

Application errors use:

```json
{
  "error": {
    "code": "stable_machine_code",
    "message": "safe operator-facing summary",
    "trace_id": "uuid",
    "details": {}
  }
}
```

`details` is optional, structured, and redacted. Validation errors retain field paths but never echo secrets.

## Idempotency and execution

Each executable proposal has a canonical payload digest. Every submission receives a persisted `client_order_id` before broker invocation. Retried or ambiguous submissions reconcile by that identifier and do not create a second order. Authorization binds the proposal digest, ruleset version, account snapshot, expiry, and decision state.

## Pagination and freshness

Future collections use opaque cursor pagination with stable ordering. Responses return `next_cursor` only when another page exists. Provider-derived records carry `observed_at`, `received_at`, source, and a freshness classification. Callers must not infer freshness from request time.

## Contract workflow

Run `pnpm contracts` after changing backend contracts. CI runs `pnpm contracts:check` and fails if regeneration changes committed output. Contract changes must update tests, this document, and any affected FRS/NFRS traceability.
