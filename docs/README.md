# PRISM engineering documentation

**One signal. Multiple perspectives. Better decisions.**

This index defines how PRISM documentation is interpreted. Product behavior is paper-only, AI-assisted, deterministically governed, and audit-oriented.

## Authority chain

When artifacts disagree, resolve them in this order:

1. Repository invariants in `AGENTS.md` and `.agents/rules/`.
2. BA-owned process and numerical authority in [FRS/NFRS](FRS_NFRS.md), [Business Rules](BUSINESS_RULES.md), [AI Profiles](AI_PROFILES.md), and the machine-readable `backend/app/rules/authorized_baseline.v1.json` register.
3. AI Engineer-owned topology and boundaries in [AI Agents](AI_AGENTS.md) and [Architecture](ARCHITECTURE.md).
4. [Data and API Contracts](DATA_API_CONTRACTS.md) and generated OpenAPI artifacts.
5. Implementation and automated tests.
6. Explanatory concept documents: [Project Concept](conceptual/PROJECT_CONCEPT.md) and `conceptual/Project_Concept.docx`.
7. External examples and vendored skills.

Do not silently reconcile a conflict. Update every affected downstream artifact in the same change.

## Start here

1. [Governance Traceability](GOVERNANCE_TRACEABILITY.md)
2. [Functional and Non-Functional Requirements](FRS_NFRS.md)
3. [Business Rules](BUSINESS_RULES.md)
4. [AI Agents](AI_AGENTS.md) and [AI Profiles](AI_PROFILES.md)
5. [Architecture](ARCHITECTURE.md)
6. [Data and API Contracts](DATA_API_CONTRACTS.md)
7. [Security](SECURITY.md)
8. [Implementation Plan](IMPLEMENTATION_PLAN.md)

## Domain and AI

- [ShadowFund](SHADOWFUND.md)
- [Alpaca Integration](ALPACA_INTEGRATION.md)
- [Market Tracker](MARKET_TRACKER.md)

## Platform, design, and operations

- [Design System and Visual Authority](DESIGN.md)
- [Technology Stack](TECH_STACK.md)
- [CI/CD and Branch Promotion](CI_CD.md)
- [Docker](DOCKER.md)
- [VPS Deployment](VPS_DEPLOYMENT.md)
- [Staging Server Maintenance Cheatsheet](deployment/staging-server-maintenance-cheatsheet.md)
- [Single Azure VM Runbook](deployment/single-azure-vm.md)
- [Security](SECURITY.md)

## Status vocabulary

- **Authorized**: BA-approved and represented in the versioned register.
- **Implemented**: executable in the current skeleton and covered by checks.
- **Illustrative**: fixed demonstration data; no provider, account, order, or fill is implied.
- **Deferred**: intentionally outside this skeleton pass.
- **Unresolved**: an owner decision is required; engineering must not guess. Current unresolved values include SLOs and backup RPO/RTO.

Per-rule outcomes are `PASS`, `MODIFY`, or `FAIL`. Aggregate authorization outcomes are `APPROVE`, `REJECT`, or `MODIFIED_PENDING_ACCEPTANCE`. Only `APPROVE` may proceed toward execution. An accepted modification creates a revised proposal that must pass authorization again.
