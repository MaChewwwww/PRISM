# Docker

## Local stack

Copy `.env.example` to an untracked `.env`, replace the development-only authentication values, and run `pnpm docker:up`. Direct development through `pnpm dev` uses frontend port 3000 and backend port 8000. The base Compose stack defaults to frontend port 3005, backend port 8005, PostgreSQL port 5439, and optional Redis port 6385.

Compose starts PostgreSQL, runs `alembic upgrade head` in a one-shot `migrate` service, then starts FastAPI after migration succeeds. The frontend starts after backend readiness. FastAPI startup does not create tables. The frontend receives only its internal API URL, environment name, and server-side authentication values; Alpaca and LLM credentials remain confined to backend services.

Readiness validates required configuration and database connectivity. When autonomous mode is enabled it also requires the pinned CLI, a verified paper account, and Level 3 options capability. Liveness only proves that the process can answer. `/api/v1/system/status` is authenticated and is not a Compose health-check target. Autonomous paper-trading variables (`AUTONOMOUS_TRADING_ENABLED`, `AUTONOMOUS_TRADING_START_AT`, and `AUTONOMOUS_TRADING_END_AT`) are server-only configuration; they default to disabled. The shared worker uses identical staging/production behavior and remains fail-closed with `NO_TRADE` until all gates pass.

## Production override

```bash
docker compose -f compose.yml -f compose.production.yml up -d --build
```

The production override publishes only Nginx on `{PRISM_HTTP_PORT:-80}`. Application and data services use private networks, and PostgreSQL/Redis have no host ports. The backend also joins an unexposed egress network for its required outbound HTTPS calls to Alpaca and other configured research providers; this does not publish a backend port. Staging adds `compose.staging.yml` and publishes Nginx on `{STAGING_HTTP_PORT:-3005}` under a distinct Compose project.

Validate the resolved production topology with `pnpm docker:config`. Execution remains disabled by default and fails closed without valid paper configuration, an active ruleset, and a current authorization.

Never bake environment files, credentials, local data, build caches, or MCP configuration into images. Scheduled execution remains paper-only and requires the deterministic authorization gate; production schedules must stay inside the BA-authorized window.
