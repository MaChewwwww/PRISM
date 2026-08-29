# VPS deployment

## Prerequisites

- Maintained Linux VPS with Docker Engine and Compose v2.
- DNS/TLS termination at Nginx or an approved upstream proxy.
- Non-root deploy account with narrowly scoped Docker access.
- Protected, distinct staging and production configuration.
- Alpaca paper credentials only when a later integration requires them; execution stays disabled by default.

## Automated flow

1. A reviewed typed branch merges into `staging` and passes CI.
2. Staging deploys when the repository switch is enabled, or through manual dispatch.
3. A reviewed promotion pull request moves `staging` into `main`.
4. Successful `main` CI triggers the protected production workflow automatically; manual dispatch remains a fallback.
5. The workflow deploys the exact verified revision.
6. Compose runs `alembic upgrade head` as a one-shot dependency.
7. FastAPI readiness validates configuration and database access.
8. The workflow checks `/api/v1/health/ready`; an operator may separately authenticate and inspect `/api/v1/system/status`.

Production publishes only ports 80/443 at the edge. PostgreSQL and Redis have no public host ports. Staging defaults to edge port 3005 and must use a distinct path, project name, database, and secrets.

## Rollback and operations

Rollback redeploys a prior verified revision/image. Migrations must be forward-compatible; destructive recovery needs a separately tested plan. Rollback never deletes audit or execution evidence.

Monitor host capacity, container health, database storage, certificate expiry, provider failure rates, readiness, and kill-switch state. Availability/latency SLOs, backup retention, RPO, and RTO remain unresolved and must be approved before they become operational requirements.
