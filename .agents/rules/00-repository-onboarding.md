# Repository Onboarding

## Start here

1. Read root `AGENTS.md` and this rule set in numeric order.
2. Read `docs/README.md` and its authority chain.
3. Read the BA requirements/register, architecture, contracts, security, subsystem, and explanatory concept documents relevant to the task.
4. Inspect `git status`; preserve unrelated work and never discard user changes.
5. Identify the affected trust boundary and its tests before editing.

## Repository map

- `frontend/`: Next.js operator interface. It consumes backend APIs only.
- `backend/`: FastAPI modular monolith, domain contracts, integrations, rules, and execution gate.
- `infra/`: Nginx and deployment configuration.
- `docs/`: authoritative engineering documentation; conceptual sources remain under `docs/conceptual/`.
- `.agents/rules/`: repository-owned agent instructions.
- `.agents/skills/`: repository-local workflows such as governed GitHub PR creation.
- `.agents/skills/vendor/`: pinned third-party skills with provenance; do not edit them locally.
- `scripts/`: cross-platform repository maintenance tooling.

## Source-of-truth order

1. User instruction and repository invariants in `AGENTS.md` and `.agents/rules/`.
2. BA-owned process and numerical authority in `docs/FRS_NFRS.md`, `docs/BUSINESS_RULES.md`, `docs/AI_PROFILES.md`, and `backend/app/rules/authorized_baseline.v1.json`.
3. AI Engineer-owned topology and boundaries in `docs/AI_AGENTS.md` and `docs/ARCHITECTURE.md`.
4. `docs/DATA_API_CONTRACTS.md` and generated OpenAPI contracts.
5. Implementation and tests.
6. Explanatory documents, including `docs/conceptual/PROJECT_CONCEPT.md` and its DOCX counterpart.
7. External examples and vendored skills.

Resolve contradictions explicitly; do not silently choose the most convenient source.

## First-change checklist

- Confirm the application name is PRISM and consume authorized values, including any fixed hackathon window, from the versioned registry; keep only values absent from the register unresolved.
- Confirm the task stays inside paper trading.
- Confirm normal work is on an allowed branch based on `staging`; do not commit directly to `staging` or `main` after bootstrap.
- Find the existing module, contract, fixture, and test before creating a parallel implementation.
- Update generated contracts through the generator.
- Run the relevant checks and update documentation in the same change.
