<div align="center">

# PRISM

**One signal. Multiple perspectives. Better decisions.**

*A paper-only, auditable multi-agent trading intelligence platform governed by deterministic rules.*

[![CI](https://github.com/MaChewwwww/Alpaca_AI_Hackaton/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/MaChewwwww/Alpaca_AI_Hackaton/actions/workflows/ci.yml)
[![Branch policy](https://github.com/MaChewwwww/Alpaca_AI_Hackaton/actions/workflows/branch-policy.yml/badge.svg?branch=main)](https://github.com/MaChewwwww/Alpaca_AI_Hackaton/actions/workflows/branch-policy.yml)
[![Paper trading only](https://img.shields.io/badge/trading-paper--only-0f766e.svg)](docs/SECURITY.md)

</div>

> [!IMPORTANT]
> This repository is a governed paper-trading platform, not a live trading product. Live trading is prohibited, execution is disabled by default, and every order path must pass deterministic authorization. Numerical business-rule thresholds remain pending BA sign-off.

## The PRISM Concept

**PRISM** is inspired by how an optical prism takes a single beam of light and separates it into different wavelengths, revealing what was previously unseen.

In the same way, **PRISM takes a single market signal and autonomously breaks it down into multiple perspectives**. Its AI agents analyze the catalyst, market reaction, historical patterns, potential strategies, risks, and alternative outcomes—while deterministic rules govern whether a trade can actually proceed.

The prism represents **PRISM’s autonomous intelligence**: rather than relying on one interpretation or one AI decision, it continuously examines the same signal from different angles, challenges its own conclusions, and learns from what actually happened versus what could have happened through ShadowFund counterfactuals.

> **One signal → Autonomous perspectives → Governed decisions → Clearer outcomes**

## The Decision Pipeline

Market events can move faster than a human can assemble context, validate a thesis, and challenge its risks. PRISM turns that workflow into a traceable decision pipeline:

```text
market + news
     │
     ▼
research report ──► trade proposal ──► risk critique ──► deterministic rules
                                                               │
                              rejected / modified ◄───────────┤
                                                               ▼
                                                     authorized paper order
                                                               │
                                                               ▼
                                                    audit trail + ShadowFund
```

AI supplies research, proposals, critiques, and recommendations. Deterministic services own business rules and authorization. The frontend never talks to Alpaca directly, and no agent can place an order on its own.

## What is in this repository

| Layer      | Current baseline                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------- |
| Web        | Next.js 16 App Router, React 19, TypeScript, Tailwind, shadcn/Radix primitives, and custom product components |
| API        | FastAPI modular monolith with Pydantic contracts, structured logging, and explicit domain boundaries          |
| Data       | PostgreSQL 17 as the durable authority; Redis is optional coordination/cache                                  |
| Alpaca     | `alpaca-py` for typed read operations and Alpaca CLI `v0.0.13` behind a gated paper-execution adapter         |
| AI / LLM   | Pluggable provider configuration for Featherless AI, Anthropic, Gemini, Ollama, DeepSeek, and OpenAI |
| Contracts  | Versioned OpenAPI/JSON Schema plus generated TypeScript types                                                 |
| Operations | Docker Compose, Nginx production topology, health checks, GitHub Actions, and protected environments          |
| Governance | Agent rules, vendored Alpaca skills with checksums, failure-path tests, secret scanning, and branch policy    |

### Scope of the first option track

The initial strategy surface is deliberately narrow: long calls, long puts, and two-leg call/put debit spreads. Unsupported account levels, inactive contracts, uncovered shorts, equity-option combinations, extended-hours options, and non-`day` option orders fail closed. Official Alpaca requirements are rechecked at hackathon kickoff before scope changes.

## Project status

**Phase 0 — governed foundation** is bootstrapped. The repository currently delivers the architecture, contracts, safety gates, custom shell, Docker topology, CI/CD workflows, and documentation needed for subsequent domain phases.

| Next phase                | Outcome                                                                                         |
| ------------------------- | ----------------------------------------------------------------------------------------------- |
| 1 · Research              | Normalized market/news ingestion and `ResearchReport` fixtures                                  |
| 2 · Proposal, risk, rules | Structured proposals, deterministic evaluation, profiles, and operator review                   |
| 3 · Paper execution       | Durable authorization, CLI submission, kill switch, reconciliation, and paper integration tests |
| 4 · ShadowFund            | Immutable counterfactual branches and comparable evaluation metrics                             |
| 5 · Production readiness  | Authentication, backups, observability, threat modeling, and protected rollout                  |

Production authentication, automatic order execution, finalized dashboard screens, and live brokerage execution are outside the current phase.

## Quick start

### Prerequisites

- Node.js 24 with Corepack and pnpm 11.24.0
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Docker with Compose v2
- Optional Alpaca paper credentials for read-only account verification

### Run locally

```bash
git clone https://github.com/MaChewwwww/Alpaca_AI_Hackaton.git
cd Alpaca_AI_Hackaton

corepack enable
cp .env.example .env                # PowerShell: Copy-Item .env.example .env
pnpm setup
pnpm contracts
pnpm dev
```

The web app is available at `http://localhost:3000` and the API at `http://localhost:8000`.

Keep `EXECUTION_ENABLED=false`, `ALPACA_PAPER=true`, and `ALPACA_LIVE_TRADE=false` in local environments. Credentials are optional for the shell and status endpoint; never commit `.env` or credential-bearing MCP configuration.

### Run the Compose stack

```bash
cp .env.example .env                # PowerShell: Copy-Item .env.example .env
pnpm docker:up
```

The base stack exposes the local web/API/database ports for development. The production override adds Nginx and keeps PostgreSQL and Redis on private networks:

```bash
docker compose -f compose.yml -f compose.production.yml up --build -d
```

Validate the resolved production topology without starting containers:

```bash
pnpm docker:config
```

## Useful commands

| Command                | Purpose                                                            |
| ---------------------- | ------------------------------------------------------------------ |
| `pnpm dev`             | Start the Next.js and FastAPI development servers.                 |
| `pnpm setup`           | Install the pnpm workspace and synchronize the Python environment. |
| `pnpm contracts`       | Regenerate the OpenAPI bundle and TypeScript API types.            |
| `pnpm contracts:check` | Regenerate contracts and fail if committed output changes.         |
| `pnpm test`            | Run frontend Vitest and backend pytest suites.                     |
| `pnpm lint`            | Run ESLint and Ruff.                                               |
| `pnpm typecheck`       | Run TypeScript and mypy checks.                                    |
| `pnpm verify`          | Run the complete repository quality gate.                          |
| `pnpm docker:config`   | Validate the production Compose configuration.                     |
| `pnpm docker:down`     | Stop and remove the local Compose stack.                           |

## Redacted status API

The initial public surface is intentionally small and safe to inspect without provider credentials:

```text
GET /api/v1/health/live
GET /api/v1/health/ready
GET /api/v1/system/status
GET /openapi.json
```

System status reports readiness, paper mode, CLI availability/version, credential-presence booleans, account verification state, and supported options level. It never returns keys, account identifiers, buying power, positions, or raw provider errors.

## Architecture and safety

The backend is a modular monolith. Data and AI providers sit behind adapters; domain contracts and deterministic policies remain provider-neutral.

```text
Next.js shell
     │  redacted API responses only
     ▼
FastAPI routes → application services → contracts + deterministic rules
                                      │
                                      ├─ Alpaca read gateway (`alpaca-py`)
                                      ├─ gated paper execution (CLI `0.0.13`)
                                      ├─ PostgreSQL audit/state
                                      └─ ShadowFund counterfactuals
```

Execution requires all of the following immediately before submission: paper endpoint, enabled execution flag, active ruleset, fresh verified account state, tradable contracts, sufficient options level, an unexpired accepted authorization, and a matching proposal digest. Ambiguous submissions reconcile by `client_order_id`; they are never blindly resubmitted.

## Documentation map

Start with the [engineering documentation index](docs/README.md), then choose the track you need:

| Need                     | Documents                                                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Understand the system    | [Architecture](docs/ARCHITECTURE.md), [Tech stack](docs/TECH_STACK.md), [Implementation plan](docs/IMPLEMENTATION_PLAN.md)                 |
| Work with AI and rules   | [AI agents](docs/AI_AGENTS.md), [AI profiles](docs/AI_PROFILES.md), [Business rules](docs/BUSINESS_RULES.md), [FRS/NFRS](docs/FRS_NFRS.md) |
| Integrate Alpaca safely  | [Alpaca integration](docs/ALPACA_INTEGRATION.md), [Data/API contracts](docs/DATA_API_CONTRACTS.md), [Security](docs/SECURITY.md)           |
| Run and deploy           | [Docker](docs/DOCKER.md), [CI/CD](docs/CI_CD.md), [VPS deployment](docs/VPS_DEPLOYMENT.md)                                                 |
| Evaluate alternatives    | [ShadowFund](docs/SHADOWFUND.md)                                                                                                           |
| Product design authority | [`DESIGN.md`](docs/DESIGN.md) (Design system & visual authority)                                                          |

Conceptual intent is preserved in [`docs/conceptual/PROJECT_CONCEPT.md`](docs/conceptual/PROJECT_CONCEPT.md) and the source [`Project_Concept.docx`](docs/conceptual/Project_Concept.docx). Engineering Markdown is the source of truth for implementation.

## Agentic development

Every coding agent starts with [`AGENTS.md`](AGENTS.md), which points to the numbered rules under [`.agents/rules/`](.agents/rules/). Those rules cover onboarding, architecture, Alpaca documentation checks, trading safety, frontend composition, testing, documentation, and commits/PRs.

The governed branch path is:

```text
feature/* · fix/* · chore/* · docs/* · refactor/* · test/* · ci/*
                                      │
                                      ▼ pull request
                                   staging
                                      │
                                      ▼ reviewed promotion pull request
                                    main
```

Use the repository-local [`github-pr` skill](.agents/skills/github-pr/SKILL.md) to prepare a commit and explicit-base PR. It never merges, force-pushes, or bypasses required checks.

## Hackathon and official references

- [Alpaca AI Trading Agents Hackathon](https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon)
- [Alpaca getting started](https://docs.alpaca.markets/us/docs/getting-started)
- [Alpaca Trading API](https://docs.alpaca.markets/us/docs/getting-started-with-trading-api)
- [Alpaca market data](https://docs.alpaca.markets/us/docs/getting-started-with-alpaca-market-data)
- [Alpaca SDKs and tools](https://docs.alpaca.markets/us/docs/sdks-and-tools)

Before changing provider behavior, consult the official Markdown documentation, `llms.txt`, OpenAPI schemas, installed CLI help/schema, SDK release notes, and the locked versions described in [the Alpaca integration guide](docs/ALPACA_INTEGRATION.md).

## Third-party provenance

Vendored Alpaca skills retain their upstream license and provenance under [`.agents/skills/vendor/alpaca/`](.agents/skills/vendor/alpaca/). The application license will be declared before external distribution.
