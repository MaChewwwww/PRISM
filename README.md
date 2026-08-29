<div align="center">

# PRISM

**One signal. Multiple perspectives. Better decisions.**

*A paper-only, auditable multi-agent market intelligence platform governed by deterministic rules.*

[![CI](https://github.com/MaChewwwww/Alpaca_AI_Hackaton/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MaChewwwww/Alpaca_AI_Hackaton/actions/workflows/ci.yml)
[![Paper trading only](https://img.shields.io/badge/trading-paper--only-0f766e.svg)](docs/SECURITY.md)

</div>

> [!IMPORTANT]
> Live trading is prohibited. Execution is disabled by default, and AI never authorizes an order. BA governance values are versioned in `backend/app/rules/authorized_baseline.v1.json`; values absent from that register remain unresolved.

## What PRISM does

PRISM decomposes one market signal through seven canonical specialists: News, Quantitative, Industry, Fundamental, Macroeconomic, Market Reaction/Mispricing, and Trading Decision. Their proposal then passes through AI-assisted Risk Management and a deterministic Rules Engine. Only a bound `APPROVE` may reach future Alpaca paper execution. ShadowFund and asynchronous Post-Analysis provide counterfactual evidence and bounded recommendations without execution authority.

```text
signal -> seven specialist perspectives -> proposal or NO_TRADE
       -> AI-assisted risk critique -> deterministic authorization
       -> paper-only execution when genuinely enabled
       -> ShadowFund -> asynchronous Post-Analysis
```

Per-rule outcomes are `PASS`, `MODIFY`, or `FAIL`. Aggregate authorization is `APPROVE`, `REJECT`, or `MODIFIED_PENDING_ACCEPTANCE`. A modification must become a revised proposal and pass authorization again.

## Current skeleton

This repository currently implements:

- a machine-readable BA ruleset/profile registry and typed governance contracts;
- FastAPI-derived OpenAPI with generated frontend TypeScript types;
- authenticated presentation APIs for overview, decisions, portfolio, alternatives, news, agents, governance, and weekly summary;
- a server-rendered, story-first Next.js skeleton connected only to those APIs;
- a non-authoritative news-analysis endpoint with redacted provider failures;
- a deterministic quantitative-analysis endpoint with typed technical indicators;
- HTTP-only session authentication without browser password disclosure;
- an Alembic baseline, one-shot Compose migration, dependency-aware readiness, and governed deployment workflows.

The presentation dataset is fixed and always labeled **Illustrative fixture**. It does not imply an Alpaca account, paper order, fill, holding, P&L record, or provider/model call. Full agent orchestration, persistence, portfolio management, ShadowFund valuation, and broker execution remain deferred.

The BA-authorized hackathon window starts Monday Aug 31, 2026 at 09:30 ET, stops new entries after Wednesday Sep 2 at 16:00 ET, and scores total account equity at Thursday Sep 3 close. All positions force-flatten by that scoring point; Friday Sep 4 at 09:30 ET is an outer boundary only. The 14-day baseline hold remains distinct from the four-trading-day hackathon override.

## Technology

| Layer | Baseline |
| --- | --- |
| Web | Next.js 16, React 19, TypeScript, Plus Jakarta Sans, Tailwind, Radix/shadcn primitives |
| API | FastAPI, Python 3.12, Pydantic, typed presentation/contracts |
| Data | PostgreSQL 17, SQLAlchemy 2, Alembic; optional Redis |
| Alpaca | `alpaca-py` 0.44.0 selected for reads; CLI 0.0.13 selected for gated future paper execution |
| Contracts | FastAPI OpenAPI plus generated `openapi-typescript` transport types |
| Operations | Docker Compose, Nginx, GitHub Actions, protected environments |

The initial option envelope is long calls, long puts, and two-leg 1:1 call/put debit spreads. Unsupported or unverified capabilities fail closed.

## Quick start

Prerequisites: Node.js 24, Corepack/pnpm 11.24.0, Python 3.12 with `uv`, and optionally Docker Compose v2.

```bash
corepack enable
cp .env.example .env
pnpm setup
pnpm contracts
pnpm dev
```

Replace the development authentication examples in `.env`. Direct development runs the web app at `http://localhost:3000` and API at `http://localhost:8000`. Keep `EXECUTION_ENABLED=false`, `ALPACA_PAPER=true`, and `ALPACA_LIVE_TRADE=false`.

### Compose

```bash
pnpm docker:up
```

Base Compose defaults to frontend port 3005, backend port 8005, and PostgreSQL port 5439. It runs `alembic upgrade head` once before starting FastAPI. Production publishes Nginx only:

```bash
docker compose -f compose.yml -f compose.production.yml up -d --build
pnpm docker:config
```

## API surface

Unauthenticated orchestration routes:

```text
GET /api/v1/health/live
GET /api/v1/health/ready
POST /api/v1/auth/login
GET /openapi.json
```

Authenticated routes include `/api/v1/auth/me`, `/api/v1/system/status`, `/api/v1/research/news/analyze`, `/api/v1/research/reaction/analyze`, `/api/v1/research/quant/analyze`, and all `/api/v1/presentation/*` endpoints. Login sets an HTTP-only `prism_session` cookie; the response does not expose the token.

## Commands

| Command | Purpose |
| --- | --- |
| `pnpm dev` | Run Next.js on 3000 and FastAPI on 8000. |
| `pnpm contracts` | Regenerate OpenAPI and TypeScript transport types. |
| `pnpm test` | Run frontend and backend tests. |
| `pnpm lint` | Run ESLint and Ruff. |
| `pnpm typecheck` | Run TypeScript and mypy. |
| `pnpm verify` | Run the complete repository quality gate. |
| `pnpm docker:config` | Validate production Compose resolution. |

## Documentation

Start at the [engineering documentation index](docs/README.md). The source authority order is repository invariants -> BA process/register -> AI architecture -> API contracts -> implementation/tests -> explanatory concepts. The [governance traceability matrix](docs/GOVERNANCE_TRACEABILITY.md) maps those layers end to end.

Key documents:

- [Business Rules](docs/BUSINESS_RULES.md) and [AI Profiles](docs/AI_PROFILES.md)
- [AI Agents](docs/AI_AGENTS.md) and [Architecture](docs/ARCHITECTURE.md)
- [Data/API Contracts](docs/DATA_API_CONTRACTS.md)
- [Design](docs/DESIGN.md), [Security](docs/SECURITY.md), and [Docker](docs/DOCKER.md)
- [Project Concept](docs/conceptual/PROJECT_CONCEPT.md) and synchronized `Project_Concept.docx`

Every coding agent begins with [AGENTS.md](AGENTS.md) and the numbered rules under [`.agents/rules/`](.agents/rules/). Vendored Alpaca skills are references; repository safety rules take precedence.
