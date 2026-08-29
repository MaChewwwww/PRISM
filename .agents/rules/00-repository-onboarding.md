# Repository Onboarding

## Start here

1. Read root `AGENTS.md` and this rule set in numeric order.
2. Read `docs/conceptual/PROJECT_CONCEPT.md` for product intent.
3. Read `docs/README.md`, then the architecture, requirements, contracts, security, and subsystem documents relevant to the task.
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

1. User instruction and approved requirements.
2. `AGENTS.md` and `.agents/rules/`.
3. `docs/FRS_NFRS.md`, `docs/ARCHITECTURE.md`, and `docs/DATA_API_CONTRACTS.md`.
4. Executable contracts and tests.
5. Other engineering documents.
6. `docs/conceptual/PROJECT_CONCEPT.md`.
7. External examples and vendored skills.

Resolve contradictions explicitly; do not silently choose the most convenient source.

## First-change checklist

- Confirm the application name is PRISM and that BA thresholds remain pending before adding labels or numbers.
- Confirm the task stays inside paper trading.
- Confirm normal work is on an allowed branch based on `staging`; do not commit directly to `staging` or `main` after bootstrap.
- Find the existing module, contract, fixture, and test before creating a parallel implementation.
- Update generated contracts through the generator.
- Run the relevant checks and update documentation in the same change.
