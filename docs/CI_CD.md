# CI/CD and branch promotion

## Governed flow

```text
typed feature branch -> reviewed pull request -> staging
staging -> reviewed promotion pull request -> main
main CI success -> protected production deployment
```

Direct changes to `staging` and `main` are prohibited outside the documented repository bootstrap. Branch policy validates typed branches into `staging` and permits only `staging` into `main`.

## Continuous integration

Pull requests and pushes targeting `staging` or `main` run repository governance, vendored-skill provenance, formatting, linting, type checks, unit tests, contract regeneration, frontend/backend builds, dependency audits, secret scanning, and container scans. Paper integration tests are opt-in and normal CI never submits an order or contacts Alpaca/LLM providers.

## Deployment automation

`.github/workflows/deploy-staging.yml` deploys a successful `staging` push only when `STAGING_DEPLOY_ENABLED=true`; manual dispatch is also available. `.github/workflows/deploy.yml` automatically deploys a successful `main` push and supports manual dispatch as a fallback. Both verify revision ancestry and deploy an exact revision over SSH.

The remote Compose command runs the one-shot Alembic migration service before backend readiness. Production deployment smoke checks use unauthenticated `/api/v1/health/ready` through the numeric `PRISM_HTTP_PORT` configured in the protected server `.env`, rather than a host TLS redirect; authenticated `/api/v1/system/status` is an operator check and requires a valid session.

Staging and production require distinct VPS paths, Compose project names, secrets, authentication values, Alpaca paper credentials when configured, and databases. Neither environment may enable live trading. Execution remains disabled unless separately reviewed and authorized. Autonomous trading is production-only and its schedule bounds are validated at startup; staging rejects `AUTONOMOUS_TRADING_ENABLED=true`. Staging historical backtests are manual, explicitly enabled, non-executing jobs and must not be added as a CI order test.

## Rollback

Rollback redeploys a previously verified revision or image digest. Do not rewrite integration history or delete audit data. Database migrations must be forward-compatible or accompanied by a separately tested recovery procedure.
