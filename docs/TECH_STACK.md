# PRISM — Technology Stack

**One signal. Multiple perspectives. Better decisions.**

| Area | Selection | Rationale |
| --- | --- | --- |
| Web | Next.js 16 App Router, React 19, TypeScript | Server-capable application shell with typed UI boundaries |
| UI | Tailwind CSS, shadcn/Radix primitives, custom product components | Accessible primitives without surrendering product identity |
| Web testing | Vitest, Testing Library | Fast component and contract-state tests |
| API | Python 3.12, FastAPI, Pydantic | Typed validation and OpenAPI generation |
| Persistence | PostgreSQL 17, SQLAlchemy 2, Alembic | Transactional audit and domain storage |
| Cache | Redis, optional | Ephemeral coordination only; never execution authority |
| Alpaca | `alpaca-py` 0.44.0, Alpaca CLI 0.0.13 | Typed reads and isolated gated execution |
| AI / LLM | Featherless AI, Anthropic, Gemini, Ollama, DeepSeek, OpenAI | Pluggable adapter architecture with structured JSON Schema output |
| Python tooling | uv, Ruff, mypy, pytest | Reproducible environment and quality gates |
| JS tooling | Node 24, pnpm 11.24.0, ESLint | Locked monorepo workflow |
| Runtime | Docker Compose, Nginx | Reproducible single-VPS deployment |
| CI/CD | GitHub Actions, protected staging/production environments | Feature-to-staging verification, isolated staging delivery, and deliberate production promotion |

Versions are locked in manifests, lockfiles, and image tags. Renovation is a reviewed change, not an automatic production mutation. AI adapters conform to the provider-neutral interfaces described in [AI_AGENTS.md](AI_AGENTS.md).
